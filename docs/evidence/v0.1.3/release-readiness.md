# v0.1.3 release-readiness audit

Audit date: **2026-10-06**. [Phase 4D is LIVE CI ACCEPTED / GO](phase4d-live-ci-acceptance.md).
**Promotion verdict: CONDITIONAL GO for `develop → staging`.** Conditions:
review the documentation-only follow-up, require its full develop pipeline to
pass, preserve candidate/branch provenance, and obtain explicit promotion
approval. No promotion, tag, Release or Wiki publication is authorized here.

## Branch snapshot before documentation formalization

The remote refs and GitLab API agreed:

| Ref | Head | Divergence from accepted develop |
| --- | --- | --- |
| `develop` | `c4b945122ad7e7174dbbb433cb91b42cb66f1c72` | Accepted source; docs commit will be a descendant |
| `staging` | `ded0cd6f1e2d99924842ab631916644a3b84ead4` | 3 staging-only / 44 develop-only commits |
| `main` | `fff9964a9d5c8f0182f664750f39512cf773d88d` | 6 main-only / 44 develop-only commits |

Staging/main-only commits are historical promotions/merges. Staging and main
have identical trees at this snapshot but divergent history. Read-only merge-tree
simulations of accepted develop into staging and main produced no conflicts.
Do not infer fast-forward eligibility or reset those histories. Re-audit refs
before each separately approved promotion. Main is protected for Maintainers;
develop/staging are not protected. The project uses merge commits and currently
does not require a successful pipeline or resolved discussions to allow a merge.
Human review must enforce the release gates; this task changes no project policy.

## Findings

| Area | Result / disposition |
| --- | --- |
| Version | `agent.__version__` is 0.1.3; package metadata, default identity and PyInstaller filename derive from it; CI requires an exact `v0.1.3` tag match. No version bump needed. |
| Changelog / notes | Unreleased v0.1.3 scope and CI corrections recorded; draft release notes prepared. No publication date or published release claimed. |
| Documentation | Live acceptance replaces current pending claims; historical experiments remain historical. Session 0 control / interactive Worker boundary is preserved. |
| CI / dependency split | All eight required jobs passed; explicit three-role tags; Agent MT5/NumPy absent; Worker dependencies separate and pinned; recursive archive exclusion passed. |
| Provenance / naming | Pipeline #11 exact candidate, size, hash and five handoffs independently verified. Each future ref pipeline produces a new candidate; identical version/filename does not establish identical bytes. |
| Security / privacy | Account values withheld; no trading; no credentials or machine-private evidence copied. Current local IPC acceptance is not a general security audit. |
| Package mirror | Existing Liara HTTPS index explicitly approved for Linux/Windows CI; no pin changes; transitive dependency hash-locking remains future hardening. |
| Clock risk | About 10h30m skew recorded in Known Issues, Operations, Troubleshooting, Security and acceptance evidence. Staging can proceed conditionally; publication needs remediation/revalidation or explicit owner risk acceptance. |
| Artifact retention | Final Job #85 package expires 2026-11-05; build/smoke artifacts use 14 days, package 30 days. Approved durable retention/publication must preserve exact binary/receipts before expiry. |
| Wiki | Enabled but empty at audit. Repository-backed Persian summaries reconciled; no approved synchronization mechanism exists. Separate publication approval required. |
| Tags / Releases | `v0.1.3` absent; Releases API returned no Releases. CI has no Release job/API publication mechanism; controlled manual publication required. |
| Outstanding product work | Signed installer, managed service/recovery, supported upgrades/rollback, customer provisioning and broader security/operations acceptance remain open. They block a commercial-production claim, not this bounded read-only staging evaluation. |

No active TODO/FIXME release blocker was found in the release configuration;
open product/operational work remains explicitly tracked in the
[Action Plan](../../ACTION_PLAN.md) and [Known Issues](../../KNOWN_ISSUES.md).
Existing dirty EOL-only source changes and unrelated untracked files are outside
the proposed documentation commit and must remain unstaged.

## Ref workflow and recommended sequence

Inspection of the accepted `.gitlab-ci.yml` confirmed pushes to develop/staging/
main and stable semantic-version tags are eligible. Metadata fails mismatching
tag/source versions. GitLab CI Lint dry-runs using the accepted configuration for develop, staging
and main were valid with all eight jobs and no errors/warnings. Tag behavior is configuration/test evidence, not a
claim that an unpublished `v0.1.3` tag pipeline has run. Open MRs can suppress
source branch push pipelines; verify the actual target-ref pipeline after merging.

1. Review the documentation follow-up and successful full develop pipeline;
   obtain explicit authorization for a history-preserving `develop → staging` merge.
2. Require the resulting staging ref's eight live gates and new candidate receipts.
   Keep Pipeline #11 acceptance tied to its original commit/hash.
3. Before final release, obtain an approved clock investigation/remediation window
   and revalidate health/safe reads, or obtain explicit owner risk acceptance.
   Preserve exact candidate artifacts, review draft notes and release scope.
4. Obtain separate `staging → main` approval; merge without rewriting history and
   require the resulting main pipeline's eight gates.
5. Obtain separate tag approval; create `v0.1.3` at the reviewed main commit.
   Require the tag pipeline's exact version check and all eight gates. This is a
   separately provenanced candidate, not a rebuild/relabel of Pipeline #11.
6. Obtain separate publication approval; create the GitLab Release manually from
   the tag pipeline's exact package output, hash and redacted receipts. Freeze
   the draft notes with that provenance; never rebuild after candidate smoke.
   Verify downstream mirroring separately.

Publishing the historical Pipeline #11 binary instead requires its own explicit
plan retaining `c4b945122ad7e7174dbbb433cb91b42cb66f1c72` and pipeline 11 as the
artifact provenance; merge/tag receipts cannot be substituted. The documentation
follow-up itself never changes the accepted source/hash.

## Documentation formalization scope

The focused follow-up changes only Markdown:

- Root: `README.md`, `CHANGELOG.md`; deployment: `RELEASE_CHECKLIST.md`.
- Canonical docs: `README.md`, `ACTION_PLAN.md`, `ROADMAP.md`, `CI.md`,
  `RELEASE_PROCESS.md`, `GITLAB_WIKI_PLAN.md`, `ARCHITECTURE.md`,
  `MT5_RUNTIME_ARCHITECTURE.md`, `MT5_RUNTIME_PROVISIONING.md`, `OPERATIONS.md`,
  `TROUBLESHOOTING.md`, `SECURITY.md`, `KNOWN_ISSUES.md`, `TEST_STRATEGY.md`,
  `TARGET_ARCHITECTURE.md`, `TRACEABILITY.md`, `GITLAB_PLAN.md`, and the accepted
  addendum in `ADR/ADR-001-unattended-mt5-runtime-hosting.md`.
- New records: `evidence/v0.1.3/phase4d-live-ci-acceptance.md`, this audit,
  and `releases/v0.1.3-release-notes.md`.
- Repository Wiki sources: `wiki-fa/Home.md`, `Architecture.md`, `Operations.md`,
  `Roadmap.md`, `Reference.md`, and `Reliability.md`.

Application code, version declarations, requirements, CI/scripts, Runner/system
policy and persistent MT5 configuration are unchanged. No Wiki write, branch
promotion, tag or Release creation is part of the formalization.

## Post-release addendum — 2026-10-08

The audit above remains the 2026-10-06 pre-release snapshot; its original
findings and recommendations are preserved as historical evidence. A later
authenticated GitLab API review confirmed that v0.1.3 was released from tag
`v0.1.3` at commit `970c04712853295fd065094b11a2bd541b5a9db8` on 2026-10-06,
with Pipeline #16 and package Job #125. The published Package Registry artifact
and its SHA-256 are recorded in the
[post-release validation record](post-release-validation.md). Pipeline #17 is
separate post-release validation on `develop`; it does not replace Pipeline #16
release provenance.
