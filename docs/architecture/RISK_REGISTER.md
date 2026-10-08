# Architecture Risk Register

**Status:** Open risks at Blueprint v1.0-draft, updated after Phase 2 evidence.
Priority is qualitative and
must be reassessed as evidence changes.

| ID | Risk | Impact | Mitigation / evidence gate | State |
|---|---|---|---|---|
| AR-01 | WPF reuses permissive `/command` defaults | Local processes can issue currently exposed reads/commands; future privilege escalation | WPF uses dedicated Management.v1 only; keep `/command` excluded; ADR-ARCH-017 | Mitigated for WPF; keep excluded |
| AR-02 | Service Session 0 cannot directly own interactive MT5 session | Runtime unavailable or insecure desktop interaction workaround | Preserve split-session Worker; session lifecycle matrix; existing ADR-001 | Accepted boundary; recovery incomplete |
| AR-03 | Autologon/account bootstrap exposes credentials or creates unusable session | Credential compromise or failed boot | Explicit consent, identity-specific secret design, session readiness check | Open, installer gate |
| AR-04 | RDP disconnect/logoff/restart semantics vary by Windows policy | Unexpected Worker exit or duplicate runtime | Profile-specific tests on each supported OS | Open |
| AR-05 | Concurrent requests exceed MT5 API safety or timeout leaves work running | Duplicate/unknown trading action | Serialized operation lane, bounded admission, reconcile ambiguous result | Open; no production trade commands |
| AR-06 | Same account visible from several Agents | Split-brain writes and duplicate orders | Execution lease, fencing epoch, idempotency and broker reconciliation | Deferred to multi-Agent phase |
| AR-07 | UI displays stale state as current | Operator acts on false readiness | 5 s polling/15 s stale threshold and explicit stale/error state implemented; verify age presentation interactively | Open UI verification gate |
| AR-08 | Machine, user and central policy values collide | Privilege escalation or stale override | Explicit ownership/schema/revision and deny-precedence model | Proposed |
| AR-09 | Credential storage is bound to wrong Windows identity | Runtime cannot use or leaks secret | Validate access identity, rotation, backup and recovery before selection | Open |
| AR-10 | Support bundle includes broker or customer secrets | Privacy/financial harm | Allowlist collection, redaction, manifest, preview, consent, secret scan | v0.1.4 gate |
| AR-11 | Installer/update migration fails during active runtime | Downtime or incompatible state | Signed artifacts, safe install windows, staged update and tested rollback | Deferred; release gates needed |
| AR-12 | WPF build/deployment package not yet proven on net48 matrix | v0.1.4 infeasible or poor UX | Official-pack clean build on Windows 10 passed; package and remaining OS matrix required | Open |
| AR-13 | Windows interactive UI test infrastructure absent | Acceptance claims unverified | Add Windows 11 interactive UIA runner; keep Session 0 build/runtime jobs separate | Infrastructure gap |
| AR-14 | Billing exhaustion disables protective operation | Existing exposure unmanaged | Separate new-order authorization from position protection; explicit offline policy | Open business/security policy |
| AR-15 | Release publisher not exercised over required TLS/token path | Failed or unsafe publication | Recheck HTTPS trust, scoped write access, owner approval, read-back | Open release readiness item |
| AR-16 | Clock drift breaks expiry, audit ordering or release evidence | Incorrect authorization/time windows | Verify synchronized clocks, monotonic local deadlines, bounded skew policy | Open compatibility/release gate |
| AR-17 | Management pipe caller identity/DACL or SID provisioning does not hold on production Service | Cross-user data leak or unauthorized Runtime control | Isolated spike verified token SID and DACL; verify production Service principal, SID provisioning and full cross-session matrix | Implementation spike passed; P0 production release gate |
| AR-18 | Windows 10 commercial support outlives Microsoft security servicing | Customer UI runs on an exposed OS | Disclose lifecycle; define edition/build and current ESU/security update condition; review per release | Accepted OS with active lifecycle risk |
| AR-19 | v0.1.4 package accidentally provisions or changes Agent Service | Unplanned privileged changes/regression | User-scope package; before/after SCM/config invariant tests; no installer/service edits in Option A | Release blocker |

No risk entry asserts a vulnerability has been exploited. Risks here are
architectural failure modes and missing verification evidence.
