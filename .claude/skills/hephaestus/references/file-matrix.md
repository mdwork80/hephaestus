# File matrix — what to emit under which answers

Replaces the Copier template's Jinja-conditional filenames. Resolve top-to-bottom against the validated answers; the union of matched rows is the file plan shown to the user before writing. `<pkg>` = slug with underscores. Language-specific artifact names come from `invariants.md` §Language mapping (e.g. "manifest" = `pyproject.toml` / `Cargo.toml` / `package.json` / `go.mod` / `*.csproj` / `*.psd1`).

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
| frontmatter validator | In-project, project's language (or natural companion). All schema.md bounds + 11 rules + `--check-cadence`. Path per language convention (`scripts/`, `src/bin/`, `tools/`) |
| logic-ref checker | In-project, same language as validator. Rules: unique `@logic-ref` IDs in source; every ID referenced by an ACTIVE ARCHITECTURE.md entry exists; ungoverned source IDs = advisory warning; deprecated entries may reference removed IDs. `--index` mode lists all IDs |

## Language scaffold (every language)

| File | Condition |
|---|---|
| Manifest + pinned-toolchain marker (`.python-version`, `rust-toolchain.toml`, `.nvmrc`, `go.mod` version, …) | always |
| `src/<pkg>/` (or language-idiomatic layout) with entrypoint, config loader, error handling | always; entrypoint omitted when `runtime_pattern: library` |
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

- Lockfile (`uv.lock`, `Cargo.lock`, `package-lock.json`, `go.sum`, …)
- `.secrets.baseline` (detect-secrets)
