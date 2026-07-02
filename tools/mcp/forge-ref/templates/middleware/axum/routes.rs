//! Route handlers.
//!
//! `/health` (liveness) and `/ready` (readiness) have different semantics and
//! must not be conflated: liveness checks only that the process is responsive
//! (a momentary dependency outage must NOT fail it, or the orchestrator
//! restarts a healthy process); readiness checks that required dependencies
//! are reachable right now (the load balancer uses it to route traffic).
use std::sync::Arc;

use axum::extract::State;
use axum::Json;
use serde_json::{json, Value};

use crate::config::Settings;

/// Liveness probe: 200 while the process is responsive. Checks no dependencies.
pub async fn health() -> Json<Value> {
    Json(json!({ "status": "ok" }))
}

/// Readiness probe: 200 only when required dependencies are reachable. Replace
/// the stub checks with real dependency probes (DB ping, Key Vault, etc.).
pub async fn ready() -> Json<Value> {
    // TODO: replace stub with real dependency probes.
    let checks = json!({ "self": "ok" });
    let overall = if checks
        .as_object()
        .map(|m| m.values().all(|v| v == "ok"))
        .unwrap_or(false)
    {
        "ok"
    } else {
        "degraded"
    };
    Json(json!({ "status": overall, "checks": checks }))
}

/// Service identity and deployed version. Does not expose auth or dependency
/// health; use `/ready` for that.
pub async fn status(State(settings): State<Arc<Settings>>) -> Json<Value> {
    Json(json!({
        "service": env!("CARGO_PKG_NAME"),
        "version": env!("CARGO_PKG_VERSION"),
        "environment": settings.runtime.environment,
    }))
}
