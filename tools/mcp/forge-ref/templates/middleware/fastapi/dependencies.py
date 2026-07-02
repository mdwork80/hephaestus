"""
Authentication dependencies.

Auth model configured for this project: **${auth_model}**

This file is a deliberate stub. A wrong authentication implementation is
worse than no authentication because it looks correct. The template does
not auto-generate a working validator because correctness requires
project-specific decisions (tenant, audience, accepted scopes, key
rotation, clock skew tolerance, cache policy) that cannot be inferred.

Before wiring any protected route, complete the implementation below, then
remove the `raise NotImplementedError`. Apply the dependency to routers via
`dependencies=[Depends(require_authenticated_user)]`.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

#IF auth_entra_id
# -----------------------------------------------------------------------------
# Microsoft Entra ID bearer token validation (stub).
#
# To implement:
#   1. pip/uv add: 'pyjwt[crypto]>=2.9' 'cryptography' 'httpx'
#   2. Fetch the tenant's JWKS from
#      https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys
#      and cache it with a sensible TTL (e.g., 24h). DO NOT fetch it on every
#      request.
#   3. Decode the bearer token using jwt.decode(...) with:
#        - algorithms=["RS256"]
#        - audience=<your app's client_id or App ID URI>
#        - issuer="https://login.microsoftonline.com/{tenant_id}/v2.0"
#        - leeway=60 for clock skew
#   4. Enforce required scopes or roles in the 'scp' or 'roles' claim.
#   5. Raise HTTPException(401) on validation failure with no detail that
#      leaks validation internals.
# -----------------------------------------------------------------------------
#ELIF auth_api_key
# -----------------------------------------------------------------------------
# API key authentication (stub).
#
# To implement:
#   1. Load the allow-list of hashed API keys from the secrets backend at
#      startup. Never load plaintext keys. Compare using hmac.compare_digest.
#   2. Accept the key via an Authorization header ("Authorization: Bearer <k>")
#      or a dedicated header like "X-API-Key". Pick one and enforce it.
#   3. Rate-limit by key at the ingress, not here. Per-key throttling in
#      app code gives false confidence and is easily bypassed.
#   4. Rotate keys via a config-driven allow-list; never hard-code.
# -----------------------------------------------------------------------------
#ELIF auth_managed_identity
# -----------------------------------------------------------------------------
# Managed identity (service-to-service, stub).
#
# Managed identity is typically for the app calling Azure services, not for
# inbound authentication. If this API is called by other Azure services, the
# caller presents an Entra ID bearer token. Use the entra_id pattern.
#
# To implement service-to-service calls OUT of this service:
#   1. Use azure.identity.DefaultAzureCredential (already wired in config).
#   2. Request a token with cred.get_token("<target-resource-scope>").
#   3. Pass the token as Authorization: Bearer <token> on outbound calls.
# -----------------------------------------------------------------------------
#ELIF auth_mutual_tls
# -----------------------------------------------------------------------------
# Mutual TLS authentication (stub).
#
# mTLS is terminated at the ingress (Azure Front Door, Container Apps
# ingress, or a sidecar). The app should validate the forwarded client cert
# claims, not perform the TLS handshake itself.
#
# To implement:
#   1. Configure the ingress to validate client certs and forward the result
#      in a signed header (e.g., X-Client-Cert-Verify, X-Client-Cert-Subject).
#   2. In this dependency, trust only signed headers from the ingress.
#      Reject requests that arrive without them (the request bypassed ingress).
#   3. Map the cert subject to an internal principal.
# -----------------------------------------------------------------------------
#ENDIF

bearer_scheme = HTTPBearer(auto_error=False)


async def require_authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """
    Validate the inbound credential and return the authenticated principal.

    RAISES
    ------
    NotImplementedError
        Always. The caller must complete the implementation before using
        this dependency on any real route.

    HTTPException
        Once implemented: 401 on missing/invalid credentials.
    """
    raise NotImplementedError(
        "Authentication is not implemented. Complete ${pkg}/dependencies.py "
        "before protecting routes with this dependency. See SECURITY.md for "
        "the decisions that must be made first."
    )
