"""Process-signal adapter for graceful hosting shutdown."""

from __future__ import annotations

import signal
import threading
import os
import logging
from collections.abc import Callable


def install_shutdown_signal_handlers(shutdown: Callable[[], None]) -> None:
    """Translate supported process termination signals into host shutdown.

    shutdown is invoked on a separate daemon thread because Python's
    BaseServer.shutdown() must not run on the serve_forever() thread.
    """

    def handle_signal(signum: int, frame: object) -> None:
        del signum, frame
        threading.Thread(target=shutdown, name="agent-host-shutdown", daemon=True).start()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)
    if os.name == "nt":
        event_name = os.environ.get("MT5_AGENT_SHUTDOWN_EVENT", "").strip()
        if event_name:
            _install_windows_shutdown_event(event_name, shutdown)


def _install_windows_shutdown_event(event_name: str, shutdown: Callable[[], None]) -> None:
    """Wait for the owning Windows Service to request graceful shutdown."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenEventW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.OpenEventW.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    synchronize = 0x00100000
    handle = kernel32.OpenEventW(synchronize, False, event_name)
    if not handle:
        error = ctypes.get_last_error()
        raise OSError(error, "Could not open the Agent Service shutdown event")

    def wait_for_shutdown() -> None:
        try:
            result = kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)
            if result == 0:
                threading.Thread(target=shutdown, name="agent-service-shutdown", daemon=True).start()
            else:
                logging.getLogger(__name__).error(
                    "Windows Service shutdown event wait failed; wait_result=%s", result
                )
        finally:
            kernel32.CloseHandle(handle)

    threading.Thread(target=wait_for_shutdown, name="agent-service-shutdown-event", daemon=True).start()
