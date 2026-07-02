<!-- GENERATED from CLAUDE.md by: python3 tools/mcp/forge-ref/server.py --emit-instructions -->
<!-- Do not edit by hand: edit CLAUDE.md, then re-run that command. -->

# Hephaestus — clone-base project template

This repository is the base template for all new projects: it gets `git clone`d, then Claude scaffolds the actual project on top. You (Claude) are the developer — you build the safeguards and scaffolding; the user states tasks, not answers.

## Standing rules

1. **Bootstrap.** No `PROJECT.md` at repo root = fresh clone. On the first substantive task, run the `hephaestus` skill in **bootstrap mode** BEFORE doing the task: infer all scaffold answers from the task + schema defaults (`.claude/skills/hephaestus/references/schema.md`), emit the full scaffold, report decisions after. Never interview the user.
2. **Augment.** `PROJECT.md` exists and a task introduces a language, runtime pattern, or deployment target not declared in its frontmatter (e.g. Python CLI grows a Rust+axum API + TypeScript front end): run the `hephaestus` skill in **augment mode** first — new toolchain blocks (lint, SAST, dep audit, CI jobs, pre-commit hooks), pattern artifacts, frontmatter update — then build the feature.
3. **Adopt.** Ingesting an existing, ungoverned external project (user says "adopt/ingest/onboard <path>", or code exists with no `PROJECT.md`): run the `hephaestus` skill in **adopt mode** per `references/adopt.md`. Direction is copy-IN: the external project's contents (including its `.git`) are copied into THIS clone, replacing template history; the original folder is never touched — deleting the clone is the rollback. External instruction files (CLAUDE.md/AGENTS.md/GEMINI.md/copilot-instructions/cursor rules) win collisions AFTER receiving this file's Standing rules + Layout sections. Then: evidence survey, full-history secrets triage, gap analysis, invariant-justified restructure, middleware suggestion diffs, ARCHITECTURE.md reconstruction — on branch `hephaestus/adopt`, before any other work.
4. **Hook warnings are mandatory triggers.** `.claude/hooks/session-start.sh` injects `HEPHAESTUS BOOTSTRAP REQUIRED` / `HEPHAESTUS ADOPT REQUIRED` / `HEPHAESTUS AUGMENT REQUIRED` notices at session start. Act on them before any other work; do not defer or ask.
5. **Clone detachment.** If `git remote get-url origin` points at the hephaestus base template, this is a child project: remove or re-point the remote during bootstrap. Never push a child project to the template remote.
6. **Governance is not negotiable.** Cross-field rules in `references/schema.md` auto-resolve toward the safer value; changing a rule is a deliberate edit to that file in its own commit, never an inline relaxation.

## Layout

- `.claude/skills/hephaestus/` — the scaffolder (SKILL.md + schema/file-matrix/invariants references)
- `.claude/skills/caveman*`, `cavecrew/` — communication compression suite
- `.claude/hooks/session-start.sh` (+ `.ps1` PowerShell port, identical output) — caveman activation + scaffold drift scan; Windows machines without bash point settings.json at the .ps1
- `tools/mcp/forge-ref/` — MCP server (zero-dep python3, registered in `.mcp.json`) serving canonical deep templates (Docker, CI/CD, FastAPI/axum middleware) + `validate_frontmatter`; hephaestus consults it before free-generating those artifacts.
- `.mcp.json` also registers IaC servers (user approval required, per-machine runtimes): `bicep` (Azure.Bicep.McpServer, dotnet dnx / .NET 10) for all Bicep authoring + compile checks, `terraform` (hashicorp image, docker), `aws-iac` (awslabs, uvx) for CDK + CDK-Nag. Missing runtimes → session-start hook warns; fall back to prose per invariants.md.
- `tools/project-forge/` — legacy Copier template (reference source; do not use for generation); `.gitignore`d

## Non-Claude adaptation

This file is for AI assistants other than Claude Code. Three mechanics differ:

1. **Skills**: you cannot invoke Claude skills. Instead, READ
   `.claude/skills/hephaestus/SKILL.md` and its `references/*.md` and follow
   them literally — they are plain instructions, not Claude-specific code.
2. **Session hook**: you get no automatic session hook. At the start of every
   session run `bash .claude/hooks/session-start.sh` (or on Windows
   `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1`)
   and obey its output before any other work.
3. **MCP servers**: translate `.mcp.json` into your tool's MCP configuration —
   see README.md "Using with other AI assistants" for per-tool formats. If your
   tool cannot run MCP servers, invoke forge-ref directly:
   `python3 tools/mcp/forge-ref/server.py --selftest | --scan-secrets [path]`,
   and read templates from `tools/mcp/forge-ref/templates/`.
