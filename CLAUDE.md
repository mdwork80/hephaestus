# Hephaestus — clone-base project template

This repository is the base template for all new projects: it gets `git clone`d, then Claude scaffolds the actual project on top. You (Claude) are the developer — you build the safeguards and scaffolding; the user states tasks, not answers.

## Standing rules

1. **Bootstrap.** No `PROJECT.md` at repo root = fresh clone. On the first substantive task, run the `hephaestus` skill in **bootstrap mode** BEFORE doing the task: infer all scaffold answers from the task + schema defaults (`.claude/skills/hephaestus/references/schema.md`), emit the full scaffold, report decisions after. Never interview the user.
2. **Augment.** `PROJECT.md` exists and a task introduces a language, runtime pattern, or deployment target not declared in its frontmatter (e.g. Python CLI grows a Rust+axum API + TypeScript front end): run the `hephaestus` skill in **augment mode** first — new toolchain blocks (lint, SAST, dep audit, CI jobs, pre-commit hooks), pattern artifacts, frontmatter update — then build the feature.
3. **Hook warnings are mandatory triggers.** `.claude/hooks/session-start.sh` injects `HEPHAESTUS BOOTSTRAP REQUIRED` / `HEPHAESTUS AUGMENT REQUIRED` notices at session start. Act on them before any other work; do not defer or ask.
4. **Clone detachment.** If `git remote get-url origin` points at the hephaestus base template, this is a child project: remove or re-point the remote during bootstrap. Never push a child project to the template remote.
5. **Governance is not negotiable.** Cross-field rules in `references/schema.md` auto-resolve toward the safer value; changing a rule is a deliberate edit to that file in its own commit, never an inline relaxation.

## Layout

- `.claude/skills/hephaestus/` — the scaffolder (SKILL.md + schema/file-matrix/invariants references)
- `.claude/skills/caveman*`, `cavecrew/` — communication compression suite
- `.claude/hooks/session-start.sh` — caveman activation + scaffold drift scan
- `tools/mcp/forge-ref/` — MCP server (zero-dep python3, registered in `.mcp.json`) serving canonical deep templates (Docker, CI/CD, FastAPI/axum middleware) + `validate_frontmatter`; hephaestus consults it before free-generating those artifacts. Bicep is NOT here — dedicated Bicep MCP server pending.
- `tools/project-forge/` — legacy Copier template (reference source; do not use for generation); `.gitignore`d
