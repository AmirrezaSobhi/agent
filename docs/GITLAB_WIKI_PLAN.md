# GitLab Wiki Plan

## Source-of-truth policy

The repository's `docs/` tree and root release records are canonical and
versioned with source. GitLab Wiki is a navigation/knowledge portal, not a
second authority. Important architecture, deployment, security, operations,
CI/CD, and release information must remain in the repository. Wiki pages should
summarize and link to the canonical repository revision instead of copying
operational detail that can drift.

## Proposed Wiki pages

| Wiki page | Canonical repository source |
| --- | --- |
| Home | `README.md`, `docs/README.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| MT5 Runtime Architecture | `docs/MT5_RUNTIME_ARCHITECTURE.md`, `docs/MT5_CAPABILITIES.md` |
| Deployment | `docs/MT5_RUNTIME_PROVISIONING.md` |
| Operations | `docs/OPERATIONS.md` |
| CI-CD | `docs/CI.md` |
| Release Process | `docs/RELEASE_PROCESS.md`, `deployment/RELEASE_CHECKLIST.md` |
| Roadmap-Action-Plan | `docs/ACTION_PLAN.md`, `docs/ROADMAP.md` |
| Troubleshooting | `docs/TROUBLESHOOTING.md`, `docs/KNOWN_ISSUES.md` |
| Security | `docs/SECURITY.md`, runtime security sections in architecture/provisioning |
| v0.1.3 Acceptance | `docs/evidence/v0.1.3/phase4d-live-ci-acceptance.md`, `docs/evidence/v0.1.3/release-readiness.md`, `docs/releases/v0.1.3-release-notes.md` |

## v0.1.3 publication readiness

Read-only GitLab inspection on 2026-10-06 found Wiki enabled with no pages.
There is no approved sync script, CI job, or publication mechanism in this
repository; this plan does not authorize a write. Phase 4D is LIVE CI ACCEPTED /
GO in Pipeline #11, while v0.1.3 tagging/publication remain pending.

After separate approval, create the pages in the table as short summaries with
links pinned to the reviewed documentation commit, plus a link to the canonical
branch for navigation. Publish Home first, followed by Architecture, MT5 Runtime
Architecture, Deployment, CI-CD, Operations, Troubleshooting, Security, Release
Process, Roadmap-Action-Plan and v0.1.3 Acceptance. The acceptance page links
Pipeline #11 and Jobs #78–#85 and states the exact accepted candidate hash; it
must distinguish later ref/tag candidates and draft release notes.

Repository-backed `docs/wiki-fa/` pages are Persian source summaries, not a
live Wiki mirror. Home, Architecture, Operations, Roadmap and Reference now link
the accepted canonical baseline; Reliability describes uncomposed foundations.
If Persian pages are desired, publish them under a separate `fa/` namespace with
links to the same canonical revision. Do not overwrite an existing Wiki without
re-reading its live contents, checking conflicts and obtaining publication scope.
Include clock risk and artifact-retention conditions; omit host names, SIDs,
transient PIDs, profile paths, credentials and account values. Validate navigation
and source revision after publication. No Wiki publication occurred in this task.

## Maintenance rules

- Every Wiki summary links to the current canonical file and, where practical,
  the source commit/revision.
- Changes to product behavior are reviewed and merged in repository Markdown
  first; Wiki summaries follow afterward.
- Never place passwords, Autologon/LSA secret material, broker credentials,
  customer account payloads, or machine-local secret state in Wiki pages.
- Do not publish pipeline IDs, artifact hashes, or acceptance claims without
  retained evidence and an authorized release record.
- Keep historical release facts in Git history/changelog rather than rewriting
  them in Wiki pages.

No GitLab Wiki page is created or modified by this plan.
