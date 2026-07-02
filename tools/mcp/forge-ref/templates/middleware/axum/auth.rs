//! Authentication stub.
//!
//! Auth model configured for this project: **${auth_model}**
//!
//! A wrong authentication implementation is worse than none because it looks
//! correct. This extractor is a deliberate fail-loud stub: applied to a route,
//! it returns 501 until completed. Correctness requires project-specific
//! decisions (tenant, audience, accepted scopes, key rotation, clock skew)
//! that cannot be inferred. Apply via a route extractor argument once done.
use axum::extract::FromRequestParts;
use axum::http::request::Parts;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::json;

/// Extractor that gates a route on authentication. Returns 501 until the
/// validation below is implemented; never returns a fake "authenticated"
/// principal.
pub struct RequireAuthenticatedUser;

impl<S> FromRequestParts<S> for RequireAuthenticatedUser
where
    S: Send + Sync,
{
    type Rejection = Response;

    async fn from_request_parts(_parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
#IF auth_entra_id
        // To implement (Entra ID): fetch and cache the tenant JWKS, decode the
        // bearer token with algorithms=["RS256"], audience=<app id>,
        // issuer=https://login.microsoftonline.com/{tenant}/v2.0, leeway=60s;
        // enforce required scopes/roles ('scp'/'roles' claim); return the
        // principal. Reject with 401 (no detail) on failure.
#ELIF auth_api_key
        // To implement (API key): load an allow-list of HASHED keys from the
        // secrets backend at startup; compare with a constant-time check.
        // Accept via Authorization: Bearer <k> or X-API-Key (pick one). Rotate
        // via a config-driven allow-list; rate-limit at the ingress, not here.
#ELIF auth_managed_identity
        // Managed identity is normally for THIS service calling Azure, not for
        // inbound auth. If other Azure services call this API, they present an
        // Entra ID bearer token -- validate it as in the entra_id pattern.
#ELIF auth_mutual_tls
        // mTLS is terminated at the ingress. Validate the FORWARDED client-cert
        // claims from a signed ingress header (e.g. X-Client-Cert-Subject);
        // reject requests arriving without it (they bypassed the ingress).
#ENDIF
        Err((
            StatusCode::NOT_IMPLEMENTED,
            Json(json!({
                "error": "authentication_not_implemented",
                "detail": "Complete src/http/auth.rs before protecting routes. See SECURITY.md.",
            })),
        )
            .into_response())
    }
}
