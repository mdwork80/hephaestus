/**
 * Authentication preHandler stub.
 *
 * Auth model configured for this project: **${auth_model}**
 *
 * A wrong authentication implementation is worse than none because it looks
 * correct. This preHandler is a deliberate fail-loud stub: applied to a
 * route, it returns 501 until completed. Never returns a fake
 * "authenticated" principal. Apply via { preHandler: requireAuthenticatedUser }.
 */

import { FastifyReply, FastifyRequest } from "fastify";

#IF auth_entra_id
// To implement (Entra ID): fetch and cache the tenant JWKS
// (https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys, ~24h TTL,
// NEVER per-request); verify the bearer token with RS256, audience = your app
// id, issuer = https://login.microsoftonline.com/{tenant}/v2.0, 60s clock
// leeway; enforce required scopes/roles ('scp'/'roles' claim). 401 with no
// detail on failure.
#ELIF auth_api_key
// To implement (API key): load an allow-list of HASHED keys from the secrets
// backend at startup; compare with crypto.timingSafeEqual. Accept via
// Authorization: Bearer <k> or X-API-Key (pick ONE). Rotate via config-driven
// allow-list; rate-limit at the ingress, not here.
#ELIF auth_managed_identity
// Managed identity is normally for THIS service calling Azure, not inbound
// auth. If other Azure services call this API, they present an Entra ID
// bearer token — validate it as in the entra_id pattern.
#ELIF auth_mutual_tls
// mTLS is terminated at the ingress. Validate the FORWARDED client-cert
// claims from a signed ingress header (e.g. X-Client-Cert-Subject); reject
// requests arriving without it (they bypassed the ingress).
#ENDIF
export async function requireAuthenticatedUser(
  _req: FastifyRequest,
  reply: FastifyReply,
): Promise<void> {
  reply.code(501).send({
    error: "authentication_not_implemented",
    detail: "Complete src/auth.ts before protecting routes. See SECURITY.md.",
  });
}
