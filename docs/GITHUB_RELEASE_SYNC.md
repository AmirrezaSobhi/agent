# GitLab to GitHub Release Synchronization

**Status: IMPLEMENTED IN CI, NOT OPERATIONAL.** GitLab remains the sole Source
of Truth. GitHub is a downstream publication target; do not change mirror
direction or treat GitHub-only releases as authoritative.

## Audited inventory (2026-10-08)

GitLab currently has one Release, `v0.1.3`, at
`970c04712853295fd065094b11a2bd541b5a9db8`. It exposes four generated source
archives and four manually linked Generic Package files, plus a
`mt5-agent/0.1.3` package. GitHub generates source archives from its mirrored
tag; synchronization uploads the four linked package files as Release assets.
Package metadata reports the executable as 8,124,497 bytes with SHA-256
`175ff421e06d0c7394721dcf2aaa9509b953bc3d9c3d8d7f6fab7afb01e4ab28`. The
Package Registry returned HTTP 401 to the audit environment, so this audit
could not independently download and hash those bytes. The metadata agrees
with the existing release record; it is not a new byte-level verification.

GitHub had eight published releases, `v0.0.2` through `v0.0.9`, and no
`v0.1.3` Release. They are GitHub-only relative to the current GitLab Release
inventory and are preserved unchanged. The mirrored GitHub `v0.1.3` tag
resolved to the same commit as GitLab. Existing `v0.0.2`, `v0.0.4`, and
`v0.0.6` Release-note checksum text did not match the corresponding GitHub
asset API digests during the read-only inventory. These historical releases
and assets are conflicts for investigation; automation will not edit or
delete them. See the [GitHub Releases page](https://github.com/AmirrezaSobhi/agent/releases).

The existing GitLab repository mirror is enabled and its last observed status
was `finished`. No GitLab release webhook receiver or GitHub Actions release
workflow was present. The audit could read public GitHub release metadata, but
GitHub rejected unauthenticated release API access with HTTP 401. No GitHub
release token was available in this environment, and the GitLab project had
no CI variables or protected tag rules at audit time.

## Workflow

`.gitlab-ci.yml` adds a final `release_sync` stage for stable version tag
pipelines. After the existing Windows package job and all preceding gates, the
Linux source Runner invokes
[`tools/release_sync/github_release_sync.py`](../tools/release_sync/github_release_sync.py).
The job polls for the *published GitLab Release* and Generic Package files;
the presence of a pushed tag alone never creates a GitHub Release. The
operator must publish the authoritative GitLab Release and package links after
the package is ready. If the bounded wait expires, publish/repair the GitLab
source release as appropriate and retry the failed sync job in that same tag
pipeline. Do not create a new tag to retry synchronization.

The optional `release:github-reconcile` manual job is available only in a
GitLab web pipeline on a protected branch. It takes `SYNC_TAG` and
`SYNC_COMMIT` pipeline variables, validates the exact GitLab tag target, and
uses the same idempotent synchronization path. This handles Releases whose
tag pipeline predates the sync job, including the existing `v0.1.3` Release,
without rewriting or recreating the tag. Run it with `v0.1.3` and
`970c04712853295fd065094b11a2bd541b5a9db8` only after the protected GitHub
credential and tag policy prerequisites are in place. The manual job does not
block ordinary branch pipelines.

Before writing to GitHub, the script verifies the GitLab tag commit, waits up
to 12 bounded attempts for the mirrored GitHub tag, and requires the GitHub
tag to resolve to the exact same commit. A different target is a hard error;
the script never creates or updates tags. GitLab title, description, stable
publication state, and linked assets are the source values.

For each linked asset it looks up the matching Generic Package Registry file,
downloads it from GitLab, and verifies the package API SHA-256 and size. If a
`SHA256SUMS.txt` or `SHA256.txt` is attached, its entries are also checked.
GitHub Releases are created as drafts, then missing assets are uploaded. The
script checks GitHub's reported size/digest, publishes only after all assets
match, and downloads every public asset again to compare size and SHA-256.
GitLab job credentials are stripped when an asset download redirects to a
different host.

The operation is repeatable: matching releases/assets are preserved; missing
assets can be added; metadata, tag, extra-asset, duplicate-name, size, or
checksum conflicts fail without replacement or deletion. GET requests use
bounded retries for transient API/network failures. Uploads are not blindly
retried; rerunning the job re-reads the draft and resumes missing assets.
Release notes and assets on conflicting releases are not overwritten.

## Credentials and permissions

Before synchronization can run successfully, an administrator must:

1. Protect stable release tags with a GitLab rule such as `v*`, restricted to
   authorized release creators. Protected variables must not be exposed to
   arbitrary tag pipelines.
2. Add `GITHUB_RELEASE_TOKEN` as a masked and protected GitLab CI variable.
   Use a fine-grained GitHub token scoped only to `AmirrezaSobhi/agent` with
   repository **Contents: write**, expiration, and an owner-managed rotation
   procedure. A GitHub App installation token with the equivalent repository
   permission is preferable when the organization has an established App
   lifecycle.
3. Ensure the GitLab job token can read the project's Release and Generic
   Package Registry. If GitLab fine-grained job-token permissions are enabled,
   allow `READ_RELEASES` and `READ_PACKAGES` for this job.

No credential value belongs in source, job output, release notes, or this
document. The script checks `CI_COMMIT_REF_PROTECTED=true` and both credentials
before it makes external requests. Missing prerequisites fail visibly. The
GitLab repository mirror's SSH credentials are not used for GitHub Releases.

Creating releases requires GitHub's release API permission to write repository
contents; see [GitHub REST Releases](https://docs.github.com/en/rest/releases/releases).
GitLab supports release event webhooks, but none was configured in the audited
project, so the selected mechanism uses the existing GitLab tag pipeline and
waits for completed source release metadata; see [GitLab webhook events](https://docs.gitlab.com/user/project/integrations/webhook_events/).
The Generic Package Registry supports CI job-token access; see [GitLab Generic Packages](https://docs.gitlab.com/user/packages/generic_packages/).

## Historical reconciliation and current limitations

The existing `v0.1.3` GitLab Release is eligible for reconciliation after the
tag is protected and the credential is configured. It was **not** published
to GitHub by this change because authenticated write access was unavailable.
Its GitLab source bytes also could not be fetched in the audit environment, so
the pipeline must perform the first byte-level validation before publishing.
The eight GitHub-only historical releases are retained. No historical
conflicting release or asset has been changed.

The workflow is **not yet operational**: the protected tag rule and GitHub
write credential are missing, CI Lint/live tag execution has not been verified,
and no end-to-end GitHub publication has run. Do not describe future releases
as automatically synchronized until those prerequisites are configured and a
real existing release completes all checks.

## Retry and incident handling

1. Open the failed `release:github-sync` job and read its redacted error.
2. Confirm the GitLab Release and every linked Generic Package file are
   published and that the release tag still resolves to the pipeline commit.
3. Confirm the tag is protected and the masked CI variable is available to the
   protected tag pipeline. Never print the variable to test it.
4. Check the GitHub tag target and release/asset inventory without editing any
   conflicting item.
5. Retry the failed job in the same pipeline after resolving a transient
   condition. The job resumes a matching GitHub draft and verifies all assets.
6. Stop and escalate on tag, metadata, extra-asset, size, or digest conflict.
   Do not delete, replace, or force-update a release, asset, or tag.

Local safe tests run with:

```sh
python3 -m unittest -v tests.test_github_release_sync
python3 tools/release_sync/github_release_sync.py --help
```

The script supports `--dry-run` for authenticated inventory comparison. A
dry run performs read requests and checks but makes no GitHub release or asset
changes. Never validate credentials by echoing or logging their values.
