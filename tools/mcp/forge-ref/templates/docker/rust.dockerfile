# syntax=docker/dockerfile:1.7
#
# Container image for ${project_name} (Rust).
#
# Multi-stage: the builder compiles a release binary with cargo against the
# committed Cargo.lock (--locked); the runtime stage carries only the binary,
# config, and minimal system packages. No cargo/rustc in the final image.
#
# Base images are pinned by digest, not tag. Dependabot opens PRs to bump the
# digest when upstream rebuilds (CVE fixes, etc.).

# =============================================================================
# Stage 1: builder
# =============================================================================
FROM rust:1-slim-bookworm@sha256:c8a94a78f67ec8c4d474ec7f71e0720f21eb7e584e158daec0874cafa7c30e4d AS builder

WORKDIR /build

# Copy the full source. (A dependency-only pre-build layer is possible but
# brittle with multiple bins; a clean --locked build is the safe default.)
COPY Cargo.toml Cargo.lock ./
COPY src/ src/

# Build only the application binary in release mode, hash-locked.
RUN cargo build --release --locked --bin ${project_slug}

# =============================================================================
# Stage 2: runtime
# =============================================================================
FROM debian:bookworm-slim@sha256:96e378d7e6531ac9a15ad505478fcc2e69f371b10f5cdf87857c4b8188404716 AS runtime

# ca-certificates for outbound TLS; tini for correct PID 1 signal handling.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Non-root user with a high UID to avoid host collisions in bind mounts.
RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid 10001 --home-dir /app --shell /sbin/nologin appuser

WORKDIR /app

#IF is_web
ENV ${slug_upper}_RUNTIME__ENVIRONMENT=production \
    # Bind to all interfaces inside the container's network namespace (the
    # isolation boundary). Keep 127.0.0.1 for local `cargo run`.
    ${slug_upper}_SERVER__HOST=0.0.0.0
#ELSE
ENV ${slug_upper}_RUNTIME__ENVIRONMENT=production
#ENDIF

# Copy only the compiled binary and the committed config.
COPY --from=builder --chown=appuser:appuser /build/target/release/${project_slug} /app/${project_slug}
COPY --chown=appuser:appuser config/ /app/config/

USER appuser

#IF is_web
# HTTP service: expose the configured port and healthcheck via the binary's
# built-in `healthcheck` subcommand (GET /health over a raw socket; no curl).
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["/app/${project_slug}", "healthcheck"]
#ENDIF
#IF ssh_server
# SSH server listens on the configured port (default 2222).
EXPOSE 2222
#ENDIF

# tini as PID 1 so the process receives SIGTERM cleanly on container stop.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/${project_slug}"]
