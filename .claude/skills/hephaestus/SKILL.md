---
name: hephaestus
description: Scaffold a new project with security-by-default governance — validated PROJECT.md frontmatter, secrets hygiene, pre-commit gates, hardened containers, CI — in ANY programming or scripting language. Pure-prose successor to the Copier template in tools/project-forge. Trigger. "new project", "scaffold", "hephaestus", "forge a project", "/hephaestus".
---

# Hephaestus (skill)

Generate a complete, governed project scaffold from a structured intake. No Copier, no Jinja, no Python scripts required at generation time. The governance contract (frontmatter schema + cross-field rules) and the security invariants are documented here as prose; you apply them idiomatically in whatever language the user picks.

Reference docs (read before emitting anything):

- `references/schema.md` — frontmatter fields, enums, validation bounds, 11 cross-field rules. The contract.
- `references/file-matrix.md` — which files to emit under which answers.
- `references/invariants.md` — security/config invariants each artifact must satisfy, with per-language mapping guidance.

## Workflow

### 1. Intake

Collect the frontmatter fields defined in `references/schema.md`. Use `AskUserQuestion` in small batches (identity → classification → deployment/runtime → security posture → governance). Rules:

- Apply the defaults from schema.md; only ask what matters. If the user gave answers up front (e.g. "python CLI, local only, internal data"), fill from that and only ask for gaps.
- `primary_language` is **free-form**: any programming or scripting language (python, rust, go, typescript, dotnet, powershell, bash, ruby, …). Normalize to a lowercase identifier.
- Derive, don't ask: `project_slug` from `project_name` (kebab-case), package/crate/module name from slug (underscores), `last_reviewed` = today.
- Also collect the generation-only options (not frontmatter): `network_exposure`, `image_signing`, ssh scaffolding — see schema.md §Generation-only options. Only prompt when their `when` condition holds.

### 2. Validate

Before writing anything, check every answer against the field bounds and ALL cross-field rules in schema.md. On violation, don't error out — explain the rule and re-ask (e.g. "regulated data forbids dotenv_local; pick key_vault or hybrid"). Auto-correct where the rule implies the fix: confidential/regulated data, any real compliance scope, or agentic AI tooling ⇒ set `threat_model_required: true` and tell the user.

### 3. Plan and confirm

Resolve the file list from `references/file-matrix.md` for the validated answers. Show the user the target directory and the file tree you intend to create. Get confirmation before writing (creating a project is many files; don't surprise).

### 4. Emit

Write every file in the resolved list. For each artifact, satisfy the invariants in `references/invariants.md` — they are requirements, not suggestions. General emission rules:

- **PROJECT.md frontmatter is the contract.** Emit exact YAML frontmatter per schema.md §Frontmatter layout. Everything else adapts per language; this does not.
- **Idiomatic per language.** Use the language's native tooling for lockfiles, linting, SAST, and packaging (see invariants.md §Language mapping). Never bolt Python tooling onto a non-Python project.
- **Config over hard-coding.** Three layers: code defaults → committed `config/default.toml` (no secrets) → env vars/`.env` (secrets, gitignored). Env prefix = `SLUG_UPPER_` with `__` as the nesting delimiter.
- **Validator ships with the project.** Generate a frontmatter validator in the project's own language (or its natural scripting companion) implementing every field bound and cross-field rule from schema.md, plus a `--check-cadence` mode (fail when today > `last_reviewed` + `review_cadence_days`). Wire it into pre-commit and CI. The generated project must validate itself offline with zero dependence on this skill.
- **Docstring/logic-ref protocol.** Every generated PROJECT.md includes the Code Documentation Protocol section (Layer 1 docstrings with `@logic-ref` IDs, Layer 2 `docs/ARCHITECTURE.md`, Layer 3 integrity check). Generate the integrity checker in the project's language alongside the validator.

### 5. Post-generation tasks

Run in the new project directory, via Bash. Each task: run it if the tool is installed; if absent, skip and list it in a "manual follow-ups" note at the end. Never fail the scaffold over a missing local tool.

1. Generate the lockfile with the language's native tool (`uv lock`, `cargo generate-lockfile`, `npm install --package-lock-only`, `go mod tidy`, …). Interpreted-without-lockfile languages (bash, powershell): skip, note why.
2. `detect-secrets scan --all-files > .secrets.baseline` (via `uv run --with detect-secrets` or `pipx run` if not installed directly).
3. Run the generated frontmatter validator against the generated PROJECT.md. This one is NOT optional — if the validator can't run (missing runtime), validate the frontmatter yourself against schema.md and say you did.
4. Offer (don't assume): `git init -b main` + initial commit, `pre-commit install`.

### 6. Verify

Confirm to the user: files written (tree), tasks run vs. skipped, validator result, and next steps (install deps, run tests, replace LICENSE placeholder if Proprietary wasn't chosen).

## Principles

- **Invariants, not templates.** The old Copier template hard-gated on python/rust. This skill documents *what must be true* of each artifact; any language satisfying the invariants is a valid scaffold. That's how "any language" stays cheap.
- **Schema rules are governance decisions.** Do not relax, reorder, or "improve" a cross-field rule during intake. Changing a rule = editing `references/schema.md` deliberately, in its own commit.
- **No update mechanism.** Unlike `copier update`, re-running this skill on an existing project regenerates; warn the user and diff before overwriting anything that exists.

## Deep-template reference points (roadmap note)

> **NOTE:** MCP servers will be built and added as reference points for the deep templates. The battle-tested verbatim assets from the Copier template — Bicep infra modules (VNet, private endpoints, Front Door/App Gateway edge), the FastAPI/axum security-middleware stacks, hardened Dockerfiles, and the SHA-pinned CI/CD workflows — are the parts most at risk of drift when regenerated as prose. Until those MCP reference servers exist, treat `references/invariants.md` as the authority for these artifacts and flag to the user that deep Azure infra and web middleware output is prose-generated, not template-verified. When the MCP servers land, consult them first for these artifacts and prefer their canonical output over free generation.
