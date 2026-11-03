"""Errors shared by the drafting engines."""


class DraftError(Exception):
    """Drafting failed. `status` is the HTTP status to return; the message is user-safe."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status
