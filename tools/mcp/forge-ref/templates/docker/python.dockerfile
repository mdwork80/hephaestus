# syntax=docker/dockerfile:1.7
#
# Container image for ${project_name}.
#
# Design notes:
#   * Base image: python:3.11-slim (Debian-based, glibc).
#     Alpine was considered and rejected due to musl wheel compatibility.
#     Distroless is a documented hardening path; see SECURITY.md.
#
#   * Multi-stage build: builder stage uses uv to materialize a virtualenv
#     from uv.lock (hash-verified). Runtime stage copies only the venv and
#     source. The uv binary is NOT present in the final image.
#
#   * Base image pinned by digest, not tag. Dependabot will open PRs to
#     bump the digest when the upstream image is rebuilt (CVE fixes, etc.).
#     To update manually: `docker buildx imagetools inspect python:3.11-slim`
#     and copy the `Digest:` value below.

# =============================================================================
# Stage 1: builder
# =============================================================================
# Digest below corresponds to a recent python:3.11-slim. Replace on update.
FROM python:3.11-slim@sha256:ae52c5bef62a6bdd42cd1e8dffef86b9cd284bde9427da79839de7a4b983e7ca AS builder

# Prevent Python from buffering stdout/stderr so logs appear in real time.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_NO_CACHE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv via pip. Slower than the upstream installer but avoids an
# external binary pull that would couple our build to uv's release cadence.
RUN pip install --no-cache-dir "uv>=0.4.0"

WORKDIR /build

# Copy only the files needed for dependency resolution first. This keeps the
# dependency layer cached across source-only changes.
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

# Sync against the lockfile.
#   --frozen       Refuses to update the lockfile. Correct behavior in CI
#                  and image builds; any lockfile change must be a conscious
#                  commit, not a build side-effect.
#   --no-dev       Excludes dev extras (pytest, ruff, etc.) from the runtime
#                  image. Keeps the image small and attack surface minimal.
#   --no-editable  CRITICAL for multi-stage builds. Without this, the venv
#                  contains an editable install pointing at /build/src,
#                  which does not exist in the runtime stage. The container
#                  would start, then fail with ModuleNotFoundError. Do NOT
#                  remove this flag. If you want an editable install for
#                  local development, use `uv sync` outside the container.
RUN uv sync --frozen --no-dev --no-editable

# =============================================================================
# Stage 2: runtime
# =============================================================================
FROM python:3.11-slim@sha256:ae52c5bef62a6bdd42cd1e8dffef86b9cd284bde9427da79839de7a4b983e7ca AS runtime

#IF is_web
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Tell the app where its config lives when running in-container.
    ${slug_upper}_RUNTIME__ENVIRONMENT=production \
    # REQUIRED for containerized operation. The container's network namespace
    # is the isolation boundary, so uvicorn must accept connections from
    # outside its own loopback. Without this, Docker port mapping cannot
    # reach the app and all external requests fail with "connection closed".
    # 0.0.0.0 here is NOT equivalent to 0.0.0.0 on bare metal; the container
    # is already isolated. The default.toml value (127.0.0.1) remains the
    # correct choice for local `uv run` outside a container.
    # DO NOT change this back to 127.0.0.1 "for safety" -- it will break the
    # container on every deployment target that is not local development.
    ${slug_upper}_SERVER__HOST=0.0.0.0
#ELSE
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Tell the app where its config lives when running in-container.
    ${slug_upper}_RUNTIME__ENVIRONMENT=production
#ENDIF

# ca-certificates is required for outbound HTTPS (Key Vault, identity
# providers, etc.). tini provides proper PID 1 behavior so signals reach
# the Python process instead of being swallowed by the kernel's PID-1
# special-casing.
#
# hadolint ignore DL3008 (apt version pinning): we intentionally take the
# current version of these OS packages at build time so security patches
# land in the image on rebuild. Pinning to a specific Debian version would
# create drift from upstream security updates.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Remove the base image's Python packaging tools (pip/setuptools/wheel). The
# app runs from /app/.venv and never invokes them at runtime; removing them
# shrinks the attack surface and clears CVEs in those build-only packages
# (the container-image vulnerability scan in CI flags them otherwise).
RUN rm -rf /usr/local/lib/python3.11/site-packages/pip* \
           /usr/local/lib/python3.11/site-packages/setuptools* \
           /usr/local/lib/python3.11/site-packages/wheel* \
           /usr/local/lib/python3.11/site-packages/pkg_resources* \
           /usr/local/bin/pip*

# Create a non-root user with a high UID to avoid collision with host users
# in bind-mount scenarios.
RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /sbin/nologin appuser

WORKDIR /app

# Copy the materialized virtualenv and source from the builder stage.
COPY --from=builder --chown=appuser:appuser /build/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /build/src /app/src
COPY --chown=appuser:appuser config/ /app/config/

USER appuser

#IF is_web
# HTTP service: expose the configured port and healthcheck via /health.
EXPOSE 8000

# Healthcheck uses Python stdlib so the image doesn't need curl/wget.
# The /health endpoint does not check dependencies; failing it means the
# process is unresponsive, not that a dependency is down.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)" || exit 1
#ELSE
# Non-HTTP runtime: healthcheck verifies the package is importable and the
# config loads. This catches most "broken image" failure modes without
# requiring the workload to expose an HTTP port.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "from ${pkg}.config import get_settings; get_settings()" || exit 1
#ENDIF

# tini as PID 1 so Python receives SIGTERM cleanly on container stop.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "${pkg}.main"]
