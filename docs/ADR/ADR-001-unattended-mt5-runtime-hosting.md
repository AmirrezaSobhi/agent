# ADR-001: Unattended MT5 Runtime Hosting on Windows

**Status:** Accepted for the split-session lab architecture; commercial
installation/service lifecycle remains pending. The implementation history and
experiment sections below are contemporaneous records from 2026-09-24 and are
preserved as historical evidence. Their statements that the Worker, IPC, or
unattended launch were unimplemented have been superseded by the acceptance
addendum at the end of this ADR. Do not use those old status statements as the
current repository baseline.

## Runtime foundation (implemented, pending Windows lifecycle validation)

A versioned, authenticated, allowlisted Worker protocol now supports only handshake,
health, and controlled shutdown. It tracks worker instance/PID/session/account/start time,
rejects invalid tokens, versions, duplicate requests, and unknown operations, and has a
single-worker lease. It is intentionally transport-agnostic: Windows launcher, Named Pipe
ACLs, boot/logon/lock/disconnect validation and ownership-safe MT5 termination remain pending.

## Windows-native IPC (implemented; lifecycle validation pending)

The control/Worker boundary uses a Windows Named Pipe. Its security descriptor contains
an allow DACL for the current Windows user, in addition to protocol token validation.
The pipe carries bounded JSON messages only; it cannot launch arbitrary programs or
invoke arbitrary MT5/Python functions. Cross-session service-to-worker ACL deployment
and lifecycle evidence remain pending before an ADR acceptance decision.

## Controlled Worker launcher (implemented; unattended lifecycle pending)

The launcher starts only a repository-owned Worker entry point with the active Python
interpreter, captures PID/session/start metadata, and rejects a second active Worker.
It does not accept Server command lines or executable paths. This validates current-session
process ownership only; service-to-interactive-session launch and boot/logon handling remain pending.

The launcher also has a Windows token-based `CreateProcessAsUser` path for a locally selected
interactive session. Session selection is deliberately local control-plane policy, never Server input.
The policy is the locally configured `MT5_AGENT_WORKER_PRINCIPAL`; discovery records the
complete WTS inventory before selecting exactly one non-zero, active session belonging to
that principal. Missing, mismatched, ambiguous, or token-unavailable sessions fail closed.
**Decision context:** the control-plane service runs in Session 0, while the
MetaTrader5 Python package communicates with a GUI-dependent terminal. Pipeline
#39 verified local-principal matching and `WTSQueryUserToken` for the active
Session 1 principal, but `CreateProcessAsUser` returned `ERROR_ACCESS_DENIED`.
Pipeline #40 explicitly targeted `winsta0\\default` and returned the same error.
Pipeline #43 / Job #382 repeated that result on `WINDOW10-TEST` under the
LocalSystem Session 0 Runner after rediscovering the policy-bound active
session. The next gate is a dedicated transaction harness: an allowlisted,
selected-session helper snapshots both DACL descriptors, grants one temporary
ACE to the token's exact logon SID, signals the Session 0 launcher gate, and
restores and verifies both original descriptors even on timeout or exception.
It is hard-gated to `WINDOW10-TEST` and LocalSystem, is never run by ordinary
tests, and records hashes without tokens or credentials. Microsoft documents
that the selected user or logon session must have access to both objects.

## Decision

Keep the durable Agent control plane as an automatic Windows Service. Do not
claim that it directly owns MT5 IPC. Evaluate a least-privilege, session-bound
MT5 Runtime Worker supervised through authenticated local IPC; a per-user
scheduled-task launch is a candidate, not a decision. Desktop-interaction
services, user-process termination, credential exposure and trading are rejected.

## Experiment evidence (2026-09-24)

**Verified:** the GitLab Runner process ran as `MANI-PC\Administrator` in
Session 0. The experiment shell and its `Explorer.EXE` evidence ran as the same
identity in Session 1. No reference terminal existed before the probe. A
non-production worker, launched directly from Session 1 with the explicit
`C:\Program Files\MetaTrader 5\terminal64.exe` path, used the repository `.venv`
(64-bit Python 3.14.7; MetaTrader5 5.0.6180). It successfully called
`initialize`, `version`, `terminal_info`, and a read-only `account_info` presence
check; account data was not persisted. It then called `shutdown` and exited 0.

The terminal created during initialization had the worker PID as parent, ran as
`MANI-PC\Administrator` in Session 1, and remained running immediately after
Python API shutdown. No pre-existing terminal or user process was stopped. The
ignored, redacted local result is `reports/adr-001-mt5-runtime-hosting.json`;
the repeatable harness is `tools/experiments/mt5_runtime_hosting_probe.py`.

**Not tested:** boot without a user session, automatic/logon Task Scheduler
launch, locked or disconnected session behavior, terminal restart, Worker restart
supervision, service-to-Worker IPC, or Python 3.11 production compatibility.

## Candidate evaluation

| Candidate | Evidence | Outcome |
| --- | --- | --- |
| Service directly hosts MT5 | Runner is Session 0; no GUI-service hack attempted. | Blocked/rejected pending contrary safe evidence. |
| Scheduled Task in interactive context | Task Scheduler is available, but no dedicated MT5 task was created or exercised. | Plausible candidate; untested. |
| Direct session-bound Worker | Direct Session 1 probe successfully initialized/read/shutdown against reference MT5. | Viable interactive execution mechanism; not unattended. |

## Controlled non-trading experiment

Run only in an isolated/demo environment with an already-authorized terminal.
Record process/session ownership, terminal discovery, `initialize`, `version`,
`terminal_info`, and optional safely available `account_info`; test readiness and
the Worker-to-Service IPC boundary. Never place/modify/cancel orders, close
positions, delete pending orders, or broadly kill `terminal64.exe`.

**Observed success:** session-bound MT5 API viability and non-destructive Python
API shutdown were proven. **Incomplete acceptance:** a supported unattended
launcher, authenticated IPC, supervisor recovery and boot/session-state behavior
remain unproven. The production Worker implementation remains blocked.

## Acceptance and follow-up

The next experiment must create a narrowly scoped Task Scheduler or other
supported launcher in an authorized test context and collect boot/logon/locked or
disconnected-session evidence. Future ownership rules must track Worker instance,
PID, creation/session identity and launch metadata; they must never broadly kill
`terminal64.exe` processes. Service-to-Worker IPC should use authenticated local
framing (for example Named Pipes protected by explicit ACLs), with service and
Worker identities, replay/versioning and least-privilege rules specified before
implementation.

## Accepted implementation addendum (v0.1.3 development)

The chosen architecture is a Session 0 control plane with a persistent
interactive Worker under a dedicated standard local runtime user. The Worker
owns the MetaTrader5 Python connection and terminal session; the Agent uses an
authenticated local Named Pipe. The Worker task uses an interactive token after
the runtime user's logon. Deterministic unattended cold boot uses the locally
configured Sysinternals Autologon bootstrap; credentials are not stored in the
repository. Direct Session 0 MT5 operation is not the production path.

Accepted lab evidence demonstrated cold boot without RDP/console login,
automatic interactive-session creation and Worker task startup, Session 0
pipe authentication without `SeImpersonatePrivilege`, MT5 initialization,
connected health, terminal/Worker account and session match, and repeated
read-only operations. The current safe reads are symbols total, terminal
version, and account information. No trading operation is included.

This addendum does not claim a customer-ready installer, generally deployed
Windows Service, or commercial production readiness. Phase 4D's three-Runner
pipeline is now **LIVE CI ACCEPTED / GO** in
[Pipeline #11](../evidence/v0.1.3/phase4d-live-ci-acceptance.md). Historical
experiment sections above remain contemporaneous records. See [MT5 Runtime Architecture](../MT5_RUNTIME_ARCHITECTURE.md),
[Provisioning](../MT5_RUNTIME_PROVISIONING.md), and [Action Plan](../ACTION_PLAN.md).
