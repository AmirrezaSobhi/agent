# MT5Agent Architecture Blueprint v1.0-draft

**Status:** Draft for architectural approval; not a release commitment.
**Repository baseline:** GitLab `origin/develop`, `d99182211696ef877171fda287dee01ef6e3fce7`, audited 2026-10-08.
**Principle:** Design for Scale, Implement for Today.

## 1. Purpose and status vocabulary

This blueprint defines the long-term architecture of MT5Agent as the Windows
execution client of a future commercial AI Trading Platform, while preserving
the narrower, evidenced v0.1.3 implementation. It is a documentation baseline,
not authority to build central services or trade. “Accepted” applies only to
decisions recorded as agreed by the Product Owner; unapproved technical
choices remain Proposed or Open in the [ADRs](adr/README.md).

## 2. System context

**Accepted target:** central services make and authorize decisions; the Agent
checks identity, current policy, runtime state, and mandatory safety controls,
then executes only authorized instructions and reports structured outcomes.
The Agent is not an independent speculative strategy engine. Billing, customer
identity, Agent identity, device identity, terminal/account identity, and
runtime identity are separate domains.

```mermaid
flowchart LR
  Customer[Customer and operators]
  UI[Windows Desktop UI]
  Agent[Windows Agent Service and Core]
  Worker[Interactive Runtime Worker]
  MT5[MT5 terminal and broker]
  CP[Future Central Control Plane]
  Brain[Future AI Trading Brain]
  Bill[Future Billing Platform]
  Customer --> UI
  UI <-->|authorized local management| Agent
  CP <-->|versioned authenticated commands and results| Agent
  Agent <-->|secured local IPC| Worker
  Worker <-->|allowlisted operations| MT5
  Brain -->|decision proposal subject to policy| CP
  CP --> Bill
```

**Deferred:** central control plane, AI brain, billing service, central
management UI, and Kubernetes deployment. They are future logical layers, not
current repository components. Kubernetes is an evolution option, not a
present deployment assumption.

## 3. Logical component architecture

```mermaid
flowchart TB
  subgraph Central[Future Control Plane]
    IAM[Tenant, identity, roles]
    Registry[Agent, device, account, runtime registry]
    Policy[Policy and risk engine]
    Orchestrator[Command orchestration and audit]
    Billing[Metering and credit ledger]
    IAM --> Registry --> Policy --> Orchestrator
    Orchestrator --> Billing
  end
  subgraph Windows[Windows Client]
    UI[Desktop UI and tray]
    LocalAPI[Versioned local management interface]
    Service[Agent Service]
    Core[Agent Core, policy gate, diagnostics]
    Supervisor[Runtime supervisor]
    Worker[Interactive Runtime Worker]
    Terminal[MT5 terminal]
    Config[Machine configuration and user preferences]
    Audit[Local operational and security records]
    UI <--> LocalAPI <--> Service
    Service --> Core --> Supervisor --> Worker --> Terminal
    Config --> UI
    Config --> Core
    Core --> Audit
  end
  Orchestrator <-->|authenticated transport| Core
```

This is a target decomposition. The actual composition currently consists of
Agent, dispatcher, HTTP transport/host, observability, and an MT5 port selected
at composition; see [baseline](IMPLEMENTATION_BASELINE.md). The Desktop UI,
Windows Service packaging, local UI API, supervisor product workflow, and
central services are not present as complete product capabilities.

## 4. Boundaries and trust

```mermaid
flowchart LR
  subgraph T1[Untrusted customer and local process boundary]
    UI[UI and other local processes]
  end
  subgraph T2[Privileged machine boundary]
    Service[Agent Service]
    Config[Machine policy and configuration]
  end
  subgraph T3[Interactive user session boundary]
    Worker[Runtime Worker principal]
    Terminal[MT5 terminal]
  end
  subgraph T4[Remote boundary]
    Central[Central platform]
    Broker[Broker state]
  end
  UI -->|authenticate, authorize, audit| Service
  Service -->|ACL, peer and protocol validation| Worker
  Worker --> Terminal
  Service <-->|TLS, enrollment, policy| Central
  Terminal <-->|broker protocol| Broker
```

The current Named Pipe secures the Session 0 Agent-to-Worker link and is not a
UI API. The current `/command` HTTP composition is not approved for privileged
UI use. The UI must never receive a shortcut around Agent authorization or
access Worker IPC directly. See [security](SECURITY_MODEL.md) and
[local API](LOCAL_API.md).

## 5. Core architectural rules

1. Service, UI, and Worker have independent lifecycles. UI shutdown or failure
   does not stop the Service or Worker; Service availability does not imply
   MT5 readiness.
2. One active Runtime is in v0.1.4 scope. Model identity and ownership so later
   multi-runtime operation does not rely on a process-global terminal.
3. Only the interactive Worker owns the MT5 Python API on the supported Windows
   production path. Keep MT5 operations serialized until thread safety is
   demonstrated.
4. Enforce least privilege and explicit policy before every privileged action.
   UI experience level never grants permission.
5. An execution timeout is not proof of cancellation. Never replay an order
   with unknown outcome; reconcile against broker state first.
6. Billing balance is not an authentication factor or trade authorization.
   Protect and report existing positions independently from new-trade ability.
7. Status includes source and observation time. Unknown/stale values are never
   presented as live.
8. Preserve Build Once → Test Same Artifact → Release Same Artifact.

## 6. Domain and policy overview

Tenant owns Users, Devices, Agent Instances, Policies, and Billing Wallets.
Agent Instances register one or more Terminal Installations and Runtime
Instances; Trading Accounts may be visible to more than one Agent, while a
separate exclusive Execution Lease grants one active writer. Commands carry
idempotency and ownership epochs. Details and lifecycle are in the
[domain model](DOMAIN_MODEL.md).

Effective policy combines mandatory local safety, central risk policy,
organization policy, customer preference, role permissions, and account
constraints. Conflict resolution is fail-closed for new execution. Commands
that protect existing positions have their own authorization classes; a
stop-loss change is not inherently risk-reducing. See [trading safety](TRADING_SAFETY.md).

## 7. Security, configuration, and local contracts

Use separate machine configuration, per-Windows-user preferences, and future
central policy. Enforce ownership, schema/revision, validation, migration,
ACLs, secret storage under the consuming identity, and explicit offline
behavior. Never let UI preferences weaken safety policy. See
[configuration](CONFIGURATION.md).

The target local management API is versioned, authenticated, least-privilege,
bounded, correlated, and audited. HTTP Loopback versus Windows-native IPC is
an **Open Decision**. Starting a stopped Service uses Windows Service Control
Manager/UAC permissions, not an API hosted by that stopped Service. See
[local API](LOCAL_API.md).

## 8. Windows lifecycle, installer, and operations

Three components are independently managed: Agent Service in Session 0,
interactive MT5 Runtime Worker in a valid nonzero user session, and Desktop UI
in the user's desktop session. Existing Autologon + `AtLogOn` lab provisioning
is evidence for one topology, not an approved general installer. Simple,
Dedicated VPS, and Enterprise Managed startup profiles need explicit recovery
and credential policy. See [Windows runtime](WINDOWS_RUNTIME.md).

Installer and signed auto-update with integrity checks, staged deployment,
health verification, rollback, and schema compatibility are target capabilities.
Only the existing build/package/release automation is current; a customer
installer and complete automatic updater are absent. Support collection is
local-first, redacted, reviewable, and requires explicit consent before any
future transmission. See [operations](OPERATIONS.md).

## 9. Desktop UX target

The modular console has Dashboard, Runtime, Accounts, Security, Settings,
Logs, Diagnostics, Updates, Support, and About modules. Dashboard status
dimensions are `SERVICE_RUNNING`, `AGENT_CONNECTED`, `WORKER_READY`,
`MT5_CONNECTED`, and `TRADING_ENABLED`. Each is independently `unknown`,
`stale`, `disconnected`, `degraded`, or `ready` with reason and observation
time. English is default; i18n infrastructure anticipates Persian/RTL. KivyMD
remains conditional on a compatibility, accessibility, and packaging spike.
See [Desktop UI](DESKTOP_UI.md).

## 10. Commercial expansion

Future central layers include Tenant/IAM/RBAC, Agent/Device/Account/Runtime
registries, policy/risk evaluation, orchestrator, audit, support, enrollment,
licensing, and update management. Billing adds a wallet, pricing policy,
usage metering, transaction records, and auditable ledger. Credit exhaustion
may disable new discretionary operations under policy; it must not silently
disable monitoring, reporting, or protective management of existing positions.
Exact grace and billing rules are Open Decisions. See [vision](PRODUCT_VISION.md).

## 11. v0.1.4 boundary

Target: modular Desktop Shell, navigation, real status, one active Runtime,
local setup, split configuration, user preferences, English/i18n foundation,
secure minimal local API, service-independent launch, offline guidance, tray,
close behavior, basic notices, safe logs/diagnostics, minimal support export,
authorized management, concurrency hardening, and Windows validation.

Substantial privileged foundations (service installation/control, a new local
authorization surface, runtime account creation or Autologon changes, secure
credential transfer, production updater) require explicit release gates. Full
multi-runtime, web console, production billing, remote support, offline license
issuance, complete updater/rollback, and production failover are deferred.
Acceptance and test-infrastructure gaps are tracked in
[v0.1.4 acceptance](ACCEPTANCE_V0.1.4.md).

## 12. Navigation, decisions, and traceability

See [roadmap](ROADMAP.md), [risk register](RISK_REGISTER.md),
[glossary](GLOSSARY.md), and [14 architecture ADRs](adr/README.md). ADRs are
Proposed, Deferred, or Open unless a corresponding explicit product decision
or repository ADR supports Accepted status. No ADR here authorizes product
implementation by itself.
