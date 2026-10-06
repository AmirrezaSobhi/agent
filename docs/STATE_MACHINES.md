# State Machines and Target Models

**Status:** mixed. Agent/Worker/runtime rows describe implemented behavior;
command, trade, bulk-job, connectivity, configuration, and update rows include
future target models. Durable/auditable state is required before consequential
execution is implemented.

| Machine | States and safety transition |
| --- | --- |
| Agent | `STARTING → RUNNING → QUIESCING → QUIESCED → RESUMING → RUNNING`; `DEGRADED` may restrict readiness; `STOPPING → STOPPED`. Quiesced retains authenticated control/heartbeat. |
| Command | `RECEIVED → VALIDATED → AUTHORIZED → ACCEPTED → EXECUTING → RESULT_OBTAINED → RESPONSE_PERSISTED → TRANSMITTED → ACKNOWLEDGED`; terminal alternatives: rejected, expired, cancelled, ambiguous. |
| Command foundation | `CommandLifecycle` implements `RECEIVED → VALIDATED → QUEUED → RUNNING → SUCCEEDED/FAILED/AMBIGUOUS`, with expiry and pre-point-of-no-return cancellation. Authorization, durable acceptance and response states remain planned. |
| Trade | `PREPARED → POINT_OF_NO_RETURN → SUBMITTED → CONFIRMED` or `AMBIGUOUS → RECONCILING → CONFIRMED/NOT_EXECUTED`. Ambiguous never automatically re-enters submitted. |
| Bulk job | `QUEUED → RUNNING_PARTITION → CHECKPOINTED/PAUSED → RUNNING_PARTITION → COMPLETED`; cancellation/preemption happens only at safe partition boundaries. |
| Agent process | `CREATED → STARTING → RUNNING`; Worker loss can make runtime health degraded while the HTTP/control process remains alive; graceful termination is `STOPPING → STOPPED`. |
| Runtime Worker | `WORKER_STARTING → WORKER_READY → WORKER_STOPPING/WORKER_STOPPED`; IPC health is distinct from MT5 runtime health. |
| MT5 Runtime | `MT5_NOT_INITIALIZED → MT5_INITIALIZING → MT5_CONNECTED`; failures/disconnects become `MT5_DISCONNECTED`, `MT5_RECONNECTING`, or `MT5_ERROR`. The persistent Worker owns initialization, serialization, reconnect, and API shutdown. Lab cold-boot and nonzero-session operation are validated. |
| Connectivity | `CONNECTED → DISCONNECTED → OUTBOXING → RESYNCING → CONNECTED`; reconnect reconciles acknowledgements and does not invent new work. |
| Configuration | `RECEIVED → AUTHORIZED → VALIDATED → STAGED → APPLIED → HEALTHY/COMMITTED`; unhealthy becomes `ROLLED_BACK` to last-known-good. |
| Update | `OFFERED → VERIFIED → STAGED → ACTIVATED → HEALTHY/COMMITTED`; failure rolls back. Update remains future work. |
