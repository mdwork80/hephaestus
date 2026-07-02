/**
 * Sanitized error responses. Never leak exception types, messages, or stack
 * traces to clients; full detail goes to structured logs with the request id
 * so operators can correlate client reports to server logs.
 */

import { FastifyInstance } from "fastify";

export function registerErrorHandler(app: FastifyInstance): void {
  app.setErrorHandler((err, req, reply) => {
    const status = err.statusCode ?? 500;
    if (status >= 500) {
      req.log.error({ err, requestId: req.id }, "server_error");
      // Intentionally minimal body: no type, no message, no stack.
      reply.code(status).send({ error: "internal_server_error", request_id: req.id });
    } else {
      req.log.info({ status, requestId: req.id, msg: err.message }, "client_error");
      reply.code(status).send({
        error: "http_error",
        status,
        detail: err.message,
        request_id: req.id,
      });
    }
  });

  app.setNotFoundHandler((req, reply) => {
    reply.code(404).send({ error: "http_error", status: 404, request_id: req.id });
  });
}
