from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ConfigurationError(ValueError):
    """Raised when startup configuration violates the application contract."""


@dataclass(frozen=True)
class HTTPTransportConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    max_request_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ConfigurationError("http host must be a non-empty string")
        if not isinstance(self.port, int) or isinstance(self.port, bool) or not 1 <= self.port <= 65535:
            raise ConfigurationError("http port must be an integer between 1 and 65535")
        if not isinstance(self.max_request_bytes, int) or isinstance(self.max_request_bytes, bool) or self.max_request_bytes <= 0:
            raise ConfigurationError("max_request_bytes must be a positive integer")


@dataclass(frozen=True)
class ManagementPipeConfig:
    pipe_name: str = r"\\.\pipe\MT5Agent.Management.v1"
    allowed_user_sids: tuple[str, ...] = ()
    max_message_bytes: int = 65_536
    request_timeout_ms: int = 2_000

    def __post_init__(self) -> None:
        if self.pipe_name != r"\\.\pipe\MT5Agent.Management.v1":
            raise ConfigurationError("management pipe name is fixed by protocol version")
        if not isinstance(self.allowed_user_sids, tuple) or any(
            not isinstance(sid, str) or not sid.startswith("S-") or len(sid) > 184
            for sid in self.allowed_user_sids
        ):
            raise ConfigurationError("management allowlist must contain Windows SID strings")
        if len(set(self.allowed_user_sids)) != len(self.allowed_user_sids):
            raise ConfigurationError("management allowlist contains duplicate SIDs")
        if self.max_message_bytes != 65_536:
            raise ConfigurationError("management protocol v1 message limit is fixed at 65536 bytes")
        if self.request_timeout_ms != 2_000:
            raise ConfigurationError("management protocol v1 request timeout is fixed at 2000 ms")


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    file: str | None = None

    def __post_init__(self) -> None:
        if self.level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ConfigurationError("MT5_AGENT_LOG_LEVEL must be DEBUG, INFO, WARNING or ERROR")
        if self.file is not None and (not isinstance(self.file, str) or not self.file.strip()
                                     or any(c in self.file for c in "\x00\r\n")):
            raise ConfigurationError("MT5_AGENT_LOG_FILE must be a non-empty file path")


@dataclass(frozen=True)
class AgentConfig:
    http: HTTPTransportConfig = HTTPTransportConfig()
    logging: LoggingConfig = LoggingConfig()
    management: ManagementPipeConfig = ManagementPipeConfig()


@runtime_checkable
class ConfigurationProvider(Protocol):
    def load(self) -> AgentConfig: ...
