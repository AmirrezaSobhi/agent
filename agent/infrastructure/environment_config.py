import os
from collections.abc import Mapping

from agent.contracts.configuration import AgentConfig, ConfigurationError, ConfigurationProvider, HTTPTransportConfig, LoggingConfig, ManagementPipeConfig


class EnvironmentConfigurationProvider(ConfigurationProvider):
    """Infrastructure adapter that translates process environment into AgentConfig."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = environ if environ is not None else os.environ

    def load(self) -> AgentConfig:
        http_enabled = self._boolean("MT5_AGENT_HTTP_ENABLED", True)
        host = self._environ.get("MT5_AGENT_HTTP_HOST", "127.0.0.1")
        port = self._integer("MT5_AGENT_HTTP_PORT", 8080)
        max_request_bytes = self._integer("MT5_AGENT_HTTP_MAX_REQUEST_BYTES", 1024 * 1024)
        log_level = self._environ.get("MT5_AGENT_LOG_LEVEL", "INFO").strip().upper()
        log_file = self._environ.get("MT5_AGENT_LOG_FILE") or None
        raw_sids = self._environ.get("MT5_AGENT_MANAGEMENT_ALLOWED_SIDS", "")
        sids = tuple(sid.strip() for sid in raw_sids.split(",") if sid.strip())
        return AgentConfig(HTTPTransportConfig(host, port, max_request_bytes, http_enabled), LoggingConfig(log_level, log_file),
                           ManagementPipeConfig(allowed_user_sids=sids))

    def _boolean(self, name: str, default: bool) -> bool:
        raw = self._environ.get(name)
        if raw is None:
            return default
        normalized = raw.strip().lower()
        if normalized in ("true", "1"):
            return True
        if normalized in ("false", "0"):
            return False
        raise ConfigurationError(f"{name} must be true, false, 1 or 0")

    def _integer(self, name: str, default: int) -> int:
        raw = self._environ.get(name)
        if raw is None:
            return default
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(f"{name} must be an integer") from exc
