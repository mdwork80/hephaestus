"""
Request ID middleware.

Assigns a unique identifier to every inbound request, exposes it on both the
request state and the response headers as X-Request-ID, and binds it to the
logging context so all log records emitted during the request carry it.

Clients may supply their own X-Request-ID; if present and well-formed, it is
trusted for correlation but not for authentication.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Context var read by the logging filter to enrich every record.
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the current request ID, or '-' outside a request scope."""
    return _request_id_ctx.get()


class RequestIDFilter(logging.Filter):
    """Logging filter that injects the current request ID into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Populate request.state.request_id and the response X-Request-ID header."""

    _HEADER = "X-Request-ID"
    _MAX_LENGTH = 128

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(self._HEADER, "").strip()
        # Accept a client-supplied ID only if it is short and printable ASCII.
        # This bounds log line size and rejects header-injection attempts.
        if (
            incoming
            and len(incoming) <= self._MAX_LENGTH
            and incoming.isascii()
            and incoming.isprintable()
        ):
            request_id = incoming
        else:
            request_id = str(uuid.uuid4())

        token = _request_id_ctx.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        response.headers[self._HEADER] = request_id
        return response
