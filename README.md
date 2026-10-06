# MT5 Agent

MT5 Agent is a Windows control-plane application that exposes a bounded local
HTTP command interface and coordinates read-only MetaTrader 5 operations. In
the supported Windows runtime, the Agent runs in Session 0 and communicates
with a persistent Worker in a separate interactive user session. The Worker,
not the Agent, owns the MetaTrader5 Python runtime and `terminal64.exe`.

The current safe MT5 reads are symbols total, terminal version, and account
information. Account values are operationally sensitive and must not be copied
into logs or documentation examples. No trading operation is production-ready
or included in the release smoke gate.

## Architecture and status

```mermaid
flowchart LR
  A[Agent / Session 0] --> P[Authenticated local Named Pipe]
  P --> W[Persistent Worker / interactive session]
  W --> M[MetaTrader 5]
```

The split-session Worker path and unattended lab cold-boot bootstrap are
**LAB VALIDATED**. Phase 4D is **LIVE CI ACCEPTED / GO** for v0.1.3 at commit
`c4b945122ad7e7174dbbb433cb91b42cb66f1c72`: Pipeline #11 passed all eight gates,
including isolated packaging and Worker-backed runtime integration. See the
[versioned acceptance evidence](docs/evidence/v0.1.3/phase4d-live-ci-acceptance.md).
Branch promotion, tagging, and release publication remain separately authorized;
this is an accepted candidate, not a published release.
See [Architecture](docs/ARCHITECTURE.md) and [Action Plan](docs/ACTION_PLAN.md).

## Development and dependencies

The control-plane package has no third-party runtime dependency and does not
install MetaTrader5 or NumPy. Use `requirements-dev.txt` for source tests and
build tooling. The interactive Worker has its own pinned Windows dependency
set; direct in-process MT5 support is isolated in the explicit legacy
requirements file. See [Configuration](docs/CONFIGURATION.md).

Portable source tests run on Linux. Windows no-MT5 CI validates the clean Agent
build and degraded control plane. A separate Windows MT5 Runner validates the
same candidate against the persistent Worker. The release invariant is:

> **BUILD ONCE → TEST SAME ARTIFACT → RELEASE SAME ARTIFACT**

Pipeline #11 verified the same candidate through build, control smoke, runtime,
and packaging without a post-smoke rebuild. See [CI/CD](docs/CI.md),
[Release Process](docs/RELEASE_PROCESS.md), and the
[draft v0.1.3 release notes](docs/releases/v0.1.3-release-notes.md).

## Documentation

The repository is the canonical, versioned product documentation. The
[documentation index](docs/README.md) organizes architecture, deployment,
security, operations, CI, testing, release, roadmap, and troubleshooting
material. Start with:

- [Runtime architecture](docs/MT5_RUNTIME_ARCHITECTURE.md)
- [Runtime provisioning](docs/MT5_RUNTIME_PROVISIONING.md)
- [Operations runbook](docs/OPERATIONS.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Action Plan](docs/ACTION_PLAN.md)
- [Known issues](docs/KNOWN_ISSUES.md)
- [Changelog](CHANGELOG.md)

## Scope

This repository does not yet provide a customer installer, a generally
provisioned Windows Service, a supported trading interface, or a completed
commercial release process. The lab runtime account uses a dedicated standard
user and Sysinternals Autologon; credentials remain local to the machine and
must never enter the repository or CI evidence. MT5 Agent must not manage
BitLocker, TPM, Secure Boot, or recovery keys; those remain the machine owner's
responsibility.
