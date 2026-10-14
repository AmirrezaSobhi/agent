# Architecture Glossary

| Term | Meaning in this blueprint |
|---|---|
| Agent | Installed Windows execution client and its logical identity. |
| Agent Core | Local application/service logic that validates, coordinates and reports operations. |
| Agent Instance | One enrolled installation, distinct from its host Device and human User. |
| Central Control Plane | Future services for identity, registry, policy, orchestration, audit and updates. |
| Device | Windows host identity that may run one or more Agent Instances over time. |
| Execution Lease | Expiring single-writer authority for a Trading Account, tied to an owner and fencing epoch. |
| Fencing token / epoch | Monotonically increasing ownership value that causes stale writers to be rejected. |
| Idempotency key | Stable operation key used to suppress duplicate processing; it does not prove broker outcome. |
| Interactive Runtime Worker | Separate process in a nonzero Windows session that owns the MT5 API connection. |
| MT5 | MetaTrader 5 terminal and its connected broker environment. |
| Runtime Instance | A particular Worker/terminal lifecycle bound to principal, session and installation. |
| Runtime Principal | Windows account identity under which the Worker/terminal run. |
| Session 0 | Windows service session, isolated from interactive desktop sessions. |
| Support Bundle | Locally generated, minimized and redacted diagnostic archive with a manifest. |
| Tenant | Customer isolation boundary for users, Agents, accounts, policy and billing. |
| Trading Account | Broker account identity under a Tenant; visibility does not grant execution authority. |
| Unknown outcome | Operation was dispatched but available evidence cannot establish whether it took effect. Requires reconciliation. |
| Usage Record | Auditable metering event used for billing; not an authentication credential. |
| Worker IPC | Existing authenticated Named Pipe between Session 0 Agent and interactive Worker. |
