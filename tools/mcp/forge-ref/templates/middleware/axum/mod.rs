//! HTTP layer: routes, middleware, sanitized errors, and the auth stub.
#IF has_auth
pub mod auth;
#ENDIF
pub mod error;
pub mod middleware;
pub mod routes;

/// Header used to carry the per-request correlation id.
pub const REQUEST_ID_HEADER: &str = "x-request-id";
