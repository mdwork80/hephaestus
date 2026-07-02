// Health/readiness handlers and sanitized error surfaces.
//
// /health (liveness): 200 while the process is responsive; checks NO
// dependencies — a momentary outage must not get a healthy process restarted.
// /ready (readiness): 200 only when required dependencies are reachable; the
// load balancer routes on it.
package httpserver

import (
	"log/slog"
	"net/http"

	"github.com/go-chi/chi/v5/middleware"
)

func HealthHandler(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func ReadyHandler(w http.ResponseWriter, _ *http.Request) {
	// TODO: replace stub with real dependency probes (DB ping, vault
	// reachability, migration state). Short timeouts, one word per check.
	checks := map[string]string{"self": "ok"}
	overall := "ok"
	for _, v := range checks {
		if v != "ok" {
			overall = "degraded"
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"status": overall, "checks": checks})
}

// NotFoundHandler: structured 404 carrying the request id, never a framework
// default page.
func NotFoundHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusNotFound, map[string]any{
		"error": "http_error", "status": 404, "request_id": middleware.GetReqID(r.Context()),
	})
}

// RecoverSanitized converts panics into minimal 500s: full detail (including
// stack) to structured logs with the request id; nothing internal to the
// client.
func RecoverSanitized(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				rid := middleware.GetReqID(r.Context())
				slog.Error("unhandled_panic", "request_id", rid, "panic", rec)
				writeJSON(w, http.StatusInternalServerError,
					map[string]any{"error": "internal_server_error", "request_id": rid})
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// StructuredLogger emits one JSON log line per request with the request id.
func StructuredLogger(_ *Settings) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)
			next.ServeHTTP(ww, r)
			slog.Info("request",
				"method", r.Method, "path", r.URL.Path, "status", ww.Status(),
				"bytes", ww.BytesWritten(), "request_id", middleware.GetReqID(r.Context()))
		})
	}
}
