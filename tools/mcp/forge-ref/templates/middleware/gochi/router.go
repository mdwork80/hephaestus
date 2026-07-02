// Package httpserver builds the chi router with the full middleware stack for
// ${project_name}. Mirrors the FastAPI/axum scaffolds' contract: request-id
// propagation, security headers, declared+actual size limits, pinned CORS,
// trusted-host check, health/ready split, sanitized errors.
package httpserver

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// BuildRouter constructs the router from settings. Tests call this directly;
// main() wraps it in http.Server with sensible timeouts.
func BuildRouter(settings *Settings) http.Handler {
	r := chi.NewRouter()

	// Recoverer outermost: panics become sanitized 500s (see errors.go),
	// never stack traces to the client.
	r.Use(RecoverSanitized)
	// Request ID: chi's middleware honors an inbound X-Request-Id and mints
	// one otherwise; RequestIDHeader echoes it on the response.
	r.Use(middleware.RequestID)
	r.Use(EchoRequestID)
	r.Use(middleware.RealIP)
	r.Use(StructuredLogger(settings))
	r.Use(TrustedHost(settings))
	r.Use(DeclaredSizeLimit(settings))
	r.Use(SecurityHeaders(settings))
#IF has_cors
	r.Use(PinnedCORS(settings)) // allow-list from PROJECT.md; wildcards schema-rejected
#ENDIF

	r.Get("/health", HealthHandler)
	r.Get("/ready", ReadyHandler)
	r.NotFound(NotFoundHandler)

	return r
}
