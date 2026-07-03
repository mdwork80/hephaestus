# Adopt mode — ingesting an existing, ungoverned project

Third mode alongside bootstrap (empty clone) and augment (declared project grows). Adopt takes a real codebase with no scaffolding or security posture and brings it under hephaestus governance without breaking it. Zero questions, same as everywhere: infer from evidence, act where safe, propose where not, report everything.

Direction of ingestion: the external project is copied INTO a fresh hephaestus clone. The original folder is never touched — the user's rollback is "delete the clone, original intact." This also keeps the flow AI-agnostic: whoever runs the adoption starts inside the clone (which carries every instruction file) and points outward at a plain folder path; no assistant ever needs to locate hephaestus.

Non-negotiable rails, before any phase:

- The external project folder is READ-ONLY throughout. All work happens in the clone.
- After ingestion, adoption work runs on a `hephaestus/adopt` branch of the copied history, one checkpoint commit per phase that changes files, so any phase can be reverted alone. Phases with nothing to change (e.g. no web code → Phase 5 no-op) skip the commit but MUST still appear in the Phase 7 report with their outcome: done / no-op / deferred — silent phase skips are indistinguishable from forgotten ones.
- Never delete or rewrite user source logic. Adopt adds, moves, and configures; it does not refactor business code.
- Every phase is idempotent — re-running adopt on a half-adopted repo detects what's done and continues.
- Existing user code is respected as the source of truth about what the project IS; hephaestus artifacts adapt to it, not vice versa.

## Phase 0 — Ingest by copy

Run from a fresh hephaestus clone (project-named directory). The user supplies the external project path ("adopt /path/to/project").

**Which repo a git command targets matters at every step.** Before the swap in step 2, the clone's `.git` holds hephaestus TEMPLATE history — useless as project evidence. The external folder is only ever a copy SOURCE. After the swap, the clone's `.git` IS the external project's history, and everything from Phase 1 on runs against it. Never run survey/triage git commands before the swap.

1. **Pre-flight (clone's own .git — the ONLY step that reads it).** Capture, before they're destroyed: `git remote get-url origin` → becomes frontmatter `hephaestus_base`; `tools/mcp/forge-ref/VERSION` → becomes `hephaestus_version` (file missing = stale clone predating kit versioning — tell the user to re-pull the base and stop); `git status --porcelain` — dirty kit files get noted in the report. Template git history is NOT evidence for anything; do not read it further.
2. **Snapshot the kit.** Stash the clone's kit files aside (in-memory or temp): `.claude/`, `.mcp.json`, `tools/mcp/forge-ref/`, `CLAUDE.md`, `docs/ARCHITECTURE.md` template knowledge.
3. **Replace history.** Delete the clone's template `.git` — template history is noise in a child project. Copy the ENTIRE external project contents into the clone, **including its `.git`**: the full-history secrets scan (Phase 2) and `git mv` reference preservation (Phase 4) depend on real history. External project has no `.git` → copy the tree, `git init -b main`, commit a `pre-adoption snapshot` so there is a clean revert point.
4. **Re-layer the kit** on top per the collision policy below, as the first checkpoint commit on a new `hephaestus/adopt` branch.
5. **Swap-verification gate (mandatory before Phase 1).** In the clone: `git log --oneline -5` must show the EXTERNAL project's commits, and `git remote get-url origin` must NOT be the hephaestus base anymore. Any hephaestus template commit subject in the log, or the base URL still on origin, means the swap failed — STOP, report, do not run any survey/triage phase against template history.
6. **Verify kit**: `python3 tools/mcp/forge-ref/server.py --selftest` passes in the clone.

Collision policy (external file exists where hephaestus has one):

| Path | Winner |
|---|---|
| `.claude/`, `.mcp.json`, `tools/mcp/` | hephaestus (kit) |
| Source code, project docs, `README.md` | external — the template README dies |
| `.gitignore` | union merge (external entries + kit entries, deduped) |
| `docs/ARCHITECTURE.md` | external kept if present; Phase 6 appends, never replaces |
| Instruction files — see below | external wins, AFTER the merge below |

**Instruction-file merge.** If the external project carries its own AI instruction file(s) — `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/*.mdc` — do NOT overwrite them. Instead, copy the **Standing rules** and **Layout** sections from the hephaestus `CLAUDE.md` into each external instruction file (append as clearly-headed sections, paths adapted to the adopted repo), and then the external file wins — the merged external file IS the instruction file going forward. Only when the external project has no instruction file at all does the hephaestus `CLAUDE.md` stand as-is (adapted: layout section describes the adopted repo, not the template).

Two facts to carry into the Phase 7 report:

- **Remote:** the copied `.git` still points `origin` at the external project's remote. Adopt never pushes; the report must remind the user that pushing from the adopted repo goes to the ORIGINAL project's remote unless re-pointed.
- **Uncommitted state:** dirty working-tree changes in the original are copied as-is and noted — adopt does not refuse, but the user should know the snapshot includes uncommitted work.

## Phase 1 — Survey (evidence → frontmatter)

Runs ONLY after the Phase 0 swap-verification gate: every git command here reads the external project's history now living in the clone. Infer every schema.md field from the repo itself. Evidence map:

| Field | Evidence |
|---|---|
| `project_name` / `description` | README, manifest metadata, repo/dir name |
| `languages` | manifests (pyproject/setup.py/requirements.txt, Cargo.toml, package.json, go.mod, *.csproj, *.psd1), source-file census; order by volume — dominant language first |
| `runtime_patterns` | entrypoints + frameworks: FastAPI/Flask/axum/express → web_app or api_service (HTML templates → web_app, JSON-only → api_service); argparse/clap/cobra → cli; queue consumers → background_worker; cron/scheduled triggers → scheduled_job; no entrypoint + exported API → library |
| `deployment_target` | Dockerfile/compose → containerized; Azure SDKs/Bicep/azure-pipelines → azure; AWS SDKs/CDK/terraform-aws → note (schema is azure-centric; use multi_cloud); none → local_only |
| `lifecycle_stage` | git history: active multi-year repo with releases → production or maintenance (recent feature velocity decides); young/sparse → prototype. NEVER default a mature repo to prototype — it weakens governance |
| `auth_model` | existing auth middleware/decorators/API-key checks; none on a networked pattern → `none` now, but Rule 8 will force a decision — record as auto-resolution |
| `data_classification` / `data_types` | schema fields, PII-shaped models (names, emails, SSNs), payment/health vocabulary in code; when evidence is thin default `internal` + `[none]` and say so |
| `secrets_backend` | .env usage → dotenv_local (Rule 3 may force upgrade); vault/Key Vault SDKs → key_vault |
| `cors_origins` | existing CORS config — wildcards found here are a Phase 2 finding, not a frontmatter value (schema rejects them) |
| `last_reviewed` | today; `review_cadence_days` default 180 |

Validate the assembled frontmatter with forge-ref `validate_frontmatter`; auto-resolve conflicts per schema.md §Resolution policy and record each one.

## Phase 2 — Security triage (before anything moves)

Order matters: find the fires before rearranging the furniture.

1. **Secrets scan — three layers, first one NOT optional**:
   - **forge-ref `scan_secrets` ALWAYS runs** (MCP tool, or `python3 tools/mcp/forge-ref/server.py --scan-secrets .` — it ships in the kit, so "no scanner installed" is never true). Record files-scanned + findings counts as evidence in the Phase 7 report; a Phase 2 with no recorded scan output did not happen.
   - gitleaks across all commits when available (history coverage forge-ref lacks).
   - detect-secrets when available (via `uv run --with`/`pipx run`).
   Findings: report file+commit, add **rotation guidance** (a secret that ever touched git is burned — rotate it; history purge via `git filter-repo` is optional cleanup, rotation is not).
2. **`.secrets.baseline` is a REQUIRED artifact** — the generated CI's detect-secrets gate hard-fails without it. Seed it with detect-secrets when available; when not, list "generate and commit .secrets.baseline before first push (CI will fail until then)" as a BLOCKING item at the top of manual follow-ups — never silently omit it.
3. **Hardcoded config inventory**: URLs, ports, timeouts, paths, credentials in source → migration list for the three-layer config stack. Migrate mechanically only where references are unambiguous; the rest goes in the suggestions list.
4. **Posture flags**: wildcard CORS, missing auth on networked routes, disabled TLS verification, debug modes, committed `.env`. Each becomes a report finding with the invariant it violates.

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

Write or extend `docs/ARCHITECTURE.md` (layer-2) for the adopted repo:

- Reverse-engineer the cross-cutting decisions the code already embodies — framework choice, storage layer, auth approach, queue/data flow, deployment shape — one ACTIVE `[decision-id]` entry each, rationale phrased as "observed + why it appears deliberate"; mark genuinely unclear rationale as such rather than inventing it.
- Add an `[adopted-into-hephaestus]` entry: date, source path of the original project, frontmatter decided, what adopt changed, what it deferred.
- Seed the protocol forward-only: new/touched code gets `@logic-ref` docstrings; do NOT retro-tag the whole codebase.
- Wire the generated logic-ref checker into pre-commit + CI like any scaffold.

## Phase 7 — Report

Single message, in order: security findings (rotation actions first), frontmatter decisions table (field → value → evidence), artifacts generated / upgraded / kept, moves applied vs demoted (with reasons), middleware suggestion diffs, ARCHITECTURE.md entries written, instruction-file merges performed, manual follow-ups (tools not installed, rotations pending, history purge decision). Always include: the `origin` remote warning (pushes go to the original project's remote until re-pointed), whether uncommitted changes from the original were captured, and the reminder that the original folder is untouched — full rollback is deleting this clone. End with the branch name and the per-phase checkpoint commits so partial rollback is one revert away.
