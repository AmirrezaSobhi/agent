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
| Architecture | `docs/ARCHITECTURE.md`, `docs/MT5_RUNTIME_ARCHITECTURE.md` |
| MT5 Runtime | `docs/MT5_RUNTIME_ARCHITECTURE.md`, `docs/MT5_CAPABILITIES.md` |
| Deployment | `docs/MT5_RUNTIME_PROVISIONING.md` |
| Operations | `docs/OPERATIONS.md` |
| CI-CD | `docs/CI.md` |
| Release Process | `docs/RELEASE_PROCESS.md`, `deployment/RELEASE_CHECKLIST.md` |
| Action Plan | `docs/ACTION_PLAN.md`, `docs/ROADMAP.md` |
| Troubleshooting | `docs/TROUBLESHOOTING.md`, `docs/KNOWN_ISSUES.md` |
| Security Model | `docs/SECURITY.md`, runtime security sections in architecture/provisioning |

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
