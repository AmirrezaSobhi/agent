# Action Plan

Living roadmap for the accepted v0.1.3 development candidate. Historical
milestones belong in [CHANGELOG](../CHANGELOG.md); this page tracks current
state and the next evidence required.

## Current Baseline

- Split Session 0 Agent / interactive Worker / MT5 architecture:
  **IMPLEMENTED; LAB VALIDATED**.
- Dedicated standard runtime user, interactive task, Autologon cold-boot
  bootstrap, authenticated local pipe, persistent MT5 connection:
  **LAB VALIDATED**.
- Three safe MT5 reads through the production application path:
  **IMPLEMENTED; LAB VALIDATED**.
- Agent/Worker dependency and PyInstaller boundary:
  **IMPLEMENTED; LOCALLY VALIDATED**.
- Phase 4D three-Runner pipeline topology and artifact provenance gates:
  **IMPLEMENTED; LOCAL VALIDATION PASSED; LIVE CI ACCEPTANCE PENDING**.
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
- [ ] Live-accept Phase 4D through GitLab using all three Runner roles.

## Immediate Next Actions

1. Review the complete explicit Phase 4 integration staging set, including this
   documentation baseline, and resolve any uncertain/unrelated files.
2. After human authorization, stage and create the integration commit on
   `develop`; preserve unrelated worktree files and EOL-only changes carefully.
3. Push only after separate authorization/policy permits it.
4. Run the first live Phase 4D GitLab pipeline and retain pipeline/job IDs,
   artifact provenance, and redacted runtime evidence.

## Release v0.1.3 Gate

- [ ] Linux source/unit suite passes on `linux-source-unit`.
- [ ] Windows tests and isolated Agent build pass on
  `windows-self-hosted-no-mt5` with MetaTrader5 absent.
- [ ] Candidate archive excludes MetaTrader5, NumPy, Worker implementation,
  legacy direct adapter, and local terminal inspection.
- [ ] Invalid-configuration and degraded control-plane checks pass.
- [ ] Exact candidate SHA/commit/pipeline provenance is retained.
- [ ] `windows-self-hosted-mt5` consumes that candidate without rebuilding.
- [ ] Worker identity/session, authenticated IPC, connected MT5, terminal
  identity/session, and three safe reads pass.
- [ ] Final package evidence matches the original candidate hash.
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

- First live Phase 4D GitLab pipeline has not yet accepted scheduling, artifact
  transfer, and runtime-gate behavior.
- The Agent executable is not yet delivered by a supported signed installer or
  managed Windows Service lifecycle.
- Autologon is a lab-validated bootstrap with a privileged-host threat tradeoff;
  customer provisioning and recovery are not productized.
- Some persistence, transport, security, scheduler, and update modules are
  foundations not composed into the current HTTP Agent runtime.

## Definition of Done

v0.1.3 release eligibility requires the live three-Runner pipeline to validate
one candidate from source tests through the real Worker-backed reads, with the
same SHA-256 at build, runtime, and package gates. Commercial production
readiness additionally requires supported installation, service lifecycle,
security, recovery, and operations acceptance. Passing unit tests or a lab boot
alone does not satisfy either bar.
