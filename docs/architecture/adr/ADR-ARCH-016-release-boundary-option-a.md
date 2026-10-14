# ADR-ARCH-016: v0.1.4 Release Boundary — Option A

- **Status:** Accepted by Product Owner
- **Decision date:** 2026-10-08

## Context

The former v0.1.4 plan mixed Desktop UI with new Service installation,
interactive account provisioning and broader commercial operations. Existing
Python Agent/Worker runtime is the tested operational foundation, while there
is no commercial installer or productized Windows Service provisioning flow.

## Decision

v0.1.4 delivers a professional **C# WPF Desktop Client for an already
installed and provisioned Agent/Runtime**. Python Agent and Python MT5 Runtime
Worker remain unchanged operational components. The WPF build must be
reproducible and have a testable deployment/package suitable for an already
prepared machine.

v0.1.4 does not require a complete commercial installer, automatic Windows
Service provisioning, runtime Windows account creation, full Autologon setup,
enterprise deployment orchestration, Central Control Plane, production billing,
full Auto-Update/Rollback, multi-runtime execution, or multi-Agent failover.
These are future releases. UI can start independently, open while Service is
stopped, and show local/cached diagnostics. Standard SCM/UAC may be used by an
already authorized operator; no custom elevated helper is required by Option A.

## Alternatives considered

- Bundle commercial Agent Service/Runtime installer and account bootstrap in
  v0.1.4 — rejected as scope expansion and a new privileged lifecycle surface.
- Rewrite the Python Agent/Worker for a single-language UI — rejected.
- Ship UI without a reproducible package or same-artifact validation — rejected.

## Consequences

The first package targets a prepared host and user-scope deployment. The
package must not install/change Service, Runtime account, Autologon or machine
configuration. Full install/repair/uninstall acceptance moves out of v0.1.4.
Build Once → Test Same Artifact → Release Same Artifact remains required.

## Risks

Users need a prepared runtime and may lack rights to restart Service. The
package must clearly explain prerequisites and fail gracefully offline. Windows
10 remains approved but carries an active support-lifecycle risk.

## Verification strategy

Install/extract and launch package on pre-provisioned x64 test hosts in the
approved OS matrix; assert SCM/service and Agent configuration are unchanged;
verify service-offline UI, package manifest/hash, runtime regression and
same-artifact provenance.

## Related documents

[Blueprint](../BLUEPRINT.md) · [Acceptance](../ACCEPTANCE_V0.1.4.md) ·
[Operations](../OPERATIONS.md) · [Roadmap](../ROADMAP.md) ·
[Implementation Plan](../IMPLEMENTATION_PLAN.md)
