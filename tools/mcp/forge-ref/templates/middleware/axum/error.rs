//! Sanitized error responses. No handler ever leaks an exception type, message,
//! or stack trace to the client; responses carry a generic code and the
//! request id so operators can correlate to logs.
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::json;

use super::REQUEST_ID_HEADER;

/// Read the request id assigned by the request-id middleware, defaulting to "-".
pub fn request_id(headers: &HeaderMap) -> String {
    headers
        .get(REQUEST_ID_HEADER)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("-")
        .to_string()
}

/// Fallback for unmatched routes: a structured 404, never a framework default.
pub async fn not_found(headers: HeaderMap) -> Response {
    let rid = request_id(&headers);
    (
        StatusCode::NOT_FOUND,
        Json(json!({ "error": "http_error", "status": 404, "request_id": rid })),
    )
        .into_response()
}
