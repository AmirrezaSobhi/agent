"""Run independent local transports under one Agent lifecycle."""

from __future__ import annotations

import logging
import threading

from agent.infrastructure.logging_observability import safe_log


class CompositeHostingPort:
    def __init__(self, primary, management, logger=None):
        self._primary = primary
        self._management = management
        self._logger = logger or logging.getLogger(__name__)
        self._stopping = threading.Event()
        self._management_thread = None

    def _serve_management(self):
        try:
            self._management.serve()
        except Exception:
            safe_log(self._logger, logging.ERROR, "Management pipe stopped after a transport failure")

    def serve(self):
        if getattr(self._management, "enabled", False):
            self._management_thread = threading.Thread(target=self._serve_management,
                                                       name="MT5Agent management pipe", daemon=True)
            self._management_thread.start()
        try:
            self._primary.serve()
        finally:
            self.shutdown()

    def shutdown(self):
        if self._stopping.is_set():
            return
        self._stopping.set()
        try:
            self._primary.shutdown()
        finally:
            self._management.shutdown()
        if self._management_thread is not None and self._management_thread is not threading.current_thread():
            self._management_thread.join(3.0)
