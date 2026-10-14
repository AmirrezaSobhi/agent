import ctypes
import os
import threading
import uuid

import pytest

from agent.infrastructure.process_signals import _install_windows_shutdown_event


@pytest.mark.skipif(os.name != "nt", reason="Windows named events are only available on Windows")
def test_windows_service_shutdown_event_invokes_host_shutdown():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateEventW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p)
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.SetEvent.argtypes = (ctypes.c_void_p,)
    kernel32.SetEvent.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    name = "Local\\MT5Agent.AgentShutdown.Test." + uuid.uuid4().hex
    event_handle = kernel32.CreateEventW(None, 1, 0, name)
    assert event_handle
    shutdown_called = threading.Event()
    try:
        _install_windows_shutdown_event(name, shutdown_called.set)
        assert kernel32.SetEvent(event_handle)
        assert shutdown_called.wait(2)
    finally:
        kernel32.CloseHandle(event_handle)
