# Configuration Ownership and Policy

**Status:** Three-layer target model proposed. Current partial sources are in
[Implementation Baseline](IMPLEMENTATION_BASELINE.md).

## Ownership layers

| Layer | Examples | Owner and storage principle |
|---|---|---|
| Machine configuration | MT5 path, runtime principal, service parameters, local API binding | Machine administrator/installer; machine ACL; consumed by Service/Worker. |
| Per-Windows-user preferences | Theme, language, Dashboard layout, notification preferences, Close to Tray | Current Windows user; user-scoped store; UI cannot write another user's preferences. |
| Future central policy | Trading permissions, risk limits, organization restrictions, account policies, support permissions | Signed/authenticated tenant policy with revision, provenance and expiry; central source remains distinct from local safety. |

Secrets are not ordinary configuration. Store under the principal that needs
them; use a protected OS-backed mechanism only after cross-session identity,
rotation, recovery and revocation behavior is designed.

### v0.1.4 storage proposal

- Keep existing Agent machine runtime settings in the current HKLM key until a
  separately approved migration; WPF does not edit HKLM directly.
- Store WPF layout/theme/language/notification/Close-to-Tray preferences in a
  versioned per-user file under that user's `%LOCALAPPDATA%\MT5Agent\Desktop`
  directory. Restrict ACL to that SID and SYSTEM; atomic temp-write/replace;
  invalid file falls back to defaults and is quarantined without losing
  diagnostics.
- WPF obtains machine/runtime status through the management pipe. It does not
  read/write runtime registry values or Service configuration itself.
- v0.1.4 Local Setup has no central policy store and no cloud sync. Do not
  persist a central identity/password because there is no approved central
  enrollment contract.

## Effective policy and precedence

Configuration values are not all mergeable settings. Machine facts select
local resources; user preferences control presentation; central policy controls
delegated actions; mandatory local safety can only restrict. Proposed
effective policy for an action is the intersection of applicable allows and
union of applicable denies, with mandatory safety constraints evaluated first.
Unknown/conflicting constraints fail closed for new trading. UI preferences
never override machine security or future central policy. In v0.1.4, user
preferences only change UI presentation and never touch Agent/Runtime state.
Exceptions require an explicitly authorized, narrow, audited workflow.

## Update and migration contract

Every persisted document has a schema version, owner, revision, timestamp,
source and validation status. Writes use compare-and-swap/revision checks to
avoid lost updates; validate whole candidate then atomically persist; retain
last-known-good on failure. Migrations are versioned, deterministic,
reversible where possible, and tested against backup/rollback. Incompatible
central revisions are rejected or held pending explicit reconciliation, not
silently overwritten by stale clients.

## Offline and conflicts

Cache only policy that has an explicit offline validity window and integrity
protection. Expiry or missing required policy disables new discretionary
commands; it does not automatically terminate monitoring or all allowed
protective management. Queue bounded audit/usage events with unique IDs and
later reconcile. Define precedence when a user edits preferences offline and
cloud sync later; central policy must never be overwritten by user preference
sync. Exact offline command set and conflict user experience remain open.

## Existing baseline mapping

Current runtime settings: Windows HKLM `SOFTWARE\MT5Agent\Runtime` values
for RuntimePrincipal and optional PipeName (see `agent/composition.py`). HTTP
host/port/request limit and logging are environment values
(`agent/infrastructure/environment_config.py`). This is not yet the target
three-layer configuration service and does not include general schema/revision
migration or customer credential storage.
