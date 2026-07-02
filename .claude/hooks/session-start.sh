#!/usr/bin/env bash
# SessionStart hook — two jobs:
#   1. Activate caveman mode before the first response.
#   2. Hephaestus drift scan: detect a fresh clone (no PROJECT.md) or
#      languages present on disk but undeclared in PROJECT.md frontmatter.
# stdout is injected into Claude's context at session start.
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- 1. Caveman activation (opt-out) ------------------------------------------
# Disable with `touch .claude/caveman.off` or HEPHAESTUS_CAVEMAN=off.
if [ "${HEPHAESTUS_CAVEMAN:-on}" != "off" ] && [ ! -f "$ROOT/.claude/caveman.off" ]; then
  echo "CAVEMAN MODE ACTIVE (level: full). Obey .claude/skills/caveman/SKILL.md"
  echo "from the FIRST response onward: terse, no filler, all technical"
  echo "substance intact. Off only on 'stop caveman' / 'normal mode'."
  echo ""
fi

# --- 1b. MCP runtime prerequisites -------------------------------------------
# .mcp.json servers need these on each machine; warn, never block.
missing=""
command -v dotnet >/dev/null 2>&1 || missing="$missing dotnet(.NET-10-SDK→bicep)"
command -v docker >/dev/null 2>&1 || missing="$missing docker(→terraform)"
command -v uvx   >/dev/null 2>&1 || missing="$missing uvx(uv→aws-iac)"
if [ -n "$missing" ]; then
  echo "MCP runtimes missing:${missing}. Matching .mcp.json servers stay dead until installed; forge-ref (python3) unaffected."
  echo ""
fi

# --- 1c. forge-ref selftest (Layer 3, docs/ARCHITECTURE.md) -------------------
# Fixture/validator lockstep + render sanity + logic-ref integrity. Fast,
# offline, zero-dep. Only meaningful where the server exists (base repo and
# clones that keep tools/mcp).
if [ -f "$ROOT/tools/mcp/forge-ref/server.py" ]; then
  if ! selftest_out="$(python3 "$ROOT/tools/mcp/forge-ref/server.py" --selftest 2>&1)"; then
    echo "FORGE-REF SELFTEST FAILED — schema/validator/fixtures drifted; fix before scaffolding:"
    echo "$selftest_out" | grep "SELFTEST FAIL" | head -5
    echo ""
  fi
fi

# --- 2. Hephaestus drift scan -----------------------------------------------
# Base-template guard: a fresh clone and the base repo are byte-identical, so
# the only cheap distinguisher is the directory name — clones get project-named
# dirs. A clone into a dir literally named "hephaestus" suppresses the notice;
# documented trade-off, rename the dir or run /hephaestus manually.
if [ "$(basename "$ROOT")" = "hephaestus" ]; then
  [ ! -f "$ROOT/PROJECT.md" ] && echo "Hephaestus base template repo (no PROJECT.md by design) — bootstrap notice suppressed; fires only in project-named clones."
  exit 0
fi

if [ ! -f "$ROOT/PROJECT.md" ]; then
  # No PROJECT.md: bootstrap (empty clone) vs adopt (real code already here).
  # Source census excludes the hephaestus kit itself and vendored/build dirs.
  code_found="$(find "$ROOT" \
    \( -name .git -o -name node_modules -o -name target -o -name .venv -o -name dist -o -name vendor \
       -o -path "$ROOT/.claude" -o -path "$ROOT/tools/mcp" -o -path "$ROOT/tools/project-forge" \) -prune -o \
    -type f \( -name '*.py' -o -name '*.rs' -o -name '*.go' -o -name '*.ts' -o -name '*.js' \
       -o -name '*.cs' -o -name '*.rb' -o -name '*.java' -o -name '*.ps1' \
       -o -name 'pyproject.toml' -o -name 'setup.py' -o -name 'requirements.txt' \
       -o -name 'Cargo.toml' -o -name 'package.json' -o -name 'go.mod' \) \
    -print -quit 2>/dev/null)"
  if [ -n "$code_found" ]; then
    echo "HEPHAESTUS ADOPT REQUIRED: source code present but no PROJECT.md —"
    echo "an adoption is in progress (external project copied in, governance"
    echo "not yet emitted). Resume the hephaestus skill in adopt mode"
    echo "(references/adopt.md; phases are idempotent) on branch"
    echo "hephaestus/adopt BEFORE any other work."
  else
    echo "HEPHAESTUS BOOTSTRAP REQUIRED: no PROJECT.md — this is a fresh clone"
    echo "of the hephaestus base. On the first substantive task, run the"
    echo "hephaestus skill in bootstrap mode (infer answers from the task, no"
    echo "questions) BEFORE doing the task."
  fi
  exit 0
fi

# Languages declared in PROJECT.md frontmatter (block list under 'languages:').
declared="$(awk '/^languages:/{f=1;next} f&&/^  - /{print $2;next} f{exit}' "$ROOT/PROJECT.md" | tr '[:upper:]' '[:lower:]')"

# Languages detected from manifests / sources on disk (skip vendored + VCS dirs).
detected=""
found() { find "$ROOT" \( -name .git -o -name node_modules -o -name target -o -name .venv -o -name dist -o -name vendor \) -prune -o -name "$1" -print -quit 2>/dev/null | grep -q .; }
found "pyproject.toml"  && detected="$detected python"
found "Cargo.toml"      && detected="$detected rust"
found "package.json"    && detected="$detected typescript"
found "go.mod"          && detected="$detected go"
found "*.csproj"        && detected="$detected dotnet"
found "*.psd1"          && detected="$detected powershell"

undeclared=""
for lang in $detected; do
  echo "$declared" | grep -qx "$lang" || undeclared="$undeclared $lang"
done

if [ -n "$undeclared" ]; then
  echo "HEPHAESTUS AUGMENT REQUIRED: language(s) present but undeclared in"
  echo "PROJECT.md frontmatter:${undeclared}. Run the hephaestus skill in"
  echo "augment mode (toolchain + safeguards + frontmatter update) before"
  echo "feature work."
fi

exit 0
