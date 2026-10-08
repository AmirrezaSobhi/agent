# v0.1.4 Phase 0 — Baseline and Architecture Evidence

**Audit date:** 2026-10-08
**Repository:** GitLab `root/agent`, project `1`
**Authoritative remote:** `origin` (`ssh://git@gitlab.local:2222/root/agent.git`)
**GitHub mirror:** `AmirrezaSobhi/agent`

This is a read-only evidence snapshot plus local fast-forward of a stale local
branch. No remote release object, tag or protected branch was changed. The
related product plan is [v0.1.4 Desktop UI](../../planning/v0.1.4-desktop-ui.md).

## Baseline and branch relationship

| Ref | SHA at audit | Relationship |
|---|---|---|
| GitLab `main` | `dbca8ca7fe65ca14a95a106d215cc9fa439ac01f` | Expected baseline; merge commit for MR !3. |
| GitLab `staging` | `e34d6d783e42c5d2fb5f1448af5f5e01d01cf095` | Parent of `main`; MR !3 source. |
| GitLab `develop` | `428d115b407dcec5f546bde4e3c3a8de5c437793` | Ancestor of `staging`; development history preserved. |
| GitHub `main` / `staging` / `develop` | Same respective SHAs | Fetched mirror refs match GitLab. GitHub `main` API also reports `dbca8ca…`. |

`dbca8ca…` is still the correct v0.1.4 starting baseline. The historical
expected main commit is exact. Local `main` had been at `84e71cd…`, a strict
ancestor six commits behind `origin/main`; it was safely fast-forwarded to
`dbca8ca…` after confirming it was not checked out in another worktree. Local
`staging` and `develop` initially matched their authoritative refs. Phase 0
was merged by MR !4 from `codex/v014-phase0-discovery` into `develop` after the
MR pipeline passed. Merge commit `b1b915e4d80167fe41b6e99e03b9087269334d49`
contains the authoritative `main` history and Phase 0 docs. Post-merge
Pipeline #35 also passed all eight required jobs; `staging` remains at its
promotion point with the same tree as `main`.

GitLab reported MR !3 merged from `staging` to `main`, merge commit
`dbca8ca…`, and protected `main`/`staging` with Maintainer-only push/merge
access and force-push disabled. Protected tag pattern `v*` permits Maintainers.
The branch flow is intentional: `develop` → `staging` → `main`; they need not
have identical tips. At the post-Phase-0 state, ancestry is `staging` → `main`
→ `develop`. No valid post-release commits were discarded or rewritten.

## v0.1.3 historical boundary

- Protected tag `v0.1.3` resolves to `970c04712853295fd065094b11a2bd541b5a9db8`.
- GitLab Release and Package Registry record artifact
  `MT5Agent-v0.1.3.exe`, 8,124,497 bytes, SHA-256
  `175ff421e06d0c7394721dcf2aaa9509b953bc3d9c3d8d7f6fab7afb01e4ab28`.
- Pipeline #16 on the tag passed all eight required jobs; build Job #121 and
  package Job #125 succeeded. The release evidence says the same build artifact
  flowed through smoke, runtime and package, with no post-acceptance rebuild.
- GitHub now has the `v0.1.3` Release (ID 406309298) targeting the same commit
  and four official assets. GitHub asset metadata reports the same executable
  size and SHA-256. The mirror's release appeared after successful manual
  `release:github-reconcile` Job #231 in web Pipeline #29 at commit `adbc4be…`;
  the automatic tag-pipeline publisher path remains separately unproven.
- GitLab's Release API also includes the four generated source archives. Those
  are GitLab-generated source downloads, not extra binary deliverables.

The GitHub Release API digest and GitLab package/release metadata agree with the
published checksum. This audit did not independently obtain a complete local
copy of the binary; byte-for-byte local artifact rehash is therefore not
claimed.

## CI baseline

GitLab API evidence at audit time:

| Ref | Pipeline | SHA | Status | Jobs |
|---|---:|---|---|---|
| `main` | #32 | `dbca8ca…` | success | Jobs #248–255: Windows validate, Linux tests, Windows tests, Windows build, invalid-config smoke, degraded control-plane smoke, MT5 runtime smoke, package. All success; all required. |
| `staging` | #30 | `e34d6d7…` | success | Jobs #232–239, same eight required jobs, all success. |
| `develop` | #25 | `428d115…` | success | Jobs #191–198, same eight required jobs, all success. |
| v0.1.3 tag | #16 | `970c047…` | success | Jobs #118–125, all eight release gates success. |
| Phase 0 MR | #34 | `4d2332b…` | success | Jobs #264–271, all eight jobs success; MR !4 merged to `develop`. |
| Post-merge `develop` | #35 | `b1b915e…` | success | Jobs #272–279, all eight jobs success. |

The release jobs are protected stable-tag push jobs. They were not run by these
branch pipelines. The successful v0.1.3 release proves the older publication
path used for that release; it does not prove the new GitLab-first publisher's
HTTPS/API/token path. The v0.1.3 GitHub mirror was subsequently reconciled by
manual Job #231 (allow-failure job) in Pipeline #29; this is distinct from an
automatic tag-pipeline publication.

## Runner inventory

GitLab listed three active, online project runners. API descriptions and tags
are used as runner identity; private IPs and tokens are intentionally omitted.

| Runner / tag | Observed host facts | Demonstrated capability | Limitation |
|---|---|---|---|
| `mt5-agent-mani-pc-linux-source-unit` / `linux-source-unit` | Linux amd64; Runner 19.4.1; same Linux host as the source checkout. | Linux validation/unit tests and release Python publisher jobs. | Not a Windows/UI/MT5 runner. |
| `mt5-agent-win10-no-mt5` / `windows-self-hosted-no-mt5` | Windows 10 Pro 22H2, build 19045, x64; Runner 19.4.0; Python 3.11.9; Windows PowerShell 5.1; Runner service automatic and running in Session 0. Console Session 1 was active during inspection. | Windows validation, tests, isolated Agent build, smoke and packaging. CI explicitly checks that MetaTrader5/NumPy are absent from the Agent build environment. | An active console is present, but no UI automation job/harness or desktop input/render test was verified. This host is not for MT5 integration. |
| `mt5-agent-win10-mt5` / `windows-self-hosted-mt5` | Windows 10 Pro 22H2, build 19045, x64; Runner 19.4.1; Python 3.11.9; Windows PowerShell 5.1; Runner service automatic and running in Session 0. Console Session 1 was active during inspection. | Pipeline #16/#25/#30/#31/#32 MT5 smoke jobs succeed; prior accepted release evidence places Worker and MT5 terminal in interactive Session 1 and Session 0 Agent-to-Worker IPC. | No UI automation job/harness or desktop input/render test was verified. |

Windows runners can be distinguished for no-MT5 vs MT5 tests by tag. Both
Windows hosts had an active console desktop session in a live read, but their
GitLab Runner services remain in Session 0. Without a UI automation job/harness,
desktop readiness is **PARTIAL**, not fully accepted. Interactive runtime tests
use the MT5-tagged host and existing locally provisioned runtime/task
configuration. Runner API shows all three unprotected;
their unprotected status is not a reason to place secrets in test output.

## Architecture traced from source

- `agent/main.py` is the CLI entry: version-only, JSON diagnosis, or startup.
  It loads environment configuration, configures safe logging, composes the
  application, installs process shutdown handlers and runs `ApplicationHost`.
- `agent/composition.py` wires `Agent`, dispatcher, application boundary,
  HTTP transport/host and observability. The Windows default is
  `RuntimeWorkerMT5Adapter`; non-Windows/development can select direct MT5.
- `agent/application/host.py` orders start → serve → stop and contains startup,
  host and shutdown failures. Windows production acceptance runs the Agent in
  Session 0. A generally productized Windows Service installer/recovery path is
  not present; Runner and lab provisioning are not customer installation.
- Windows runtime configuration is read from HKLM
  `SOFTWARE\MT5Agent\Runtime`; HTTP bind/port/request limit and logging are
  environment settings. No active server URL, customer login, generic config
  file loader or credential-store integration exists.
- `--diagnose --json`, `agent.get_status`, `agent.get_health`, and the runtime
  adapter expose process/Worker/MT5 state. They do not supply an explicit
  live/cached/inferred/unknown freshness contract for UI display.
- Logging writes fixed lifecycle messages; current logger levels are DEBUG,
  INFO, WARNING and ERROR, and sensitive payloads are excluded. File output is
  append-only with no rotation/retention. No UI viewer, TRACE level or support
  bundle exists.

### Runtime and Session model

The accepted lab topology uses a Session 0 Agent/control process and a
dedicated standard interactive runtime user. A locally configured Autologon
bootstrap and `AtLogOn` Scheduled Task start the persistent Worker in a
nonzero session; the Worker owns the MT5 Python package/API and terminal. The
Agent remains alive with degraded health if Worker/pipe is unavailable. Pipeline
#16 acceptance reports boot without RDP/console login, but general customer
service installation and recovery remain unaccepted. Lock/disconnect behavior
must be tested explicitly; RDP is not the intended lifecycle owner.

### IPC and concurrency

`agent/infrastructure/windows_named_pipe.py` implements local
`\\.\pipe\MT5Agent.Runtime.v1` message-mode IPC, rejects remote clients,
requires exactly one configured control principal and applies an exclusive
pipe DACL. The Worker checks the authenticated peer principal/SID and
nonzero/session policy; the control adapter requires its own Session 0 role.
Messages are versioned JSON, capped at 65,536 bytes, single-instance, and
request/response uses an acknowledgement. Connection and read deadlines use
`time.monotonic()` with bounded retry loops. This boundary is specifically
Agent-to-Worker IPC, not a desktop UI API.

The HTTP adapter uses `ThreadingHTTPServer`, so request handlers can execute
concurrently with no application-level bounded admission. Default bind is
loopback; the configurable host can be changed. Default composition injects no
authenticator/authorizer, so `ApplicationBoundary` selects allow-all defaults.
Do not expose this endpoint beyond its loopback default without an approved
authentication and authorization design.

The Worker accepts one pipe client/request at a time; its persistent MT5
runtime uses a lock to serialize API operations. The Agent runtime adapter also
uses an `RLock` around lifecycle and runtime calls. One slow operation can
therefore delay subsequent Worker work. IPC timeout/transport failure does not
prove the Worker operation was cancelled. No bounded queue/backpressure,
end-to-end cancellation or active request-drain policy is connected to this
path. `BoundedScheduler` (limit 100, priorities and aging) and cancellation
contracts exist as foundations but are not composed into the production
request path. Keep MT5 operations serialized unless thread-safety is proven.

## v0.1.4 UI planning status

`docs/planning/v0.1.4-desktop-ui.md` is tracked and was introduced by commit
`04f6e7969321d065384eab40aad927addb73ef2c` on `develop`. It records KivyMD as
the preferred but conditional Windows desktop direction; UI/Core lifecycle
separation; tray failure isolation; local-only client scope; explicit live,
cached, inferred and unknown status; credential identity questions; and central
management, automatic updates and backend features as deferred. It correctly
leaves startup/tray ownership, secure UI control API, server contract, credential
principal, and Windows/accessibility support matrix open. Source review agrees
with those open questions. CI proves no UI dependency, UI implementation,
tray process, credential store, updater or UI smoke job is present.

The existing plan now contains a capability matrix, architecture boundaries,
test matrix, seven-phase implementation sequence, and ADR candidates. The
KivyMD choice remains unfinalized pending the compatibility spike.

## Release automation findings

| Known issue | Status | Evidence / action before v0.1.4 publication |
|---|---|---|
| GitLab API is HTTP while publisher requires HTTPS | CONFIRMED | Project API/web URL is `http://gitlab.local`; release publisher fails closed. Configure TLS and use an HTTPS `CI_API_V4_URL`. |
| Runner trusts future TLS certificate | UNVERIFIED | HTTPS is not currently available at the configured GitLab URL. Install/verify trust on Linux publisher runner before tag. |
| Protected `MT5_RELEASE_OWNER_USER_ID` | CONFIRMED missing | Project CI variable inventory has no such key. Configure protected variable and perform separate human approval/risk review. |
| Effective `CI_JOB_TOKEN` package/Release write access | UNVERIFIED | No new publisher tag pipeline has exercised write/read-back. Do not substitute a PAT silently. |
| Traceable Release Owner approval/risk acceptance | UNVERIFIED | Publisher validates version/commit-bound authorization and merged MR, but its CI job token cannot independently prove MR approval. Human Maintainer review remains a required control. |
| End-to-end automatic v0.1.4 publication | UNVERIFIED | Do not test with a fake tag. Test publisher/read-back code with local fakes; production proof only on the authorized v0.1.4 tag after all other gates. |
| GitHub v0.1.3 mirror/release | RESOLVED for v0.1.3 | Git refs match. GitHub Release is now published at the v0.1.3 commit with four assets; manual reconcile Job #231 succeeded. This does not prove future automatic sync. |

Current branch CI is healthy, but release automation is **PARTIAL**, not ready.
The immediate hard blocker is HTTP vs required HTTPS; Release Owner variable and
the human review procedure also need setup. Preserve artifact provenance and
the build-once chain; publisher must consume the accepted package artifact.

## Clock-skew classification

Existing KI-009 recorded the historical approximately 10h30m disagreement.
Pipeline #16 release evidence reports active W32Time synchronization, an
independent UTC check and GitLab timestamp correlation. This is point-in-time
evidence only; reboot/network-transition persistence and autonomous monitoring
remain open. In a live read on 2026-10-08, the no-MT5 Runner's W32Time service
was stopped (demand-start); the MT5 Runner's service was running but
`w32tm /query /status` reported leap indicator 3 (not synchronized), stratum 0,
source `time.windows.com,0x9`, and last successful sync at 02:56 local. Both
were configured for `Iran Standard Time` (+03:30). One contemporaneous sample
put each Windows wall clock within roughly five seconds of Linux UTC; this does
not establish a current 10h30m offset, but confirms time-source synchronization
is not currently verified. The release-readiness record and checklist require
clock remediation or explicit Release Owner risk acceptance before release.
Treat this as a **potential v0.1.4 release blocker** until a pre-tag time-source
and offset check passes or the owner records acceptance. The active HTTP
timestamp validator checks ISO-8601 but does not implement expiry, and active
named-pipe deadlines use a monotonic clock. No active token-expiration decision
was found. KI-009 is the formal v0.1.5 investigation/acceptance backlog.

## Verification limits

- Git refs, ancestry, GitLab project/branch/tag/release/pipeline/job/runner
  metadata, protected branch/tag rules, configured variable keys and public
  GitHub ref/release/asset metadata were read during this audit.
- Remote Windows hosts were queried read-only for OS build, Python and
  PowerShell versions, active session, Runner service state/session, time-zone
  and W32Time status. Job records corroborate practical capabilities.
- Pipelines #33–35 were generated automatically by the normal MR/push workflow;
  the latest MR and post-merge pipelines passed. No release tag or published
  release/package was created or modified, and no branch-protection or runner
  setting was changed. No real trading operation was executed.
- GitLab historical artifact identity is verified by registry/release and
  GitHub checksum metadata; this snapshot does not claim an independent
  byte-for-byte local rehash.
