"""
FastAPI app factory for ${project_name}.

The factory pattern keeps the app construction separate from the uvicorn
entrypoint. Tests import `create_app()` directly; main.py starts uvicorn.

Middleware ordering matters. Starlette executes middleware in the REVERSE
order they are added, so the first `add_middleware` call is the OUTERMOST
layer. The ordering below is deliberate:

    1. TrustedHostMiddleware  (outermost: reject bad Host headers first)
    2. RequestSizeLimitMiddleware  (reject oversized requests next)
#IF has_cors
    3. CORSMiddleware
    4. RequestIDMiddleware  (assign ID before anything else touches the request)
    5. SecurityHeadersMiddleware  (innermost: set headers on outbound response)
#ELSE
    3. RequestIDMiddleware  (assign ID before anything else touches the request)
    4. SecurityHeadersMiddleware  (innermost: set headers on outbound response)
#ENDIF
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
#IF has_cors
from fastapi.middleware.cors import CORSMiddleware
#ENDIF
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ${pkg} import __version__
from ${pkg}.config import Settings, get_settings
from ${pkg}.exceptions import register_exception_handlers
from ${pkg}.middleware.request_id import RequestIDFilter, RequestIDMiddleware
from ${pkg}.middleware.security import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from ${pkg}.routers import health, v1


def _configure_logging(level: str) -> None:
    """
    Configure root logging with request-ID enrichment.

    The RequestIDFilter is attached to the HANDLER, not the logger. Filters
    on a logger only run for records emitted through that logger; records
    propagated from child loggers (uvicorn, starlette, any library) skip
    them and would reach the formatter without a request_id attribute,
    crashing every log call made outside the middleware path. Handler
    filters run for every record the handler processes. The formatter
    `defaults` entry is a second layer of protection for records that reach
    a different handler entirely.
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(RequestIDFilter())
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
                defaults={"request_id": "-"},
            )
        )
        root.addHandler(handler)


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build and return the FastAPI application.

    Accepts an optional Settings override so tests can inject custom config
    without touching environment variables.
    """
    settings = settings or get_settings()
    _configure_logging(settings.runtime.log_level)

    app = FastAPI(
        title="${project_name}",
        version=__version__,
        # Disable the default /docs and /redoc in production; operators should
        # opt in per environment. Set to None to hide entirely.
        docs_url="/docs" if settings.runtime.environment != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.runtime.environment != "production" else None,
    )

    # Middleware stack (added in REVERSE execution order; see module docstring).
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.server.trusted_hosts,
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=settings.server.max_request_size_bytes,
    )
#IF has_cors

    # CORS: explicit allow-list pinned at generation time. No wildcards.
    # Replace the origins list with the exact cors_origins from PROJECT.md.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.server.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
#ENDIF
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # Exception handlers.
    register_exception_handlers(app)

    # Routers. Infrastructure routes at root, business routes under /api/v1/.
    app.include_router(health.router)
    app.include_router(v1.router, prefix="/api")

    return app
