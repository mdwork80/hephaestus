---
name: hephaestus
description: Zero-question project scaffolder with security-by-default governance — validated PROJECT.md frontmatter, secrets hygiene, pre-commit gates, hardened containers, CI — in ANY programming or scripting language. Infers all answers from the task; never interviews. Bootstrap mode scaffolds a fresh clone; augment mode adds toolchain + safeguards when a new language or runtime pattern enters the project; adopt mode ingests an existing ungoverned codebase. Trigger. fresh clone with no PROJECT.md, "new project", "scaffold", "hephaestus", "/hephaestus", a task introducing a language/runtime not declared in PROJECT.md, or "adopt"/"ingest"/"onboard this existing project".
---

# Hephaestus (skill)

Generate or extend a governed project scaffold with **zero questions**. You are the developer: infer every answer from the user's task, the repository state, and the schema defaults; apply the cross-field rules; emit the scaffold; report the decisions afterward. Never run an intake interview — `AskUserQuestion` is not part of this skill.

Reference docs (read before emitting anything):

- `references/schema.md` — frontmatter fields, defaults, inference sources, 11 cross-field rules. The contract.
- `references/file-matrix.md` — which files to emit under which answers; augment deltas.
- `references/invariants.md` — security/config invariants each artifact must satisfy, with per-language mapping guidance.

## Mode selection

- **Bootstrap** — no `PROJECT.md` at repo root AND no pre-existing source code (fresh clone of the hephaestus base, or empty target dir). Full scaffold.
- **Augment** — `PROJECT.md` exists and the current task introduces a language, runtime pattern, or deployment change not declared in its frontmatter (e.g. Python CLI grows a Rust+axum API and a TypeScript front end). Emit only the delta, then continue with the task. The session-start drift scan (`.claude/hooks/session-start.sh`) also flags undeclared languages — treat its warning as a mandatory augment trigger before feature work.
- **Adopt** — no `PROJECT.md` but real source code exists (an external project being ingested). Full workflow in `references/adopt.md`: kit transplant → evidence survey → security triage (full-history secrets scan first) → gap analysis → invariant-justified restructure with reference rewriting → middleware suggestion diffs → ARCHITECTURE.md reconstruction → report. Runs on a `hephaestus/adopt` branch with per-phase checkpoints; never rewrites business logic.

## Bootstrap workflow

### 1. Infer

Resolve every frontmatter field from, in priority order: (a) the user's task statement, (b) repository/environment context (`git config user.name` for owner, directory name for project name), (c) schema.md defaults. "Build a python CLI that syncs dotfiles" carries `languages: [python]`, `runtime_patterns: [cli]`, name, description — the rest is defaults. Also resolve generation-only options (`network_exposure`, `image_signing`, `ssh_scaffold`) per their relevance conditions.

### 2. Validate + auto-resolve

Check all field bounds and ALL 11 cross-field rules. Resolve violations per schema.md §Resolution policy: rules 4/9 force `threat_model_required: true`; everything else resolves toward the safer value. Record every auto-resolution for the decisions report. Do not ask; only stop on genuinely contradictory explicit user statements.

### 3. Clone detachment (base-repo clones only)

If the repo's `origin` points at the hephaestus base template, this is a child project: remove or re-point the remote (`git remote rm origin`), and note it in the decisions report. Never push a child project to the template remote.

### 4. Emit

Resolve the file list from `references/file-matrix.md`; write every file, satisfying every invariant in `references/invariants.md` — requirements, not suggestions:

- **Deep artifacts come from the forge-ref MCP server first.** Dockerfiles, compose, CI/CD workflows, FastAPI/axum middleware: call `list_templates` / `get_template` on the `forge-ref` server (registered in `.mcp.json`) and use its rendered output verbatim. Free-generate only when no template matches, and say so in the decisions report. Azure IaC (Bicep) comes from the dedicated Bicep MCP server, not forge-ref.
- **PROJECT.md frontmatter is the contract.** Exact YAML per schema.md §Frontmatter layout. Everything else adapts per language; this does not. Validate with forge-ref's `validate_frontmatter` tool when available.
- **Idiomatic per language, for EVERY language in `languages`.** Native lockfiles, lint, SAST, dep audit per invariants.md §Language mapping. Never bolt Python tooling onto a non-Python project.
- **Config over hard-coding.** Code defaults → committed `config/default.toml` (no secrets) → env vars/`.env` (gitignored). Prefix `SLUG_UPPER_`, `__` nesting.
- **Validator ships with the project** in the primary language: all schema bounds + 11 rules + `--check-cadence` + the manifest-vs-frontmatter language drift check. Wired into pre-commit and CI. Self-validating offline, zero dependence on this skill.
- **Docstring/logic-ref protocol** section in PROJECT.md; integrity checker generated alongside the validator.

### 5. Post-generation tasks

Run via Bash in the project dir. Tool present → run; absent → skip and list under "manual follow-ups". Never fail the scaffold over a missing local tool.

1. Lockfile per language (`uv lock`, `cargo generate-lockfile`, `npm install --package-lock-only`, `go mod tidy`, …).
2. `detect-secrets scan --all-files > .secrets.baseline` (direct, `uv run --with detect-secrets`, or `pipx run`).
3. Run the generated frontmatter validator against the generated PROJECT.md. NOT optional — if its runtime is missing, validate manually against schema.md and say so.
4. `pre-commit install` if pre-commit is available; initial commit only if the user asked for one.

### 6. Report (replaces confirmation)

No pre-write confirmation — this skill acts, then reports. End with:

- **Decisions table**: field → value → source (`inferred` / `default` / `auto-corrected: <rule>`).
- File tree written; tasks run vs. skipped; validator result.
- Corrections invited: any wrong inference, state it and hephaestus re-runs as an augment/fix pass.

## Augment workflow

1. Read current `PROJECT.md` frontmatter. Compute the delta the task implies: new `languages` entries, new `runtime_patterns`, changed `deployment_target`/`auth_model`/etc.
2. Re-validate the MERGED answer set against all 11 rules (a new `api_service` pattern on a non-local deployment invalidates `auth_model: none` — Rule 8; auto-resolve to `api_key` and report).
3. Emit only missing artifacts per file-matrix.md §Augment deltas: new language toolchain blocks (manifest, lint/SAST/audit hooks, CI jobs, Dockerfile stage), new pattern artifacts (middleware stack, health endpoints), updated frontmatter (`languages`, `runtime_patterns`, NOT `last_reviewed` — an augment is not a review).
4. Update, never regenerate, existing files: append language blocks to `.pre-commit-config.yaml`, add CI jobs, extend `.gitignore`, extend the in-project validator's language list.
5. Post-gen tasks for the new language only; then the decisions report (delta form); then continue with the user's actual feature task.

## Principles

- **Never interview.** Infer, default, auto-resolve toward safety, report after. The user corrects the report; corrections are cheaper than interrogations.
- **Invariants, not templates.** Any language satisfying invariants.md is a valid scaffold — that keeps "any language" cheap.
- **Schema rules are governance decisions.** Never relax or reorder a cross-field rule during a scaffold. Rule changes edit `references/schema.md` in their own commit.
- **Regeneration warns.** Re-running bootstrap over an existing scaffold: diff first, show what would be overwritten, preserve `last_reviewed`.

## Deep-template reference points

> **STATUS:** the `forge-ref` MCP server (`tools/mcp/forge-ref/`, registered in `.mcp.json`) now serves the battle-tested deep templates as byte-stable rendered assets: hardened Dockerfiles (python/rust), compose, dockerignore, SHA-pinned CI (python/rust), deploy (OIDC + cosign gate), release (GHCR + Sigstore), and the FastAPI/axum security-middleware stacks — plus a `validate_frontmatter` tool implementing the full schema. Prefer its output over free generation; `references/invariants.md` remains the authority for judging any gap or extension.
>
> **IaC MCP servers (registered in `.mcp.json`, per-machine runtimes required):**
> - `bicep` (`Azure.Bicep.McpServer` via dotnet dnx, needs .NET 10 SDK) — use for ALL `infra/` Bicep work: `get_bicep_best_practices` before authoring, `list_avm_metadata` to prefer Azure Verified Modules, resource-type schemas while writing, `build_bicep` / `get_bicep_file_diagnostics` to verify every emitted file compiles clean. invariants.md §Azure infra still governs WHAT to build (private endpoints, least-privilege RBAC, edge modules); the MCP server governs correctness.
> - `terraform` (hashicorp/terraform-mcp-server via docker) — provider/module registry lookups and plan guidance when a project chooses Terraform over Bicep or targets multi_cloud.
> - `aws-iac` (`awslabs.aws-iac-mcp-server` via uvx) — CDK guidance, patterns, and CDK-Nag security checks for AWS targets (successor to the deprecated CDK MCP server).
>
> All IaC servers require user approval on first use (project-scope `.mcp.json`, no auto-approve) and their tool calls prompt like any other tool. If a required runtime is missing (session-start hook warns), fall back to prose generation against invariants.md and say so in the decisions report.
