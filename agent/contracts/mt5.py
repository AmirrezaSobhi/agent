"""Shared, transport-neutral failures from safe MT5 read operations."""


class MT5ReadError(RuntimeError):
    def __init__(self, code, details):
        super().__init__(code)
        self.code = code
        self.details = details
