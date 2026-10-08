# GitLab Wiki Plan

## Source-of-truth policy

The repository's Markdown and release records are the canonical, versioned
product documentation. GitLab Wiki is a concise navigation and knowledge
portal, not a second source of operational truth. Summarize canonical sources;
do not copy whole documents or machine-specific procedures into Wiki pages.

## Proposed eleven-page structure

Each page should contain a short summary, links to its canonical sources, and
links to related Wiki pages. Keep implementation detail in the repository.

| Title | Wiki slug | Canonical sources | Summary and navigation |
|---|---|---|---|
| Home | `Home` | `README.md`, `docs/README.md` | Product purpose, current v0.1.3 release status, safe starting points; link to Architecture, CI-CD, Release Process, Roadmap-Action-Plan, and v0.1.3 Acceptance. |
| Architecture | `Architecture` | `docs/ARCHITECTURE.md` | Control-plane boundary, supported scope, and runtime overview; link to MT5 Runtime Architecture, Deployment, Security, and Operations. |
| MT5 Runtime Architecture | `MT5-Runtime-Architecture` | `docs/MT5_RUNTIME_ARCHITECTURE.md`, `docs/MT5_CAPABILITIES.md` | Agent/Worker/terminal responsibilities, session boundary, readiness, and safe-read capability scope; link to Deployment, Operations, and Troubleshooting. |
| Deployment | `Deployment` | `docs/MT5_RUNTIME_PROVISIONING.md` | High-level prerequisites and provisioning boundaries; omit credentials, host-local identities, and secret-handling procedures; link to Runtime Architecture, Operations, and Security. |
| Operations | `Operations` | `docs/OPERATIONS.md` | Health meanings, safe observation, and escalation boundaries; summarize the unresolved Worker startup reliability risk; link to Troubleshooting, Security, and Runtime Architecture. |
| CI-CD | `CI-CD` | `docs/CI.md` | Runner roles and pipeline provenance; distinguish release Pipeline #16 from post-release Pipeline #17 and historical Pipeline #11; link to Release Process and v0.1.3 Acceptance. |
| Release Process | `Release-Process` | `docs/RELEASE_PROCESS.md`, `deployment/RELEASE_CHECKLIST.md` | Release gates, provenance, and approval boundaries; link to CI-CD, Roadmap-Action-Plan, and v0.1.3 Acceptance. |
| Roadmap-Action-Plan | `Roadmap-Action-Plan` | `docs/ACTION_PLAN.md`, `docs/ROADMAP.md` | Released v0.1.3 and v0.1.4 planning topics; state that scope and dates are not approved; link to Operations, CI-CD, and v0.1.3 Acceptance. |
| Troubleshooting | `Troubleshooting` | `docs/TROUBLESHOOTING.md`, `docs/KNOWN_ISSUES.md` | Safe evidence collection and known limits; do not claim the Job #132 cause is known or Worker reliability is resolved; link to Operations and Runtime Architecture. |
| Security | `Security` | `docs/SECURITY.md`, security sections in `docs/MT5_RUNTIME_ARCHITECTURE.md` and `docs/MT5_RUNTIME_PROVISIONING.md` | Summarize trust boundaries and safe handling rules; omit machine-local identities, private paths, account data, and secret details; link to Architecture, Deployment, and Operations. |
| v0.1.3 Acceptance | `v0.1.3-Acceptance` | `docs/releases/v0.1.3-release-notes.md`, `docs/evidence/v0.1.3/post-release-validation.md`, `docs/evidence/v0.1.3/phase4d-live-ci-acceptance.md`, `docs/evidence/v0.1.3/release-readiness.md` | Separate release Pipeline #16 provenance, Pipeline #17 post-release validation, and historical Pipeline #11 evidence; link to CI-CD, Release Process, Troubleshooting, and Roadmap-Action-Plan. |

## Source links and publication manifest

Pin repository links to a revision that contains the reviewed documentation
changes. The revision for these pending edits does not exist yet; after the
documentation diff is approved and committed, use that exact commit in
repository blob links. Historical release facts may additionally link to tag
`v0.1.3`. Do not invent a future revision or link an updated page to a commit
that does not contain its content.

An authenticated GitLab API inventory returned no Wiki pages on 2026-10-08.
The preliminary action for all eleven rows is therefore `CREATE`, subject to a
fresh inventory check immediately before any separately approved publication.
If a page appears or a slug conflicts, stop and inspect it; do not overwrite it
automatically. Publish Home first only after explicit Gate 3 approval, then
publish and read back each remaining page individually.

## Content and security rules

- Keep each page concise and link to canonical files for details.
- Include navigation links among the eleven pages and verify their slugs before
  publication.
- Use Mermaid only when a small diagram materially improves understanding.
- Never publish credentials, tokens, private keys, Autologon secrets, account
  values, machine-local host details, SIDs, transient PIDs, or private profile
  paths. Do not repeat operational instructions that reveal secret state.
- Publish release identifiers, pipeline IDs, job IDs, and hashes only when
  backed by the canonical release evidence and appropriate for the page.
- Do not describe the initial MT5 smoke failure's root cause as known. The
  successful Job #134 does not resolve the Worker startup reliability issue.
- Do not present v0.1.4 planning topics as an approved scope or release promise.
- Repository-backed `docs/wiki-fa/` is not a live Wiki mirror. A Persian `fa/`
  namespace would need a separate review and approval; this plan does not modify
  or authorize publication of those files.

## Maintenance

Update repository documentation first, then revise concise Wiki summaries after
approval. Revalidate source revision, links, navigation, and live page inventory
before each publication. No Wiki page is created or modified by this plan.
