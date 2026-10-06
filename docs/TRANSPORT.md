# Transport — v0.0.8

The production Windows Agent-to-Worker transport is a local authenticated
Named Pipe implemented separately from the HTTP command transport described
below. The pipe is local-only, ACL-authorized for the configured control-principal
SID, and restricted to a Session 0 caller. It carries bounded, versioned
allowlisted operations; it is not a TCP listener or arbitrary remote invocation
interface. See [MT5 Runtime Architecture](MT5_RUNTIME_ARCHITECTURE.md).

The v0.0.6 HTTP request contract remains unchanged: `POST /command` translates HTTP/JSON into `TransportRequest`, delegates to `ApplicationPort`, and maps `TransportResponse` back to deterministic HTTP responses.

v0.0.8 separates request translation from server lifecycle ownership:

```text
HTTPServerHost [Infrastructure]
        ↓ owns lifecycle of
ThreadingHTTPServer
        ↓ delegates request handling to
HTTPTransportAdapter
        ↓
ApplicationPort
```

`HTTPTransportAdapter` remains responsible for protocol translation, request-size enforcement, endpoint behavior, response serialization, and deterministic HTTP mapping. `HTTPServerHost` owns blocking `serve_forever()`, graceful `shutdown()`, and socket closure.

No HTTP type is introduced into `HostingPort`, ApplicationHost, Core, or domain contracts. Security ordering and identity propagation remain unchanged.

## Work Item #13 — secure transport foundation

**IMPLEMENTED:** Kafka producer and HTTPS mTLS adapter boundaries accept configured
clients only and deliver already-durable outbox records. mTLS material must exist before
client construction; paths and secrets are never logged. Send is not acknowledgement.
**PENDING PRODUCTION VALIDATION:** real Kafka broker, certificate issuance/rotation,
server authentication, outage and load behavior.

These Kafka/HTTPS adapter foundations are not the active production Agent
request path. The current Agent runtime uses its local HTTP boundary and, on
Windows, the Runtime Worker Named Pipe; presence of these adapters does not
claim a deployed broker or mTLS service.
