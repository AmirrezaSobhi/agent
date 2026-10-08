# ADR-ARCH-007: Startup and Recovery Profiles

- **Status:** Accepted product constraints; startup and recovery mechanism remains Proposed
- **Date:** 2026-10-08

## Context

Lab cold-boot behavior uses an interactive runtime account bootstrap and task;
product installation must account for desktop, VPS and enterprise Windows
policies without equating account creation to interactive session readiness.

## Decision

Define Personal Desktop, Dedicated VPS Runtime and Enterprise Managed
profiles. Keep Agent Service, Worker and UI independently managed. Allow an
existing runtime account or installer-created dedicated account only after
explicit customer approval. Classify faults; use bounded retry/backoff; encode
intentional stop so it is not restarted as a crash. No broad terminal kill.

## Alternatives considered

- One startup policy for all hosts — rejected due session and admin differences.
- Treat RDP disconnect as logoff — rejected; Windows distinguishes session
  disconnect from logoff.
- Automatically create account/Autologon without consent — rejected.

## Consequences

Requires target OS/profile test matrix and decision on SCM versus Worker
supervisor restart ownership; those mechanisms are not selected here.

## Risks

Competing supervisors, credential exposure, stuck sessions and duplicate
Workers may result from poor recovery ownership.

## Verification strategy

Cold boot, RDP disconnect, logoff, crash, IPC failure, server loss, intentional
stop and retry-exhaustion tests for each supported profile.

## Related documents

[Windows Runtime](../WINDOWS_RUNTIME.md) · [Operations](../OPERATIONS.md) ·
[Risk Register](../RISK_REGISTER.md)
