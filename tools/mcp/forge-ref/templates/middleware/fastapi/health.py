"""
Liveness and readiness endpoints.

The two endpoints have different semantics and must not be conflated:

    GET /health  (liveness)
        Returns 200 if the process is alive and responsive. Checks no
        dependencies. Used by the orchestrator to decide whether to restart
        the container. A momentary dependency outage must NOT cause this to
        fail, or the orchestrator will restart a healthy process.

    GET /ready   (readiness)
        Returns 200 only if the service can actually serve traffic right
        now. Checks required dependencies (database, secret store, etc.).
        Used by the load balancer to decide whether to route traffic to
        this instance. Failing /ready while /health passes is the correct
        signal for "up but not serving yet" (warmup) or "degraded
        dependency" (failover).
"""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def health() -> HealthResponse:
    """Return 200 while the process is responsive."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
)
async def ready() -> ReadyResponse:
    """
    Return 200 only when all required dependencies are reachable.

    Replace the stub below with real dependency checks (database ping, Key
    Vault reachability, migration state, etc.). Each check should have a
    short timeout and return a single-word status. Aggregate into an overall
    status: 'ok' only if every dependency is 'ok'.
    """
    # TODO: replace stub with real dependency probes.
    checks = {"self": "ok"}
    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return ReadyResponse(status=overall, checks=checks)
