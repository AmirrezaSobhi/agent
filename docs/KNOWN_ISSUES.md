# Known issues and maintenance status

## Resolved in v0.1.1 development

- **KI-001:** `agent.get_status` now reads `agent.identity.version` and
  `agent.identity.app_name`. Regression tests cover the real dispatcher and
  composed HTTP path without adding a compatibility `config` attribute.
- **KI-002:** `agent.__version__` is the authority for package metadata,
  default runtime identity and executable naming. CI rejects mismatching tags.

## Current status

The previous Session 0 limitation has been resolved for the accepted split
runtime architecture. Phase 3F cold-boot acceptance demonstrated automatic
`MT5RuntimeUser` interactive logon without RDP/console interaction, automatic
Worker task startup, authenticated Session 0 IPC, MT5 initialization,
connected health, same-session terminal ownership, safe reads, and persistent
runtime health. This is lab evidence, not a general installer/support
acceptance.

v0.1.3 is released from tag `v0.1.3` at commit
`970c04712853295fd065094b11a2bd541b5a9db8`; Release Pipeline #16 passed all
eight gates. Pipeline #11 remains historical candidate evidence. Pipeline #17
is separate post-release validation on `develop`; its first MT5 runtime smoke
failed, while a later execution succeeded. The initial failure cause is
unknown and Worker startup reliability remains under investigation. The
repository still lacks generally productized Windows Service
installation/recovery, signed installer/upgrades, and customer provisioning.
See [Action Plan](ACTION_PLAN.md) and
[post-release validation](evidence/v0.1.3/post-release-validation.md).

## Historical maintenance issues

Historical paths below refer to baseline
`1a133e6c6ea1b02a039f45610182037d347390ba` and remain accessible with `git show`.

## KI-008: Direct Session 0 MT5 is unsupported; split runtime is lab validated

The original Session 0 concern remains valid for direct in-process MT5 access,
which is not the production architecture. It is resolved by the interactive
Worker boundary and was validated in the lab, including a cold boot without
human login. Do not regress to direct Session 0 MT5. Broader customer deployment
remains an open gate; Phase 4D live CI acceptance passed.

## KI-003: historical Worker is syntactically incomplete

`Version 1_0_0/agent/core/worker.py` ends inside a string literal at line 981 in
the baseline. It cannot be parsed. It is retained in Git history and is not
imported, repaired, or incorporated into the active runtime.

## KI-004: historical Kafka packaging references missing paths

`Version 1_0_0/agent/deployment/KafkaAgent.spec` refers to missing
`agent/config.example.json` and hidden import `agent.transport.kafka_transport`;
the tracked module was under `agent/transport/kafka/kafka_transport.py`.
This spec is historical only and is not reused by the canonical build.

## KI-005: historical release documents contain stale labels

Several documents inside `Version 0_0_9`, including CHANGELOG, RELEASE_NOTES,
FINAL_AUDIT and RELEASE_CHECKLIST, still describe v0.0.8. Their original contents
remain in history. The root changelog attributes those facts to v0.0.8; it does
not relabel them as proof of v0.1.0 validation. The new deployment checklist is
an unchecked template, not a retroactive modification of release evidence.

## KI-006: historical tag and checksum discrepancies need reconciliation

- `v0.0.6` resolves to `4f052425842132dffc22ab79be857255f23c2e27`, a v0.0.5
  documentation merge whose tree contains no `Version 0_0_6`. Later documents
  describe v0.0.6 HTTP functionality. Both facts are recorded in CHANGELOG.md;
  the tag must not be moved as part of this migration.
- The v0.0.2 architecture document records a different executable hash from
  the later release notes/checklist. Both hashes are preserved with provenance.
  Published release assets have not been re-downloaded in this migration.

## KI-007: older regression suites are not part of the current suite

The migration preserved six active test files; v0.1.1 adds targeted regressions. Historical tests
`test_agent.py` (latest at `Version 0_0_2/tests/`) and `test_commands.py`,
`test_dispatcher.py`, `test_security_observability.py`, `test_transport.py`
(latest at `Version 0_0_5/tests/`) remain recoverable from the baseline.
Some import the old `contracts.models.AgentConfig`; they need API adaptation
and coverage review in a separate task, not blind collection in this migration.

## KI-009: Time synchronization monitoring and persistence follow-up

Pipeline #11 acceptance observed approximately **10h30m** disagreement between
MT5-host and Linux UTC. The v0.1.3 release record states that Pipeline #16
established W32Time synchronization, independently verified UTC accuracy, and
correlated tag-pipeline timestamps with GitLab. Do not use cross-host log times
alone to infer ordering, freshness, deadlines, or replay safety. Autonomous
time polling and synchronization persistence through reboot/network transition
remain operational follow-up; see the
[operations plan](OPERATIONS.md#clock-skew-and-audit-correlation).

**Backlog:** v0.1.5 distributed-time correctness. Phase 0 (2026-10-08) found
the active HTTP command path validates that `timestamp` is ISO-8601 but does
not enforce expiry; the active Windows Named Pipe uses `time.monotonic()` for
local request deadlines. Durable lifecycle contracts contain `received_at` and
`expires_at` fields, but they are not evidence of an active remote command
expiry policy. No active token-expiry decision was found. The successful
Pipeline #16 time check is a point-in-time release observation, not proof that
time synchronization survives reboot or network loss. Phase 0 read-only
inspection on 2026-10-08 found W32Time stopped on the no-MT5 Windows Runner and
running but reporting `Leap Indicator: 3 (not synchronized)` / stratum 0 on the
MT5 Runner. Their sampled wall clocks were within approximately five seconds
of Linux UTC, so this does not prove a current 10h30m clock offset. The unsynced
service state does leave future MT5-runner acceptance timestamps without
verified synchronization. Treat KI-009 as a **potential v0.1.4 release
blocker** until a pre-tag time-source/offset check passes or the Release Owner
records explicit risk acceptance as required by the release checklist. Reopen
as an immediate security blocker if active authentication, authorization,
replay or deadline decisions are found to depend on cross-host wall time.

### Investigation plan

- Capture Windows Time Service status, selected source, offset, last sync,
  polling and correction behavior before and after reboot/network transition.
- Compare UTC on the Ubuntu host, KVM/QEMU host and guest; inspect guest RTC
  mode and Windows time zone/DST without conflating local display time with UTC.
- Correlate GitLab server, Runner, Python, MT5 terminal, protocol and log
  timestamps, recording their source, timezone and precision.
- Trace each token expiration, replay check, request deadline and command
  expiry decision to its clock source and enforcement point.
- Test controlled offset and clock-step scenarios without trading or changing
  production security controls.

### Direction to evaluate

- Use UTC-aware wall-clock timestamps for cross-host records and protocol data.
- Use monotonic clocks for elapsed-time measurement and local timeouts.
- Expose clock source, last synchronization, measured offset and confidence in
  local diagnostics; define approved skew thresholds and alerts.
- Add cross-host correlation tests and define safe behavior when skew exceeds
  the threshold. Keep these as proposals until evidence and acceptance review.

### Impact and v0.1.5 acceptance

Review logs/traces, request deadlines/timeouts, token expiry, replay protection,
audit trails, event ordering, data freshness and release evidence. Acceptance
requires: (1) a documented UTC/monotonic clock contract for every distributed
timestamp/deadline; (2) diagnostics report source, last sync and measured skew
without secrets; (3) reboot and network-transition checks remain within the
approved threshold or fail visibly; (4) controlled skew tests prove expiry,
replay and deadline behavior fails safely; and (5) CI cross-host correlation
tests do not use local display time. Regression tests must cover UTC offsets,
naive/malformed timestamps, DST transitions, monotonic timeout behavior,
forward/backward wall-clock steps, excessive skew and unavailable time source.

**Risk:** medium reliability risk while synchronization persistence and
monitoring are not proven; elevate to high/security-blocking if a security or
release decision is shown to trust unsynchronized wall clocks. No trading
operation is needed for investigation or acceptance.

## KI-010: Candidate retention and ref provenance

Job #85's package is scheduled to expire on **2026-11-05**. Preserve it and its
redacted receipts if the historical Pipeline #11 candidate is still needed.
This is distinct from the released v0.1.3 binary: Pipeline #16 Job #125's
artifact is in the Generic Package Registry as `mt5-agent` version `0.1.3`,
with its SHA-256 recorded in the release notes. A rebuild cannot recover or
replace either candidate's original provenance. See
[Release Process](RELEASE_PROCESS.md#historical-promotion-and-publication-record).

## KI-011: MT5 Worker startup reliability is not resolved

In post-release Pipeline #17, MT5 runtime smoke Job #132 failed with
`script_failure`; the expected runtime report was absent. Later Job #134 passed
and recorded `MT5_CONNECTED`, Agent Session 0, Worker and terminal Session 1,
and three successful safe reads. The root cause of Job #132 is unknown. A
Windows reboot and manual retry were reported operationally but are not
independently proven by the GitLab API. Do not attribute this incident to
startup timing without evidence, and do not mark Worker startup reliability as
resolved because of the successful later execution. See
[post-release validation](evidence/v0.1.3/post-release-validation.md).
