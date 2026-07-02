//! Custom middleware: TrustedHost filtering and a declared-size (Content-Length)
//! limit that returns a clean JSON 413 before the body is read. The actual-byte
//! limit is enforced separately by `tower_http::limit::RequestBodyLimitLayer`.
use std::sync::Arc;

use axum::body::Body;
use axum::extract::State;
use axum::http::{header, Request, StatusCode};
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::json;

use crate::config::Settings;

/// Reject requests whose Host header is not in `server.trusted_hosts`.
/// `["*"]` disables the check (use only locally).
pub async fn trusted_host(
    State(settings): State<Arc<Settings>>,
    req: Request<Body>,
    next: Next,
) -> Response {
    let hosts = &settings.server.trusted_hosts;
    if hosts.iter().any(|h| h == "*") {
        return next.run(req).await;
    }
    let host = req
        .headers()
        .get(header::HOST)
        .and_then(|v| v.to_str().ok())
        .map(|h| h.split(':').next().unwrap_or(h).to_string());
    match host {
        Some(h) if hosts.iter().any(|allowed| allowed == &h) => next.run(req).await,
        _ => (
            StatusCode::BAD_REQUEST,
            Json(json!({ "error": "invalid_host" })),
        )
            .into_response(),
    }
}

/// Reject requests whose declared Content-Length exceeds the configured limit.
pub async fn declared_size_limit(
    State(settings): State<Arc<Settings>>,
    req: Request<Body>,
    next: Next,
) -> Response {
    if let Some(cl) = req.headers().get(header::CONTENT_LENGTH) {
        match cl.to_str().ok().and_then(|s| s.parse::<usize>().ok()) {
            Some(declared) if declared > settings.server.max_request_size_bytes => {
                return (
                    StatusCode::PAYLOAD_TOO_LARGE,
                    Json(json!({
                        "error": "request_entity_too_large",
                        "max_bytes": settings.server.max_request_size_bytes,
                    })),
                )
                    .into_response();
            }
            Some(_) => {}
            None => {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(json!({ "error": "invalid_content_length" })),
                )
                    .into_response();
            }
        }
    }
    next.run(req).await
}
