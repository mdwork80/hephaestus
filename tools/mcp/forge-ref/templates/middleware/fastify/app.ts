/**
 * Fastify app factory for ${project_name}.
 *
 * Factory pattern: tests import buildApp() directly; the entrypoint calls
 * listen(). Mirrors the FastAPI/axum scaffolds' middleware contract:
 * request-id propagation, security headers, declared-size limit, pinned
 * CORS, health/ready split, sanitized errors.
 */

import Fastify, { FastifyInstance } from "fastify";
import { randomUUID } from "node:crypto";

import { Settings } from "./config.js";
import { registerHealthRoutes } from "./routes/health.js";
import { registerErrorHandler } from "./errors.js";

const REQUEST_ID_HEADER = "x-request-id";
const REQUEST_ID_MAX_LENGTH = 128;

/** Baseline security headers. HSTS is intentionally omitted: it belongs at
 *  the TLS-terminating ingress, not in application code. */
const SECURITY_HEADERS: Record<string, string> = {
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "referrer-policy": "strict-origin-when-cross-origin",
  "permissions-policy":
    "accelerometer=(), autoplay=(), camera=(), display-capture=(), " +
    "geolocation=(), gyroscope=(), magnetometer=(), microphone=(), " +
    "midi=(), payment=(), usb=()",
#IF is_web_app
  // CSP for HTML-serving apps. Restrictive default; tighten or extend per
  // the app's real asset sources. JSON-only APIs omit this.
  "content-security-policy":
    "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
#ENDIF
};

export async function buildApp(settings: Settings): Promise<FastifyInstance> {
  const app = Fastify({
    // Declared+actual body size limit (Fastify enforces both).
    bodyLimit: settings.server.maxRequestSizeBytes,
    // Request-id: accept a short printable client value, else mint a UUID.
    genReqId: (req) => {
      const incoming = (req.headers[REQUEST_ID_HEADER] as string | undefined)?.trim() ?? "";
      const ok =
        incoming.length > 0 &&
        incoming.length <= REQUEST_ID_MAX_LENGTH &&
        /^[\x20-\x7e]+$/.test(incoming);
      return ok ? incoming : randomUUID();
    },
    logger: {
      level: settings.runtime.logLevel.toLowerCase(),
      // Structured JSON logs by default (pino); request id rides on reqId.
    },
    // Trusted-host enforcement: reject Host headers not in the allow-list.
    // ["*"] disables the check (local development only).
  });

  app.addHook("onRequest", async (req, reply) => {
    const hosts = settings.server.trustedHosts;
    if (!hosts.includes("*")) {
      const host = (req.headers.host ?? "").split(":")[0];
      if (!hosts.includes(host)) {
        reply.code(400).send({ error: "invalid_host" });
      }
    }
  });

  app.addHook("onSend", async (req, reply, payload) => {
    for (const [header, value] of Object.entries(SECURITY_HEADERS)) {
      if (!reply.hasHeader(header)) reply.header(header, value);
    }
    reply.header(REQUEST_ID_HEADER, req.id);
    return payload;
  });
#IF has_cors

  // CORS: explicit allow-list pinned from PROJECT.md cors_origins (wildcards
  // are schema-rejected upstream and cannot reach here).
  const cors = await import("@fastify/cors");
  await app.register(cors.default, {
    origin: settings.server.corsOrigins,
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE", "PATCH"],
    allowedHeaders: ["Authorization", "Content-Type", "X-Request-ID"],
    exposedHeaders: ["X-Request-ID"],
    maxAge: 600,
  });
#ENDIF

  registerErrorHandler(app);
  registerHealthRoutes(app);

  return app;
}
