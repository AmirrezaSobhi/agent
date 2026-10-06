# Product-to-Delivery Traceability

| Product requirement | Architecture / ADR | Roadmap | GitLab issue family | Test evidence |
| --- | --- | --- | --- | --- |
| One safe unattended MT5 runtime | ADR-001 (accepted split-session lab architecture) | v0.1.3 runtime | #1, #14 | Cold boot without RDP, interactive task, authenticated Session 0 IPC, connected MT5, same-session terminal, repeated safe reads; general customer provisioning remains pending |
| Same artifact across CI/release gates | CI.md / RELEASE_PROCESS.md | v0.1.3 CI | Phase 4D | [Pipeline #11: LIVE CI ACCEPTED / GO](evidence/v0.1.3/phase4d-live-ci-acceptance.md); matching hash/size across Jobs #81–#85, runtime reads and no-rebuild packaging |
| Explicit/versioned allowlisted commands | Target Architecture | A | #2, #3 | Schema/negative compatibility |
| No duplicate or expired trade | Target Architecture | C, G | #3, #4, #5, #14 | Crash/retry/TTL/ambiguity tests |
| Large historical data safely | Target Architecture | D, E | #7, #8, #9 | UTC, bounded-memory, integrity/resume |
| Durable disconnection recovery | Target Architecture | C, F | #4, #6 | Migration/restart/outage tests |
| Secure controlled operations | Target Architecture | A, F, H | #10–#13, #15 | Security/redaction/rollback tests |

Track status precisely: implemented code, lab validation, live CI acceptance,
and production readiness are separate evidence levels. Planned items remain
non-implemented until their acceptance criteria are met. The original issue
numbers and planning material remain historical traceability, not proof that a
GitLab pipeline or commercial release has passed.
