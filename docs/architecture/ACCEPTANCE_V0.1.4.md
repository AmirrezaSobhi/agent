# v0.1.4 Acceptance Checklist

**Status:** Proposed release acceptance criteria; none are claimed passed by
this documentation audit. Execute only in approved test/demo accounts. No real
trades are permitted during this mission.

## Scope and release gates

Mandatory foundation: modular UI shell/navigation, truthful real Agent/MT5
status for one active Runtime, local setup, machine/user configuration
separation, English/i18n foundation, independent UI lifecycle, service-offline
guidance, tray/close behavior, safe diagnostic/log view, and minimal local
support export. A secure local management interface and operations that require
substantial privilege are release gates, not assumed scope. Installer account
creation, Autologon, service recovery helper, production updater, or central
backend require their own explicit design approval.

## Traceable checklist

“Not executed” means no evidence was collected for v0.1.4. Existing v0.1.3 CI
does not pass these criteria by implication.

| ID | Acceptance criterion | Verification evidence required | Initial status / gap |
|---|---|---|---|
| A01 | UI runs independently from Agent Service | Windows test starts UI with Service running/stopped; UI process and service state evidence | Not executed; UI absent |
| A02 | UI crash does not terminate Agent or Worker | Fault-inject UI exit; assert Service/Worker PID and health remain | Not executed; UI harness absent |
| A03 | Agent remains operational when UI closes | Close/exit UI; poll Agent and Worker health independently | Not executed |
| A04 | Service-offline UI opens successfully | Stop Service; launch UI; inspect recovery guidance without crash/hang | Not executed |
| A05 | Cached state is clearly labeled stale | Disconnect probe source; assert observation age/source and stale label | Not executed; freshness contract absent |
| A06 | Dashboard displays actual runtime information | Compare UI projection with live diagnostic/Worker evidence, including unavailable case | Not executed |
| A07 | Unauthorized privileged requests are rejected | Negative tests by user/session/principal/action; audit denial and no side effect | Not executed; local API absent |
| A08 | Machine and user settings remain isolated | Cross-user access/write test, ACL inspection, service/UI identity test | Not executed; config split absent |
| A09 | MT5 continues in a valid interactive session | Assert principal, nonzero session, Worker/terminal identity and safe-read health | Current v0.1.3 lab evidence exists; rerun against release artifact required |
| A10 | Windows Cold Boot behavior is tested | Boot without RDP/console login; capture Service, Worker, MT5 readiness timeline | Prior lab evidence exists; v0.1.4 profile/release artifact test not executed |
| A11 | RDP disconnect behavior is tested | Disconnect/reconnect RDP without logoff; assert profile-specific runtime state | Not executed; compatibility gap |
| A12 | MT5 operation concurrency remains controlled | Concurrent requests; show one serialized lane, bounded admission and no overlapping MT5 calls | Existing Worker serialization evidence; UI/API load test not executed |
| A13 | Unknown execution outcomes are not blindly replayed | Inject timeout/disconnect after dispatch; verify outcome unknown and reconciliation before retry | No trade command exists; future command test infrastructure needed |
| A14 | Diagnostics do not expose secrets | Seed synthetic canary secrets; inspect UI, logs, exports and error paths | Not executed; bundle absent |
| A15 | Support bundles require appropriate consent | Preview and cancel path; assert no transmission; explicit consent audit for any future upload | Not executed; local export design needed |
| A16 | Installer/build output validates on supported Windows targets | Clean install/upgrade/repair/uninstall on each approved OS family; artifact evidence | Not executed; target matrix pending |
| A17 | Windows CI tests pass | Release-candidate commit's Windows jobs, with artifact and logs | Existing runtime CI passed on prior refs; no v0.1.4 UI CI job |
| A18 | No real trades are executed | Confirm demo/test account and inspect command logs/test harness; no order operations | Mission constraint; no trades run |
| A19 | v0.1.3 behavior does not regress | Same-artifact regression suite plus Session 0/Worker/pipe and safe-read smoke | Not executed for v0.1.4 |
| A20 | Build Once → Test Same Artifact → Release Same Artifact is preserved | Hash/provenance records prove tested artifact equals released artifact | Existing pipeline design/evidence; verify v0.1.4 release pipeline |

## Cross-cutting release evidence

Record exact commit and artifact SHA-256; OS build/architecture; user/session
identity without secrets; test timestamps and clock health; pipeline/job IDs;
test account/demo status; logs; failures/retries; and reviewer. Do not mark
acceptance passed from code inspection alone. If CI lacks UI, accessibility,
installer or session tests, identify the infrastructure gap and name an
approved manual gate before release.

## Explicitly deferred

Full multi-runtime execution, central Web Console, production billing,
enterprise custom roles, Remote Support implementation, central offline
license issuance, complete auto-update/rollback and production multi-Agent
failover. No criterion in this list authorizes those features for v0.1.4.
