# Architecture Decision Records

These ADRs belong to Architecture Blueprint v1.0-draft. They do not replace
the historical [repository ADR-001](../../ADR/ADR-001-unattended-mt5-runtime-hosting.md).
IDs use `ADR-ARCH-NNN` to avoid colliding with existing repository ADR IDs.

Status meanings: **Accepted** means the Product Owner explicitly agreed to the
decision; **Proposed** needs architectural approval; **Deferred** is a future
capability intentionally postponed; **Open** needs evidence or a choice before
implementation. No ADR marked Proposed/Deferred is implementation approval.

| ID | Decision | Status |
|---|---|---|
| [ADR-ARCH-001](ADR-ARCH-001-service-ui-independence.md) | UI and Service independence | Accepted product direction |
| [ADR-ARCH-002](ADR-ARCH-002-interactive-mt5-runtime.md) | Interactive MT5 Runtime | Accepted, aligned with existing ADR-001 |
| [ADR-ARCH-003](ADR-ARCH-003-runtime-domain-model.md) | Runtime and domain model | Accepted domain constraints; persistence/execution proposed or deferred |
| [ADR-ARCH-004](ADR-ARCH-004-configuration-ownership.md) | Configuration ownership | Accepted separation; realization proposed |
| [ADR-ARCH-005](ADR-ARCH-005-local-api-security.md) | Local API security | Proposed, separate SID-authorized pipe |
| [ADR-ARCH-006](ADR-ARCH-006-trading-policy-enforcement.md) | Trading policy enforcement | Accepted safety requirements; algorithm proposed |
| [ADR-ARCH-007](ADR-ARCH-007-startup-recovery-profiles.md) | Startup and recovery profiles | Accepted constraints; mechanism proposed |
| [ADR-ARCH-008](ADR-ARCH-008-support-privacy.md) | Support privacy | Accepted workflow requirements; implementation proposed |
| [ADR-ARCH-009](ADR-ARCH-009-versioned-updates.md) | Versioned releases and update safety | Accepted artifact principle; updater deferred |
| [ADR-ARCH-010](ADR-ARCH-010-modular-desktop-ui.md) | Superseded KivyMD proposal | Superseded by ADR-ARCH-015 |
| [ADR-ARCH-011](ADR-ARCH-011-agent-identity-enrollment.md) | Agent identity and enrollment | Deferred; identity requirements accepted, protocol open |
| [ADR-ARCH-012](ADR-ARCH-012-multi-agent-ownership.md) | Multi-Agent execution ownership | Deferred; safety constraints accepted, lease protocol proposed |
| [ADR-ARCH-013](ADR-ARCH-013-billing-vs-authentication.md) | Billing credits versus authentication | Accepted product constraint |
| [ADR-ARCH-014](ADR-ARCH-014-offline-authorization.md) | Offline authorization | Deferred for v0.1.4; future trading policy open |
| [ADR-ARCH-015](ADR-ARCH-015-wpf-technology.md) | C# WPF technology decision | Accepted by Product Owner |
| [ADR-ARCH-016](ADR-ARCH-016-release-boundary-option-a.md) | v0.1.4 Option A release boundary | Accepted by Product Owner |
| [ADR-ARCH-017](ADR-ARCH-017-management-ipc.md) | Dedicated management Named Pipe | Proposed; verify SID/DACL before implementation |

All active decisions include alternatives, consequences, risk, a verification
strategy, and links to the relevant blueprint sections. ADR-ARCH-010 is kept
for history and explicitly superseded; do not use it as the current UI choice.
