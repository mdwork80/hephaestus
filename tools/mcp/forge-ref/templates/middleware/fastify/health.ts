/**
 * Liveness and readiness endpoints. The two have different semantics and
 * must not be conflated:
 *
 *   GET /health  (liveness): 200 while the process is responsive. Checks NO
 *   dependencies — a momentary dependency outage must not cause the
 *   orchestrator to restart a healthy process.
 *
 *   GET /ready   (readiness): 200 only when required dependencies are
 *   reachable right now. The load balancer uses it to route traffic.
 */

import { FastifyInstance } from "fastify";

export function registerHealthRoutes(app: FastifyInstance): void {
  app.get("/health", async () => ({ status: "ok" }));

  app.get("/ready", async () => {
    // TODO: replace stub with real dependency probes (DB ping, vault
    // reachability, migration state). Short timeouts, one word per check.
    const checks: Record<string, string> = { self: "ok" };
    const overall = Object.values(checks).every((v) => v === "ok") ? "ok" : "degraded";
    return { status: overall, checks };
  });
}
