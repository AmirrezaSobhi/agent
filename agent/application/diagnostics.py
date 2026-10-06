"""Control-plane self-check using only the configured Runtime Worker boundary."""
from agent.contracts.configuration import ConfigurationError
from agent.contracts.models import AgentIdentity


def diagnose(config_provider, inspect_runtime):
    identity = AgentIdentity()
    configuration = {"valid": False, "http_host": None, "http_port": None}
    runtime = {
        "worker_available": False,
        "runtime_state": "RUNTIME_UNAVAILABLE",
        "last_error_code": "RUNTIME_NOT_INSPECTED",
    }
    config = None
    try:
        config = config_provider.load()
        configuration.update(valid=True, http_host=config.http.host, http_port=config.http.port)
    except ConfigurationError as exc:
        # Configuration errors contain fixed messages, never rejected raw values.
        configuration["error"] = str(exc)
    if config is not None:
        try:
            result = inspect_runtime(config)
            if isinstance(result, dict):
                # Keep the diagnostic schema to non-secret, operational evidence.
                allowed = (
                    "worker_available", "runtime_state", "mt5_initialized", "mt5_connected",
                    "worker_identity", "terminal_pid", "terminal_owner", "terminal_session_id",
                    "terminal_path", "terminal_build", "last_successful_mt5_operation",
                    "last_mt5_error", "last_error_code", "protocol_version", "control_session_id",
                )
                runtime.update({key: result[key] for key in allowed if key in result})
        except Exception:
            runtime["last_error_code"] = "RUNTIME_INSPECTION_FAILED"
    ready = (
        configuration["valid"]
        and runtime.get("worker_available") is True
        and runtime.get("runtime_state") == "MT5_CONNECTED"
        and runtime.get("mt5_initialized") is True
        and runtime.get("mt5_connected") is True
    )
    return {
        "schema_version": "2", "agent_version": identity.version, "app_name": identity.app_name,
        "configuration": configuration, "runtime": runtime, "ready": bool(ready),
        "inspection_only": True,
        "limitations": "Diagnostics query the authenticated Runtime Worker without initializing MT5. "
                       "Readiness does not prove HTTP port availability or broker-side authorization.",
    }
