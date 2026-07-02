// Authentication middleware stub.
//
// Auth model configured for this project: **${auth_model}**
//
// A wrong authentication implementation is worse than none because it looks
// correct. This middleware is a deliberate fail-loud stub: applied to a
// route group, it returns 501 until completed. Never passes through a fake
// "authenticated" principal.
package httpserver

import "net/http"

#IF auth_entra_id
// To implement (Entra ID): fetch and cache the tenant JWKS
// (https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys, ~24h TTL,
// NEVER per-request); verify the bearer token (RS256, audience = app id,
// issuer = https://login.microsoftonline.com/{tenant}/v2.0, 60s leeway);
// enforce required scopes/roles ('scp'/'roles' claim). 401, no detail, on
// failure.
#ELIF auth_api_key
// To implement (API key): load an allow-list of HASHED keys from the secrets
// backend at startup; compare with subtle.ConstantTimeCompare. Accept via
// Authorization: Bearer <k> or X-API-Key (pick ONE). Rotate via a
// config-driven allow-list; rate-limit at the ingress, not here.
#ELIF auth_managed_identity
// Managed identity is normally for THIS service calling Azure, not inbound
// auth. If other Azure services call this API, they present an Entra ID
// bearer token — validate it as in the entra_id pattern.
#ELIF auth_mutual_tls
// mTLS is terminated at the ingress. Validate the FORWARDED client-cert
// claims from a signed ingress header (e.g. X-Client-Cert-Subject); reject
// requests arriving without it (they bypassed the ingress).
#ENDIF
func RequireAuthenticatedUser(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusNotImplemented, map[string]any{
			"error":  "authentication_not_implemented",
			"detail": "Complete auth.go before protecting routes. See SECURITY.md.",
		})
	})
}
