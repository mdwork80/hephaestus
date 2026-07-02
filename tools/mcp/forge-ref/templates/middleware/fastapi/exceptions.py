"""
Exception handlers.

Philosophy: never let an unhandled exception leak internal state to the
client. The default FastAPI behavior in debug mode can return stack traces
and library versions, which is an information-disclosure bug when it ships
to production accidentally.

The handlers here:
    * Log the full exception with stack trace and request ID.
    * Return a minimal JSON body with an error code and the request ID, so
      operators can correlate client reports to server logs.
    * Use generic error codes; no introspection into the exception type.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the standard exception handlers to the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        # Client errors (4xx) are informational; server errors (5xx) are bugs.
        if exc.status_code >= 500:
            logger.exception(
                "server_error status=%s path=%s request_id=%s",
                exc.status_code,
                request.url.path,
                request_id,
            )
        else:
            logger.info(
                "client_error status=%s path=%s request_id=%s detail=%s",
                exc.status_code,
                request.url.path,
                request_id,
                exc.detail,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "status": exc.status_code,
                "detail": exc.detail if exc.status_code < 500 else None,
                "request_id": request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        logger.info(
            "validation_error path=%s request_id=%s errors=%s",
            request.url.path,
            request_id,
            exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_failed",
                "errors": exc.errors(),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(
            "unhandled_exception path=%s request_id=%s",
            request.url.path,
            request_id,
        )
        # Intentionally minimal body. No exception type, no message, no stack.
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "request_id": request_id,
            },
        )
