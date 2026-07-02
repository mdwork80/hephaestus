# Hephaestus

Clone-base project template with an AI-driven scaffolder. Clone it, state your first task, and the assistant builds a governed project around it: validated `PROJECT.md` frontmatter, secrets hygiene, pre-commit gates, hardened containers, SHA-pinned CI/CD — in any programming or scripting language. No interviews; the scaffolder infers everything from your task and reports its decisions afterward.

Built for [Claude Code](https://claude.com/claude-code), portable to other AI coding assistants (see [Using with other AI assistants](#using-with-other-ai-assistants)).

## How it works

1. `git clone` this repo into a directory named after your new project (the directory name matters — see below).
2. Open it in your AI assistant and state your first real task ("build a python CLI that syncs dotfiles to S3").
3. The **hephaestus** scaffolder runs first: infers the project's identity, language(s), runtime pattern(s), and security posture from your task; applies the governance schema's defaults and cross-field rules (auto-resolving conflicts toward the safer option); emits the full scaffold; then does your task.
4. You get a decisions table — correct anything wrong and it re-scaffolds the delta.

Later, when a task introduces a new language or runtime ("add a Rust API and a TypeScript front end"), **augment mode** adds the new toolchain blocks (lint, SAST, dependency audit, CI jobs, pre-commit hooks) and updates the frontmatter before building the feature.

Already have a project with no scaffolding? **Adopt mode** ingests it — see [Adopting an existing project](#adopting-an-existing-project).

Every scaffolded project records the kit version and base-template URL in its `PROJECT.md` frontmatter (`hephaestus_version` / `hephaestus_base`). When the base template improves, say **"sync hephaestus"** in any child project — **sync mode** fetches the base, re-layers only the kit paths (skills, hooks, forge-ref, `.mcp.json`), leaves your project files untouched, and reports the diff.

## Repository layout

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Standing rules the assistant loads every session: bootstrap on fresh clone, adopt on existing code, augment on new language, sync for kit updates, current-docs-first (context7), governance non-negotiables |
| `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/hephaestus.mdc` | The same rules for non-Claude assistants — GENERATED from `CLAUDE.md`, drift-checked by the selftest; edit `CLAUDE.md`, never these |
| `.claude/skills/hephaestus/` | The scaffolder: workflow (`SKILL.md`) + governance schema, file matrix, and security invariants (`references/`) |
| `.claude/skills/context7/` | Current-documentation lookup for any library/framework/API — standing rule: consult before coding against external APIs |
| `.claude/skills/caveman*`, `cavecrew/` | Optional token-compression communication suite (opt out: `touch .claude/caveman.off` or `HEPHAESTUS_CAVEMAN=off`) |
| `.claude/hooks/session-start.sh` / `.ps1` | Session hook (bash + PowerShell ports, identical output): activates compressed mode, runs the forge-ref selftest, dispatches bootstrap/adopt/augment notices, warns on missing MCP runtimes |
| `.mcp.json` | MCP server registry (see below) |
| `tools/mcp/forge-ref/` | Zero-dependency python3 MCP server: canonical deep templates, frontmatter validation, machine-readable schema, secrets scanning. Kit version lives at `tools/mcp/forge-ref/VERSION` |
| `docs/ARCHITECTURE.md` | Cross-cutting design decisions for this repo, enforced by the selftest's logic-ref integrity check |
| `skills-lock.json` | Provenance record (source repo + hash) for installed third-party skills — not an update mechanism once local edits diverge |

## MCP servers

Registered in `.mcp.json`. All require your approval on first use; none auto-approve.

| Server | Runtime needed | Provides |
|---|---|---|
| `forge-ref` | python3 only | Byte-stable deep templates (hardened Dockerfiles, compose, SHA-pinned CI, deploy + cosign gate, release + Sigstore, FastAPI/axum/Fastify/Go-chi security middleware), `validate_frontmatter`, `get_schema`, `scan_secrets` |
| `bicep` | .NET 10 SDK (`dotnet dnx`) | Bicep authoring, compile diagnostics, Azure Verified Modules metadata, resource schemas |
| `terraform` | Docker | Terraform provider/module registry lookups |
| `aws-iac` | uv (`uvx`) | AWS CDK guidance, IaC patterns, CDK-Nag security checks |

Missing a runtime? That server stays dead and the scaffolder falls back to prose generation against the documented invariants — the session hook tells you which ones are unavailable.

## Quickstart (Claude Code)

```bash
git clone <this-repo> my-new-project   # NOT a dir named "hephaestus" — that suppresses bootstrap
cd my-new-project
claude
# state your first task; scaffold happens first, task second
```

**Windows without bash:** the session hook has a PowerShell port. In `.claude/settings.json`, change the SessionStart hook command to:

```
powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1
```

(If Git for Windows is installed, `bash` is usually on PATH and the default works as-is.)

The scaffolder detaches `origin` during bootstrap so you never push a child project back to this template.

## Adopting an existing project

For codebases that already exist but have no scaffolding or security posture. Adoption copies the external project INTO a fresh hephaestus clone — **your original folder is never touched**. If anything about the conversion goes wrong, delete the clone; the original is exactly as it was.

```bash
git clone <this-repo> my-project-adopted   # fresh clone, NOT named "hephaestus"
cd my-project-adopted
claude   # or your AI of choice — its instruction file ships pre-built (see below)
# say: "adopt /path/to/my-existing-project"
```

The full workflow is defined in [`.claude/skills/hephaestus/references/adopt.md`](.claude/skills/hephaestus/references/adopt.md). Because the clone already carries every instruction file and MCP config, this works the same whichever AI assistant runs it — nothing ever needs to ask where hephaestus lives. Seven phases, one checkpoint commit each, on a `hephaestus/adopt` branch:

1. **Ingest by copy** — the template's git history is discarded and your project's entire contents *including its `.git`* are copied in (real history is needed for the secrets scan and for history-preserving moves). The governance kit is re-layered on top. Collisions: kit files win for `.claude/`/`.mcp.json`/`tools/mcp/`; your files win for everything else — and if your project has its own AI instruction file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, copilot-instructions, Cursor rules), the hephaestus standing rules are merged into *your* file and yours wins.
2. **Evidence survey** — infers the full `PROJECT.md` frontmatter from what's actually there: manifests and source census → languages, frameworks and entrypoints → runtime patterns, Dockerfiles/cloud SDKs → deployment target, git history age → lifecycle stage. No questions.
3. **Security triage** — *before anything moves*: full-history secrets scan (gitleaks + detect-secrets), rotation guidance for anything found (a secret that ever touched git is burned), hardcoded-config inventory, posture flags (wildcard CORS, missing auth, disabled TLS verification).
4. **Gap analysis** — every required artifact is generated (missing), diffed against the canonical forge-ref version (present but weak — applied only when safe-additive), or kept as-is (adequate, even if unconventional). Plus lockfile generation and a dependency vulnerability audit.
5. **Restructure** — only when the existing layout blocks a documented invariant, never for cosmetics. Moves use `git mv`, every reference is rewritten (imports, manifests, CI paths, Dockerfile COPYs, doc links), and each batch is gated on tests passing before *and* after. No tests → smoke tests get written first, or the move is demoted to a suggestion.
6. **Middleware suggestions** — web/API code is diffed against the security-middleware invariants (request IDs, security headers, size limits, health/ready split, sanitized errors, pinned CORS). Gaps come back as ready-to-apply diffs for your review; only zero-behavior-change hardening is applied directly.
7. **ARCHITECTURE.md reconstruction** — the decisions your code already embodies (framework, storage, auth, data flow) get recorded as proper decision entries, plus an `[adopted-into-hephaestus]` entry documenting the source path, what changed, and what was deferred.

You end with a single report: security findings (rotation actions first), the frontmatter decisions table with evidence, what was generated/upgraded/kept, moves applied vs. demoted, suggestion diffs, and manual follow-ups. Two warnings always included: the adopted repo's `origin` still points at your original project's remote (re-point before pushing), and any uncommitted changes in the original were captured in the snapshot.

Rerunning adopt on a half-adopted clone is safe — phases detect completed work and continue. Full rollback at any point: delete the clone.

## Using with other AI assistants

**Instruction files for Codex/ChatGPT (`AGENTS.md`), Gemini (`GEMINI.md`), Copilot (`.github/copilot-instructions.md`), and Cursor (`.cursor/rules/hephaestus.mdc`) ship pre-built** — generated from `CLAUDE.md` and drift-checked by the forge-ref selftest. Your tool picks its file up automatically; usually the only manual step left is translating the MCP config below. (After editing `CLAUDE.md`, regenerate with `python3 tools/mcp/forge-ref/server.py --emit-instructions`.)

Everything load-bearing is markdown, JSON, and a bash script — nothing is Claude-proprietary except the file *locations*. The pieces, if you need to port by hand:

1. **Instructions** — `CLAUDE.md` + `.claude/skills/hephaestus/SKILL.md` + its `references/*.md` become your tool's instruction file(s).
2. **MCP servers** — `.mcp.json` becomes your tool's MCP config (same servers, same commands, different key names).
3. **The session hook** — no other tool has session hooks; run `bash .claude/hooks/session-start.sh` manually at session start (it prints the same bootstrap/adopt/augment/drift notices), or fold its checks into your instruction file. Windows: use the PowerShell port, `powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1` (works on Windows PowerShell 5.1 and pwsh 7).

Concept map:

| Claude Code | OpenAI Codex CLI | Gemini CLI | GitHub Copilot (VS Code) | Cursor |
|---|---|---|---|---|
| `CLAUDE.md` | `AGENTS.md` | `GEMINI.md` | `.github/copilot-instructions.md` | `.cursor/rules/*.mdc` |
| `.claude/skills/*/SKILL.md` | inline into `AGENTS.md` | `.gemini/commands/*.toml` or inline | `.github/prompts/*.prompt.md` | `.cursor/rules/*.mdc` |
| `.mcp.json` | `~/.codex/config.toml` `[mcp_servers.*]` | `.gemini/settings.json` `mcpServers` | `.vscode/mcp.json` `servers` | `.cursor/mcp.json` `mcpServers` |
| `.claude/hooks/` | — (run manually) | — (run manually) | — (run manually) | — (run manually) |

Using a tool not covered by the pre-built files? This conversion prompt works on any assistant:

> Read CLAUDE.md, .claude/skills/hephaestus/SKILL.md, and .claude/skills/hephaestus/references/*.md. Merge their rules into this tool's instruction file (see the concept map in README.md), preserving verbatim: the bootstrap/adopt/augment/sync rules, the 11 cross-field governance rules, and the "never interview, infer + report after" behavior. Then translate .mcp.json into this tool's MCP configuration format. Do not modify the .claude/ directory — leave it intact for Claude users.

Per-tool notes (instruction files already exist; only MCP config is manual):

### OpenAI Codex CLI

- `AGENTS.md` ships pre-built at repo root (Codex reads it automatically).
- MCP goes in `~/.codex/config.toml` (global, per-machine — Codex has no project-scope MCP file):

```toml
[mcp_servers.forge-ref]
command = "python3"
args = ["tools/mcp/forge-ref/server.py"]

[mcp_servers.bicep]
command = "dotnet"
args = ["dnx", "-y", "Azure.Bicep.McpServer"]
```

  Note: with a global config, relative paths like `tools/mcp/forge-ref/server.py` resolve against the working directory — use an absolute path per clone, or skip forge-ref and rely on the reference markdown.

### Gemini CLI

- `GEMINI.md` ships pre-built at repo root.
- MCP goes in `.gemini/settings.json` (project-scope, shareable — closest match to `.mcp.json`):

```json
{
  "mcpServers": {
    "forge-ref": { "command": "python3", "args": ["tools/mcp/forge-ref/server.py"] },
    "bicep":     { "command": "dotnet", "args": ["dnx", "-y", "Azure.Bicep.McpServer"] },
    "terraform": { "command": "docker", "args": ["run", "-i", "--rm", "hashicorp/terraform-mcp-server"] },
    "aws-iac":   { "command": "uvx", "args": ["awslabs.aws-iac-mcp-server@latest"], "env": { "FASTMCP_LOG_LEVEL": "ERROR" } }
  }
}
```

### GitHub Copilot (VS Code)

- `.github/copilot-instructions.md` ships pre-built. Optional: add `.github/prompts/hephaestus.prompt.md` with the SKILL.md workflow so `/hephaestus` works in Copilot Chat.
- MCP goes in `.vscode/mcp.json` — note the key is `servers` and each entry takes `"type": "stdio"`:

```json
{
  "servers": {
    "forge-ref": { "type": "stdio", "command": "python3", "args": ["tools/mcp/forge-ref/server.py"] }
  }
}
```

### Cursor

- `.cursor/rules/hephaestus.mdc` ships pre-built (`alwaysApply: true`).
- MCP goes in `.cursor/mcp.json`, same `mcpServers` shape as `.mcp.json` — often a straight copy.

### What does not port

- **Session hooks** — the drift scan and bootstrap/augment notices fire automatically only in Claude Code. Elsewhere: run `bash .claude/hooks/session-start.sh` yourself, or add "run the session-start script and obey its output before any work" as the first rule in your instruction file (agentic tools with shell access will comply).
- **Skill auto-triggering** — Claude Code invokes the hephaestus skill on trigger phrases. Other tools need the workflow inlined in their instruction file or exposed as a prompt/command file.
- **Permission prompting** — each tool has its own MCP trust model; review yours before enabling the IaC servers.

Whatever the tool, keep `.claude/` intact and additive — the same clone should work for Claude and non-Claude users side by side.

## Template development

Working on the base template itself (not a child project):

```bash
python3 tools/mcp/forge-ref/server.py --selftest            # fixtures, renders, logic-refs, derived-file drift
python3 tools/mcp/forge-ref/server.py --scan-secrets .      # zero-dep working-tree secrets scan
python3 tools/mcp/forge-ref/server.py --emit-instructions   # regenerate AGENTS.md/GEMINI.md/copilot/cursor after editing CLAUDE.md
```

Two lockstep rules the selftest enforces: any governance-schema change updates `references/schema.md` + the validator + the fixtures in the same commit, and any `CLAUDE.md` edit regenerates the derived instruction files. CI (`.github/workflows/ci.yml`) runs the same gates plus shellcheck, hook dispatch smoke tests, and gitleaks over full history.

## License

[GPLv3](LICENSE). Projects scaffolded *by* the template choose their own license (`license` frontmatter field); the template itself and its kit are GPLv3.
