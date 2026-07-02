// Custom middleware: security headers, trusted-host filtering, declared-size
// limit, request-id echo, pinned CORS. HSTS is intentionally NOT set here —
// it belongs at the TLS-terminating ingress, not application code.
package httpserver

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/go-chi/chi/v5/middleware"
)

var securityHeaders = map[string]string{
	"X-Content-Type-Options": "nosniff",
	"X-Frame-Options":        "DENY",
	"Referrer-Policy":        "strict-origin-when-cross-origin",
	"Permissions-Policy": "accelerometer=(), autoplay=(), camera=(), display-capture=(), " +
		"geolocation=(), gyroscope=(), magnetometer=(), microphone=(), midi=(), payment=(), usb=()",
#IF is_web_app
	// CSP for HTML-serving apps; JSON-only APIs omit this.
	"Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
#ENDIF
}

// SecurityHeaders adds the baseline headers when not already present.
func SecurityHeaders(_ *Settings) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			for k, v := range securityHeaders {
				if w.Header().Get(k) == "" {
					w.Header().Set(k, v)
				}
			}
			next.ServeHTTP(w, r)
		})
	}
}

// EchoRequestID mirrors chi's request id onto the response header so clients
// can quote it in bug reports.
func EchoRequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if id := middleware.GetReqID(r.Context()); id != "" {
			w.Header().Set("X-Request-Id", id)
		}
		next.ServeHTTP(w, r)
	})
}

// TrustedHost rejects Host headers not in server.trusted_hosts. ["*"]
// disables the check (local development only).
func TrustedHost(settings *Settings) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			hosts := settings.Server.TrustedHosts
			for _, h := range hosts {
				if h == "*" {
					next.ServeHTTP(w, r)
					return
				}
			}
			host := strings.Split(r.Host, ":")[0]
			for _, h := range hosts {
				if h == host {
					next.ServeHTTP(w, r)
					return
				}
			}
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid_host"})
		})
	}
}

// DeclaredSizeLimit rejects oversized declared Content-Length with a clean
// JSON 413 before the body is read, and caps actual reads with
// http.MaxBytesReader for lying or chunked clients.
func DeclaredSizeLimit(settings *Settings) func(http.Handler) http.Handler {
	limit := settings.Server.MaxRequestSizeBytes
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if cl := r.Header.Get("Content-Length"); cl != "" {
				declared, err := strconv.ParseInt(cl, 10, 64)
				if err != nil {
					writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid_content_length"})
					return
				}
				if declared > limit {
					writeJSON(w, http.StatusRequestEntityTooLarge,
						map[string]any{"error": "request_entity_too_large", "max_bytes": limit})
					return
				}
			}
			r.Body = http.MaxBytesReader(w, r.Body, limit)
			next.ServeHTTP(w, r)
		})
	}
}
#IF has_cors

// PinnedCORS grants cross-origin access ONLY to the exact origins from
// PROJECT.md cors_origins (wildcards are schema-rejected upstream).
func PinnedCORS(settings *Settings) func(http.Handler) http.Handler {
	allowed := map[string]bool{}
	for _, o := range settings.Server.CorsOrigins {
		allowed[o] = true
	}
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" && allowed[origin] {
				h := w.Header()
				h.Set("Access-Control-Allow-Origin", origin)
				h.Set("Access-Control-Allow-Credentials", "true")
				h.Set("Access-Control-Expose-Headers", "X-Request-Id")
				h.Add("Vary", "Origin")
				if r.Method == http.MethodOptions {
					h.Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH")
					h.Set("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Request-Id")
					h.Set("Access-Control-Max-Age", "600")
					w.WriteHeader(http.StatusNoContent)
					return
				}
			}
			next.ServeHTTP(w, r)
		})
	}
}
#ENDIF

func writeJSON(w http.ResponseWriter, status int, body map[string]any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
