import hashlib
import unittest
from unittest.mock import patch

from tools.release_sync.github_release_sync import (
    GitLabRelease,
    ReleaseAsset,
    SyncError,
    _verify_manifest,
    synchronize,
)


def asset(name="MT5Agent-v0.1.3.exe", data=b"verified executable"):
    return ReleaseAsset(name, data, len(data), hashlib.sha256(data).hexdigest())


def source_release(assets=None):
    return GitLabRelease("v0.1.3", "a" * 40, "MT5 Agent v0.1.3", "Release notes",
                         tuple(assets or [asset()]))


class FakeGitHub:
    def __init__(self, commit=None, release=None):
        self.commit = commit or "a" * 40
        self.release = release
        self.upload_count = 0
        self.published = False

    def wait_for_tag(self, tag, expected_commit):
        if self.commit != expected_commit:
            raise SyncError("GitHub mirror tag points to a different commit")
        return self.commit

    def release_by_tag(self, tag):
        return self.release

    def create_draft(self, source):
        self.release = {"id": 7, "tag_name": source.tag, "name": source.title,
                        "body": source.body, "prerelease": False, "draft": True,
                        "upload_url": "https://uploads.github.com/repos/test/releases/7/assets{?name}",
                        "assets": []}
        return self.release

    def upload(self, release, source):
        self.upload_count += 1
        self.release["assets"].append({"name": source.name, "size": source.size,
                                       "digest": "sha256:" + source.sha256,
                                       "browser_download_url": "https://github.com/test/releases/download/v/" + source.name})

    def release_by_id(self, release_id):
        return self.release

    def publish(self, release_id):
        self.release["draft"] = False
        self.published = True
        return self.release

    def download_published_asset(self, url):
        name = url.rsplit("/", 1)[-1]
        return next(data for data_name, data in self.files.items() if data_name == name)


class ReleaseSyncTests(unittest.TestCase):
    def prepare(self, client, release):
        client.files = {item.name: item.data for item in release.assets}

    def test_missing_release_creates_draft_uploads_and_verifies(self):
        source = source_release()
        github = FakeGitHub()
        self.prepare(github, source)
        result = synchronize(source, github)
        self.assertEqual(result["action"], "created")
        self.assertTrue(result["published"])
        self.assertEqual(github.upload_count, 1)

    def test_matching_release_is_idempotent(self):
        source = source_release()
        item = source.assets[0]
        release = {"id": 7, "tag_name": source.tag, "name": source.title, "body": source.body,
                   "prerelease": False, "draft": False,
                   "assets": [{"name": item.name, "size": item.size,
                               "digest": "sha256:" + item.sha256,
                               "browser_download_url": "https://github.com/test/releases/download/v/" + item.name}]}
        github = FakeGitHub(release=release)
        self.prepare(github, source)
        result = synchronize(source, github)
        self.assertEqual(result["action"], "reconciled")
        self.assertEqual(github.upload_count, 0)

    def test_missing_asset_is_added_to_matching_release(self):
        source = source_release([asset("one.bin", b"one"), asset("two.bin", b"two")])
        first = source.assets[0]
        release = {"id": 7, "tag_name": source.tag, "name": source.title, "body": source.body,
                   "prerelease": False, "draft": True,
                   "upload_url": "https://uploads.github.com/repos/test/releases/7/assets{?name}",
                   "assets": [{"name": first.name, "size": first.size,
                               "digest": "sha256:" + first.sha256,
                               "browser_download_url": "https://github.com/test/releases/download/v/" + first.name}]}
        github = FakeGitHub(release=release)
        self.prepare(github, source)
        result = synchronize(source, github)
        self.assertTrue(result["published"])
        self.assertEqual(github.upload_count, 1)

    def test_dry_run_does_not_create_release_or_upload(self):
        source = source_release()
        github = FakeGitHub()
        plan = synchronize(source, github, dry_run=True)
        self.assertEqual(plan["action"], "create")
        self.assertIsNone(github.release)
        self.assertEqual(github.upload_count, 0)

    def test_tag_mismatch_stops_before_release_lookup(self):
        with self.assertRaisesRegex(SyncError, "different commit"):
            synchronize(source_release(), FakeGitHub(commit="b" * 40))

    def test_conflicting_asset_is_never_replaced(self):
        source = source_release()
        bad = asset(data=b"x" * 19)
        release = {"id": 7, "tag_name": source.tag, "name": source.title, "body": source.body,
                   "prerelease": False, "draft": False,
                   "assets": [{"name": bad.name, "size": bad.size,
                               "digest": "sha256:" + bad.sha256, "browser_download_url": "unused"}]}
        github = FakeGitHub(release=release)
        with self.assertRaisesRegex(SyncError, "SHA-256 conflict"):
            synchronize(source, github)
        self.assertEqual(github.upload_count, 0)

    def test_duplicate_github_asset_names_fail_closed(self):
        source = source_release()
        item = source.assets[0]
        remote = {"name": item.name, "size": item.size, "digest": "sha256:" + item.sha256,
                  "browser_download_url": "unused"}
        release = {"id": 7, "tag_name": source.tag, "name": source.title, "body": source.body,
                   "prerelease": False, "draft": False, "assets": [remote, remote.copy()]}
        with self.assertRaisesRegex(SyncError, "duplicate"):
            synchronize(source, FakeGitHub(release=release))

    def test_manifest_mismatch_fails_before_sync(self):
        binary = asset()
        manifest = asset("SHA256SUMS.txt", ("0" * 64 + "  " + binary.name + "\n").encode())
        with self.assertRaisesRegex(SyncError, "manifest mismatch"):
            _verify_manifest((binary, manifest))

    def test_retry_waits_for_mirror_tag_but_rejects_wrong_target(self):
        from tools.release_sync.github_release_sync import GitHubAPI

        client = object.__new__(GitHubAPI)
        answers = iter([SyncError("HTTP 404 from api.github.com"), "a" * 40])
        client.tag_commit = lambda tag: (_ for _ in ()).throw(value) if isinstance((value := next(answers)), Exception) else value
        slept = []
        result = client.wait_for_tag("v0.1.3", "a" * 40, attempts=2, interval=3, sleep=slept.append)
        self.assertEqual(result, "a" * 40)
        self.assertEqual(slept, [3])

    def test_missing_github_credential_fails_before_network_access(self):
        from tools.release_sync.github_release_sync import run_from_environment

        env = {"CI_COMMIT_TAG": "v0.1.3", "CI_COMMIT_SHA": "a" * 40,
               "CI_COMMIT_REF_PROTECTED": "true", "CI_JOB_TOKEN": "job-token",
               "CI_API_V4_URL": "https://gitlab.local/api/v4", "CI_PROJECT_ID": "1",
               "CI_PROJECT_PATH": "root/agent", "CI_PIPELINE_SOURCE": "push"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(SyncError, "GITHUB_RELEASE_TOKEN"):
                run_from_environment()

    def test_gitlab_sync_requires_https(self):
        from tools.release_sync.github_release_sync import GitLabAPI

        with self.assertRaisesRegex(SyncError, "HTTPS"):
            GitLabAPI("http://gitlab.local/api/v4", "1", "test-token")

    def test_automatic_sync_rejects_non_push_and_unexpected_project(self):
        from tools.release_sync.github_release_sync import run_from_environment

        with patch.dict("os.environ", {"CI_PIPELINE_SOURCE": "web"}, clear=True):
            with self.assertRaisesRegex(SyncError, "tag push pipeline"):
                run_from_environment()
        with patch.dict("os.environ", {"CI_PIPELINE_SOURCE": "push", "CI_PROJECT_ID": "2",
                                        "CI_PROJECT_PATH": "other/project"}, clear=True):
            with self.assertRaisesRegex(SyncError, "root/agent"):
                run_from_environment()

    def test_gitlab_sync_strips_credentials_on_scheme_downgrade(self):
        from tools.release_sync.github_release_sync import _StripSensitiveRedirectHeaders
        from urllib.request import Request

        handler = _StripSensitiveRedirectHeaders()
        request = Request("https://gitlab.local/api/v4/packages", headers={"JOB-TOKEN": "secret"})
        redirected = handler.redirect_request(request, None, 302, "Found", {},
                                               "http://gitlab.local/api/v4/packages/file")
        self.assertIsNotNone(redirected)
        self.assertFalse(any(key.lower() == "job-token" for key in redirected.headers))
        self.assertFalse(any(key.lower() == "job-token" for key in redirected.unredirected_hdrs))

    def test_historical_tag_override_requires_exact_pair_and_protected_ref(self):
        from tools.release_sync.github_release_sync import run_from_environment

        env = {"CI_COMMIT_REF_PROTECTED": "false"}
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(SyncError, "both --tag and --commit"):
                run_from_environment(tag_override="v0.1.3")
            with self.assertRaisesRegex(SyncError, "protected credentials"):
                run_from_environment(tag_override="v0.1.3", commit_override="a" * 40)


if __name__ == "__main__":
    unittest.main()
