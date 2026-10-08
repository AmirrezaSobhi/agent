# Proposed Versioned Roadmap

**Status:** Planning proposal; version assignments are not immutable release
commitments. Dependencies and security gates are mandatory even if release
numbers move.

| Version | Proposed theme | Dependencies / gates |
|---|---|---|
| v0.1.3 | Interactive Runtime Foundation | Released. Session 0 Agent, interactive Worker, authenticated Named Pipe and safe read-only MT5 operations. Customer installer is not implied. |
| v0.1.4 | Desktop Client Foundation | UI framework compatibility/accessibility spike; secure local management contract; one active Runtime; user/machine config separation; Windows UI test strategy; no real trades in validation. |
| v0.1.5 | Installer, Recovery, Operational Hardening | v0.1.4 architecture approval; account/session consent model; tested service installation/control, supported Windows matrix, bounded recovery, logging/retention and signed packaging. |
| v0.2.x | Central Enrollment and Management | Tenant/Agent/device identities; key lifecycle and revocation; authenticated transport and policy revision contract; privacy/audit design. |
| v0.3.x | Multi-Runtime and Fleet Operations | Runtime registry, account discovery/confirmation, per-account serialization, execution leases/fencing/idempotency, partition and reconciliation tests. |
| v0.4.x+ | Commercial Platform Capabilities | Billing ledger/metering and safe exhaustion; central web management, AI orchestration, scoped support and scalable central operations. |

## Dependency and compatibility constraints

- Keep v0.1.3 Worker protocol/session separation compatible while UI work is
  added; no UI direct pipe access.
- Do not introduce trade execution without authorization, policy and ambiguous
  outcome reconciliation gates.
- Central enrollment requires distinct tenant/user/device/Agent identities,
  credential rotation and revocation before broad fleet operations.
- Multi-runtime/multi-Agent writes require leases and fencing before failover.
- Billing needs immutable usage events and pricing version; wallet balance
  never becomes auth or position-protection switch.
- New Windows UI must validate supported OS versions and packaging; Windows 7
  remains legacy test-only.
- Releases preserve Build Once → Test Same Artifact → Release Same Artifact.

## Scope-change record

Any proposed transfer of capability across these versions records the reason,
dependency impact, security review, compatibility effect and acceptance
criteria in a versioned decision/ADR. The roadmap should be updated by additive
review rather than silently changing an earlier scope.
