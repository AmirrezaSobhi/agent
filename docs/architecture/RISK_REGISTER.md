# Architecture Risk Register

**Status:** Open risks at Blueprint v1.0-draft, updated after Phase 2 evidence.
Priority is qualitative and
must be reassessed as evidence changes.

| ID | Risk | Impact | Mitigation / evidence gate | State |
|---|---|---|---|---|
| AR-01 | WPF reuses permissive `/command` defaults | Local processes can issue currently exposed reads/commands; future privilege escalation | WPF uses dedicated Management.v1 only; keep `/command` excluded; ADR-ARCH-017 | Mitigated for WPF; keep excluded |
| AR-02 | Service Session 0 cannot directly own interactive MT5 session | Runtime unavailable or insecure desktop interaction workaround | Preserve split-session Worker; session lifecycle matrix; existing ADR-001 | Accepted boundary; recovery incomplete |
| AR-03 | Autologon/account bootstrap exposes credentials or creates unusable session | Credential compromise or failed boot | Explicit consent, identity-specific secret design, session readiness check | Open, installer gate |
| AR-04 | RDP disconnect/logoff/restart semantics vary by Windows policy | Unexpected Worker exit or duplicate runtime | Profile-specific tests on each supported OS | Open |
| AR-05 | Concurrent requests exceed MT5 API safety or timeout leaves work running | Duplicate/unknown trading action | Serialized operation lane, bounded admission, reconcile ambiguous result | Open; no production trade commands |
| AR-06 | Same account visible from several Agents | Split-brain writes and duplicate orders | Execution lease, fencing epoch, idempotency and broker reconciliation | Deferred to multi-Agent phase |
| AR-07 | UI displays stale state as current | Operator acts on false readiness | 5 s polling/15 s stale threshold and explicit stale/error state implemented; verify age presentation interactively | Open UI verification gate |
| AR-08 | Machine, user and central policy values collide | Privilege escalation or stale override | Explicit ownership/schema/revision and deny-precedence model | Proposed |
| AR-09 | Credential storage is bound to wrong Windows identity | Runtime cannot use or leaks secret | Validate access identity, rotation, backup and recovery before selection | Open |
| AR-10 | Support bundle includes broker or customer secrets | Privacy/financial harm | Allowlist collection, redaction, manifest, preview, consent, secret scan | v0.1.4 gate |
| AR-11 | Installer/update migration fails during active runtime | Downtime or incompatible state | Signed artifacts, safe install windows, staged update and tested rollback | Deferred; release gates needed |
| AR-12 | WPF package/runtime behavior is not fully verified across the approved OS matrix | Installation/UX regressions | Windows 10 Phase 5 build and interactive evidence; Windows 11/Server rows deferred by PO; validate before commercial release | Open release gate; deferred OS tests do not block Phase 5 |
| AR-13 | Interactive desktop evidence is limited to one Windows 10 display/session | DPI, session and accessibility regressions | Windows 10 Session 1 UIA/screenshots completed; test other DPI and required lifecycle when safe | Partially mitigated; 96 DPI only |
| AR-14 | Billing exhaustion disables protective operation | Existing exposure unmanaged | Separate new-order authorization from position protection; explicit offline policy | Open business/security policy |
| AR-15 | Release publisher not exercised over required TLS/token path | Failed or unsafe publication | Recheck HTTPS trust, scoped write access, owner approval, read-back | Open release readiness item |
| AR-16 | Clock drift breaks expiry, audit ordering or release evidence | Incorrect authorization/time windows | Verify synchronized clocks, monotonic local deadlines, bounded skew policy | Open compatibility/release gate |
| AR-17 | Management pipe caller identity/DACL or SID provisioning differs under the installed Agent Service | Cross-user data leak or unauthorized Runtime control | Worker ACL DACL rollback passed; temporary SCM harness verified the real Agent Core token, allowed Administrator access and LocalSystem operation denial; Windows 10 Users-only account SID `...-1011` was denied by the live Pipe DACL with Win32 error 5 before application authorization; validate eventual product Service identity | Mitigated for the tested harness; product Service identity/provisioning remains a P0 release gate |
| AR-18 | Windows 10 commercial support outlives Microsoft security servicing | Customer UI runs on an exposed OS | Disclose lifecycle; define edition/build and current ESU/security update condition; review per release | Accepted OS with active lifecycle risk |
| AR-19 | v0.1.4 package accidentally provisions or changes Agent Service | Unplanned privileged changes/regression | User-scope package; before/after SCM/config invariant tests; no installer/service edits in Option A | Release blocker |

No risk entry asserts a vulnerability has been exploited. Risks here are
architectural failure modes and missing verification evidence.

## Phase 5 evidence update — 2026-10-08

| ID | Updated Phase 5 evidence / treatment |
|---|---|
| AR-04 | Open: console Session 1 UI and Worker fixture were tested. RDP disconnect/reconnect, logoff/login and reboot were not run on the shared Runner. |
| AR-07 | Partially mitigated: Phase 5 screens show explicit offline/unavailable/timeout states; C# stale-status tests passed. Live Service timestamps remain unavailable. |
| AR-12 | Open for commercial release: official net48 clean build and Windows 10 interactive UI passed; no deployable package was validated. Windows 11/Server OS tests are `DEFERRED — PRODUCT OWNER VALIDATION`, not a Phase 5 blocker. |
| AR-13 | Partially mitigated: Windows 10 interactive UIA and evidence screenshots captured at 96 DPI. Other DPI scales and assistive technology remain pending. |
| AR-17 | DACL denial is verified for the tested harness: allowlisted Admin operations succeeded; a Users-only local account (`...-1011`) was rejected by the runtime Pipe DACL at `CreateFile` with error 5; observed SDDL contained only LocalSystem and the configured Administrator ACE. The NetworkService task failure remains a harness failure. Product Service identity/provisioning and cross-session behavior remain a P0 release gate. |
| AR-20 | Revised: Windows 11/Server 2022/2025 tests are explicitly deferred to Product Owner validation and are excluded from Phase 5 completion. The three OS rows are not an infrastructure blocker. |
| AR-21 | New — no productized SCM Service wrapper/installer exists. A temporary SCM harness was explicitly authorized, exercised and rolled back on `window10-test`; it hosted the real Python Agent Core in Session 0 with Runtime disabled. Customer-ready SCM provisioning, recovery policy and live Worker session remain unverified. |
| AR-22 | Phase 5 closure Pipeline [#48](http://gitlab.local/root/agent/-/pipelines/48) passed all 9 jobs on `bb7013f30c43ddf940212f9332341c0fb51ba55d`. The standalone Windows DACL probe is manually executed evidence, not a CI job. |
| AR-23 | New — Windows 10 UI Automation cannot identify the individual NotifyIcon or expose its context menu from the `User Promoted Notification Area` toolbar. Close-to-tray was directly verified to keep the UI process alive with no main window; actual menu Exit remains uninvoked. Isolated as an automation-surface limitation; manual tray Exit verification remains a commercial-release check. |

No real trade was executed. No Windows 11 or Server environment was provisioned or
accessed. The Windows 10 test reports and screenshots are in the [Phase 5
evidence bundle](../evidence/v0.1.4/phase5/windows10-19045/).

## Phase 6 distribution risks

| ID | Risk | Impact | Mitigation / evidence gate | State |
|---|---|---|---|---|
| AR-24 | Desktop package contains undeclared binaries or differs from tested build | Supply-chain confusion or execution of untested bits | Build once; manifest/checksum; downstream same-artifact verification; content allowlist | PASS for package hash/manifest/provenance verification in pipeline #53; independent secret-canary scan remains pending |
| AR-25 | ZIP is unsigned or signer identity is unavailable | Users cannot authenticate publisher; tampering warning | Require authorized production certificate and verified Authenticode signature before public distribution | BLOCKED for commercial release; package build may complete unsigned |
| AR-26 | Desktop upgrade/removal mutates user or Agent data | Lost preferences, Service/runtime interruption | Side-by-side version folders; keep prior build; preserve LocalAppData and machine/runtime state; before/after tests | PENDING: runbook and automated preference tests only; no package replacement/removal walkthrough |
| AR-27 | User assumes Windows 10 testing proves all approved OS families | Unsupported behavior or lifecycle assumptions | Explicit per-OS result; Windows 11 and Server rows remain `DEFERRED — PRODUCT OWNER VALIDATION` | Active disclosure; not Phase 6 blocker |

Phase 6 must not claim commercial readiness from successful package validation.
Public publication remains separately gated by signing, Product Owner approval,
Windows lifecycle policy, and any remaining customer deployment requirements.
