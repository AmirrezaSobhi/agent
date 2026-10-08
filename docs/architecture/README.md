# MT5Agent Architecture

**Status:** Architecture Blueprint v1.0-draft; technology and Option A release
boundary approved by Product Owner; Phase 1 WPF foundation and Phase 2
read-only Management IPC implemented, with production provisioning, full OS
matrix and interactive-verification gaps recorded.
**Baseline:** `origin/develop` at `d99182211696ef877171fda287dee01ef6e3fce7` (2026-10-08).

This directory is the proposed authoritative architecture reference. Existing
records elsewhere in `docs/` remain intact; this blueprint links to them and
does not supersede historical release evidence. Status labels are normative:

- **Current implementation** — evidenced in source, tests, or a cited CI record.
- **Accepted target architecture** — a product direction explicitly recorded
  as confirmed or accepted; it may still need implementation.
- **Proposed design** — a concrete design for review, not approval.
- **Deferred capability** — intentionally outside v0.1.4.
- **Open decision** — evidence or Product Owner approval is still required.

## Reading order

1. [Blueprint](BLUEPRINT.md) — architecture overview, boundaries, diagram, scope.
2. [Implementation baseline](IMPLEMENTATION_BASELINE.md) — verified state and gaps.
3. [Product vision](PRODUCT_VISION.md) and [domain model](DOMAIN_MODEL.md).
4. [Security model](SECURITY_MODEL.md), [trading safety](TRADING_SAFETY.md),
   [Windows runtime](WINDOWS_RUNTIME.md), and [local API](LOCAL_API.md).
5. [Desktop UI](DESKTOP_UI.md), [configuration](CONFIGURATION.md), and
   [operations](OPERATIONS.md).
6. [WPF Solution and Design System](WPF_SOLUTION.md),
   [IPC contract](IPC_CONTRACT.md), and [quality gates](QUALITY_GATES.md).
   Phase 1 code and build/test instructions are in
   [`src/desktop`](../../src/desktop/README.md); the Management v1 pipe is
   read-only and its scope/evidence are recorded in the IPC contract.
7. [Implementation plan](IMPLEMENTATION_PLAN.md), [roadmap](ROADMAP.md),
   [risks](RISK_REGISTER.md), [v0.1.4 acceptance](ACCEPTANCE_V0.1.4.md),
   [Windows compatibility matrix](WINDOWS_COMPATIBILITY.md), and [glossary](GLOSSARY.md).
   Phase 6 package and release evidence: [Distribution](DISTRIBUTION.md) and
   [Release Checklist](RELEASE_CHECKLIST.md).
8. [Architecture ADRs](adr/README.md) (17 records; one superseded historical ADR).

## Existing source records

- [Repository architecture](../ARCHITECTURE.md)
- [Target architecture](../TARGET_ARCHITECTURE.md)
- [Runtime architecture](../MT5_RUNTIME_ARCHITECTURE.md)
- [Existing accepted runtime ADR](../ADR/ADR-001-unattended-mt5-runtime-hosting.md)
- [v0.1.4 Desktop UI planning record](../planning/v0.1.4-desktop-ui.md)
- [Phase 0 evidence snapshot](../evidence/v0.1.4/phase0-baseline-and-architecture.md)
- [CI](../CI.md) · [release process](../RELEASE_PROCESS.md) · [known issues](../KNOWN_ISSUES.md)

This draft is additive. Where an older source record has a different point-in-
time branch or pipeline value, consult its dated evidence in its original
context. The refreshed baseline here is the checked-out `develop` commit above.

The earlier KivyMD proposal in the planning record is superseded by the
Product Owner-approved C#/WPF/XAML/.NET Framework 4.8/MVVM decision in
[ADR-ARCH-015](adr/ADR-ARCH-015-wpf-technology.md). v0.1.4 uses approved
**Option A**: a client for an already installed/provisioned Python Agent and
Runtime, with a reproducible WPF build and testable user-scope package. See
[ADR-ARCH-016](adr/ADR-ARCH-016-release-boundary-option-a.md).
