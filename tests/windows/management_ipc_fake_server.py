"""Disposable Windows Session 0 fixture for the Python-to-WPF pipe contract test."""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

if os.name != "nt":
    raise SystemExit("Windows only")

import win32api
import win32con
import win32security

from agent.infrastructure.management_named_pipe import ManagementNamedPipeServer


def current_sid() -> str:
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return win32security.ConvertSidToStringSid(win32security.GetTokenInformation(token, win32security.TokenUser)[0])
    finally:
        win32api.CloseHandle(token)


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    ready_path, stop_path = sys.argv[1:]
    status = {
        "service_running": True,
        "agent_state": "AGENT_RUNNING",
        "worker_available": True,
        "worker_state": "READY",
        "runtime_state": "MT5_CONNECTED",
        "mt5_connected": True,
        "central_state": "NOT_CONFIGURED",
        "trading_capability": "UNSUPPORTED",
        "trading_authorized": "NOT_AUTHORIZED",
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    host = ManagementNamedPipeServer(lambda: dict(status), (current_sid(),))
    worker = threading.Thread(target=host.serve, name="interop pipe fixture", daemon=True)
    worker.start()
    time.sleep(0.25)
    with open(ready_path, "w", encoding="ascii") as stream:
        stream.write("READY")
    deadline = time.monotonic() + 30
    while not os.path.exists(stop_path) and time.monotonic() < deadline:
        time.sleep(0.05)
    host.shutdown()
    worker.join(3)
    return 0 if not worker.is_alive() else 1


if __name__ == "__main__":
    raise SystemExit(main())
