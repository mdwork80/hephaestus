#!/usr/bin/env bash
# SessionStart hook — two jobs:
#   1. Activate caveman mode before the first response.
#   2. Hephaestus drift scan: detect a fresh clone (no PROJECT.md) or
#      languages present on disk but undeclared in PROJECT.md frontmatter.
# stdout is injected into Claude's context at session start.
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- 1. Caveman activation --------------------------------------------------
echo "CAVEMAN MODE ACTIVE (level: full). Obey .claude/skills/caveman/SKILL.md"
echo "from the FIRST response onward: terse, no filler, all technical"
echo "substance intact. Off only on 'stop caveman' / 'normal mode'."
echo ""

# --- 2. Hephaestus drift scan -----------------------------------------------
if [ ! -f "$ROOT/PROJECT.md" ]; then
  echo "HEPHAESTUS BOOTSTRAP REQUIRED: no PROJECT.md — this is a fresh clone"
  echo "of the hephaestus base. On the first substantive task, run the"
  echo "hephaestus skill in bootstrap mode (infer answers from the task, no"
  echo "questions) BEFORE doing the task."
  exit 0
fi

# Languages declared in PROJECT.md frontmatter (block list under 'languages:').
declared="$(awk '/^languages:/{f=1;next} f&&/^  - /{print $2;next} f{exit}' "$ROOT/PROJECT.md" | tr 'A-Z' 'a-z')"

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
