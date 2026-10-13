"""Blocking lifecycle host for packaged Windows Service mode without HTTP."""

from __future__ import annotations

import threading


class IdleHostingPort:
    """Keep the Agent lifecycle alive until Service shutdown without a socket."""

    def __init__(self) -> None:
        self._stopping = threading.Event()

    def serve(self) -> None:
        self._stopping.wait()

    def shutdown(self) -> None:
        self._stopping.set()
