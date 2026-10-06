# Action Plan

Living roadmap for the accepted v0.1.3 development candidate. Historical
milestones belong in [CHANGELOG](../CHANGELOG.md); this page tracks current
state and the next evidence required.

## Current Baseline

- Split Session 0 Agent / interactive Worker / MT5 architecture:
  **IMPLEMENTED; LAB VALIDATED; LIVE CI ACCEPTED**.
- Dedicated standard runtime user, interactive task, Autologon cold-boot
  bootstrap, authenticated local pipe, persistent MT5 connection:
  **LAB VALIDATED**.
- Three safe MT5 reads through the production application path:
  **IMPLEMENTED; LAB VALIDATED; LIVE CI ACCEPTED**.
- Agent/Worker dependency and PyInstaller boundary:
  **IMPLEMENTED; LIVE CI ACCEPTED**.
- Phase 4D three-Runner pipeline topology and artifact provenance gates:
  **LIVE CI ACCEPTED / GO**, Pipeline #11 at
  `c4b945122ad7e7174dbbb433cb91b42cb66f1c72`; see
  [acceptance evidence](evidence/v0.1.3/phase4d-live-ci-acceptance.md).
- No v0.1.3 release is claimed. No trading operation is production-ready.

## Completed

- [x] Separate Session 0 control plane from the interactive MT5 runtime Worker.
- [x] Require account-SID pipe authorization and Session 0 caller policy without
  Worker impersonation privilege.
- [x] Keep MT5 API ownership persistent and serialized in the Worker.
- [x] Validate the lab's unattended cold boot without RDP/console login.
- [x] Route the safe reads through `MT5Port` and the Worker adapter.
- [x] Separate Agent and Worker dependency sets and exclude Worker/MT5 packages
  from the Agent artifact.
- [x] Implement Phase 4D CI configuration and local tests/evidence validation.
- [x] Live-accept Phase 4D through GitLab using all three Runner roles (Pipeline #11).

## Immediate Next Actions

1. Review the [release-readiness audit](evidence/v0.1.3/release-readiness.md)
   and documentation-only follow-up pipeline; keep Pipeline #11 provenance intact.
2. Obtain separate authorization for `develop → staging`; merge historical
   branch divergence without resetting or rewriting branches, then require all
   eight staging gates before considering `staging → main`.
3. Plan an approved maintenance window to investigate the MT5-host clock skew;
   remediation or explicit owner risk acceptance is required before publication.
4. Preserve the accepted package before its GitLab artifact expiry, and obtain
   separate main/tag/publication authorization. No release is automatic.

## Release v0.1.3 Gate

- [x] Linux source/unit suite passes on `linux-source-unit`.
- [x] Windows tests and isolated Agent build pass on
  `windows-self-hosted-no-mt5` with MetaTrader5 absent.
- [x] Candidate archive excludes MetaTrader5, NumPy, Worker implementation,
  legacy direct adapter, and local terminal inspection.
- [x] Invalid-configuration and degraded control-plane checks pass.
- [x] Exact candidate SHA/commit/pipeline provenance is retained.
- [x] `windows-self-hosted-mt5` consumes that candidate without rebuilding.
- [x] Worker identity/session, authenticated IPC, connected MT5, terminal
  identity/session, and three safe reads pass.
- [x] Final package evidence matches the original candidate hash.
- [ ] Human release review, promotion authorization, and tag/release approval
  are completed separately.

## Production Hardening

- [ ] Productize signed Windows installation/provisioning and least-privilege
  service installation/recovery.
- [ ] Validate supported upgrade, rollback, uninstall, and task/service repair.
- [ ] Generalize machine policy from lab identities without embedding machine
  state or secrets.
- [ ] Define supportable Autologon threat model and customer provisioning UX.
- [ ] Expand crash/logoff/network recovery tests and operational evidence.
- [ ] Complete security, privacy, retention, and customer support reviews.

## Future Runtime Capabilities

- [ ] Integrate durable command foundations only after explicit application
  contracts and lifecycle ownership are approved.
- [ ] Add read capabilities only with allowlisted schemas, bounded payloads,
  privacy review, and Worker-path tests.
- [ ] Validate transport, remote configuration, and update foundations before
  claiming they are active production features.

## Future Trading Capabilities

- [ ] No trade execution until explicit authorization and a separate safety,
  typed-contract, idempotency, ambiguity/reconciliation, audit, and demo-only
  acceptance design is approved.
- [ ] CI and ordinary release gates remain strictly non-trading.

## Known Technical Debt

- Approximately 10h30m MT5-host clock skew affects cross-host audit correlation;
  see [Operations](OPERATIONS.md#clock-skew-and-audit-correlation).
- Promotion/ref pipelines create separately provenanced candidates. Pipeline #11
  acceptance does not automatically accept another commit or binary.
- The Agent executable is not yet delivered by a supported signed installer or
  managed Windows Service lifecycle.
- Autologon is a lab-validated bootstrap with a privileged-host threat tradeoff;
  customer provisioning and recovery are not productized.
- Some persistence, transport, security, scheduler, and update modules are
  foundations not composed into the current HTTP Agent runtime.

## Definition of Done

The live three-Runner CI eligibility gate is satisfied for the Pipeline #11
candidate: the same SHA-256 passed source/build, real Worker-backed reads, and
packaging. Final publication still requires the controlled promotion/tag,
artifact-retention, clock-risk, and human-approval conditions in the release
audit. Commercial production readiness additionally requires supported installation, service lifecycle,
security, recovery, and operations acceptance. Passing unit tests or a lab boot
alone does not satisfy either bar.
