//! Application factory: builds the axum Router with the full middleware stack.
//!
//! Middleware is assembled with a `ServiceBuilder` (outermost first). The order
//! mirrors the Python scaffold's intent: catch panics outermost, assign and
//! propagate a request id (and bind it to trace spans) early so every log line
//! carries it, reject untrusted hosts and oversized requests before work,
//! apply CORS, and set security headers on the way out.
use std::any::Any;
use std::sync::Arc;

use axum::http::{header, HeaderName, HeaderValue, Method};
use axum::routing::get;
use axum::Router;
use bytes::Bytes;
use http_body_util::Full;
use tower::ServiceBuilder;
use tower_http::catch_panic::CatchPanicLayer;
use tower_http::cors::{AllowOrigin, CorsLayer};
use tower_http::limit::RequestBodyLimitLayer;
use tower_http::request_id::{MakeRequestUuid, PropagateRequestIdLayer, SetRequestIdLayer};
use tower_http::set_header::SetResponseHeaderLayer;
use tower_http::trace::TraceLayer;

use crate::config::Settings;
use crate::http::{error, middleware as mw, routes};

/// Baseline security headers. HSTS is intentionally omitted: it belongs at the
/// TLS-terminating ingress, not in application code.
fn security_header_layers() -> [SetResponseHeaderLayer<HeaderValue>; 4] {
    [
        SetResponseHeaderLayer::if_not_present(
            HeaderName::from_static("x-content-type-options"),
            HeaderValue::from_static("nosniff"),
        ),
        SetResponseHeaderLayer::if_not_present(
            HeaderName::from_static("x-frame-options"),
            HeaderValue::from_static("DENY"),
        ),
        SetResponseHeaderLayer::if_not_present(
            HeaderName::from_static("referrer-policy"),
            HeaderValue::from_static("strict-origin-when-cross-origin"),
        ),
        SetResponseHeaderLayer::if_not_present(
            HeaderName::from_static("permissions-policy"),
            HeaderValue::from_static(
                "accelerometer=(), autoplay=(), camera=(), display-capture=(), \
                 geolocation=(), gyroscope=(), magnetometer=(), microphone=(), \
                 midi=(), payment=(), usb=()",
            ),
        ),
    ]
}

#IF is_web_app
/// Content-Security-Policy for HTML-serving apps. A restrictive default that
/// blocks inline/external resources; tighten or extend per the app's real
/// asset sources. JSON-only APIs do not serve a document context and omit this.
fn csp_layer() -> SetResponseHeaderLayer<HeaderValue> {
    SetResponseHeaderLayer::if_not_present(
        HeaderName::from_static("content-security-policy"),
        HeaderValue::from_static(
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        ),
    )
}

#ENDIF
/// CORS layer pinned to an explicit allow-list. An empty list means
/// same-origin only (no cross-origin grant). Wildcards are rejected upstream
/// by the PROJECT.md schema, so they cannot reach here.
fn cors_layer(origins: &[String]) -> CorsLayer {
    let parsed: Vec<HeaderValue> = origins
        .iter()
        .filter_map(|o| o.parse::<HeaderValue>().ok())
        .collect();
    CorsLayer::new()
        .allow_origin(AllowOrigin::list(parsed))
        .allow_credentials(true)
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PUT,
            Method::DELETE,
            Method::PATCH,
        ])
        .allow_headers([
            header::AUTHORIZATION,
            header::CONTENT_TYPE,
            HeaderName::from_static("x-request-id"),
        ])
        .expose_headers([HeaderName::from_static("x-request-id")])
        .max_age(std::time::Duration::from_secs(600))
}

/// Sanitized 500 for panics: minimal body, no type/message/stack.
fn handle_panic(_err: Box<dyn Any + Send + 'static>) -> axum::http::Response<Full<Bytes>> {
    let body = serde_json::json!({ "error": "internal_server_error" }).to_string();
    axum::http::Response::builder()
        .status(500)
        .header(header::CONTENT_TYPE, "application/json")
        .body(Full::from(body))
        .expect("static panic response is valid")
}

/// Build the application router with state and middleware.
pub fn build_app(settings: Arc<Settings>) -> Router {
    let x_request_id = HeaderName::from_static("x-request-id");
    let [sec0, sec1, sec2, sec3] = security_header_layers();

    let middleware = ServiceBuilder::new()
        .layer(CatchPanicLayer::custom(handle_panic))
        .layer(SetRequestIdLayer::new(
            x_request_id.clone(),
            MakeRequestUuid,
        ))
        .layer(TraceLayer::new_for_http())
        .layer(PropagateRequestIdLayer::new(x_request_id))
        .layer(axum::middleware::from_fn_with_state(
            settings.clone(),
            mw::trusted_host,
        ))
        .layer(axum::middleware::from_fn_with_state(
            settings.clone(),
            mw::declared_size_limit,
        ))
        .layer(RequestBodyLimitLayer::new(
            settings.server.max_request_size_bytes,
        ))
        .layer(cors_layer(&settings.server.cors_origins))
        .layer(sec0)
        .layer(sec1)
        .layer(sec2)
#IF is_web_app
        .layer(sec3)
        .layer(csp_layer());
#ELSE
        .layer(sec3);
#ENDIF

    Router::new()
        .route("/health", get(routes::health))
        .route("/ready", get(routes::ready))
        .route("/api/v1/status", get(routes::status))
        .fallback(error::not_found)
        .layer(middleware)
        .with_state(settings)
}
