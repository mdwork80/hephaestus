# SessionStart hook — PowerShell port of session-start.sh for Windows machines
# without bash on PATH. Same two jobs, same output contract:
#   1. Activate caveman mode before the first response.
#   2. Hephaestus scans: forge-ref selftest, missing-PROJECT.md dispatch
#      (bootstrap vs adopt), language drift, MCP runtime prerequisites.
# stdout is injected into Claude's context at session start.
#
# To use on Windows, point the SessionStart hook in .claude/settings.json at:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/session-start.ps1
# (or pwsh instead of powershell). Keep the .sh variant for macOS/Linux.

$ErrorActionPreference = 'SilentlyContinue'

$root = & git rev-parse --show-toplevel 2>$null
if (-not $root) { $root = (Get-Location).Path }

# --- 1. Caveman activation ----------------------------------------------------
Write-Output "CAVEMAN MODE ACTIVE (level: full). Obey .claude/skills/caveman/SKILL.md"
Write-Output "from the FIRST response onward: terse, no filler, all technical"
Write-Output "substance intact. Off only on 'stop caveman' / 'normal mode'."
Write-Output ""

# --- 1b. MCP runtime prerequisites ---------------------------------------------
$missing = @()
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) { $missing += 'dotnet(.NET-10-SDK→bicep)' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { $missing += 'docker(→terraform)' }
if (-not (Get-Command uvx   -ErrorAction SilentlyContinue)) { $missing += 'uvx(uv→aws-iac)' }
if ($missing.Count -gt 0) {
    Write-Output ("MCP runtimes missing: " + ($missing -join ' ') + ". Matching .mcp.json servers stay dead until installed; forge-ref (python) unaffected.")
    Write-Output ""
}

# --- 1c. forge-ref selftest (Layer 3, docs/ARCHITECTURE.md) ---------------------
# ?? needs PS7; stay Windows-PowerShell-5.1 compatible.
$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
$server = Join-Path $root 'tools/mcp/forge-ref/server.py'
if ($python -and (Test-Path $server)) {
    $selftest = & $python.Source $server --selftest 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output "FORGE-REF SELFTEST FAILED — schema/validator/fixtures drifted; fix before scaffolding:"
        $selftest | Where-Object { $_ -match 'SELFTEST FAIL' } | Select-Object -First 5 | ForEach-Object { Write-Output $_ }
        Write-Output ""
    }
} elseif (-not $python -and (Test-Path $server)) {
    Write-Output "python not found — forge-ref MCP server and its selftest are unavailable on this machine."
    Write-Output ""
}

# --- 2. Hephaestus drift scan ---------------------------------------------------
# Base-template guard: same dir-name heuristic as the .sh variant.
if ((Split-Path $root -Leaf) -eq 'hephaestus') {
    if (-not (Test-Path (Join-Path $root 'PROJECT.md'))) {
        Write-Output "Hephaestus base template repo (no PROJECT.md by design) — bootstrap notice suppressed; fires only in project-named clones."
    }
    exit 0
}

# Shared exclusions for filesystem census (vendored/build dirs + the kit itself).
$excludeDirs = '\.git|node_modules|target|\.venv|dist|vendor'
$kitPaths = @((Join-Path $root '.claude'), (Join-Path $root 'tools/mcp'), (Join-Path $root 'tools/project-forge'))

function Select-ProjectFiles {
    param([string[]]$Patterns)
    Get-ChildItem -Path $root -Recurse -File -Include $Patterns -ErrorAction SilentlyContinue |
        Where-Object {
            $dir = $_.DirectoryName
            ($dir -notmatch "[\\/]($excludeDirs)([\\/]|$)") -and
            (-not ($kitPaths | Where-Object { $dir -like "$_*" }))
        }
}

if (-not (Test-Path (Join-Path $root 'PROJECT.md'))) {
    $codePatterns = @('*.py','*.rs','*.go','*.ts','*.js','*.cs','*.rb','*.java','*.ps1',
                      'pyproject.toml','setup.py','requirements.txt','Cargo.toml','package.json','go.mod')
    $code = Select-ProjectFiles -Patterns $codePatterns | Select-Object -First 1
    if ($code) {
        Write-Output "HEPHAESTUS ADOPT REQUIRED: source code present but no PROJECT.md —"
        Write-Output "an adoption is in progress (external project copied in, governance"
        Write-Output "not yet emitted). Resume the hephaestus skill in adopt mode"
        Write-Output "(references/adopt.md; phases are idempotent) on branch"
        Write-Output "hephaestus/adopt BEFORE any other work."
    } else {
        Write-Output "HEPHAESTUS BOOTSTRAP REQUIRED: no PROJECT.md — this is a fresh clone"
        Write-Output "of the hephaestus base. On the first substantive task, run the"
        Write-Output "hephaestus skill in bootstrap mode (infer answers from the task, no"
        Write-Output "questions) BEFORE doing the task."
    }
    exit 0
}

# Languages declared in PROJECT.md frontmatter (block list under 'languages:').
$declared = @()
$inBlock = $false
foreach ($line in Get-Content (Join-Path $root 'PROJECT.md')) {
    if ($line -match '^languages:') { $inBlock = $true; continue }
    if ($inBlock) {
        if ($line -match '^\s{2}- (\S+)') { $declared += $Matches[1].ToLower(); continue }
        break
    }
}

# Languages detected from manifests on disk.
$detected = @()
if (Select-ProjectFiles -Patterns @('pyproject.toml') | Select-Object -First 1) { $detected += 'python' }
if (Select-ProjectFiles -Patterns @('Cargo.toml')     | Select-Object -First 1) { $detected += 'rust' }
if (Select-ProjectFiles -Patterns @('package.json')   | Select-Object -First 1) { $detected += 'typescript' }
if (Select-ProjectFiles -Patterns @('go.mod')         | Select-Object -First 1) { $detected += 'go' }
if (Select-ProjectFiles -Patterns @('*.csproj')       | Select-Object -First 1) { $detected += 'dotnet' }
if (Select-ProjectFiles -Patterns @('*.psd1')         | Select-Object -First 1) { $detected += 'powershell' }

$undeclared = $detected | Where-Object { $declared -notcontains $_ }
if ($undeclared) {
    Write-Output "HEPHAESTUS AUGMENT REQUIRED: language(s) present but undeclared in"
    Write-Output ("PROJECT.md frontmatter: " + ($undeclared -join ' ') + ". Run the hephaestus skill in")
    Write-Output "augment mode (toolchain + safeguards + frontmatter update) before"
    Write-Output "feature work."
}

exit 0
