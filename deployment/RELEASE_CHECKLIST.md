# MT5 Agent Release Checklist

Start an unchecked copy for each candidate. This is a template, not a record of
a completed release. Historical release facts remain in
[CHANGELOG.md](../CHANGELOG.md). Promotion, tag creation, and publication each
require their own authorization. The completed v0.1.3 live CI record is
[versioned evidence](../docs/evidence/v0.1.3/phase4d-live-ci-acceptance.md);
[release readiness](../docs/evidence/v0.1.3/release-readiness.md) records remaining
promotion/publication conditions. Keep this reusable template unchecked.

## Candidate and source

- [ ] Record source commit, candidate version, intended scope, and reviewer.
- [ ] Confirm GitLab is canonical and GitHub is a downstream mirror.
- [ ] Review the complete diff, including explicit staging scope and docs.
- [ ] Confirm version metadata, candidate filename, and tag policy agree.
- [ ] Review current known issues and evidence status; do not infer live CI from
  local tests or lab validation.
- [ ] Confirm no credentials, local environments, generated evidence, caches,
  or build output are included in source.

## Source and build gates

- [ ] GitLab CI Lint accepts `.gitlab-ci.yml` for the installed GitLab version.
- [ ] Linux source/unit job passes on `linux-source-unit` using the Runner's
  isolated checkout/workspace.
- [ ] Windows tests and build pass on `windows-self-hosted-no-mt5`.
- [ ] Agent build environment proves MetaTrader5 and NumPy are absent.
- [ ] Recursive PyInstaller archive inspection, including PYZ, excludes MetaTrader5, NumPy, Worker implementation,
  legacy direct adapter, and local terminal inspection.
- [ ] Build evidence records commit, pipeline, version, filename, size, Python,
  dependency checks, forbidden-module inspection, and SHA-256.
- [ ] Invalid-configuration and degraded control-plane checks pass without a
  local MT5 installation.

## Real runtime and artifact custody

- [ ] `windows-self-hosted-mt5` validates Worker task/configuration, expected
  principal, nonzero session, authenticated local pipe, and protocol.
- [ ] Candidate Agent runs through its production application/HTTP path from
  Session 0; it does not import or initialize MetaTrader5 directly.
- [ ] Health, `mt5.get_symbols_total`, `mt5.get_terminal_version`, and
  `mt5.get_account_information` pass through the Worker. No trading occurs.
- [ ] Runtime evidence redacts account values and contains no credentials.
- [ ] Worker/terminal identity and session match; runtime remains connected.
- [ ] Candidate SHA-256 matches build evidence before and after runtime smoke.
- [ ] Final package gate validates matching commit, pipeline, version, filename,
  and SHA-256 without rebuilding.
- [ ] Retain build, control-plane, runtime, package receipts and job IDs.

Required invariant: **BUILD ONCE → TEST SAME ARTIFACT → RELEASE SAME ARTIFACT**.
Never rebuild or substitute the candidate after a smoke gate.

## Promotion and release authorization

- [ ] Review CI evidence and operational/security gaps, including the MT5-host
  clock-skew remediation or explicit release-owner risk acceptance.
- [ ] Retain the exact candidate and receipts before GitLab artifact expiry.
- [ ] Review draft release notes and identify which ref pipeline's candidate
  will be published; never relabel Pipeline #11 provenance.
- [ ] Require post-merge staging/main and final tag pipelines explicitly;
  the GitLab project does not currently enforce a successful-pipeline merge gate.
- [ ] Obtain separate authorization for branch promotion
  `develop` → `staging` → `main`.
- [ ] Merge the exact versioned release notes and
  `docs/releases/vX.Y.Z-authorization.json` record to protected `main`. The
  record must identify the exact tag and commit, the configured Release Owner
  GitLab user ID, an ISO-8601 approval time, a merged-main MR reference, and an
  explicit disposition and Owner approval for each known release-blocking
  risk (including KI-009). Configure protected CI variable
  `MT5_RELEASE_OWNER_USER_ID`; the tag creator must be a different user.
- [ ] Use HTTPS for the GitLab API and confirm Runner certificate trust. The
  publisher and downstream sync fail closed on HTTP because they send
  `CI_JOB_TOKEN`.
- [ ] A reviewer verifies actual GitLab MR approval before creating the tag;
  CI_JOB_TOKEN can read the MR but cannot read the approval API.
- [ ] Confirm the commit is reachable from protected `main`; only an authorized
  Maintainer may create a protected stable `vMAJOR.MINOR.PATCH` tag. That tag
  push starts automatic publication after all required gates pass.
- [ ] Preserve existing release tags/assets and historical evidence unchanged.
- [ ] Let `release:gitlab-publish` publish only the exact validated candidate
  and checksum; it does not rebuild. It validates and reads back Generic
  Package files before creating the GitLab Release.
- [ ] Confirm `release:github-sync` ran only after verified GitLab publication.
- [ ] On failure, retry the same tag pipeline after correcting the cause. Do
  not move/recreate a tag or overwrite a conflicting package, asset, or Release.
- [ ] Confirm downstream mirroring without direct GitHub release mutation.

## Scope exclusions

The release gate is read-only. It must not place, modify, cancel, or close
trades. It must not change Windows accounts, Runner registration, Scheduled
Tasks, Autologon, pipe ACLs, BitLocker, TPM, Secure Boot, or recovery keys. The
historical ACL experiment is not an ordinary release prerequisite.
