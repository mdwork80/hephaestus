# Hephaestus

Clone-base project template with an AI-driven scaffolder. Clone it, state your first task, and the assistant builds a governed project around it: validated `PROJECT.md` frontmatter, secrets hygiene, pre-commit gates, hardened containers, SHA-pinned CI/CD — in any programming or scripting language. No interviews; the scaffolder infers everything from your task and reports its decisions afterward.

Built for [Claude Code](https://claude.com/claude-code), portable to other AI coding assistants (see [Using with other AI assistants](#using-with-other-ai-assistants)).

## How it works

1. `git clone` this repo into a directory named after your new project (the directory name matters — see below).
2. Open it in your AI assistant and state your first real task ("build a python CLI that syncs dotfiles to S3").
3. The **hephaestus** scaffolder runs first: infers the project's identity, language(s), runtime pattern(s), and security posture from your task; applies the governance schema's defaults and cross-field rules (auto-resolving conflicts toward the safer option); emits the full scaffold; then does your task.
4. You get a decisions table — correct anything wrong and it re-scaffolds the delta.

Later, when a task introduces a new language or runtime ("add a Rust API and a TypeScript front end"), **augment mode** adds the new toolchain blocks (lint, SAST, dependency audit, CI jobs, pre-commit hooks) and updates the frontmatter before building the feature.

## Repository layout

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Standing rules the assistant loads every session: bootstrap on fresh clone, augment on new language, governance non-negotiables |
| `.claude/skills/hephaestus/` | The scaffolder: workflow (`SKILL.md`) + governance schema, file matrix, and security invariants (`references/`) |
| `.claude/skills/caveman*`, `cavecrew/` | Optional token-compression communication suite |
| `.claude/hooks/session-start.sh` | Session hook: activates compressed mode, scans for scaffold drift (undeclared languages), warns on missing MCP runtimes |
| `.mcp.json` | MCP server registry (see below) |
| `tools/mcp/forge-ref/` | Zero-dependency python3 MCP server serving canonical deep templates + frontmatter validation |
| `tools/project-forge/` | Legacy Copier template (gitignored reference source; not used for generation) |

## MCP servers

Registered in `.mcp.json`. All require your approval on first use; none auto-approve.

| Server | Runtime needed | Provides |
|---|---|---|
| `forge-ref` | python3 only | Byte-stable deep templates (hardened Dockerfiles, compose, SHA-pinned CI, deploy + cosign gate, release + Sigstore, FastAPI/axum security middleware) and `validate_frontmatter` |
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

The scaffolder detaches `origin` during bootstrap so you never push a child project back to this template.

## Using with other AI assistants

Everything load-bearing is markdown, JSON, and a bash script — nothing is Claude-proprietary except the file *locations*. To port, you translate three things:

1. **Instructions** — `CLAUDE.md` + `.claude/skills/hephaestus/SKILL.md` + its `references/*.md` become your tool's instruction file(s).
2. **MCP servers** — `.mcp.json` becomes your tool's MCP config (same servers, same commands, different key names).
3. **The session hook** — no other tool has session hooks; run `bash .claude/hooks/session-start.sh` manually at session start (it prints the same bootstrap/augment/drift notices), or fold its checks into your instruction file.

Concept map:

| Claude Code | OpenAI Codex CLI | Gemini CLI | GitHub Copilot (VS Code) | Cursor |
|---|---|---|---|---|
| `CLAUDE.md` | `AGENTS.md` | `GEMINI.md` | `.github/copilot-instructions.md` | `.cursor/rules/*.mdc` |
| `.claude/skills/*/SKILL.md` | inline into `AGENTS.md` | `.gemini/commands/*.toml` or inline | `.github/prompts/*.prompt.md` | `.cursor/rules/*.mdc` |
| `.mcp.json` | `~/.codex/config.toml` `[mcp_servers.*]` | `.gemini/settings.json` `mcpServers` | `.vscode/mcp.json` `servers` | `.cursor/mcp.json` `mcpServers` |
| `.claude/hooks/` | — (run manually) | — (run manually) | — (run manually) | — (run manually) |

Ask your assistant to do the conversion for you — this prompt works on any of them:

> Read CLAUDE.md, .claude/skills/hephaestus/SKILL.md, and .claude/skills/hephaestus/references/*.md. Merge their rules into this tool's instruction file (see the concept map in README.md), preserving verbatim: the bootstrap and augment rules, the 11 cross-field governance rules, and the "never interview, infer + report after" behavior. Then translate .mcp.json into this tool's MCP configuration format. Do not modify the .claude/ directory — leave it intact for Claude users.

Per-tool notes:

### OpenAI Codex CLI

- Create `AGENTS.md` at repo root containing the CLAUDE.md rules plus a condensed hephaestus workflow (Codex reads `AGENTS.md` automatically).
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

- Create `GEMINI.md` at repo root (same content strategy as `AGENTS.md`).
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

- Create `.github/copilot-instructions.md` with the CLAUDE.md rules; put the hephaestus workflow in `.github/prompts/hephaestus.prompt.md` so `/hephaestus` works in Copilot Chat.
- MCP goes in `.vscode/mcp.json` — note the key is `servers` and each entry takes `"type": "stdio"`:

```json
{
  "servers": {
    "forge-ref": { "type": "stdio", "command": "python3", "args": ["tools/mcp/forge-ref/server.py"] }
  }
}
```

### Cursor

- Create `.cursor/rules/hephaestus.mdc` with `alwaysApply: true` frontmatter carrying the CLAUDE.md rules + workflow.
- MCP goes in `.cursor/mcp.json`, same `mcpServers` shape as `.mcp.json` — often a straight copy.

### What does not port

- **Session hooks** — the drift scan and bootstrap/augment notices fire automatically only in Claude Code. Elsewhere: run `bash .claude/hooks/session-start.sh` yourself, or add "run the session-start script and obey its output before any work" as the first rule in your instruction file (agentic tools with shell access will comply).
- **Skill auto-triggering** — Claude Code invokes the hephaestus skill on trigger phrases. Other tools need the workflow inlined in their instruction file or exposed as a prompt/command file.
- **Permission prompting** — each tool has its own MCP trust model; review yours before enabling the IaC servers.

Whatever the tool, keep `.claude/` intact and additive — the same clone should work for Claude and non-Claude users side by side.

## License

See [LICENSE](LICENSE) if present; otherwise treat as proprietary to the template owner.
