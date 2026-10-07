# Product Roadmap

This roadmap tracks capability status and acceptance evidence. It is not a
release promise. See [Action Plan](ACTION_PLAN.md) for current planning topics.

| Area | Status | Scope / evidence |
|---|---|---|
| v0.1.3 split-session runtime | RELEASED | Tag `v0.1.3`, commit `970c04712853295fd065094b11a2bd541b5a9db8`; release Pipeline #16 passed all eight gates. The Agent runs in Session 0 and the Worker/terminal in an interactive session. |
| Safe read capabilities | RELEASED | Symbols total, terminal version, and account information through the Agent application path; account values are not retained in evidence. |
| Agent/Worker packaging split | RELEASED | The release artifact excludes MetaTrader5, NumPy, the Worker implementation, the legacy direct adapter, and local terminal inspection. |
| Historical Phase 4D candidate | HISTORICAL ACCEPTANCE | Pipeline #11 remains tied to its own source commit and binary hash; it is not the v0.1.3 release artifact. |
| Post-release validation | COMPLETE; reliability follow-up open | Pipeline #17 passed all eight final jobs on `develop`. MT5 Runtime Smoke Job #132 failed; Job #134 later succeeded. The initial failure cause is unknown, so Worker startup reliability is not marked resolved. |
| v0.1.4 | PLANNING PHASE | Evaluate Worker reliability and hybrid threading, and define evidence and acceptance criteria. Scope and release dates are not approved. |
| Windows product provisioning | PLANNED / PENDING PRODUCTION VALIDATION | Signed installer, service registration/recovery, customer runtime policy, upgrades, and rollback. Lab scripts are not a supported customer installer. |
| Runtime resilience | PARTIAL | Bounded Worker recovery and degraded Agent behavior exist; broader startup, crash, logoff, reboot, network-transition, and service-recovery acceptance remains. |
| Time synchronization operations | FOLLOW-UP | Pipeline #16 records synchronization and UTC checks for release acceptance. Autonomous polling and persistence across reboot/network transitions still need evaluation. |
| Durable command foundations | IMPLEMENTED foundation; NOT COMPOSED into production request path | SQLite, outbox, lifecycle, idempotency, and reconciliation foundations require separate integration and acceptance. |
| Remote transport/configuration | IMPLEMENTED foundation; NOT PRODUCTION ACCEPTED | Kafka/mTLS and remote configuration remain outside the accepted production request path. |
| Trading/execution | EXCLUDED / PLANNED | No production trade capability. Separate product/security authorization and controlled acceptance are required. |
| Commercial production readiness | NOT READY | Release acceptance does not establish supported installation, customer operations, service lifecycle, or broader production security readiness. |

## v0.1.4 planning questions

Planning should evaluate, without promising delivery:

- What evidence is needed to understand and improve Worker startup reliability?
- Where, if anywhere, could hybrid threading help while preserving safe MT5
  operation ordering?
- What acceptance is needed for time synchronization monitoring and persistence
  across reboot/network transitions?
- Which productization and recovery requirements should be in a future release
  scope?

No release date or feature commitment is implied. Any proposed scope requires
separate review and approval.

## Acceptance discipline

For each roadmap item, retain source commit, test output, and environment- or
pipeline-specific evidence. Do not infer that an implementation or one passing
scenario establishes reliability or production readiness. See the
[v0.1.3 release record](releases/v0.1.3-release-notes.md) and
[post-release validation](evidence/v0.1.3/post-release-validation.md).
