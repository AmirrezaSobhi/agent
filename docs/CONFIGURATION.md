# Configuration

Configuration is split into a transport-neutral immutable contract and an infrastructure adapter.

| Environment variable | Default | Validation |
| --- | --- | --- |
| `MT5_AGENT_HTTP_HOST` | `127.0.0.1` | non-empty string |
| `MT5_AGENT_HTTP_PORT` | `8080` | integer, `1..65535` |
| `MT5_AGENT_HTTP_MAX_REQUEST_BYTES` | `1048576` | positive integer |

`EnvironmentConfigurationProvider` is replaceable through the `ConfigurationProvider` protocol. Core does not read process environment. No credentials or secrets are stored in `AgentConfig`.

## Windows Runtime Worker configuration

On Windows, the production composition reads machine-local policy from
`HKLM\SOFTWARE\MT5Agent\Runtime` and selects `RuntimeWorkerMT5Adapter`. The
required runtime values and their security boundaries are described in
[MT5 Runtime Provisioning](MT5_RUNTIME_PROVISIONING.md). Missing or invalid
runtime policy results in a degraded/unavailable Worker state; it does not
silently select the Administrator profile or fall back to in-process MT5.
The Linux source/test path may use the explicit legacy adapter for development
and test compatibility; it is not the supported production Windows path.

## Dependency sets

| Set | Purpose | Runtime boundary |
| --- | --- | --- |
| `requirements.txt` | Agent/control-plane runtime | No third-party package; no MetaTrader5 or NumPy |
| `requirements-dev.txt` | Tests and release-style Agent build | PyInstaller 6.22.3, pytest 9.1.1, Pillow 12.3.0; pywin32 312 on Windows; no MetaTrader5 or NumPy |
| `requirements-legacy-mt5.txt` | Explicit in-process development/legacy adapter | MetaTrader5 5.0.6231 and NumPy 1.26.4; not for Agent production build |
| `requirements-mt5-worker.txt` | Interactive Windows Worker | MetaTrader5 5.0.6231, NumPy 2.4.6, pywin32 312 on Windows |

The release-style Agent artifact excludes MetaTrader5, NumPy, the interactive
Worker implementation, the legacy direct adapter, and local terminal
inspection. The Worker environment must remain separate from the Agent build
environment. These are requirements-file pins for the current candidate, not a
claim that a v0.1.3 release artifact has been published.

There is no active YAML/TOML/JSON config-file loader or Vault/secrets-manager
integration. The Windows runtime registry key is machine-local deployment
policy, not remote configuration. Production IAM and service identity
provisioning remain future work.

## Remote configuration — Work Item #11

**IMPLEMENTED foundation:** versioned candidates are policy-validated before atomic apply;
`LOCAL_ONLY` values (including trust roots) reject remote mutation, while `WITH_LIMITS`
values retain local bounds. A failed health check leaves the known-good revision active;
rollback restores the prior revision. Durable remote-config storage and authenticated transport
remain **PENDING PRODUCTION VALIDATION**.

## Logging (v0.1.2)

`MT5_AGENT_LOG_LEVEL` accepts DEBUG, INFO (default), WARNING and ERROR,
case-insensitively. Invalid levels produce the existing configuration error exit
2 in normal mode; diagnostics report not-ready with exit 1.
`MT5_AGENT_LOG_FILE` optionally appends UTF-8 logs to an existing parent directory.
Opening/writing a log sink is best-effort and does not fail the runtime.
Inspection-only diagnostics never create the file.
