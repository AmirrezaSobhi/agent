# Product Vision and Platform Boundaries

**Status:** Accepted product direction; individual platform services are
future capabilities unless called out as Current in
[Implementation Baseline](IMPLEMENTATION_BASELINE.md).

## Product role

MT5Agent is the Windows-side execution component of a future commercial,
multi-tenant AI Trading Platform. The central platform decides and issues
authorized instructions. MT5Agent validates instruction shape, authenticated
source, effective policy, runtime readiness and mandatory local constraints;
then it executes only an allowed operation and returns a structured outcome.
It is not an autonomous speculative strategy engine and must not independently
choose speculative trades.

## Future platform capabilities

| Layer | Intended responsibility | Status |
|---|---|---|
| Central Control Plane | Tenant/IAM/RBAC; Agent, Device, account and runtime registry; policies, risk, orchestration, audit, support, enrollment, licensing and update management | Deferred; no claim of implementation |
| AI Trading Brain | Model/agent analysis, strategy evaluation, risk-aware decision proposal and orchestration | Deferred; always subordinate to execution authorization and safety |
| Billing Platform | Wallet, pricing, usage metering, complexity rules, transaction records and auditable usage ledger | Deferred; no production billing |
| Windows Client | Desktop UI, Service/Core, local authorization, config, runtime supervision, interactive Worker, diagnostics, audit, update client and support bundle | Mixed; see implementation baseline |
| Future deployment | Central services may evolve toward Kubernetes | Proposed evolution; not a current infrastructure assumption |

## Identity separation

Never reuse identifiers or credentials across these concepts:

- **Tenant/customer identity:** commercial ownership boundary.
- **User identity:** human principal; assigned roles and permissions within a tenant.
- **Device identity:** Windows host enrollment identity.
- **Agent Instance identity:** one installed client instance and its lifecycle.
- **Trading Account identity:** broker/account relationship, with sensitive fields protected.
- **Terminal Installation identity:** local MT5 installation/path/version.
- **Runtime identity:** process/session/principal that owns a running terminal connection.
- **Authentication token:** proof for a specified service and audience, with expiry and revocation.
- **Billing credit:** monetary/usage accounting unit; never an authentication token or implicit authorization.

## Billing and safe credit exhaustion

Usage-based credit consumption is the primary planned model; a fixed monthly
subscription is not mandatory. Metered events need stable identifiers,
pricing-policy version, quantity/complexity, timestamp, Agent/account context,
and an auditable ledger entry. Wallet balance is not a source of truth for
identity or authorization.

When credit is insufficient, future central policy may deny new discretionary
trading commands or require a customer action. Agent availability, central
connectivity, authorization for *new* trades, and protection/monitoring of
existing positions remain separate. Credit depletion must not silently stop
position observation, report delivery where feasible, or protective actions
that policy explicitly permits. Grace, offline metering, debt/settlement, and
which protective commands remain allowed are **Open Decisions**.

## Customer scale and account visibility

A customer may have multiple users, roles, devices, Agent Instances, MT5
installations and Trading Accounts. Account visibility from several Agents
does not mean each can execute simultaneously. Enforce a lease, fencing epoch,
idempotency, duplicate suppression, and broker-state reconciliation before
failover. Four future account workflows must coexist: automatic discovery,
manual terminal/account configuration, explicit customer confirmation, and
central web-console management. Discovery is evidence for confirmation, not
permission to trade.

## Scope protection

v0.1.4 remains client-side and limited to the [acceptance scope](ACCEPTANCE_V0.1.4.md).
Central web management, production billing, enterprise custom roles, remote
support, central offline-license issuance and production multi-Agent failover
are explicitly deferred. Adding them requires a separately reviewed plan and
security decisions.
