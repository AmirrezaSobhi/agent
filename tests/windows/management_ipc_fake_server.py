"""Cross-process Windows fixture: Agent lifecycle -> Management Pipe -> WPF client.

The Runtime adapter is deterministic test data. This verifies real Agent and
ApplicationHost lifecycle code and the OS Named Pipe, but does not claim that a
deployed Worker or MT5 terminal was present.
"""

from __future__ import annotations

import os
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

if os.name != "nt":
    raise SystemExit("Windows only")

import win32api
import win32con
import win32security

from agent.core.agent import Agent
from agent.application.host import ApplicationHost
from agent.infrastructure.composite_host import CompositeHostingPort
from agent.infrastructure.management_named_pipe import ManagementNamedPipeServer, build_status


def current_sid() -> str:
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token, win32security.TokenUser)[0])
    finally:
        win32api.CloseHandle(token)


class TestRuntimeAdapter:
    runtime_state = "MT5_CONNECTED"
    health_details = {
        "worker_available": True,
        "worker_state": "WORKER_READY",
        "runtime_state": "MT5_CONNECTED",
        "mt5_connected": True,
    }

    def connect(self) -> bool:
        return True

    def is_connected(self) -> bool:
        return True

    def disconnect(self) -> bool:
        return True


class BlockingTestHost:
    def __init__(self, ready_path: str, stop_path: str) -> None:
        self._ready_path = ready_path
        self._stop_path = stop_path
        self._stopping = threading.Event()

    def serve(self) -> None:
        with open(self._ready_path, "w", encoding="ascii") as stream:
            stream.write("AGENT_RUNNING")
        while not self._stopping.is_set() and not os.path.exists(self._stop_path):
            self._stopping.wait(0.05)

    def shutdown(self) -> None:
        self._stopping.set()


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    ready_path, stop_path = sys.argv[1:]
    agent = Agent(TestRuntimeAdapter())
    management = ManagementNamedPipeServer(lambda: build_status(agent), (current_sid(),))
    host = CompositeHostingPort(BlockingTestHost(ready_path, stop_path), management)
    status = ApplicationHost(agent, host).run()
    return 0 if status.ok and agent.state.value == "stopped" else 1


if __name__ == "__main__":
    raise SystemExit(main())
