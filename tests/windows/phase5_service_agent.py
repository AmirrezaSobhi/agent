"""Run the real read-only Agent Management pipe for a temporary SCM test host.

The companion C# ServiceBase adapter starts this process in Session 0. The
Runtime adapter is deliberately configuration-disabled so no Worker, MT5
terminal, trading operation, or production registry configuration is touched.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

import win32api
import win32con
import win32event
import win32security

from agent.adapters.runtime_worker_mt5_adapter import RuntimeWorkerMT5Adapter
from agent.application.host import ApplicationHost
from agent.core.agent import Agent
from agent.infrastructure.composite_host import CompositeHostingPort
from agent.infrastructure.environment_config import EnvironmentConfigurationProvider
from agent.infrastructure.logging_observability import configure_logging
from agent.infrastructure.management_named_pipe import ManagementNamedPipeServer, build_status


ALLOWLIST_SID = "S-1-5-21-950479549-2068523145-3370569714-500"
STOP_EVENT_NAME = "Global\\MT5AgentPhase5TestStop"
CONTEXT_PATH = Path(os.environ.get(
    "MT5_AGENT_PHASE5_CONTEXT",
    r"C:\Users\Administrator\AppData\Local\Temp\mt5agent-phase5-service-context.json",
))


def _identity() -> tuple[str, int, int]:
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        sid = win32security.ConvertSidToStringSid(
            win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        )
    finally:
        win32api.CloseHandle(token)
    session = win32process_id_session(os.getpid())
    return sid, session, os.getpid()


def win32process_id_session(pid: int) -> int:
    import ctypes

    value = ctypes.c_uint32()
    if not ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(value)):
        raise OSError(ctypes.get_last_error(), "ProcessIdToSessionId failed")
    return int(value.value)


class _BlockingHost:
    def __init__(self, stop: threading.Event) -> None:
        self._stop = stop

    def serve(self) -> None:
        self._stop.wait()

    def shutdown(self) -> None:
        self._stop.set()


def main() -> int:
    os.environ["MT5_AGENT_MANAGEMENT_ALLOWED_SIDS"] = ALLOWLIST_SID
    os.environ["MT5_AGENT_LOG_LEVEL"] = "INFO"
    os.environ["MT5_AGENT_LOG_FILE"] = r"C:\Users\Administrator\AppData\Local\Temp\mt5agent-phase5-agent.log"
    sid, session_id, pid = _identity()
    CONTEXT_PATH.write_text(json.dumps({
        "process_sid": sid,
        "session_id": session_id,
        "pid": pid,
        "python_agent_core": True,
        "runtime_adapter": "disabled_for_phase5_test",
        "management_pipe": r"\\.\pipe\MT5Agent.Management.v1",
        "http_listener": False,
    }, indent=2) + "\n", encoding="utf-8")

    config = EnvironmentConfigurationProvider().load()
    logger = configure_logging(config.logging)
    logger.info("Phase 5 test Agent context process=%s session=%s sid=redacted", pid, session_id)
    adapter = RuntimeWorkerMT5Adapter(
        configuration_error="PHASE5_TEST_RUNTIME_DISABLED",
        require_session_zero=True,
    )
    agent = Agent(adapter, logger=logger)
    management = ManagementNamedPipeServer(lambda: build_status(agent), config.management.allowed_user_sids,
                                           logger=logger)
    stopped = threading.Event()
    control = win32event.OpenEvent(win32event.EVENT_MODIFY_STATE | win32event.SYNCHRONIZE,
                                   False, STOP_EVENT_NAME)

    def wait_for_service_stop() -> None:
        win32event.WaitForSingleObject(control, win32event.INFINITE)
        stopped.set()
        host.shutdown()

    host = CompositeHostingPort(_BlockingHost(stopped), management, logger=logger)
    signal_thread = threading.Thread(target=wait_for_service_stop, name="Phase5 test stop signal", daemon=True)
    signal_thread.start()
    status = ApplicationHost(agent, host, logger=logger).run()
    signal_thread.join(timeout=2.0)
    win32api.CloseHandle(control)
    try:
        CONTEXT_PATH.unlink()
    except OSError:
        pass
    return 0 if status.ok else 1


if __name__ == "__main__":
    import win32process

    raise SystemExit(main())
