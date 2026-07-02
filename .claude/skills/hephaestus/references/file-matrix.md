# File matrix — what to emit under which answers

Replaces the Copier template's Jinja-conditional filenames. Resolve top-to-bottom against the validated answers; the union of matched rows is the file plan. `<pkg>` = slug with underscores, adjusted per language convention. Language-specific artifact names come from `invariants.md` §Language mapping (e.g. "manifest" = `pyproject.toml` / `Cargo.toml` / `package.json` / `go.mod` / `*.csproj` / `*.psd1`). "Language scaffold" and language-gated rows apply once PER entry in `languages`; runtime-pattern rows apply once per entry in `runtime_patterns`, emitted in the language that implements that pattern.

## Always (every project, every language)

| File | Content requirements |
|---|---|
| `PROJECT.md` | Frontmatter per schema.md layout + Charter / Scope / Key decisions (ADRs under `docs/adr/`) / Code Documentation Protocol section / Status. Protocol section text: invariants.md §Documentation protocol |
| `README.md` | What it is, config resolution order, how to run, how to develop (hooks install, test, lint) |
| `SECURITY.md` | Content varies by `data_classification` + `compliance_scope`: reporting contact, secrets handling rules, hardening posture; regulated/confidential adds data-handling and access sections |
| `LICENSE` | Canonical SPDX text when a known identifier; short proprietary notice when `Proprietary` |
| `CODEOWNERS` | Owner on `*`; extra protection on security-sensitive paths (`SECURITY.md`, validator, CI workflows, `PROJECT.md`, infra/) |
| `.gitignore` | Language-idiomatic + always: `.env`, `secrets/`, venv/build dirs, editor cruft |
| `.env.example` | Env contract: `SLUG_UPPER_` prefix, `__` nesting delimiter, one commented entry per configurable setting, no real values. Header warns: copy to `.env`, never commit, `KEY=value` no spaces |
| `config/default.toml` | Committed defaults, NO secrets. `[runtime]` (environment, log_level) always; `[server]` when web/api; `[ai]` when ai_tooling ∈ (runtime_inference, agentic); `[ssh]` when ssh_scaffold ≠ none |
| `.pre-commit-config.yaml` | Per invariants.md §Pre-commit |
| `docs/ARCHITECTURE.md` | Layer-2 decision log seeded with the `[decision-id]` entry template |
| `.github/workflows/ci.yml` | Per invariants.md §CI |
| `.github/dependabot.yml` | Ecosystems: github-actions + language package ecosystem + docker when containerized |
| `.github/CODEOWNERS` | May be the same file as root CODEOWNERS — pick one location, not both |
| `_schema/schema.json` | Output of forge-ref `get_schema`, copied verbatim. The machine-readable contract the in-project validator interprets; sync mode refreshes it |
| frontmatter validator | In-project, project's language (or natural companion). A thin INTERPRETER of `_schema/schema.json` (field bounds, enums, the 11 rules as data) + `--check-cadence` — do NOT hardcode rules in validator logic. Path per language convention (`scripts/`, `src/bin/`, `tools/`) |
| logic-ref checker | In-project, same language as validator. Rules: unique `@logic-ref` IDs in source; every ID referenced by an ACTIVE ARCHITECTURE.md entry exists; ungoverned source IDs = advisory warning; deprecated entries may reference removed IDs. `--index` mode lists all IDs |

## Language scaffold (every language)

| File | Condition |
|---|---|
| Manifest + pinned-toolchain marker (`.python-version`, `rust-toolchain.toml`, `.nvmrc`, `go.mod` version, …) | always |
| `src/<pkg>/` (or language-idiomatic layout) with entrypoint, config loader, error handling | always; entrypoint omitted when the language only serves `library` |
| Config loader module | always — implements the three-layer resolution (defaults → default.toml → env with `SLUG_UPPER_`/`__`) |
| Test suite: config-loading test + smoke test | always |
| Lint/format/SAST config (in manifest or dotfiles) | always, per invariants.md §Language mapping |

## Runtime pattern: `web_app` / `api_service`

| File | Content |
|---|---|
| App-factory module + HTTP middleware stack | Per invariants.md §Web service. Framework: language-idiomatic (FastAPI, axum, Fastify, Gin/Echo, ASP.NET minimal…) |
| Health/readiness endpoints + tests | `/health` = process alive (no dependency checks); `/ready` = dependencies OK |
| Auth stub | Raises not-implemented with guidance specific to the chosen `auth_model`; never a fake pass-through |

## Runtime pattern: others

- `background_worker` / `scheduled_job` / `agent_pipeline` / `cli`: entrypoint skeleton wired to config + logging. Deep worker/job scaffolds (retries, dead-letter, overlap locks) are roadmap — note as TODO in the generated ARCHITECTURE.md rather than half-generating.
- `library`: no entrypoint, no Dockerfile even if deployment ≠ local_only unless user insists; public-API module + doc stub.

## Containerized: `deployment_target != local_only`

| File | Content |
|---|---|
| `Dockerfile` | Per invariants.md §Container |
| `compose.yaml` | Local dev parity: builds the Dockerfile, maps port when web/api, loads `.env` |
| `.dockerignore` | Excludes VCS, tests, docs, `.env`, secrets, caches |
| `.trivyignore` | Empty with header comment explaining baseline usage |
| `.github/workflows/release.yml` | Only when `image_signing: cosign_keyless`: GHCR publish + cosign keyless + SBOM + SLSA provenance |

## Azure: `deployment_target in (azure, hybrid)`

| File | Content |
|---|---|
| `infra/main.bicep` + `infra/modules/*` + `infra/main.parameters.json` + `infra/README.md` | Per invariants.md §Azure infra. Modules: naming, monitoring, storage, keyVault, identity, containerAppsEnv, containerApp; `network_isolation: private` adds vnet + privateEndpoints + one edge module per `network_exposure` |
| `infra/scripts/register-providers.{sh,ps1}` | Provider registration for the emitted services |
| `DEPLOYMENT.md` | Federated-identity (OIDC) setup steps; no long-lived secrets anywhere |
| `.github/workflows/deploy.yml` | Per invariants.md §CI/CD |
| `.checkov.yaml` | Documented skip baseline for the emitted Bicep |

## Conditional extras

| File | Condition |
|---|---|
| `THREAT_MODEL.md` | `threat_model_required: true`. STRIDE-lite template: assets, trust boundaries, threats, mitigations, residual risk — pre-seeded from the answers (data types, auth model, exposure) |
| `docs/AGENT_SAFETY.md` | `ai_tooling: agentic`. Tool allow-listing, prompt-injection posture, output validation, sandboxing expectations |
| SSH modules (`src/.../ssh/`) + `config/authorized_keys` (server) + `[ssh]` config/env sections | `ssh_scaffold != none`. ed25519 only, key-based auth only, host key path on disk never committed |

## Post-generation artifacts (created by tasks, not written by hand)

- Lockfile (`uv.lock`, `Cargo.lock`, `package-lock.json`, `go.sum`, …) — one per language that has one
- `.secrets.baseline` (detect-secrets)

## Augment deltas (existing project gains a language or runtime pattern)

Emit ONLY what the delta requires; update shared files in place, never regenerate them.

**New language added to `languages`:**

| Artifact | Action |
|---|---|
| Manifest + toolchain pin marker + `src/` layout + config loader + tests | create (Language scaffold rows for the new language) |
| `.pre-commit-config.yaml` | append the new language's lint/format/SAST/audit/lockfile-drift block |
| `.github/workflows/ci.yml` | add the new language's jobs (lint, SAST, test matrix, dep audit, locked install) |
| `.github/dependabot.yml` | add the new package ecosystem |
| `.gitignore` | append language-idiomatic entries |
| `Dockerfile`/`compose.yaml` (if containerized) | new build stage or sidecar service — decide by whether the new language is part of the same deployable or a separate one; record in ARCHITECTURE.md |
| In-project validator + logic-ref checker | extend accepted `languages` list; scanner covers the new source extensions |
| `PROJECT.md` | add to `languages`; do NOT touch `last_reviewed` |

**New runtime pattern added to `runtime_patterns`:**

| Artifact | Action |
|---|---|
| Pattern artifacts (middleware stack, health/ready, auth stub for web/api; entrypoint skeleton for worker/job) | create in the implementing language |
| `config/default.toml` + `.env.example` | append the pattern's sections (`[server]`, …) |
| Re-run cross-field rules on merged answers | Rule 8 (auth none × networked pattern) and Rule 10 are the usual casualties — auto-resolve safer, report |
| `PROJECT.md` | add to `runtime_patterns` |

**Deployment change (`local_only` → azure/hybrid):** emit the Containerized + Azure sections wholesale; re-check Rules 1, 3, 8, 11; `secrets_backend: dotenv_local` becomes invalid (Rule 3) — upgrade to `key_vault`/`hybrid` and report.
