# Security lifecycle — Work Item #12

## Windows runtime security boundary

The current Windows runtime uses a standard local `MT5RuntimeUser` in a
nonzero interactive session. The Agent/control process runs separately in
Session 0. The Worker code directory is read/execute for the runtime user;
mutable data belongs in that user's local profile. The runtime user is not
Administrator, and the Worker does not require LocalSystem or
`SeImpersonatePrivilege`.

The local Named Pipe rejects remote clients and its DACL grants access only to
the SID resolved from configured `ControlPrincipal`. The Worker independently
requires a Session 0 client. This is account-level authorization: any process
running as the authorized account is inside the trust boundary. Do not replace
the ACL with broad groups or trust a protocol-supplied username.

Deterministic cold-boot operation uses Sysinternals Autologon to establish the
required interactive session. Its encrypted LSA secret is retrievable by local
Administrators/SYSTEM; host administrator compromise means credential/host
compromise. Never put the credential in the repository, normal configuration,
command line, CI, or logs. Machine owners manage disk encryption and recovery;
MT5 Agent must never change BitLocker, TPM, Secure Boot, or recovery keys.

See [runtime architecture](MT5_RUNTIME_ARCHITECTURE.md) and
[provisioning](MT5_RUNTIME_PROVISIONING.md) for implementation details.

**IMPLEMENTED foundation:** Agent and installation identities are non-secret UUIDs.
Credential material is represented only by a SHA-256 fingerprint in the local authority;
unknown, rotated, and revoked credentials fail closed. Authorization reuses the existing
command/capability model: a READ permission cannot authorize execution.

**PENDING PRODUCTION VALIDATION:** durable secret storage, enrollment transport, certificate
issuance, mTLS, and production credential rotation/recovery. No trust anchor is remotely mutable.

## Accepted CI scope and dependency-source policy

[Pipeline #11](evidence/v0.1.3/phase4d-live-ci-acceptance.md) accepted local
Worker authorization/protocol/session checks and the read-only runtime path;
it is not a general security audit or commercial security acceptance.
Linux and Windows build/test installs use the explicitly approved existing
Liara package mirror over HTTPS. Requirements pins and Worker isolation remain
in place; changing that trust policy needs separate approval. Transitive build
dependencies are not fully locked with hashes. See [CI](CI.md#dependency-boundary).

The observed clock skew is an audit/freshness risk wherever host wall time
is trusted; see [Operations](OPERATIONS.md#clock-skew-and-audit-correlation).
Keep account payloads, credentials, pipe/Worker secret material, machine SIDs,
and private runtime profiles out of repository evidence and Wiki summaries.
