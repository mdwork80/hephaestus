# Architecture Decisions — Hephaestus

Cross-cutting design decisions only. Per-function rationale lives in source
docstrings (Layer 1), keyed by `@logic-ref`. This file (Layer 2) records
decisions that span multiple files and have no single function to attach to.
Each entry is keyed by a stable `[decision-id]`, never a line number.

Layer 3 for this repo is `python3 tools/mcp/forge-ref/server.py --selftest`:
it verifies fixture agreement with the schema contract, render sanity, and
logic-ref integrity (unique IDs; every ID referenced by an ACTIVE entry below
exists in source). It runs from the session-start hook; run it manually after
any change to the schema, the server, or this file.

Ported from `tools/project-forge/docs/ARCHITECTURE.md` (the legacy Copier
repo); `[schema-validator-lockstep]` supersedes that repo's
`[single-canonical-validator]` and the dual-validator mitigation in
`[rust-governance-port]`.

---

## [documentation-protocol]
- Scope: entire repository (executable code under tools/mcp/; generated
  projects receive the same protocol via the hephaestus skill)
- Decision: Design rationale travels with code in docstrings (Layer 1).
  Cross-cutting decisions are recorded here (Layer 2). A deterministic,
  LLM-free selftest enforces integrity (Layer 3).
- Rationale: Centralizing rationale in a single hand-maintained file drifts
  silently and bloats context. Docstrings move with their code automatically,
  eliminating the orphaned-comment failure mode during refactors. The selftest
  removes dependence on model discipline; integrity is enforced by the build.
- Affected @logic-refs: forge-ref-selftest
- Status: ACTIVE

---

## [schema-validator-lockstep]
- Scope: .claude/skills/hephaestus/references/schema.md,
  tools/mcp/forge-ref/server.py, tools/mcp/forge-ref/fixtures/
- Decision: The prose contract in schema.md is canonical. Two kinds of
  executable twin exist: forge-ref's `validate_frontmatter` (this repo) and
  the per-language validator each generated project ships. Any change to a
  field bound, enum, or cross-field rule MUST update, in the SAME commit:
  (1) schema.md, (2) server.py's validator, (3) the fixture pair under
  tools/mcp/forge-ref/fixtures/. The selftest fails when the fixtures and the
  validator disagree, making silent drift between (2) and (3) impossible;
  drift against (1) is caught at review because all three travel together.
- Rationale: The legacy Copier repo enforced a single canonical validator
  invoked in place; the skill architecture deliberately abandons that (each
  generated project must validate itself offline, in its own language), which
  re-creates the drift risk its [rust-governance-port] mitigated with shared
  fixtures + cross-checking. This entry ports that mitigation. Generated
  projects' validators are cross-checked at generation time: the skill runs
  forge-ref `validate_frontmatter` against the same PROJECT.md the in-project
  validator accepts.
- Affected @logic-refs: forge-ref-frontmatter-validator forge-ref-selftest
  forge-ref-schema-as-data
- Status: ACTIVE

---

## [forge-ref-zero-dep]
- Scope: tools/mcp/forge-ref/
- Decision: The forge-ref MCP server uses only the python3 standard library —
  no uv, pip, venv, or third-party packages — and implements MCP stdio
  (newline-delimited JSON-RPC 2.0) and the template renderer directly.
- Rationale: This repo is the clone-base for every new project; the server
  must run on any machine that has python3, with zero setup, or clones
  silently lose the canonical deep templates. Alternatives rejected: the
  official `mcp` SDK via uv (adds a runtime prerequisite the target machines
  demonstrably lack) and Node (same problem). Costs accepted: hand-rolled
  protocol handling and a constrained YAML-subset frontmatter parser that
  only accepts the exact layout schema.md §Frontmatter layout emits.
- Affected @logic-refs: forge-ref-zero-dep-server forge-ref-conditionals
  forge-ref-frontmatter-validator forge-ref-secrets-scanner
- Status: ACTIVE

---

## [derived-instruction-files]
- Scope: CLAUDE.md, AGENTS.md, GEMINI.md, .github/copilot-instructions.md,
  .cursor/rules/hephaestus.mdc, tools/mcp/forge-ref/server.py
- Decision: CLAUDE.md is the single source of truth for assistant
  instructions. The four non-Claude files are GENERATED from it via
  `python3 tools/mcp/forge-ref/server.py --emit-instructions` (CLAUDE.md body
  + a non-Claude adaptation section covering skills-as-plain-docs, manual
  session-hook invocation, and MCP config translation). The selftest fails
  when any derivative drifts from CLAUDE.md.
- Rationale: Peers use ChatGPT/Codex, Gemini, Copilot, and Cursor;
  instructions-as-artifact beats a conversion prompt (nothing to run, nothing
  to trust). Hand-maintaining four copies would drift silently — generation +
  a drift gate makes divergence impossible. Alternative rejected: symlinks
  (Windows unfriendliness, Cursor needs .mdc frontmatter).
- Affected @logic-refs: forge-ref-derived-instructions
- Status: ACTIVE

---

## [template-example]
<!-- Copy this block for new decisions. Replace the id above. -->
- Scope: which modules or agents this governs
- Decision: what was decided
- Rationale: why; alternatives rejected
- Affected @logic-refs: list the stable IDs here
- Status: ACTIVE | SUPERSEDED-BY:<id> | DEPRECATED:<date>
