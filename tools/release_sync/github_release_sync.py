"""One-way, integrity-checked GitLab Release to GitHub Release sync.

The job runs only for semantic-version tags. It waits for the authoritative
GitLab Release and Package Registry files, verifies both mirrored tag targets,
then creates/resumes a GitHub draft and publishes it only after every asset is
verified. GitHub credentials are never included in logs or URLs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


GITHUB_REPOSITORY = "AmirrezaSobhi/agent"
PACKAGE_NAME = "mt5-agent"
SEMVER_TAG = re.compile(r"^v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MANIFEST_LINE = re.compile(r"^\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*$")


class SyncError(RuntimeError):
    """A safe, user-readable synchronization failure."""


class NotReady(SyncError):
    """The GitLab Release has not published all of its assets yet."""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    data: bytes
    size: int
    sha256: str


@dataclass(frozen=True)
class GitLabRelease:
    tag: str
    commit: str
    title: str
    body: str
    assets: tuple[ReleaseAsset, ...]


def _safe_error(error: HTTPError, host: str) -> SyncError:
    # Do not include response bodies or request headers: either can contain
    # server details or credentials added by an intermediary.
    return SyncError(f"HTTP {error.code} from {host}; request was not completed")


def _retry_delay(headers: Any, attempt: int) -> float:
    retry_after = headers.get("Retry-After") if headers else None
    if retry_after:
        try:
            return min(30.0, max(0.0, float(retry_after)))
        except ValueError:
            try:
                seconds = (parsedate_to_datetime(retry_after) -
                           parsedate_to_datetime(time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))).total_seconds()
                return min(30.0, max(0.0, seconds))
            except (TypeError, ValueError, OverflowError):
                pass
    return min(2 ** attempt, 20)


class HTTP:
    """Small urllib client; retries only idempotent GET requests."""

    def __init__(self, headers: dict[str, str] | None = None, timeout: int = 30):
        self.headers = headers or {}
        self.timeout = timeout
        self.opener = build_opener(_StripSensitiveRedirectHeaders())

    def request(self, method: str, url: str, *, data: bytes | None = None,
                headers: dict[str, str] | None = None, retry_get: bool = True) -> tuple[int, dict[str, str], bytes]:
        attempts = 5 if method == "GET" and retry_get else 1
        for attempt in range(attempts):
            merged_headers = {**self.headers, **(headers or {})}
            request = Request(url, data=data, headers=merged_headers, method=method)
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    return response.status, dict(response.headers.items()), response.read()
            except HTTPError as error:
                transient = error.code in (408, 429, 500, 502, 503, 504)
                if transient and attempt + 1 < attempts:
                    time.sleep(_retry_delay(error.headers, attempt))
                    continue
                host = urlsplit(url).hostname or "remote host"
                raise _safe_error(error, host) from None
            except (TimeoutError, URLError, OSError):
                if attempt + 1 < attempts:
                    time.sleep(min(2 ** attempt, 20))
                    continue
                host = urlsplit(url).hostname or "remote host"
                raise SyncError(f"Network request to {host} failed after bounded retries") from None
        raise SyncError("Network request failed after bounded retries")

    def json(self, method: str, url: str, payload: dict[str, Any] | None = None,
             *, retry_get: bool = True) -> Any:
        headers = {"Accept": "application/vnd.github+json"}
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        _, _, body = self.request(method, url, data=data, headers=headers, retry_get=retry_get)
        try:
            return json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SyncError("Remote API returned invalid JSON") from None


class _StripSensitiveRedirectHeaders(HTTPRedirectHandler):
    """Do not forward GitLab job credentials to redirected object storage."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        if redirected is not None and urlsplit(new_url).netloc.lower() != urlsplit(request.full_url).netloc.lower():
            for name in tuple(redirected.headers):
                if name.lower() in ("job-token", "authorization", "private-token"):
                    del redirected.headers[name]
            for name in tuple(redirected.unredirected_hdrs):
                if name.lower() in ("job-token", "authorization", "private-token"):
                    del redirected.unredirected_hdrs[name]
        return redirected


class GitLabAPI:
    def __init__(self, api_url: str, project_id: str, job_token: str):
        if not api_url.startswith("http://") and not api_url.startswith("https://"):
            raise SyncError("CI_API_V4_URL must be an HTTP(S) URL")
        self.api_url = api_url.rstrip("/")
        self.project_id = quote(project_id, safe="")
        self.http = HTTP({"JOB-TOKEN": job_token, "Accept": "application/json"})

    def _json(self, path: str) -> Any:
        _, _, body = self.http.request("GET", f"{self.api_url}{path}")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SyncError("GitLab returned invalid JSON") from None

    def release(self, tag: str) -> dict[str, Any]:
        path = f"/projects/{self.project_id}/releases/{quote(tag, safe='')}"
        try:
            return self._json(path)
        except SyncError as error:
            if "HTTP 404" in str(error):
                raise NotReady(f"GitLab Release {tag} is not published yet") from None
            raise

    def tag_commit(self, tag: str) -> str:
        path = f"/projects/{self.project_id}/repository/tags/{quote(tag, safe='')}"
        tag_data = self._json(path)
        commit = tag_data.get("commit", {}).get("id")
        if not isinstance(commit, str) or not commit:
            raise SyncError("GitLab tag has no resolved commit SHA")
        return commit

    def package_files(self, version: str) -> dict[str, dict[str, Any]]:
        query = urlencode({"package_type": "generic", "package_name": PACKAGE_NAME,
                           "package_version": version, "per_page": "100"})
        packages = self._json(f"/projects/{self.project_id}/packages?{query}")
        matches = [item for item in packages if item.get("name") == PACKAGE_NAME
                   and item.get("version") == version and item.get("package_type") == "generic"]
        if not matches:
            raise NotReady(f"GitLab Package Registry version {version} is not available yet")
        if len(matches) != 1:
            raise SyncError(f"GitLab has duplicate {PACKAGE_NAME} packages for {version}")
        files = self._json(f"/projects/{self.project_id}/packages/{matches[0]['id']}/package_files?per_page=100")
        result: dict[str, dict[str, Any]] = {}
        for item in files:
            name = item.get("file_name")
            if isinstance(name, str):
                if name in result:
                    raise SyncError(f"GitLab package contains duplicate asset name: {name}")
                result[name] = item
        return result

    def download(self, url: str) -> bytes:
        expected_host = urlsplit(self.api_url).netloc.lower()
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != expected_host:
            raise SyncError("Release assets must come from the configured GitLab host")
        _, _, data = self.http.request("GET", url)
        return data


class GitHubAPI:
    def __init__(self, token: str, repository: str = GITHUB_REPOSITORY):
        if "/" not in repository or repository.startswith("/"):
            raise SyncError("GITHUB_REPOSITORY must be owner/name")
        self.repository = repository
        self.base = f"https://api.github.com/repos/{repository}"
        self.http = HTTP({"Authorization": f"Bearer {token}",
                          "Accept": "application/vnd.github+json",
                          "X-GitHub-Api-Version": "2022-11-28"})

    def _json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.http.json(method, f"{self.base}{path}", payload, retry_get=(method == "GET"))

    def tag_commit(self, tag: str) -> str:
        ref_path = f"/git/ref/tags/{quote(tag, safe='')}"
        ref = self._json("GET", ref_path)
        obj = ref.get("object", {})
        for _ in range(6):
            kind, sha = obj.get("type"), obj.get("sha")
            if kind == "commit" and isinstance(sha, str):
                return sha
            if kind != "tag" or not isinstance(sha, str):
                break
            annotated = self._json("GET", f"/git/tags/{quote(sha, safe='')}")
            obj = annotated.get("object", {})
        raise SyncError("GitHub tag does not resolve to a commit")

    def wait_for_tag(self, tag: str, expected_commit: str, *, attempts: int = 12,
                     interval: float = 5, sleep=time.sleep) -> str:
        for attempt in range(attempts):
            try:
                actual = self.tag_commit(tag)
            except SyncError as error:
                if "HTTP 404" not in str(error) or attempt + 1 == attempts:
                    raise
                sleep(interval)
                continue
            if actual != expected_commit:
                raise SyncError("GitHub mirror tag points to a different commit; refusing to publish")
            return actual
        raise SyncError("Timed out waiting for the GitHub mirror tag")

    def release_by_tag(self, tag: str) -> dict[str, Any] | None:
        path = f"/releases/tags/{quote(tag, safe='')}"
        try:
            return self._json("GET", path)
        except SyncError as error:
            if "HTTP 404" in str(error):
                return None
            raise

    def release_by_id(self, release_id: int) -> dict[str, Any]:
        return self._json("GET", f"/releases/{release_id}")

    def create_draft(self, release: GitLabRelease) -> dict[str, Any]:
        try:
            return self._json("POST", "/releases", {
                "tag_name": release.tag,
                "target_commitish": release.commit,
                "name": release.title,
                "body": release.body,
                "draft": True,
                "prerelease": False,
                "generate_release_notes": False,
            })
        except SyncError:
            # A request can time out after GitHub commits it. Re-read by tag so
            # a retry resumes a matching draft instead of making a duplicate.
            existing = self.release_by_tag(release.tag)
            if existing is not None:
                return existing
            raise

    def upload(self, release: dict[str, Any], asset: ReleaseAsset) -> dict[str, Any]:
        upload_url = release.get("upload_url", "").split("{", 1)[0]
        if not upload_url.startswith("https://uploads.github.com/"):
            raise SyncError("GitHub returned an unexpected release asset upload host")
        separator = "&" if "?" in upload_url else "?"
        url = f"{upload_url}{separator}{urlencode({'name': asset.name})}"
        _, _, body = self.http.request("POST", url, data=asset.data,
                                       headers={"Content-Type": "application/octet-stream"},
                                       retry_get=False)
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SyncError("GitHub returned invalid asset upload metadata") from None

    def publish(self, release_id: int) -> dict[str, Any]:
        return self._json("PATCH", f"/releases/{release_id}", {"draft": False})

    def download_published_asset(self, url: str) -> bytes:
        prefix = f"https://github.com/{self.repository}/releases/download/"
        if not url.startswith(prefix):
            raise SyncError("GitHub release asset download URL does not match the repository")
        # Public release assets need no bearer token. Do not send the API token
        # through GitHub's asset CDN redirects.
        public_http = HTTP()
        _, _, data = public_http.request("GET", url)
        return data


def _normalized_body(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _verify_manifest(assets: tuple[ReleaseAsset, ...]) -> None:
    by_name = {asset.name: asset for asset in assets}
    manifests = [asset for asset in assets if asset.name.lower() in ("sha256sums.txt", "sha256.txt")]
    if len(manifests) > 1:
        raise SyncError("GitLab release contains multiple SHA-256 manifests")
    if not manifests:
        return
    try:
        lines = manifests[0].data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise SyncError("GitLab SHA-256 manifest is not UTF-8") from None
    entries = 0
    for line in lines:
        if not line.strip():
            continue
        match = MANIFEST_LINE.match(line)
        if not match:
            raise SyncError("GitLab SHA-256 manifest has an unsupported line")
        expected, name = match.group(1).lower(), PurePosixPath(match.group(2).strip()).name
        source = by_name.get(name)
        if source is None:
            raise SyncError(f"SHA-256 manifest names an unavailable asset: {name}")
        if source.sha256 != expected:
            raise SyncError(f"SHA-256 manifest mismatch for {name}")
        entries += 1
    if entries == 0:
        raise SyncError("GitLab SHA-256 manifest contains no entries")


def load_gitlab_release(api: GitLabAPI, tag: str, expected_commit: str,
                        *, attempts: int = 60, interval: float = 10,
                        sleep=time.sleep) -> GitLabRelease:
    if not SEMVER_TAG.fullmatch(tag):
        raise SyncError("Only stable semantic-version tags can be synchronized")
    actual_commit = api.tag_commit(tag)
    if actual_commit != expected_commit:
        raise SyncError("GitLab tag target does not match the CI commit")
    version = tag[1:]
    last_not_ready = "GitLab Release assets are not ready"
    for attempt in range(attempts):
        try:
            raw = api.release(tag)
            if raw.get("tag_name") != tag or not raw.get("released_at"):
                raise NotReady(f"GitLab Release {tag} is not published yet")
            title, body = raw.get("name"), raw.get("description")
            links = raw.get("assets", {}).get("links", [])
            if not isinstance(title, str) or not title.strip() or not isinstance(body, str):
                raise SyncError("GitLab Release title or notes are missing")
            if not links:
                raise NotReady(f"GitLab Release {tag} has no attached assets yet")
            package_files = api.package_files(version)
            assets = []
            names = set()
            for link in links:
                name = link.get("name")
                source_url = link.get("url") or link.get("direct_asset_url")
                if not isinstance(name, str) or not name or name in names:
                    raise SyncError("GitLab Release has an invalid or duplicate asset name")
                names.add(name)
                metadata = package_files.get(name)
                if metadata is None:
                    raise NotReady(f"GitLab Package Registry asset {name} is not ready")
                expected = metadata.get("file_sha256")
                if not isinstance(expected, str) or not SHA256.fullmatch(expected.lower()):
                    raise SyncError(f"GitLab Package Registry has no valid SHA-256 for {name}")
                if not isinstance(source_url, str):
                    raise SyncError(f"GitLab Release asset URL is missing for {name}")
                data = api.download(source_url)
                digest = hashlib.sha256(data).hexdigest()
                if digest != expected.lower():
                    raise SyncError(f"Downloaded GitLab asset SHA-256 mismatch for {name}")
                declared_size = metadata.get("size")
                if isinstance(declared_size, int) and len(data) != declared_size:
                    raise SyncError(f"Downloaded GitLab asset size mismatch for {name}")
                assets.append(ReleaseAsset(name, data, len(data), digest))
            assets_tuple = tuple(assets)
            _verify_manifest(assets_tuple)
            return GitLabRelease(tag, actual_commit, title, body, assets_tuple)
        except NotReady as error:
            last_not_ready = str(error)
            if attempt + 1 < attempts:
                sleep(interval)
    raise SyncError(f"Timed out waiting for GitLab Release assets: {last_not_ready}")


def _remote_digest(asset: dict[str, Any]) -> str | None:
    digest = asset.get("digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        return None
    value = digest.removeprefix("sha256:").lower()
    return value if SHA256.fullmatch(value) else None


def synchronize(release: GitLabRelease, github: GitHubAPI, *, dry_run: bool = False) -> dict[str, Any]:
    github.wait_for_tag(release.tag, release.commit)

    current = github.release_by_tag(release.tag)
    created = False
    if current is not None:
        if current.get("tag_name") != release.tag:
            raise SyncError("GitHub returned a release for a different tag")
        if current.get("name") != release.title or _normalized_body(current.get("body") or "") != _normalized_body(release.body):
            raise SyncError("GitHub Release title or notes conflict with GitLab; no overwrite performed")
        if bool(current.get("prerelease")):
            raise SyncError("GitHub Release prerelease state conflicts with stable GitLab tag")
    expected_by_name = {asset.name: asset for asset in release.assets}

    def validate_existing_assets(release_data: dict[str, Any]) -> tuple[list[ReleaseAsset], list[ReleaseAsset]]:
        remote_assets = release_data.get("assets", [])
        by_name = {}
        for item in remote_assets:
            name = item.get("name")
            if not isinstance(name, str) or name in by_name:
                raise SyncError("GitHub Release contains duplicate or invalid asset names")
            by_name[name] = item
        extras = sorted(set(by_name) - set(expected_by_name))
        if extras:
            raise SyncError("GitHub Release has extra assets that are not in GitLab: " + ", ".join(extras))
        matched, missing = [], []
        for name, source in expected_by_name.items():
            remote = by_name.get(name)
            if remote is None:
                missing.append(source)
                continue
            if remote.get("size") != source.size:
                raise SyncError(f"GitHub asset size conflict for {name}; no overwrite performed")
            remote_sha = _remote_digest(remote)
            if remote_sha is None:
                if release_data.get("draft"):
                    raise SyncError(f"GitHub has no verifiable SHA-256 for draft asset {name}")
                downloaded = github.download_published_asset(remote.get("browser_download_url", ""))
                remote_sha = hashlib.sha256(downloaded).hexdigest()
                if len(downloaded) != source.size:
                    raise SyncError(f"Downloaded GitHub asset size mismatch for {name}")
            if remote_sha != source.sha256:
                raise SyncError(f"GitHub asset SHA-256 conflict for {name}; no overwrite performed")
            matched.append(source)
        return matched, missing

    if current is not None:
        _, missing = validate_existing_assets(current)
    else:
        missing = list(release.assets)
    if dry_run:
        return {"tag": release.tag, "commit": release.commit,
                "action": "create" if current is None else "verify",
                "upload_assets": [asset.name for asset in missing],
                "publish_draft": bool(current and current.get("draft"))}

    if current is None:
        current = github.create_draft(release)
        created = True
        if current.get("name") != release.title or _normalized_body(current.get("body") or "") != _normalized_body(release.body):
            raise SyncError("GitHub draft metadata does not match GitLab after creation")
        _, missing = validate_existing_assets(current)

    for asset in missing:
        github.upload(current, asset)
        current = github.release_by_id(current["id"])
        _, missing = validate_existing_assets(current)

    current = github.release_by_id(current["id"])
    validate_existing_assets(current)
    if current.get("draft"):
        current = github.publish(current["id"])
    if current.get("draft"):
        raise SyncError("GitHub Release remained a draft after publish request")

    # Independently download every public asset after publication and hash the
    # bytes that users will receive.
    current = github.release_by_id(current["id"])
    remote_by_name = {item.get("name"): item for item in current.get("assets", [])}
    for source in release.assets:
        remote = remote_by_name.get(source.name)
        if remote is None:
            raise SyncError(f"Published GitHub Release is missing asset {source.name}")
        downloaded = github.download_published_asset(remote.get("browser_download_url", ""))
        if len(downloaded) != source.size or hashlib.sha256(downloaded).hexdigest() != source.sha256:
            raise SyncError(f"Published GitHub asset integrity check failed for {source.name}")
    return {"tag": release.tag, "commit": release.commit,
            "action": "created" if created else "reconciled",
            "assets_verified": [asset.name for asset in release.assets],
            "published": True}


def run_from_environment(*, dry_run: bool = False, tag_override: str | None = None,
                         commit_override: str | None = None) -> dict[str, Any]:
    if (tag_override is None) != (commit_override is None):
        raise SyncError("Historical reconciliation requires both --tag and --commit")
    tag = tag_override if tag_override is not None else os.environ.get("CI_COMMIT_TAG", "")
    expected_commit = commit_override if commit_override is not None else os.environ.get("CI_COMMIT_SHA", "")
    if not SEMVER_TAG.fullmatch(tag):
        raise SyncError("CI_COMMIT_TAG must be a stable semantic version tag")
    if not COMMIT_SHA.fullmatch(expected_commit.lower()):
        raise SyncError("CI_COMMIT_SHA is missing or invalid")
    if os.environ.get("CI_COMMIT_REF_PROTECTED", "false").lower() != "true":
        raise SyncError("CI_COMMIT_REF_PROTECTED must be true before protected credentials are used")

    github_token = os.environ.get("GITHUB_RELEASE_TOKEN", "")
    if not github_token:
        raise SyncError("Missing protected GitLab CI variable GITHUB_RELEASE_TOKEN")
    gitlab_job_token = os.environ.get("CI_JOB_TOKEN", "")
    if not gitlab_job_token:
        raise SyncError("CI_JOB_TOKEN is unavailable; cannot read GitLab Release assets")
    api_url = os.environ.get("CI_API_V4_URL", "")
    project_id = os.environ.get("CI_PROJECT_ID", "")
    if not api_url or not project_id:
        raise SyncError("CI_API_V4_URL and CI_PROJECT_ID are required")

    gitlab = GitLabAPI(api_url, project_id, gitlab_job_token)
    release = load_gitlab_release(gitlab, tag, expected_commit)
    github = GitHubAPI(github_token)
    return synchronize(release, github, dry_run=dry_run)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate and report planned GitHub changes without writing")
    parser.add_argument("--tag", help="explicit source tag for protected-branch historical reconciliation")
    parser.add_argument("--commit", help="expected full commit SHA for --tag")
    args = parser.parse_args()
    try:
        result = run_from_environment(dry_run=args.dry_run, tag_override=args.tag,
                                      commit_override=args.commit)
        print(json.dumps(result, sort_keys=True))
        return 0
    except SyncError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
