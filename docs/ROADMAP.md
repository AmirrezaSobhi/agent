# Product Roadmap

This roadmap tracks product capability and acceptance evidence. It is not a
release promise or historical changelog. See [Action Plan](ACTION_PLAN.md) for
the immediate work queue and current status labels.

| Area | Status | Scope / acceptance |
| --- | --- | --- |
| v0.1.3 split-session runtime | IMPLEMENTED; LAB VALIDATED | Session 0 Agent to authenticated local IPC to persistent interactive Worker; MT5 remains Worker-owned. Cold-boot lab acceptance passed. |
| Safe read capabilities | IMPLEMENTED; LAB VALIDATED | Symbols total, terminal version, and account information through the Agent application path. No account values in logs/evidence. |
| Agent/Worker packaging split | IMPLEMENTED; locally validated | Agent artifact excludes MetaTrader5, NumPy, Worker implementation, and legacy direct adapter; Worker has a separate pinned environment. |
| Phase 4D CI migration | IMPLEMENTED; LOCAL VALIDATION PASSED; LIVE CI ACCEPTANCE PENDING | Linux source/unit, Windows no-MT5 build/control-plane, and Windows real-MT5 gate consume one candidate; the archive matcher checks all prohibited MT5/Worker/local-inspection modules. First live GitLab pipeline remains required. |
| Windows product provisioning | PLANNED / PENDING PRODUCTION VALIDATION | Signed installer, service registration/recovery, customer-specific runtime policy and upgrade/rollback. Lab scripts are not a polished customer installer. |
| Runtime resilience | PARTIAL | Bounded Worker restart/reconnect and degraded Agent behavior exist; broader crash, logoff, upgrade, and service recovery acceptance is required. |
| Durable command foundations | IMPLEMENTED foundation; NOT COMPOSED into production request path | SQLite, outbox, lifecycle, idempotency and reconciliation foundations require separate integration and acceptance. Presence in source is not active command processing. |
| Remote transport/configuration | IMPLEMENTED foundation; NOT PRODUCTION ACCEPTED | Kafka/mTLS and remote configuration boundaries exist; broker, certificate lifecycle, auth, outage, and security acceptance remain. |
| Trading/execution | EXCLUDED / PLANNED | No production trade capability. Requires explicit product/security authorization, typed contracts, ambiguity/reconciliation semantics, and controlled demo-only validation. |
| Commercial release readiness | NOT READY | Requires first live Phase 4D pipeline, supported installation and update paths, security/operations acceptance, and documented customer recovery. |

## Acceptance discipline

For each roadmap item retain source commit, test output, and environment- or
pipeline-specific evidence. `IMPLEMENTED` means code exists; `LAB VALIDATED`
means the named lab scenario passed; `CI ACCEPTED` means a live pipeline passed;
`PRODUCTION READY` requires supported provisioning, operations, security, and
release evidence. Do not promote one status to another by inference.
