# Security & configuration invariants

What must be TRUE of each artifact, independent of language. These replace the battle-tested verbatim templates from the Copier repo — treat every bullet as a requirement. When an invariant can't be met in the chosen language/ecosystem, say so explicitly in the generated ARCHITECTURE.md instead of silently dropping it.

> **NOTE — deep-template reference points:** MCP servers will be built and added as reference points for the deep templates (Bicep infra modules, web security-middleware stacks, hardened Dockerfiles, SHA-pinned CI/CD workflows). Until they exist, this file is the authority for those artifacts; flag to the user that deep infra/middleware output is prose-generated, not template-verified. Once available, consult the MCP reference servers first and prefer their canonical output.

## Configuration discipline

- Three layers, later wins: code defaults → committed `config/default.toml` → environment variables / `.env`.
- `config/default.toml` is committed and contains NO secrets, ever.
- Env var contract: prefix `SLUG_UPPER_` (slug uppercased, hyphens→underscores), `__` delimiter for nesting (`FOO_RUNTIME__LOG_LEVEL` → `runtime.log_level`).
- No application code hard-codes URLs, ports, paths, timeouts, or credentials.
- `.env` is gitignored; `.env.example` documents every variable with placeholder values and warns: `KEY=value`, no spaces around `=`.
- If the language's config lib can't parse list-typed env vars, document that lists belong in `default.toml` (the Rust `config`-crate precedent).

## Secrets

- `secrets_backend: dotenv_local` → `.env` only, plus the schema's guardrails (local_only + public/internal — already enforced at intake).
- `key_vault` / `hybrid` → Key Vault URI via env (`FOO_KEY_VAULT__URI`), access via managed identity in Azure; `.env` fallback only in `hybrid` for local dev.
- Two secret scanners with different heuristics on purpose: gitleaks + detect-secrets (with `.secrets.baseline`).
- Key material (SSH host keys, certs) lives on disk under `secrets/` (gitignored), never in committed config.

## Pre-commit

Every project, regardless of language:

1. **First-party first:** frontmatter validator on `PROJECT.md`; logic-ref integrity check (always run). Both invoke the in-project implementations — zero dependence on this skill or on Python for non-Python projects.
2. Hygiene: trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-added-large-files (500 KB), check-merge-conflict, detect-private-key.
3. Secrets: gitleaks + detect-secrets (baseline-excluded from its own scan, lockfiles excluded).
4. Language block: formatter (check mode), linter (warnings = errors), SAST, dependency vulnerability audit, lockfile-drift check (fail when manifest changed without lockfile). See §Language mapping.
5. Pin hook `rev`s to tags; local hooks use `language: system`.

## Container (`deployment_target != local_only`)

- Multi-stage build: builder resolves deps from the lockfile (`--frozen`/`--locked` semantics — a lockfile change must be a commit, not a build side-effect); runtime stage copies only the built artifact/venv + source + config. Build tooling absent from the final image.
- Base image pinned by **SHA256 digest**, not tag; Dependabot bumps it. Instruct: obtain digest via `docker buildx imagetools inspect <image:tag>`.
- Non-root user, high UID (10001) to avoid bind-mount collisions. `USER` set before runtime instructions.
- Init process (tini or equivalent) as PID 1 so SIGTERM reaches the app.
- Strip package managers / build tools from the runtime layer (the pip/setuptools-removal precedent) — they're CVE surface with no runtime purpose.
- HEALTHCHECK with **no curl/wget dependency**: language-stdlib HTTP probe for web/api (`/health`, process-alive semantics); for non-HTTP runtimes, probe "package imports and config loads".
- Web/api in-container bind host = `0.0.0.0` (container netns is the isolation boundary); local non-container default stays `127.0.0.1`. Document BOTH and why — this is the single most-reverted line in the old template; keep its "do not change back for safety" warning.
- OS packages: install only ca-certificates + init, clean apt lists; deliberately unpinned so security patches land on rebuild (document this hadolint DL3008 exception).
- Read-only root filesystem posture at the orchestrator level (Container Apps / compose `read_only: true`) where the runtime tolerates it.

## Web service (`web_app` / `api_service`)

Framework is language-idiomatic; the middleware contract is not negotiable:

- App-factory pattern (construct app from settings; no import-time side effects).
- `/health` (process alive, NO dependency checks) vs `/ready` (dependencies OK) — keep the semantic distinction and test both.
- Request-ID middleware: per-request UUID bound into structured logs and echoed as a response header.
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`; `Content-Security-Policy` for `web_app`.
- Request-size limit middleware (default 10 MiB, configurable `server.max_request_size_bytes`).
- CORS only when `cors_origins` non-empty; pinned allow-list straight from frontmatter; wildcards impossible by schema.
- Trusted-host validation (`server.trusted_hosts`, default `["*"]` locally, tighten-for-prod comment).
- Sanitized error responses: no stack traces or internal paths to clients; full detail to structured logs.
- Auth stub per `auth_model`: raises not-implemented with model-specific implementation guidance. Never generate a placeholder that silently allows requests.
- Structured logging (JSON in production), level from config.

## CI (`.github/workflows/ci.yml`)

- All third-party actions pinned by **full commit SHA** (comment the tag); Dependabot proposes bumps.
- Jobs: lint+format check → SAST → tests (version matrix where the ecosystem supports it) → dependency audit → frontmatter validation **including `--check-cadence`** → logic-ref integrity.
- Containerized adds: hadolint, image build, Trivy image scan, CycloneDX SBOM artifact.
- Azure adds: Bicep build/what-if validation + Checkov against the compiled ARM (with the committed skip baseline).
- Egress hardening (harden-runner, audit mode) on security-sensitive jobs.
- Install with frozen/locked semantics (`uv sync --frozen`, `cargo build --locked`, `npm ci`, …) — CI must fail on lockfile drift.

## CD (`deploy.yml`, Azure targets)

- Federated identity (OIDC) only — **no long-lived cloud secrets in GitHub**.
- When `image_signing: cosign_keyless`: `cosign verify` gate before deploy (Sigstore keyless, GHCR), SBOM + SLSA provenance attestations produced at release.
- Resource-group-scoped deployment (least-privilege deployer identity).

## Azure infra (Bicep)

- Resource-group scope; user-assigned managed identity; least-privilege RBAC role assignments (no Owner/Contributor sprawl).
- Baseline modules: naming, monitoring (Log Analytics + App Insights), storage, keyVault, identity, containerAppsEnv, containerApp.
- `network_isolation: private`: VNet-integrated internal Container Apps env; private endpoints for Key Vault + Storage with public network access disabled; plus one edge module per `network_exposure` — `front_door` (Front Door Premium + WAF, Private Link origin), `app_gateway` (WAF_v2 in VNet), or `internal` (no public ingress).
- Key Vault + Storage: optional IP allow-listing when public.
- Emit ONLY services the answers require; schema-accepted-but-unscaffolded services (cosmos_db, sql, service_bus, openai, ai_search) get a TODO note, not half-generated modules.

## SSH scaffold (`ssh_scaffold != none`)

- ed25519 keys only; key-based auth only — no password auth, ever.
- Server mode: `authorized_keys` file in `config/`, host key under `secrets/` (gitignored). Generated SECURITY.md notes server mode warrants `threat_model_required: true` and a real `auth_model`.

## Documentation protocol (all projects)

Generated PROJECT.md carries the three-layer Code Documentation Protocol verbatim in spirit:

- **Layer 1:** rationale in docstrings/header blocks with stable `@logic-ref` IDs (lowercase alphanumeric, ≥1 hyphen; never renamed; move with the code).
- **Layer 2:** `docs/ARCHITECTURE.md` for cross-cutting decisions only, keyed by `[decision-id]`, listing affected `@logic-ref`s, status ACTIVE/SUPERSEDED-BY/DEPRECATED.
- **Layer 3:** in-project `logic_ref_check` (deterministic, offline, LLM-free): unique IDs; ACTIVE entries reference existing IDs; ungoverned IDs = advisory; `--index` derives the ID index from source on demand. Wired into pre-commit + CI.

## Language mapping (illustrative, not exhaustive)

Pick the ecosystem-standard tool per role; if a role has no ecosystem tool, note the gap in ARCHITECTURE.md.

| Role | python | rust | typescript/node | go | dotnet | powershell / bash |
|---|---|---|---|---|---|---|
| Manifest + lock | pyproject.toml + uv.lock | Cargo.toml + Cargo.lock | package.json + package-lock.json | go.mod + go.sum | csproj + packages.lock.json | none (note it) |
| Format/lint | ruff (lint+format) | cargo fmt + clippy `-D warnings` | biome or eslint+prettier | gofmt + golangci-lint | dotnet format + analyzers | PSScriptAnalyzer / shellcheck+shfmt |
| SAST | bandit | clippy + cargo-deny | eslint security plugins / semgrep | gosec | Roslyn security analyzers | PSScriptAnalyzer rules |
| Dep audit | pip-audit | cargo-deny (advisories/licenses/sources) | npm audit / osv-scanner | govulncheck | dotnet list package --vulnerable | n/a |
| Types | mypy | rustc | tsc --strict | rustc-equiv builtin | builtin | n/a |
| Config stack | pydantic-settings | config crate + serde | zod + dotenv-style loader | viper or koanf | Microsoft.Extensions.Configuration | env + parsing functions |
| Web framework | FastAPI | axum + tower-http | Fastify | net/http + chi, or Gin/Echo | ASP.NET minimal APIs | n/a — re-ask runtime_pattern |
| Structured logging | stdlib logging/structlog JSON | tracing + tracing-subscriber | pino | slog | Microsoft.Extensions.Logging JSON | Write-Information + transcript |
| Test | pytest | cargo test | vitest/node:test | go test | xUnit | Pester / bats |
| Validator + logic-ref checker language | python | rust (src/bin/) | typescript | go | C# | powershell; bash projects may use any available scripting runtime — ask |

Toolchain pin markers: `.python-version`, `rust-toolchain.toml`, `.nvmrc`/`engines`, `go.mod` go-directive, `global.json`, `#Requires -Version`.
