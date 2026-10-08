"""Publisher policy and retry-safety tests; all API writes use an in-memory fake."""
import hashlib
import json
from pathlib import Path

import pytest

from tools.release_sync import gitlab_release_publish as publisher


TAG = "v0.1.4"
SHA = "a" * 40
PIPELINE = "314"
API = "https://gitlab.local/api/v4"


def _receipt_common(digest):
    return {"schema_version": "1", "pipeline_id": PIPELINE, "commit_sha": SHA,
            "candidate_version": "0.1.4", "candidate_filename": f"MT5Agent-{TAG}.exe",
            "candidate_sha256": digest}


@pytest.fixture
def fixture_root(tmp_path):
    (tmp_path / "agent").mkdir()
    (tmp_path / "dist").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "docs/releases").mkdir(parents=True)
    (tmp_path / "agent/__init__.py").write_text('__version__ = "0.1.4"\n', encoding="utf-8")
    (tmp_path / "dist" / f"MT5Agent-{TAG}.exe").write_bytes(b"tested executable bytes")
    data = (tmp_path / "dist" / f"MT5Agent-{TAG}.exe").read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    common = _receipt_common(digest)
    build = dict(common, source_commit=SHA, candidate_size=len(data), metatrader5_present_in_build_environment=False,
                 numpy_present_in_build_environment=False, archive_inspection_success=True,
                 archive_forbidden_module_matches=[])
    control = dict(common, status="PASS", test="control-plane-degraded-startup",
                   health="AGENT_RUNNING_DEGRADED", worker_available=False,
                   runtime_state="RUNTIME_UNAVAILABLE")
    invalid = dict(common, status="PASS", test="invalid-configuration", expected_exit=2, actual_exit=2)
    runtime = dict(common, status="PASS", candidate_sha256_after=digest, runtime_state="MT5_CONNECTED",
                   final_health="AGENT_RUNNING + MT5_CONNECTED", symbols_total_success=True,
                   terminal_version_success=True, account_information_success=True,
                   account_information_field_count=8,
                   agent={"session_id": 0},
                   worker={"principal": "runtime-account", "sid": "redacted", "session_id": 1,
                           "protocol_version": "1"},
                   terminal={"principal": "runtime-account", "sid": "redacted", "session_id": 1})
    release = dict(common, release_eligible=True, build_once=True, post_smoke_rebuild=False,
                   control_plane_gate="PASS", mt5_runtime_gate="PASS")
    for name, value in (("build", build), ("invalid-configuration", invalid),
                        ("control-plane", control), ("mt5-runtime", runtime),
                        ("release-evidence", release)):
        (tmp_path / f"reports/{name}.json").write_text(json.dumps(value), encoding="utf-8")
    (tmp_path / "sha256.txt").write_text(f"SHA256={digest}\n", encoding="utf-8")
    (tmp_path / f"docs/releases/{TAG}-release-notes.md").write_text(f"# MT5Agent {TAG}\n\nNotes.\n", encoding="utf-8")
    authorization = {"schema_version": 1, "tag": TAG, "commit_sha": SHA,
                     "approved_by_user_id": 23, "approved_at": "2026-10-08T10:00:00Z",
                     "approval_reference": "https://gitlab.local/root/agent/-/merge_requests/42",
                     "release_blocking_risks": [{"id": "KI-009", "disposition": "accepted",
                                                  "reference": "https://gitlab.local/root/agent/-/issues/9",
                                                  "approved_by_user_id": 23,
                                                  "approved_at": "2026-10-08T10:00:00Z",
                                                  "approval_reference": "https://gitlab.local/root/agent/-/merge_requests/42"}]}
    (tmp_path / f"docs/releases/{TAG}-authorization.json").write_text(json.dumps(authorization), encoding="utf-8")
    return tmp_path


@pytest.fixture
def env():
    return {"CI_COMMIT_TAG": TAG, "CI_COMMIT_SHA": SHA, "CI_PIPELINE_ID": PIPELINE,
            "CI_PROJECT_ID": "1", "CI_PROJECT_PATH": "root/agent", "CI_API_V4_URL": API,
            "CI_JOB_TOKEN": "test-token-never-logged", "CI_COMMIT_REF_PROTECTED": "true",
            "CI_PIPELINE_SOURCE": "push", "GITLAB_USER_ID": "17", "MT5_RELEASE_OWNER_USER_ID": "23",
            "CI_PIPELINE_URL": "https://gitlab.local/root/agent/-/pipelines/314"}


class FakeAPI:
    def __init__(self):
        self.package = {}
        self.release_data = None
        self.mutations = []

    def assert_tag_and_main(self, tag, sha):
        assert tag == TAG and sha == SHA

    def assert_merged_authorization_mr(self, reference):
        assert reference.endswith("/merge_requests/42")

    def package_versions(self, version):
        if not self.package:
            return []
        return [{"id": 1, "name": "mt5-agent", "version": version}]

    def package_files(self, package_id):
        return {name: {"file_name": name, "size": len(data)} for name, data in self.package.items()}

    def download_package_file(self, version, name):
        return self.package[name]

    def upload_package_file(self, version, asset):
        self.mutations.append(("upload", asset.name))
        if asset.name in self.package:
            raise AssertionError("test fake refuses overwrite")
        self.package[asset.name] = asset.data

    def release(self, tag):
        return self.release_data

    def create_release(self, payload):
        self.mutations.append(("release", payload["tag_name"]))
        self.release_data = {"tag_name": payload["tag_name"], "commit": {"id": SHA},
                             "name": payload["name"], "description": payload["description"],
                             "assets": {"links": payload["assets"]["links"]}}
        return self.release_data


def test_semver_is_stable_and_strict(env):
    assert publisher.validate_environment(env)["version"] == "0.1.4"
    for tag in ("v01.2.3", "v1.2", "v1.2.3-rc1", "1.2.3"):
        candidate = dict(env, CI_COMMIT_TAG=tag)
        with pytest.raises(publisher.PublishError):
            publisher.validate_environment(candidate)


@pytest.mark.parametrize("key,value", [
    ("CI_COMMIT_REF_PROTECTED", "false"), ("CI_PIPELINE_SOURCE", "web"),
    ("CI_PIPELINE_SOURCE", "schedule"), ("CI_PIPELINE_SOURCE", "api"),
    ("CI_PIPELINE_SOURCE", "merge_request_event"),
    ("CI_COMMIT_SHA", "short"), ("CI_PROJECT_ID", "2"), ("CI_JOB_TOKEN", ""),
])
def test_fails_closed_on_auth_or_environment(env, key, value):
    with pytest.raises(publisher.PublishError):
            publisher.validate_environment(dict(env, **{key: value}))


def test_http_gitlab_api_and_tag_owner_self_approval_are_rejected(env):
    with pytest.raises(publisher.PublishError, match="HTTPS"):
        publisher.validate_environment(dict(env, CI_API_V4_URL="http://gitlab.local/api/v4"))
    with pytest.raises(publisher.PublishError, match="distinct"):
        publisher.validate_environment(dict(env, GITLAB_USER_ID="23"))


def test_dry_run_is_read_only_and_produces_exact_assets(env, fixture_root):
    api = FakeAPI()
    result = publisher.publish(env, fixture_root, dry_run=True, api=api)
    assert result["result"] == "dry-run-valid"
    assert result["mutations"] == 0
    assert api.mutations == []
    assert len(result["assets"]) == 4


def test_publication_uploads_then_creates_release_and_retry_is_idempotent(env, fixture_root):
    api = FakeAPI()
    first = publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert first["result"] == "published-and-verified"
    assert len(api.package) == 4 and api.mutations[-1] == ("release", TAG)
    mutation_count = len(api.mutations)
    second = publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert second["result"] == "matching-existing-release"
    assert len(api.mutations) == mutation_count


def test_partial_package_upload_resumes_without_overwrite(env, fixture_root):
    api = FakeAPI()
    assets, _ = publisher.validate_local(publisher.validate_environment(env), fixture_root)
    api.package[assets[0].name] = assets[0].data
    result = publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert result["result"] == "published-and-verified"
    assert len([op for op in api.mutations if op[0] == "upload"]) == 3


@pytest.mark.parametrize("applied_before_error", [False, True])
def test_ambiguous_upload_is_read_back_before_a_safe_retry(env, fixture_root, applied_before_error):
    class FlakyUpload(FakeAPI):
        failed = False
        def upload_package_file(self, version, asset):
            if not self.failed:
                self.failed = True
                if applied_before_error:
                    self.package[asset.name] = asset.data
                raise publisher.APIRequestError("simulated transient upload failure", retryable=True)
            return super().upload_package_file(version, asset)
    api = FlakyUpload()
    result = publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert result["result"] == "published-and-verified"
    assert len(api.package) == 4


def test_conflicting_package_asset_stops_before_any_write(env, fixture_root):
    api = FakeAPI()
    api.package["MT5Agent-v0.1.4.exe"] = b"different bytes"
    with pytest.raises(publisher.PublishError, match="conflicts"):
        publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert api.mutations == []


def test_wrong_gitlab_tag_target_stops(env, fixture_root):
    class WrongTag(FakeAPI):
        def assert_tag_and_main(self, tag, sha):
            raise publisher.PublishError("Protected tag does not resolve to CI_COMMIT_SHA")
    api = WrongTag()
    with pytest.raises(publisher.PublishError, match="does not resolve"):
        publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert api.mutations == []


def test_duplicate_package_versions_stop(env, fixture_root):
    class Duplicate(FakeAPI):
        def package_versions(self, version):
            return [{"id": 1}, {"id": 2}]
    with pytest.raises(publisher.PublishError, match="Duplicate"):
        publisher.publish(env, fixture_root, dry_run=False, api=Duplicate())


def test_permission_failure_is_not_retried_or_hidden(env, fixture_root):
    class DeniedUpload(FakeAPI):
        attempts = 0
        def upload_package_file(self, version, asset):
            self.attempts += 1
            raise publisher.APIRequestError("GitLab API returned HTTP 403", retryable=False)

    api = DeniedUpload()
    with pytest.raises(publisher.APIRequestError, match="403"):
        publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert api.attempts == 1
    assert api.release_data is None


@pytest.mark.parametrize("file,mutate", [
    ("build.json", lambda x: x.update(candidate_size=999)),
    ("invalid-configuration.json", lambda x: x.update(status="FAIL")),
    ("control-plane.json", lambda x: x.update(pipeline_id="stale")),
    ("mt5-runtime.json", lambda x: x.update(candidate_sha256_after="0" * 64)),
    ("release-evidence.json", lambda x: x.update(post_smoke_rebuild=True)),
])
def test_bad_or_stale_evidence_fails_closed(env, fixture_root, file, mutate):
    path = fixture_root / "reports" / file
    data = json.loads(path.read_text())
    mutate(data)
    path.write_text(json.dumps(data))
    with pytest.raises(publisher.PublishError):
        publisher.publish(env, fixture_root, dry_run=True, api=FakeAPI())


def test_missing_risk_approval_and_notes_fail_closed(env, fixture_root):
    auth_path = fixture_root / f"docs/releases/{TAG}-authorization.json"
    auth = json.loads(auth_path.read_text())
    auth["release_blocking_risks"] = []
    auth_path.write_text(json.dumps(auth))
    with pytest.raises(publisher.PublishError, match="KI-009"):
        publisher.validate_local(publisher.validate_environment(env), fixture_root)
    auth["release_blocking_risks"] = [{"id": "KI-009", "disposition": "accepted", "reference": "issue"}]
    auth_path.write_text(json.dumps(auth))
    (fixture_root / f"docs/releases/{TAG}-release-notes.md").unlink()
    with pytest.raises(publisher.PublishError):
        publisher.validate_local(publisher.validate_environment(env), fixture_root)


def test_release_owner_identity_must_match_protected_configuration(env, fixture_root):
    auth_path = fixture_root / f"docs/releases/{TAG}-authorization.json"
    auth = json.loads(auth_path.read_text())
    auth["approved_by_user_id"] = 17
    auth_path.write_text(json.dumps(auth))
    with pytest.raises(publisher.PublishError, match="Release Owner"):
        publisher.publish(env, fixture_root, dry_run=True, api=FakeAPI())


def test_existing_conflicting_release_fails_without_mutation(env, fixture_root):
    api = FakeAPI()
    api.release_data = {"tag_name": TAG, "commit": {"id": "b" * 40}, "name": f"MT5Agent {TAG}",
                        "description": "wrong", "assets": {"links": []}}
    with pytest.raises(publisher.PublishError, match="conflicting"):
        publisher.publish(env, fixture_root, dry_run=False, api=api)
    assert api.mutations == []


def test_http_retries_only_safe_reads_and_redacts_auth_errors(monkeypatch):
    import io
    from urllib.error import HTTPError

    calls = []

    class Response:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return b"{}"

    def fake_open(request, timeout):
        calls.append(request.get_method())
        if len(calls) == 1:
            raise HTTPError(request.full_url, 503, "retry", {}, io.BytesIO(b"secret error payload"))
        return Response()

    monkeypatch.setattr(publisher.time, "sleep", lambda _: None)
    client = publisher.GitLabAPI(API, "1", "sensitive-token")
    class Opener:
        def open(self, request, timeout): return fake_open(request, timeout)
    client.opener = Opener()
    assert client.request("GET", "/releases/v0.1.4")[0] == 200
    assert calls == ["GET", "GET"]
    calls.clear()
    def fail_write(request, timeout):
        calls.append(request.get_method())
        raise HTTPError(request.full_url, 403, "denied", {}, io.BytesIO(b"sensitive-token"))
    class FailingOpener:
        def open(self, request, timeout): return fail_write(request, timeout)
    client.opener = FailingOpener()
    with pytest.raises(publisher.PublishError) as failure:
        client.request("PUT", "/packages/generic/mt5-agent/0.1.4/a.exe", b"file")
    assert calls == ["PUT"]
    assert "sensitive-token" not in str(failure.value)


def test_registry_inventory_pagination_is_complete(monkeypatch):
    client = publisher.GitLabAPI(API, "1", "test-token")
    pages = {
        1: ({"X-Next-Page": "2"}, [{"file_name": f"file-{n}"} for n in range(100)]),
        2: ({"X-Next-Page": ""}, [{"file_name": "file-100"}]),
    }
    def fake_request(method, path, data=None, content_type=None):
        page = int(path.rsplit("page=", 1)[1])
        headers, values = pages[page]
        return 200, headers, json.dumps(values).encode()
    monkeypatch.setattr(client, "request", fake_request)
    values = client.json_pages("/packages?package_type=generic")
    assert len(values) == 101 and values[-1]["file_name"] == "file-100"


def test_authorization_merge_request_must_be_merged_into_main():
    client = publisher.GitLabAPI(API, "1", "test-token")
    responses = iter([{"state": "merged", "target_branch": "main"},
                      {"state": "merged", "target_branch": "develop"}])
    client.json = lambda method, path, payload=None: next(responses)
    client.assert_merged_authorization_mr("https://gitlab.local/root/agent/-/merge_requests/42")
    with pytest.raises(publisher.PublishError, match="not merged into main"):
        client.assert_merged_authorization_mr("https://gitlab.local/root/agent/-/merge_requests/43")


def test_release_response_must_match_entire_immutable_contract(env, fixture_root):
    class BadCreate(FakeAPI):
        def create_release(self, payload):
            result = super().create_release(payload)
            result["name"] = "wrong"
            return result
    with pytest.raises(publisher.PublishError, match="conflicting"):
        publisher.publish(env, fixture_root, dry_run=False, api=BadCreate())


def test_ci_graph_publishes_gitlab_before_github():
    source = (Path(__file__).resolve().parents[1] / ".gitlab-ci.yml").read_text(encoding="utf-8")
    assert "  - release_publish\n  - release_sync" in source
    block = source.split("release:gitlab-publish:\n", 1)[1].split("release:github-sync:\n", 1)[0]
    assert "job: package:windows" in block
    assert "CI_COMMIT_REF_PROTECTED == \"true\"" in block
    assert "CI_PIPELINE_SOURCE == \"push\"" in block
    github = source.split("release:github-sync:\n", 1)[1].split("release:github-reconcile:", 1)[0]
    assert "job: release:gitlab-publish" in github
    assert "job: package:windows" not in github
    assert "CI_PIPELINE_SOURCE == \"push\"" in github
