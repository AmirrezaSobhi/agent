# Architecture Risk Register

**Status:** Open risks at Blueprint v1.0-draft. Priority is qualitative and
must be reassessed as evidence changes.

| ID | Risk | Impact | Mitigation / evidence gate | State |
|---|---|---|---|---|
| AR-01 | UI control reuses permissive `/command` defaults | Unauthorized privileged operations | Separate authenticated API; negative auth tests; see ADR-ARCH-005 | Open, release blocker for privileged UI |
| AR-02 | Service Session 0 cannot directly own interactive MT5 session | Runtime unavailable or insecure desktop interaction workaround | Preserve split-session Worker; session lifecycle matrix; existing ADR-001 | Accepted boundary; recovery incomplete |
| AR-03 | Autologon/account bootstrap exposes credentials or creates unusable session | Credential compromise or failed boot | Explicit consent, identity-specific secret design, session readiness check | Open, installer gate |
| AR-04 | RDP disconnect/logoff/restart semantics vary by Windows policy | Unexpected Worker exit or duplicate runtime | Profile-specific tests on each supported OS | Open |
| AR-05 | Concurrent requests exceed MT5 API safety or timeout leaves work running | Duplicate/unknown trading action | Serialized operation lane, bounded admission, reconcile ambiguous result | Open; no production trade commands |
| AR-06 | Same account visible from several Agents | Split-brain writes and duplicate orders | Execution lease, fencing epoch, idempotency and broker reconciliation | Deferred to multi-Agent phase |
| AR-07 | UI displays stale state as current | Operator acts on false readiness | Observation timestamp/freshness, explicit stale/unknown states | v0.1.4 acceptance gate |
| AR-08 | Machine, user and central policy values collide | Privilege escalation or stale override | Explicit ownership/schema/revision and deny-precedence model | Proposed |
| AR-09 | Credential storage is bound to wrong Windows identity | Runtime cannot use or leaks secret | Validate access identity, rotation, backup and recovery before selection | Open |
| AR-10 | Support bundle includes broker or customer secrets | Privacy/financial harm | Allowlist collection, redaction, manifest, preview, consent, secret scan | v0.1.4 gate |
| AR-11 | Installer/update migration fails during active runtime | Downtime or incompatible state | Signed artifacts, safe install windows, staged update and tested rollback | Deferred; release gates needed |
| AR-12 | UI framework/packaging/accessibility unproven | v0.1.4 infeasible or poor UX | KivyMD compatibility, screen-reader, DPI, RTL and build spike | Open |
| AR-13 | Windows UI test infrastructure absent | Acceptance claims unverified | Add isolated UI automation or documented witnessed manual procedure | Infrastructure gap |
| AR-14 | Billing exhaustion disables protective operation | Existing exposure unmanaged | Separate new-order authorization from position protection; explicit offline policy | Open business/security policy |
| AR-15 | Release publisher not exercised over required TLS/token path | Failed or unsafe publication | Recheck HTTPS trust, scoped write access, owner approval, read-back | Open release readiness item |
| AR-16 | Clock drift breaks expiry, audit ordering or release evidence | Incorrect authorization/time windows | Verify synchronized clocks, monotonic local deadlines, bounded skew policy | Open compatibility/release gate |

No risk entry asserts a vulnerability has been exploited. Risks here are
architectural failure modes and missing verification evidence.
