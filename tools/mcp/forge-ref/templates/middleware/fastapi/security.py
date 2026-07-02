"""
Security middleware.

Provides:
    * SecurityHeadersMiddleware: adds defense-in-depth response headers.
    * RequestSizeLimitMiddleware: rejects oversized requests before body parse.

HSTS is intentionally NOT set here. HSTS belongs at the TLS-terminating
ingress (Azure Front Door, Container Apps ingress, reverse proxy). Setting
it in application code is the wrong layer and creates drift risk.
"""

from __future__ import annotations

from typing import ClassVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add baseline security headers to every response."""

    _HEADERS: ClassVar[dict[str, str]] = {
        # MIME sniffing can lead to XSS when user-controlled content is served.
        "X-Content-Type-Options": "nosniff",
        # Block this origin from being framed. Adjust to SAMEORIGIN if you
        # serve UI that legitimately embeds itself.
        "X-Frame-Options": "DENY",
        # Tell browsers not to leak the full URL to cross-origin destinations.
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # Disable browser features this API does not use. Extend as needed.
        "Permissions-Policy": (
            "accelerometer=(), autoplay=(), camera=(), display-capture=(), "
            "geolocation=(), gyroscope=(), magnetometer=(), microphone=(), "
            "midi=(), payment=(), usb=()"
        ),
#IF is_web_app
        # Content-Security-Policy for HTML-serving apps. Restrictive default;
        # tighten or extend per the app's real asset sources. JSON-only APIs
        # do not serve a document context and omit this.
        "Content-Security-Policy": (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        ),
#ENDIF
    }

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in self._HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Reject requests whose declared Content-Length exceeds the configured limit.

    Note: this enforces the *declared* size via the Content-Length header. For
    transfer-encoded or lying clients, the underlying ASGI server (uvicorn)
    should be configured with a matching limit. This middleware handles the
    common case cheaply and produces a clean JSON 413 response.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_content_length"},
                )
            if declared > self._max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "request_entity_too_large",
                        "max_bytes": self._max_bytes,
                    },
                )
        return await call_next(request)
