# v0.1.3 Phase 4D live CI acceptance

**Verdict: LIVE CI ACCEPTED / GO**, recorded 2026-10-06. This accepts the
candidate below; it does not authorize promotion, tagging, or publication.

## Provenance

| Field | Accepted value |
| --- | --- |
| Project / ref | GitLab `root/agent`, `develop` |
| Source commit | [`c4b945122ad7e7174dbbb433cb91b42cb66f1c72`](http://gitlab.local/root/agent/-/commit/c4b945122ad7e7174dbbb433cb91b42cb66f1c72) |
| Pipeline | [#11](http://gitlab.local/root/agent/-/pipelines/11), push, success |
| Version / filename | `0.1.3` / `MT5Agent-v0.1.3.exe` |
| Size | **8,124,304 bytes** |
| SHA-256 | `797eb30f4e26f6668001c5edb3a3bce6edbeb3e0d13b5644bae925c2448461d9` |
| Build Python | 3.11.9, isolated Windows environment |
| Final package | [Job #85 artifacts](http://gitlab.local/root/agent/-/jobs/85/artifacts/download) |

Documentation follow-ups and later ref pipelines do not change this source
commit, pipeline, or hash. Do not relabel receipts to a later commit.

## Final live jobs

All roles retained explicit tags and `run_untagged=false`.

| Job | Gate | Status | Runner role tag |
| --- | --- | --- | --- |
| [78](http://gitlab.local/root/agent/-/jobs/78) | `validate:windows` | success | `windows-self-hosted-no-mt5` |
| [79](http://gitlab.local/root/agent/-/jobs/79) | `test:linux` | success | `linux-source-unit` |
| [80](http://gitlab.local/root/agent/-/jobs/80) | `test:windows` | success | `windows-self-hosted-no-mt5` |
| [81](http://gitlab.local/root/agent/-/jobs/81) | `build:windows` | success | `windows-self-hosted-no-mt5` |
| [82](http://gitlab.local/root/agent/-/jobs/82) | `smoke:invalid-configuration` | success | `windows-self-hosted-no-mt5` |
| [83](http://gitlab.local/root/agent/-/jobs/83) | `smoke:control-plane` | success | `windows-self-hosted-no-mt5` |
| [84](http://gitlab.local/root/agent/-/jobs/84) | `smoke:mt5-runtime` | success | `windows-self-hosted-mt5` |
| [85](http://gitlab.local/root/agent/-/jobs/85) | `package:windows` | success | `windows-self-hosted-no-mt5` |

## Verification summary

- GitLab API independently confirmed Pipeline #11 source/ref/status and Jobs
  #78–#85. Downloaded JUnit reports confirmed Linux **209 passed, 34 skipped**
  (Python 3.14) and Windows **248 passed, 2 skipped** (Python 3.11.9).
  Linux excludes the native Windows launcher module and skips Windows/PowerShell
  gates; the two Windows skips are the non-mandatory dedicated ACL experiment.
- MetaTrader5 and NumPy were absent from the isolated Agent build environment.
  Worker requirements remain separate and pinned: MetaTrader5 5.0.6231,
  NumPy 2.4.6, pywin32 312 on Windows.
- Recursive PyInstaller inspection, including embedded PYZ, found no
  MetaTrader5, NumPy, `agent.adapters.mt5_adapter`,
  `agent.infrastructure.interactive_mt5_worker`, or
  `agent.infrastructure.terminal_inspection`. Independent recursive inspection
  of the downloaded candidate also passed all five exclusions.
- Independent downloads of **81 → 82 → 83 → 84 → 85** had identical executable
  size/SHA-256. Build/control/runtime/release receipts agree on commit, pipeline,
  version, filename and hash; runtime before/after hashes match. The release
  receipt records `build_once=true`, `post_smoke_rebuild=false`, and both gates
  PASS. Packaging succeeded without rebuilding.
- Invalid configuration returned expected exit **2**. Degraded control smoke
  kept the Agent alive in **Session 0**, `AGENT_RUNNING_DEGRADED`,
  `RUNTIME_UNAVAILABLE`, Worker unavailable.
- Runtime preflight validated the configured control/runtime identities, task
  SID and interactive-token mode, authenticated local IPC and protocol **1**.
  The candidate Agent ran in **Session 0**; Worker and MT5 shared the configured
  standard Runtime identity/SID and **Session 1**. Terminal build was **6235**.
  Machine names, SIDs, private profile paths, and transient PIDs are omitted here.
- The production Agent HTTP/application path passed health before reads and
  `AGENT_RUNNING + MT5_CONNECTED` afterward, with unchanged Worker identity.
- Safe reads: `mt5.get_symbols_total` **PASS (12,335)**;
  `mt5.get_terminal_version` **PASS (500, 6235, 02 Oct 2026)**;
  `mt5.get_account_information` **PASS (28 fields; all values withheld)**.
  **No trading operation was performed.**
- The retained post-cleanup read-only operator observation confirmed the same
  Worker and terminal identities remained alive in Session 1, the Worker task
  remained running/enabled, and no candidate Agent process remained. This
  observation supplements the CI receipt, which records health before cleanup;
  raw host/process evidence stays outside the repository.

The final package contains `reports/build.json`, `invalid-configuration.json`,
`control-plane.json`, `mt5-runtime.json`, `release-evidence.json`, and
`sha256.txt`. This record retains only the durable, redacted summary.

## Risks and next gates

- Approximately **10h30m MT5-host clock skew** affects cross-host event ordering,
  freshness/deadline/replay interpretation and audit correlation. It did not
  invalidate the verified hash/session/non-trading CI gates. Controlled staging
  may proceed with this risk recorded; publication requires approved remediation
  and revalidation or explicit release-owner risk acceptance. See
  [Operations](../../OPERATIONS.md#clock-skew-and-audit-correlation).
- CI uses the explicitly approved existing Liara package mirror; top-level pins
  are unchanged, while transitive build dependencies are not fully hash-locked.
- Job #85 artifacts are scheduled to expire **2026-11-05**; retain the exact
  package/receipts under separate authorization before expiry. Rebuilding does
  not recover this accepted binary.
- Signed installation, managed service/recovery, customer provisioning, broader
  operational/security acceptance, and trading are outside this accepted scope.

See [release readiness](release-readiness.md),
[draft notes](../../releases/v0.1.3-release-notes.md), and
[Release Process](../../RELEASE_PROCESS.md) for separate promotion/publication gates.
