"""Publish a validated tag pipeline to the authoritative GitLab Release.

The publisher is deliberately fail-closed. Generic Package files are verified
before a Release is created; the Release is the final publication mutation.
The dry-run path performs read-only API calls only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


PROJECT_ID = "1"
PROJECT_PATH = "root/agent"
PACKAGE_NAME = "mt5-agent"
SEMVER_TAG = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class PublishError(RuntimeError):
    """Safe, non-secret-bearing publication error."""


class APIRequestError(PublishError):
    """API error with an explicit retry classification."""

    def __init__(self, message: str, *, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


class _StripJobTokenRedirectHeaders(HTTPRedirectHandler):
    """Never forward the project job token to redirected object storage."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        old = urlsplit(request.full_url)
        new = urlsplit(new_url)
        if redirected is not None and (new.scheme.lower(), new.netloc.lower()) != (old.scheme.lower(), old.netloc.lower()):
            for collection in (redirected.headers, redirected.unredirected_hdrs):
                for name in tuple(collection):
                    if name.lower() in ("job-token", "authorization", "private-token"):
                        del collection[name]
        return redirected


@dataclass(frozen=True)
class Asset:
    name: str
    data: bytes
    sha256: str

    @property
    def size(self) -> int:
        return len(self.data)


def _need(env: dict[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise PublishError(f"Missing required CI variable: {name}")
    return value


def validate_environment(env: dict[str, str]) -> dict[str, str]:
    required = ("CI_COMMIT_TAG", "CI_COMMIT_SHA", "CI_PIPELINE_ID", "CI_PROJECT_ID",
                "CI_PROJECT_PATH", "CI_API_V4_URL", "CI_JOB_TOKEN", "CI_COMMIT_REF_PROTECTED",
                "CI_PIPELINE_SOURCE", "GITLAB_USER_ID", "MT5_RELEASE_OWNER_USER_ID")
    values = {key: _need(env, key) for key in required}
    tag_match = SEMVER_TAG.fullmatch(values["CI_COMMIT_TAG"])
    if not tag_match:
        raise PublishError("Only stable vMAJOR.MINOR.PATCH tags may be published")
    if not COMMIT.fullmatch(values["CI_COMMIT_SHA"]):
        raise PublishError("CI_COMMIT_SHA is not a full commit SHA")
    if (not values["CI_PIPELINE_ID"].isdigit() or not values["GITLAB_USER_ID"].isdigit() or
            not values["MT5_RELEASE_OWNER_USER_ID"].isdigit()):
        raise PublishError("Pipeline and tag actor identifiers must be numeric")
    if values["GITLAB_USER_ID"] == values["MT5_RELEASE_OWNER_USER_ID"]:
        raise PublishError("The release owner must be distinct from the protected-tag creator")
    if values["CI_PROJECT_ID"] != PROJECT_ID or values["CI_PROJECT_PATH"] != PROJECT_PATH:
        raise PublishError("Publisher is configured for an unexpected GitLab project")
    if values["CI_COMMIT_REF_PROTECTED"] != "true":
        raise PublishError("Release tag is not protected")
    if values["CI_PIPELINE_SOURCE"] != "push":
        raise PublishError("Release publication requires the protected tag push pipeline")
    parsed = urlsplit(values["CI_API_V4_URL"])
    if (parsed.scheme != "https" or parsed.hostname != "gitlab.local" or
            parsed.username or parsed.password or parsed.query or parsed.fragment or
            parsed.path.rstrip("/") != "/api/v4"):
        raise PublishError("CI_API_V4_URL must be this project's HTTPS GitLab API")
    values["version"] = ".".join(tag_match.groups())
    return values


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        result = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise PublishError(f"Missing or invalid {label}") from None
    if not isinstance(result, dict):
        raise PublishError(f"Invalid {label} structure")
    return result


def _text(path: Path, label: str) -> str:
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise PublishError(f"Missing or invalid {label}") from None
    if not value.strip():
        raise PublishError(f"{label} is empty")
    return value


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return value.endswith("Z") or "+" in value[10:]


def validate_local(env: dict[str, str], root: Path) -> tuple[list[Asset], dict[str, Any]]:
    tag, sha, pipeline, version = (env[k] for k in ("CI_COMMIT_TAG", "CI_COMMIT_SHA", "CI_PIPELINE_ID", "version"))
    exe_name = f"MT5Agent-{tag}.exe"
    try:
        source_version = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']\s*$',
                                   (root / "agent/__init__.py").read_text(encoding="utf-8"))
    except OSError:
        source_version = None
    if not source_version or source_version.group(1) != version:
        raise PublishError("Release tag does not match the version in the tested source")
    exe_path = root / "dist" / exe_name
    build = _read_json(root / "reports/build.json", "build receipt")
    invalid = _read_json(root / "reports/invalid-configuration.json", "invalid-configuration receipt")
    control = _read_json(root / "reports/control-plane.json", "control-plane receipt")
    runtime = _read_json(root / "reports/mt5-runtime.json", "MT5 runtime receipt")
    release = _read_json(root / "reports/release-evidence.json", "release evidence")
    try:
        data = exe_path.read_bytes()
    except OSError:
        raise PublishError("The validated executable is missing") from None
    digest = hashlib.sha256(data).hexdigest()
    common = {"schema_version": "1", "pipeline_id": pipeline, "commit_sha": sha,
              "candidate_version": version, "candidate_filename": exe_name, "candidate_sha256": digest}
    for label, receipt in (("build", build), ("control-plane", control), ("MT5 runtime", runtime)):
        for key, expected in common.items():
            if receipt.get(key) != expected:
                raise PublishError(f"{label} receipt has inconsistent {key}")
    for key, expected in common.items():
        if invalid.get(key) != expected:
            raise PublishError(f"invalid-configuration receipt has inconsistent {key}")
    if (invalid.get("status") != "PASS" or invalid.get("test") != "invalid-configuration" or
            invalid.get("expected_exit") != 2 or invalid.get("actual_exit") != 2):
        raise PublishError("Invalid-configuration gate evidence is incomplete or failed")
    try:
        checksum = (root / "sha256.txt").read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError):
        raise PublishError("Package checksum receipt is missing") from None
    if checksum != f"SHA256={digest}":
        raise PublishError("Package checksum receipt does not match the validated executable")
    if build.get("source_commit") != sha or build.get("candidate_size") != len(data):
        raise PublishError("Build receipt does not match executable size or source commit")
    if (build.get("metatrader5_present_in_build_environment") is not False or
            build.get("numpy_present_in_build_environment") is not False or
            build.get("archive_inspection_success") is not True or
            build.get("archive_forbidden_module_matches") != []):
        raise PublishError("Build provenance or clean-archive checks failed")
    if (control.get("status") != "PASS" or control.get("test") != "control-plane-degraded-startup" or
            control.get("health") != "AGENT_RUNNING_DEGRADED" or control.get("worker_available") is not False or
            control.get("runtime_state") not in ("RUNTIME_CONFIGURATION_UNAVAILABLE", "RUNTIME_UNAVAILABLE")):
        raise PublishError("Current-pipeline control-plane evidence is incomplete or failed")
    worker, terminal, agent = runtime.get("worker"), runtime.get("terminal"), runtime.get("agent")
    if not all(isinstance(item, dict) for item in (worker, terminal, agent)):
        raise PublishError("Current-pipeline runtime identity/session evidence is incomplete")
    if (runtime.get("status") != "PASS" or runtime.get("candidate_sha256_after") != digest or
            runtime.get("runtime_state") != "MT5_CONNECTED" or
            runtime.get("final_health") != "AGENT_RUNNING + MT5_CONNECTED" or
            runtime.get("symbols_total_success") is not True or runtime.get("terminal_version_success") is not True or
            runtime.get("account_information_success") is not True or
            type(runtime.get("account_information_field_count")) is not int or
            runtime.get("account_information_field_count", -1) < 0 or agent.get("session_id") != 0 or
            worker.get("protocol_version") != "1" or type(worker.get("session_id")) is not int or
            worker.get("session_id", 0) <= 0 or terminal.get("session_id") != worker.get("session_id") or
            terminal.get("principal") != worker.get("principal") or terminal.get("sid") != worker.get("sid")):
        raise PublishError("Current-pipeline MT5 integration evidence is incomplete or inconsistent")
    for key, expected in common.items():
        if release.get(key) != expected:
            raise PublishError(f"Release evidence has inconsistent {key}")
    if (release.get("release_eligible") is not True or release.get("build_once") is not True or
            release.get("post_smoke_rebuild") is not False or release.get("control_plane_gate") != "PASS" or
            release.get("mt5_runtime_gate") != "PASS"):
        raise PublishError("Release eligibility/build-once evidence failed")
    notes_path = root / "docs/releases" / f"{tag}-release-notes.md"
    notes = _text(notes_path, "versioned release notes")
    auth_path = root / "docs/releases" / f"{tag}-authorization.json"
    approval = _read_json(auth_path, "release authorization record")
    owner_id = int(env["MT5_RELEASE_OWNER_USER_ID"])
    approver_id = approval.get("approved_by_user_id")
    if (approval.get("schema_version") != 1 or approval.get("tag") != tag or
            approval.get("commit_sha") != sha or type(approver_id) is not int or
            approver_id != owner_id or approver_id == int(env["GITLAB_USER_ID"]) or
            not _valid_timestamp(approval.get("approved_at")) or
            not isinstance(approval.get("approval_reference"), str) or
            not re.fullmatch(r"https://gitlab\.local/root/agent/-/merge_requests/\d+", approval["approval_reference"])):
        raise PublishError("Release authorization must match the tag/commit and the configured independent Release Owner")
    risks = approval.get("release_blocking_risks")
    if not isinstance(risks, list) or not any(isinstance(risk, dict) and risk.get("id") == "KI-009" for risk in risks):
        raise PublishError("Authorization must explicitly disposition the known release-blocking risk KI-009")
    for risk in risks:
        if (not isinstance(risk, dict) or not isinstance(risk.get("id"), str) or
                risk.get("disposition") not in ("accepted", "resolved") or
                not isinstance(risk.get("reference"), str) or
                not re.fullmatch(r"https://gitlab\.local/root/agent/-/(?:issues|merge_requests)/\d+", risk["reference"])):
            raise PublishError("Every release-blocking risk needs a traceable accepted/resolved disposition")
        if (type(risk.get("approved_by_user_id")) is not int or
                risk["approved_by_user_id"] != owner_id or
                risk["approved_by_user_id"] == int(env["GITLAB_USER_ID"]) or
                not _valid_timestamp(risk.get("approved_at")) or
                risk.get("approval_reference") != approval["approval_reference"]):
            raise PublishError("Every release-blocking risk requires independent Release Owner approval in the referenced MR")
    if tag not in notes.splitlines()[0]:
        raise PublishError("Versioned release notes must identify their exact release tag in the first line")
    acceptance = (
        "# Release acceptance\n\n"
        f"- Tag: `{tag}`\n- Version: `{version}`\n- Commit: `{sha}`\n"
        f"- GitLab pipeline ID: `{pipeline}`\n"
        f"- Validated executable: `{exe_name}` ({len(data)} bytes)\n"
        f"- SHA-256: `{digest}`\n- Linux source tests: passed (required pipeline dependency)\n"
        "- Windows tests: passed (required pipeline dependency)\n"
        "- Windows build: passed; clean archive and no-MT5 build checks passed\n"
        "- Control-plane smoke: passed; Agent remained running in degraded no-Worker mode\n"
        "- Interactive MT5 integration: passed; connected state and safe read checks passed\n"
        "- Build-once invariant: passed; the tested executable was packaged without rebuilding\n"
        f"- Risk decision record: `{auth_path.relative_to(root).as_posix()}`\n"
    )
    assets_data: list[tuple[str, bytes]] = [(exe_name, data), ("release-notes.md", notes.encode("utf-8")),
                                             ("release-acceptance.md", acceptance.encode("utf-8"))]
    sums = "".join(f"{hashlib.sha256(content).hexdigest()}  {name}\n" for name, content in assets_data).encode()
    assets_data.insert(1, ("SHA256SUMS.txt", sums))
    assets = [Asset(name, content, hashlib.sha256(content).hexdigest()) for name, content in assets_data]
    # Ensure the executable itself has exactly the package evidence digest.
    assert assets[0].sha256 == digest
    return assets, approval


class GitLabAPI:
    def __init__(self, api: str, project_id: str, token: str, *, timeout: int = 30, retries: int = 4):
        self.base = api.rstrip("/") + f"/projects/{quote(project_id, safe='')}"
        self.token = token
        self.timeout = timeout
        self.retries = retries
        self.opener = build_opener(_StripJobTokenRedirectHeaders())

    def request(self, method: str, path: str, data: bytes | None = None,
                content_type: str | None = None) -> tuple[int, dict[str, str], bytes]:
        url = self.base + path
        # Only GET is blindly retried. A timed-out upload may already have
        # succeeded; a later job retry re-reads the Registry before acting.
        attempts = self.retries if method == "GET" else 1
        for attempt in range(attempts):
            headers = {"JOB-TOKEN": self.token, "Accept": "application/json"}
            if content_type:
                headers["Content-Type"] = content_type
            req = Request(url, data=data, headers=headers, method=method)
            try:
                with self.opener.open(req, timeout=self.timeout) as response:
                    return response.status, dict(response.headers.items()), response.read()
            except HTTPError as exc:
                retryable = exc.code in (408, 429, 500, 502, 503, 504)
                if retryable and attempt + 1 < attempts:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise APIRequestError(
                    f"GitLab API returned HTTP {exc.code} for {method} {urlsplit(url).path}",
                    retryable=retryable) from None
            except (URLError, TimeoutError, OSError):
                if attempt + 1 < attempts:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise APIRequestError(f"GitLab API network request failed after bounded retries: {method}",
                                      retryable=True) from None
        raise PublishError("GitLab API request failed after bounded retries")

    def json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        _, _, content = self.request(method, path, body, "application/json" if body is not None else None)
        try:
            return json.loads(content.decode("utf-8")) if content else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise PublishError("GitLab API returned invalid JSON") from None

    def json_pages(self, path: str) -> list[dict[str, Any]]:
        """Read a complete paginated list, with a hard page bound."""
        separator = "&" if "?" in path else "?"
        page = 1
        output: list[dict[str, Any]] = []
        while page <= 1000:
            _, headers, body = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            try:
                values = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise PublishError("GitLab API returned invalid JSON") from None
            if not isinstance(values, list) or any(not isinstance(item, dict) for item in values):
                raise PublishError("GitLab API returned an invalid paginated list")
            output.extend(values)
            response_headers = {key.lower(): value for key, value in headers.items()}
            next_page = response_headers.get("x-next-page", "").strip()
            if next_page:
                try:
                    page = int(next_page)
                except ValueError:
                    raise PublishError("GitLab API returned an invalid pagination cursor") from None
                if page <= 0:
                    raise PublishError("GitLab API returned an invalid pagination cursor")
            elif len(values) == 100:
                page += 1
            else:
                return output
        raise PublishError("GitLab API pagination exceeded the safety bound")

    def assert_tag_and_main(self, tag: str, sha: str) -> None:
        tag_data = self.json("GET", f"/repository/tags/{quote(tag, safe='')}")
        commit_data = tag_data.get("commit") if isinstance(tag_data, dict) else None
        if not isinstance(commit_data, dict) or commit_data.get("id") != sha:
            raise PublishError("Protected tag does not resolve to CI_COMMIT_SHA")
        # GitLab 19.4 commit refs endpoint reports branches containing this commit.
        refs = self.json_pages(f"/repository/commits/{sha}/refs?type=branch")
        if not any(item.get("name") == "main" for item in refs):
            raise PublishError("Release commit is not reachable from protected main")

    def assert_merged_authorization_mr(self, reference: str) -> None:
        match = re.fullmatch(r"https://gitlab\.local/root/agent/-/merge_requests/(\d+)", reference)
        if not match:
            raise PublishError("Release authorization must reference a project merge request")
        approval_mr = self.json("GET", f"/merge_requests/{match.group(1)}")
        if (not isinstance(approval_mr, dict) or approval_mr.get("state") != "merged" or
                approval_mr.get("target_branch") != "main"):
            raise PublishError("Release authorization merge request is not merged into main")

    def package_versions(self, version: str) -> list[dict[str, Any]]:
        query = urlencode({"package_type": "generic", "package_name": PACKAGE_NAME,
                           "package_version": version})
        result = self.json_pages(f"/packages?{query}")
        matches = [item for item in result if item.get("name") == PACKAGE_NAME and
                   item.get("version") == version and item.get("package_type") == "generic"]
        if any(type(item.get("id")) is not int or item["id"] <= 0 for item in matches):
            raise PublishError("GitLab package inventory has an invalid package ID")
        return matches

    def package_files(self, package_id: int) -> dict[str, dict[str, Any]]:
        result = self.json_pages(f"/packages/{package_id}/package_files")
        files: dict[str, dict[str, Any]] = {}
        for item in result:
            name = item.get("file_name")
            if not isinstance(name, str) or type(item.get("size")) is not int or item["size"] < 0:
                raise PublishError("GitLab package file inventory has invalid metadata")
            if name in files:
                raise PublishError("Duplicate filename in Generic Package Registry")
            files[name] = item
        return files

    def download_package_file(self, version: str, name: str) -> bytes:
        path = f"/packages/generic/{quote(PACKAGE_NAME, safe='')}/{quote(version, safe='')}/{quote(name, safe='')}"
        _, _, data = self.request("GET", path)
        return data

    def upload_package_file(self, version: str, asset: Asset) -> None:
        path = f"/packages/generic/{quote(PACKAGE_NAME, safe='')}/{quote(version, safe='')}/{quote(asset.name, safe='')}"
        self.request("PUT", path, asset.data, "application/octet-stream")

    def release(self, tag: str) -> dict[str, Any] | None:
        path = f"/releases/{quote(tag, safe='')}"
        try:
            return self.json("GET", path)
        except PublishError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise

    def create_release(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.json("POST", "/releases", payload)


def _package_url(api: str, version: str, name: str) -> str:
    api_path = api.rstrip("/")
    return (f"{api_path}/projects/{PROJECT_ID}/packages/generic/{quote(PACKAGE_NAME, safe='')}/"
            f"{quote(version, safe='')}/{quote(name, safe='')}")


def _check_existing_release(existing: dict[str, Any], tag: str, sha: str, title: str,
                            notes: str, assets: list[Asset], api_url: str, version: str) -> None:
    if not isinstance(existing, dict):
        raise PublishError("GitLab returned an invalid Release response")
    commit_data = existing.get("commit")
    if existing.get("tag_name") != tag or not isinstance(commit_data, dict) or commit_data.get("id") != sha:
        raise PublishError("An existing GitLab Release has a conflicting tag target")
    if existing.get("name") != title or existing.get("description") != notes:
        raise PublishError("An existing GitLab Release has conflicting immutable metadata")
    asset_data = existing.get("assets")
    links = asset_data.get("links") if isinstance(asset_data, dict) else None
    if not isinstance(links, list):
        raise PublishError("GitLab Release response has no valid asset link list")
    expected = {a.name: _package_url(api_url, version, a.name) for a in assets}
    found: dict[str, str] = {}
    for link in links:
        if not isinstance(link, dict) or not isinstance(link.get("name"), str):
            raise PublishError("Existing GitLab Release contains invalid asset links")
        if link["name"] in found:
            raise PublishError("Existing GitLab Release contains duplicate asset links")
        found[link["name"]] = link.get("url", "")
    if found != expected:
        raise PublishError("Existing GitLab Release asset links conflict with the official asset contract")


def _verify_and_prepare_package(api: GitLabAPI, version: str, assets: list[Asset], *, dry_run: bool) -> int:
    packages = api.package_versions(version)
    if len(packages) > 1:
        raise PublishError("Duplicate Generic Package versions exist; refusing mutation")
    package = packages[0] if packages else None
    files = api.package_files(package["id"]) if package else {}
    expected = {asset.name: asset for asset in assets}
    extra = set(files) - set(expected)
    if extra:
        raise PublishError("Generic Package version contains unexpected files; refusing mutation")
    for name, asset in expected.items():
        if name not in files:
            continue
        item = files[name]
        actual = api.download_package_file(version, name)
        if (len(actual) != asset.size or hashlib.sha256(actual).hexdigest() != asset.sha256 or
                item.get("size") not in (None, asset.size)):
            raise PublishError(f"Existing Generic Package asset conflicts: {name}")
    if dry_run:
        return 0
    uploaded = 0
    for name, asset in expected.items():
        if name not in files:
            for attempt in range(3):
                try:
                    api.upload_package_file(version, asset)
                    uploaded += 1
                    break
                except PublishError as failure:
                    # Resolve ambiguous/non-transient PUT outcomes by reading
                    # the registry before deciding whether another PUT is safe.
                    refreshed_packages = api.package_versions(version)
                    if len(refreshed_packages) > 1:
                        raise PublishError("Duplicate package versions appeared during retry recovery") from None
                    refreshed_files = (api.package_files(refreshed_packages[0]["id"])
                                       if refreshed_packages else {})
                    if name in refreshed_files:
                        actual = api.download_package_file(version, name)
                        if len(actual) == asset.size and hashlib.sha256(actual).hexdigest() == asset.sha256:
                            uploaded += 1  # The timed-out PUT took effect.
                            break
                        raise PublishError(f"Ambiguous upload left a conflicting asset: {name}") from None
                    if not getattr(failure, "retryable", False):
                        raise
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
    # Read-back from Registry is mandatory, including files uploaded now.
    refreshed_packages = api.package_versions(version)
    if len(refreshed_packages) != 1:
        raise PublishError("Generic Package version did not appear exactly once after upload")
    refreshed = api.package_files(refreshed_packages[0]["id"])
    if set(refreshed) != set(expected):
        raise PublishError("Generic Package file set is incomplete after upload")
    for name, asset in expected.items():
        actual = api.download_package_file(version, name)
        if len(actual) != asset.size or hashlib.sha256(actual).hexdigest() != asset.sha256:
            raise PublishError(f"Generic Package read-back integrity check failed: {name}")
    return uploaded


def publish(env: dict[str, str], root: Path, *, dry_run: bool, api: GitLabAPI | None = None) -> dict[str, Any]:
    values = validate_environment(env)
    tag, sha, version = values["CI_COMMIT_TAG"], values["CI_COMMIT_SHA"], values["version"]
    assets, approval = validate_local(values, root)
    notes = next(asset.data.decode("utf-8") for asset in assets if asset.name == "release-notes.md")
    title = f"MT5Agent {tag}"
    client = api or GitLabAPI(values["CI_API_V4_URL"], values["CI_PROJECT_ID"], values["CI_JOB_TOKEN"])
    client.assert_tag_and_main(tag, sha)
    client.assert_merged_authorization_mr(approval["approval_reference"])
    existing = client.release(tag)
    if existing is not None:
        # Detect immutable-release conflicts before the first package write.
        _check_existing_release(existing, tag, sha, title, notes, assets, values["CI_API_V4_URL"], version)
    package_mutations = _verify_and_prepare_package(client, version, assets, dry_run=dry_run)
    if existing is not None:
        return {"result": "matching-existing-release", "tag": tag, "commit": sha,
                "assets": [{"name": a.name, "size": a.size, "sha256": a.sha256} for a in assets],
                "mutations": package_mutations}
    plan = {"name": title, "tag_name": tag, "ref": sha, "description": notes,
            "assets": {"links": [{"name": asset.name, "url": _package_url(values["CI_API_V4_URL"], version, asset.name),
                                   "link_type": "package"} for asset in assets]}}
    if dry_run:
        return {"result": "dry-run-valid", "tag": tag, "commit": sha,
                "assets": [{"name": a.name, "size": a.size, "sha256": a.sha256} for a in assets],
                "planned_release": {"tag_name": tag, "name": title}, "mutations": 0}
    # All assets are already uploaded and read-back verified; this is the first
    # publicly visible mutation. Never update an existing Release.
    try:
        created = client.create_release(plan)
    except PublishError:
        # A timeout/ambiguous response is safe to resolve by a read, never by
        # blindly POSTing a duplicate release.
        created = client.release(tag)
        if created is None:
            raise
        _check_existing_release(created, tag, sha, title, notes, assets, values["CI_API_V4_URL"], version)
        return {"result": "matching-release-after-ambiguous-create", "tag": tag,
                "commit": sha, "mutations": package_mutations + 1}
    _check_existing_release(created, tag, sha, title, notes, assets, values["CI_API_V4_URL"], version)
    read_back = client.release(tag)
    if read_back is None:
        raise PublishError("GitLab Release was not readable after creation")
    _check_existing_release(read_back, tag, sha, title, notes, assets, values["CI_API_V4_URL"], version)
    return {"result": "published-and-verified", "tag": tag, "commit": sha,
            "assets": [{"name": a.name, "size": a.size, "sha256": a.sha256} for a in assets],
            "mutations": package_mutations + 1}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate using read-only API requests; perform no mutations")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    try:
        result = publish(dict(os.environ), args.root, dry_run=args.dry_run)
    except PublishError as exc:
        print(f"Release publication failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
