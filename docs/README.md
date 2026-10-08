# Documentation Index

Repository documentation is the canonical, version-controlled product source
of truth. An authenticated GitLab API check on 2026-10-08 returned no Wiki pages.
The Wiki remains a proposed navigation portal that links here rather than
maintaining conflicting copies; recheck its inventory before any publication.

**v0.1.3 is released.** Tag Pipeline #16 at `970c04712853295fd065094b11a2bd541b5a9db8`
passed the eight release gates. Pipeline #17 is a separate post-release
validation on `develop`. Start with the [release notes](releases/v0.1.3-release-notes.md),
[post-release validation](evidence/v0.1.3/post-release-validation.md), and
[historical Phase 4D acceptance](evidence/v0.1.3/phase4d-live-ci-acceptance.md).

## Architecture

- [System architecture](ARCHITECTURE.md)
- [MT5 runtime architecture](MT5_RUNTIME_ARCHITECTURE.md)
- [Target architecture and future boundaries](TARGET_ARCHITECTURE.md)
- [State machines](STATE_MACHINES.md)

## Runtime and deployment

- [Runtime provisioning](MT5_RUNTIME_PROVISIONING.md)
- [Configuration](CONFIGURATION.md)
- [Operations](OPERATIONS.md)
- [Troubleshooting](TROUBLESHOOTING.md)

## Security

- [Security lifecycle/foundations](SECURITY.md)
- [Runtime account, pipe, and Autologon security](MT5_RUNTIME_ARCHITECTURE.md#ipc-trust-boundary)
- [Runtime provisioning security](MT5_RUNTIME_PROVISIONING.md#automatic-interactive-logon-and-credential-boundary)

## CI/CD and testing

- [GitLab CI](CI.md)
- [Test strategy](TEST_STRATEGY.md)
- [MT5 capability inventory](MT5_CAPABILITIES.md)
- [Error model](ERROR_MODEL.md)

## Release and roadmap

- [Release process](RELEASE_PROCESS.md)
- [v0.1.3 release notes and provenance](releases/v0.1.3-release-notes.md)
- [v0.1.3 post-release validation](evidence/v0.1.3/post-release-validation.md)
- [Historical v0.1.3 release-readiness audit](evidence/v0.1.3/release-readiness.md)
- [Historical Phase 4D candidate acceptance](evidence/v0.1.3/phase4d-live-ci-acceptance.md)
- [Release checklist](../deployment/RELEASE_CHECKLIST.md)
- [Action Plan](ACTION_PLAN.md)
- [Product roadmap](ROADMAP.md)
- [v0.1.4 Desktop UI planning](planning/v0.1.4-desktop-ui.md)
- [Known issues](KNOWN_ISSUES.md)
- [Changelog](../CHANGELOG.md)

## Contracts and reference

- [Contracts](CONTRACTS.md)
- [Transport](TRANSPORT.md)
- [Storage foundation](STORAGE.md)
- [Migration history](MIGRATION.md)
- [Traceability](TRACEABILITY.md)
- [GitLab planning](GITLAB_PLAN.md)
- [GitLab Wiki plan](GITLAB_WIKI_PLAN.md)
- [ADR-001: Unattended MT5 Runtime Hosting](ADR/ADR-001-unattended-mt5-runtime-hosting.md)
