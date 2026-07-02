# Adopt mode — ingesting an existing, ungoverned project

Third mode alongside bootstrap (empty clone) and augment (declared project grows). Adopt takes a real codebase with no scaffolding or security posture and brings it under hephaestus governance without breaking it. Zero questions, same as everywhere: infer from evidence, act where safe, propose where not, report everything.

Non-negotiable rails, before any phase:

- Work on a dedicated branch: `hephaestus/adopt`. One commit checkpoint per phase, so any phase can be reverted alone.
- Never delete or rewrite user source logic. Adopt adds, moves, and configures; it does not refactor business code.
- Every phase is idempotent — re-running adopt on a half-adopted repo detects what's done and continues.
- Existing user code is respected as the source of truth about what the project IS; hephaestus artifacts adapt to it, not vice versa.

## Phase 0 — Kit transplant

External projects have none of the hephaestus machinery. Copy from the base template into the target repo root:

- `.claude/` (skills, hooks, settings.json — NOT settings.local.json)
- `.mcp.json`
- `tools/mcp/forge-ref/` (server + templates + fixtures)
- `CLAUDE.md` (then adapt: layout section reflects the adopted repo, not the template)

Do NOT copy: `tools/project-forge/`, `README.md`, `docs/ARCHITECTURE.md` (Phase 6 writes the adopted repo's own), any git history. Verify `python3 tools/mcp/forge-ref/server.py --selftest` passes in the target before continuing.

## Phase 1 — Survey (evidence → frontmatter)

Infer every schema.md field from the repo itself. Evidence map:

| Field | Evidence |
|---|---|
| `project_name` / `description` | README, manifest metadata, repo/dir name |
| `languages` | manifests (pyproject/setup.py/requirements.txt, Cargo.toml, package.json, go.mod, *.csproj, *.psd1), source-file census; order by volume — dominant language first |
| `runtime_patterns` | entrypoints + frameworks: FastAPI/Flask/axum/express → web_app or api_service (HTML templates → web_app, JSON-only → api_service); argparse/clap/cobra → cli; queue consumers → background_worker; cron/scheduled triggers → scheduled_job; no entrypoint + exported API → library |
| `deployment_target` | Dockerfile/compose → containerized; Azure SDKs/Bicep/azure-pipelines → azure; AWS SDKs/CDK/terraform-aws → note (schema is azure-centric; use multi_cloud) ; none → local_only |
| `lifecycle_stage` | git history: active multi-year repo with releases → production or maintenance (recent feature velocity decides); young/sparse → prototype. NEVER default a mature repo to prototype — it weakens governance |
| `auth_model` | existing auth middleware/decorators/API-key checks; none on a networked pattern → `none` now, but Rule 8 will force a decision — record as auto-resolution |
| `data_classification` / `data_types` | schema fields, PII-shaped models (names, emails, SSNs), payment/health vocabulary in code; when evidence is thin default `internal` + `[none]` and say so |
| `secrets_backend` | .env usage → dotenv_local (Rule 3 may force upgrade); vault/Key Vault SDKs → key_vault |
| `cors_origins` | existing CORS config — wildcards found here are a Phase 2 finding, not a frontmatter value (schema rejects them) |
| `last_reviewed` | today; `review_cadence_days` default 180 |

Validate the assembled frontmatter with forge-ref `validate_frontmatter`; auto-resolve conflicts per schema.md §Resolution policy and record each one.

## Phase 2 — Security triage (before anything moves)

Order matters: find the fires before rearranging the furniture.

1. **Full-history secrets scan**: gitleaks across all commits + detect-secrets on the working tree (via `uv run --with`/`pipx run` when not installed; if neither runs, grep-based best effort and say so). Findings: report file+commit, add **rotation guidance** (a secret that ever touched git is burned — rotate it; history purge via `git filter-repo` is optional cleanup, rotation is not), then seed `.secrets.baseline`.
2. **Hardcoded config inventory**: URLs, ports, timeouts, paths, credentials in source → migration list for the three-layer config stack. Migrate mechanically only where references are unambiguous; the rest goes in the suggestions list.
3. **Posture flags**: wildcard CORS, missing auth on networked routes, disabled TLS verification, debug modes, committed `.env`. Each becomes a report finding with the invariant it violates.

## Phase 3 — Gap analysis (found state vs file-matrix)

Resolve the file-matrix for the inferred frontmatter, then bucket every required artifact:

- **Missing** → generate (PROJECT.md, SECURITY.md, CODEOWNERS, .pre-commit-config.yaml, validator + logic-ref checker, .env.example, config/default.toml…). Deep artifacts through forge-ref/IaC MCP servers as usual.
- **Present but noncompliant** → produce a diff against the canonical version (existing Dockerfile vs forge-ref's hardened one, unpinned CI vs SHA-pinned). Apply when the change is safe-additive (adding a pre-commit hook); leave as a suggestion when it alters runtime behavior (swapping base images, changing users).
- **Present and adequate** → keep, untouched. Existing lint/test configs that meet the invariant stand even when they differ from the language-mapping default — respect incumbent tooling.

Dependency hygiene here too: generate the lockfile for what exists, run the language's vulnerability audit, report criticals.

## Phase 4 — Restructure (only when an invariant demands it)

Cosmetic moves are forbidden: a consistent existing layout that doesn't block any invariant stays. Restructure only for real blockers (tests interleaved with source breaking packaging, config unlocatable by the config stack, secrets dir inside static assets).

For each justified move batch:

1. Establish the verification net: existing tests must pass BEFORE the move. No tests → write smoke tests first (import/build + entrypoint) or demote the move to the suggestions list. Never move blind.
2. `git mv` (history-preserving).
3. Rewrite every reference: imports/module paths, manifest entries (packages, package-dir, workspace members), CI workflow paths, Dockerfile COPY/CMD, compose volumes, doc links, tool configs (pytest/ruff/tsconfig paths).
4. Re-run tests + build. Green → checkpoint commit; red → revert the batch and demote to suggestion with the failure attached.

## Phase 5 — Middleware suggestions (suggest, never rewrite silently)

For web_app/api_service code, diff the live app against invariants §Web service: request-ID propagation, security headers, request-size limit, health vs ready split, sanitized error responses, pinned CORS, auth posture, structured logging. For each gap emit a ready-to-apply diff (framework-idiomatic, modeled on the forge-ref fastapi/axum stacks) into the report — applied only if the user says so. Exception: fixes that are pure hardening with zero behavior change for legitimate clients (adding security headers) may be applied directly and noted.

## Phase 6 — ARCHITECTURE.md reconstruction

Write `docs/ARCHITECTURE.md` (layer-2) for the adopted repo:

- Reverse-engineer the cross-cutting decisions the code already embodies — framework choice, storage layer, auth approach, queue/data flow, deployment shape — one ACTIVE `[decision-id]` entry each, rationale phrased as "observed + why it appears deliberate"; mark genuinely unclear rationale as such rather than inventing it.
- Add an `[adopted-into-hephaestus]` entry: date, frontmatter decided, what adopt changed, what it deferred.
- Seed the protocol forward-only: new/touched code gets `@logic-ref` docstrings; do NOT retro-tag the whole codebase.
- Wire the generated logic-ref checker into pre-commit + CI like any scaffold.

## Phase 7 — Report

Single message, in order: security findings (rotation actions first), frontmatter decisions table (field → value → evidence), artifacts generated / upgraded / kept, moves applied vs demoted (with reasons), middleware suggestion diffs, ARCHITECTURE.md entries written, manual follow-ups (tools not installed, rotations pending, history purge decision). End with the branch name and the per-phase checkpoint commits so partial rollback is one revert away.
