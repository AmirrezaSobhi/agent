# Proposed Versioned Roadmap

**Status:** Planning proposal; version assignments are not immutable release
commitments. Dependencies and security gates are mandatory even if release
numbers move.

| Version | Proposed theme | Dependencies / gates |
|---|---|---|
| v0.1.3 | Interactive Runtime Foundation | Released. Session 0 Agent, interactive Worker, authenticated Named Pipe and safe read-only MT5 operations. Customer installer is not implied. |
| v0.1.4 | WPF Desktop Client Foundation — approved Option A | C#/WPF/XAML/.NET Framework 4.8/MVVM; client for an already installed/provisioned Python Agent/Runtime; dedicated authenticated management pipe; one active Runtime; per-user preferences; reproducible build and testable user-scope package on the approved OS matrix. No commercial Service installer/provisioning. |
| v0.1.5 | Installer, Recovery, Operational Hardening | Separate approval after v0.1.4; account/session consent model; tested Service installation/control, bounded recovery, operational retention and signed packaging. |
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
  is out of commercial scope. Approved v0.1.4 matrix: Windows 10 x64, Windows
  11 x64, Windows Server 2022 x64 and Windows Server 2025 x64. Server requires
  Desktop Experience; Windows 10 lifecycle risk is tracked separately.
- Releases preserve Build Once → Test Same Artifact → Release Same Artifact.

## v0.1.4 execution phases

The implementation sequence is [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md):
WPF foundation → secure management IPC → real Dashboard → Desktop operations →
hardening → package/release. Each phase lists dependencies, likely modules,
deliverables, acceptance, tests and risks. It is an execution plan, not an
authorization to change application or CI files in this documentation task.

## Scope-change record

Any proposed transfer of capability across these versions records the reason,
dependency impact, security review, compatibility effect and acceptance
criteria in a versioned decision/ADR. The roadmap should be updated by additive
review rather than silently changing an earlier scope.
