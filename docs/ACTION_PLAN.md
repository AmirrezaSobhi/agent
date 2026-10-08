# Action Plan

This page tracks current product status and future evidence needs. Historical
release facts belong in [CHANGELOG](../CHANGELOG.md); v0.1.3 provenance is in
the [release record](releases/v0.1.3-release-notes.md).

## Current baseline

- v0.1.3 is released from tag `v0.1.3`, commit
  `970c04712853295fd065094b11a2bd541b5a9db8`. Release Pipeline #16 passed all
  eight gates; package Job #125 produced the published binary.
- The split Session 0 Agent / interactive Worker / MT5 architecture is
  implemented and lab validated. The released runtime path passed the release
  acceptance gates.
- Pipeline #17 passed all eight required jobs on `develop` commit
  `2e01ff78c447d5242e0d582944c43f0d952b3446`. Its first MT5 runtime smoke
  failed in Job #132; a later execution passed in Job #134. The initial cause
  is unknown, and Worker startup reliability remains open. See
  [post-release validation](evidence/v0.1.3/post-release-validation.md).
- Pipeline #11 remains historical Phase 4D candidate evidence. It is not the
  provenance of the published v0.1.3 binary.
- No trading operation is production-ready.

## Completed for v0.1.3

- [x] Separate Session 0 control plane from the interactive MT5 Runtime Worker.
- [x] Route the supported safe reads through `MT5Port` and the Worker adapter.
- [x] Separate Agent and Worker dependency sets and exclude MT5/Worker runtime
  components from the Agent artifact.
- [x] Pass all eight release gates in tag Pipeline #16 and publish the exact
  package from Job #125 to the Generic Package Registry.
- [x] Complete post-release Pipeline #17 with eight successful final jobs,
  including successful MT5 Runtime Smoke Job #134 after failed Job #132.

## Next planning phase: v0.1.4

v0.1.4 remains a planning phase; scope, implementation tasks, and dates are not
approved. The detailed client-side Windows Desktop UI decisions, architecture
boundaries, open questions, and measurable proposed gates are in the
[Desktop UI planning document](planning/v0.1.4-desktop-ui.md). KivyMD is the
preferred framework candidate, subject to compatibility and packaging
feasibility. This plan does not authorize UI implementation.

One-way GitLab-to-GitHub Release synchronization has a CI implementation
proposal and focused local tests, documented in the
[Release sync runbook](GITHUB_RELEASE_SYNC.md). It is **not operational** until
an administrator protects release tags, configures the scoped GitHub write
token, and a real existing Release passes end-to-end verification. No historic
GitHub-only release or conflicting asset has been modified.

Other v0.1.4 evaluation topics remain:

1. Worker startup reliability: collect repeatable evidence across startup,
   recovery, reboot, and network-transition scenarios. Job #132's cause remains
   unknown; do not assume a timing defect.
2. Hybrid threading: evaluate whether it can improve responsiveness or
   reliability while preserving serialized MT5 operations unless evidence and
   design approval justify a change.
3. Time synchronization: evaluate autonomous polling and persistence through
   reboot/network transitions. Pipeline #16's release checks do not prove
   these future controls.
4. Productization: assess signed installation, managed service/recovery,
   customer provisioning, upgrades, rollback, and operational support.

These are evaluation areas, not committed features or a release date.

## Production hardening still required

- [ ] Productize signed Windows installation and least-privilege service
  installation/recovery.
- [ ] Validate supported upgrade, rollback, uninstall, and task/service repair.
- [ ] Generalize machine policy without embedding machine state or secrets.
- [ ] Define supported customer provisioning and recovery.
- [ ] Expand crash, logoff, reboot, network-transition, and Worker-startup
  reliability evidence.
- [ ] Complete security, privacy, retention, and customer-support reviews.

## Future runtime and trading capabilities

- [ ] Integrate durable-command foundations only after explicit application
  contracts and lifecycle ownership are approved.
- [ ] Add read capabilities only with allowlisted schemas, bounded payloads,
  privacy review, and Worker-path acceptance.
- [ ] Validate transport, remote configuration, and update foundations before
  describing them as active production features.
- [ ] Do not enable trading until separate product/security authorization and
  safety, idempotency, ambiguity/reconciliation, audit, and controlled-demo
  acceptance are approved.
- [ ] Keep CI and ordinary release gates strictly non-trading.

## Definition of status

`IMPLEMENTED` means code exists; `LAB VALIDATED` means the named lab scenario
passed; `CI ACCEPTED` means a live pipeline passed; `RELEASED` means a tagged
release and its artifact provenance were verified; `PRODUCTION READY` requires
supported provisioning, operations, security, and release evidence. Do not
promote one status to another by inference.
