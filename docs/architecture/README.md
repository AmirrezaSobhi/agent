# MT5Agent Architecture

**Status:** Architecture Blueprint v1.0-draft; prepared for Product Owner review.
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
6. [Roadmap](ROADMAP.md), [risks](RISK_REGISTER.md),
   [v0.1.4 acceptance](ACCEPTANCE_V0.1.4.md), and [glossary](GLOSSARY.md).
7. [Architecture ADRs](adr/README.md).

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
