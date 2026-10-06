import logging

from agent.contracts.models import AgentIdentity, HealthStatus, LifecycleState, Status
from agent.contracts.ports import MT5Port


class Agent:
    def __init__(self, mt5_adapter: MT5Port, identity: AgentIdentity | None = None, logger: logging.Logger | None = None) -> None:
        self.identity = identity or AgentIdentity()
        self.logger = logger or logging.getLogger(__name__)
        self.mt5 = mt5_adapter
        self._state = LifecycleState.CREATED

    @property
    def state(self) -> LifecycleState:
        return self._state

    def start(self) -> Status:
        if self._state is LifecycleState.RUNNING:
            return Status(True, "Agent is already running.", "already_running")
        if self._state in (LifecycleState.STARTING, LifecycleState.STOPPING):
            return Status(False, "Agent is busy with another lifecycle transition.", "lifecycle_busy")
        self._state = LifecycleState.STARTING
        try:
            connected = bool(self.mt5.connect())
        except Exception:
            self.logger.exception("MT5 adapter connection failed")
            connected = False
        if connected:
            self._state = LifecycleState.RUNNING
            return Status(True, "MT5 connection established.", "connected")
        if getattr(self.mt5, "supports_degraded_startup", False):
            # Keep the Session 0 control plane alive while its interactive Worker
            # logs on, starts, or recovers. Health remains false until MT5 is live.
            self._state = LifecycleState.RUNNING
            return Status(True, "Agent started; MT5 runtime is unavailable.", "started_degraded")
        self._state = LifecycleState.FAILED
        return Status(False, "Unable to connect to MT5.", "connection_failed")

    def stop(self) -> Status:
        if self._state is LifecycleState.STOPPING:
            return Status(False, "Agent is already stopping.", "lifecycle_busy")
        self._state = LifecycleState.STOPPING
        try:
            disconnected = bool(self.mt5.disconnect())
        except Exception:
            self.logger.exception("MT5 adapter disconnect failed")
            disconnected = False
        if not disconnected:
            self._state = LifecycleState.FAILED
            return Status(False, "Unable to stop the agent cleanly.", "disconnect_failed")
        self._state = LifecycleState.STOPPED
        return Status(True, "Agent stopped.", "stopped")

    def health(self) -> HealthStatus:
        if self._state is not LifecycleState.RUNNING:
            runtime_details = self._runtime_health_details()
            runtime_state = getattr(self.mt5, "runtime_state", None)
            if not isinstance(runtime_state, str):
                runtime_state = self._state.value.upper()
            return HealthStatus(False, self._state, f"Agent is not running ({self._state.value}).",
                                runtime_state, runtime_details)
        try:
            connected = bool(self.mt5.is_connected())
        except Exception:
            self.logger.exception("MT5 health probe failed")
            connected = False
        if connected:
            runtime_state = getattr(self.mt5, "runtime_state", "MT5_CONNECTED")
            return HealthStatus(True, self._state, "Agent and MT5 runtime are healthy.",
                                runtime_state, self._runtime_health_details())
        runtime_details = self._runtime_health_details()
        return HealthStatus(False, self._state, "Agent is running but the MT5 runtime is unavailable.",
                            getattr(self.mt5, "runtime_state", "MT5_DISCONNECTED"), runtime_details)

    def _runtime_health_details(self) -> dict[str, object]:
        details = getattr(self.mt5, "health_details", {})
        if callable(details):
            try:
                details = details()
            except Exception:
                return {"runtime_state": "MT5_ERROR"}
        if not isinstance(details, dict):
            return {}
        return dict(details)
