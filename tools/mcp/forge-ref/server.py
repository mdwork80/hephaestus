#!/usr/bin/env python3
"""
forge-ref — MCP reference server for hephaestus deep templates.

Purpose: serve byte-stable, battle-tested scaffold artifacts (Dockerfiles,
CI/CD workflows, web middleware stacks) so the hephaestus skill never
free-generates the drift-prone parts, and validate PROJECT.md frontmatter
against the governance schema.

Zero third-party dependencies by design: this repo is the clone-base for
every new project, so the server must run on any machine with python3 —
no uv, no pip install, no venv. MCP stdio transport is newline-delimited
JSON-RPC 2.0, implemented directly below.

Bicep/Azure IaC assets are deliberately NOT served here; they come from the
dedicated Bicep MCP server integration.

Rationale: @logic-ref: forge-ref-zero-dep-server

Template syntax (templates/*):
    ${name}          substitution var, lowercase identifiers only — never
                     collides with GitHub Actions ${{ ... }} or shell
                     ${UPPERCASE} vars, both of which pass through verbatim.
    #IF flag / #ELIF flag / #ELSE / #ENDIF
                     line-level conditional blocks (nestable); marker lines
                     are removed from output. Unknown flags are false.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "forge-ref", "version": "0.1.0"}

_VAR_RE = re.compile(r"\$\{([a-z][a-z0-9_]*)\}")


# =============================================================================
# Rendering
# =============================================================================


def _apply_conditionals(text: str, flags: dict[str, bool]) -> str:
    """
    Process #IF/#ELIF/#ELSE/#ENDIF line markers.

    Purpose: resolve variant blocks without a template engine.
    Rationale: line-level markers survive any host syntax (dockerfile, yaml,
    python, rust) because they are stripped from output; an expression
    language was rejected as needless surface. @logic-ref: forge-ref-conditionals
    """
    out: list[str] = []
    # Stack of (branch_taken_so_far, currently_emitting) per nesting level.
    stack: list[list[bool]] = []

    def emitting() -> bool:
        return all(level[1] for level in stack)

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("#IF "):
            flag = stripped[4:].strip()
            active = bool(flags.get(flag, False))
            stack.append([active, active])
        elif stripped.startswith("#ELIF "):
            if not stack:
                raise ValueError("#ELIF without #IF")
            flag = stripped[6:].strip()
            taken, _ = stack[-1]
            active = (not taken) and bool(flags.get(flag, False))
            stack[-1] = [taken or active, active]
        elif stripped == "#ELSE":
            if not stack:
                raise ValueError("#ELSE without #IF")
            taken, _ = stack[-1]
            stack[-1] = [True, not taken]
        elif stripped == "#ENDIF":
            if not stack:
                raise ValueError("#ENDIF without #IF")
            stack.pop()
        elif emitting():
            out.append(line)
    if stack:
        raise ValueError("unclosed #IF block")
    return "".join(out)


def _substitute(text: str, variables: dict[str, str]) -> str:
    missing: set[str] = set()

    def repl(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in variables:
            return str(variables[name])
        missing.add(name)
        return m.group(0)

    result = _VAR_RE.sub(repl, text)
    if missing:
        raise ValueError(f"missing template vars: {sorted(missing)}")
    return result


def _derive_vars(variables: dict[str, str]) -> dict[str, str]:
    v = dict(variables)
    slug = v.get("project_slug")
    if slug:
        v.setdefault("pkg", slug.replace("-", "_"))
        v.setdefault("slug_upper", slug.upper().replace("-", "_"))
    return v


def _load_manifest() -> dict:
    return json.loads((TEMPLATES / "manifest.json").read_text())["templates"]


def render_template(name: str, params: dict) -> str:
    manifest = _load_manifest()
    if name not in manifest:
        known = ", ".join(sorted(manifest))
        raise ValueError(f"unknown template {name!r}; known: {known}")
    entry = manifest[name]
    raw = (TEMPLATES / entry["path"]).read_text()
    flags = {k: bool(v) for k, v in params.items() if isinstance(v, bool)}
    variables = _derive_vars({k: v for k, v in params.items() if isinstance(v, str)})
    return _substitute(_apply_conditionals(raw, flags), variables)


# =============================================================================
# Frontmatter validation (hephaestus schema: languages/runtime_patterns lists)
# =============================================================================

RUNTIME_PATTERNS = {
    "cli", "web_app", "api_service", "background_worker",
    "scheduled_job", "agent_pipeline", "library",
}
DATA_CLASSIFICATIONS = {"public", "internal", "confidential", "regulated"}
DATA_TYPES = {"none", "pii", "phi", "pci", "cui", "ferpa", "financial", "credentials", "source_code"}
COMPLIANCE_SCOPES = {
    "none", "hipaa", "pci_dss", "cmmc_l1", "cmmc_l2", "cmmc_l3", "soc2_type1",
    "soc2_type2", "fedramp_moderate", "fedramp_high", "iso_27001", "nist_800_171", "nist_csf",
}
CUI_SCOPES = {"cmmc_l1", "cmmc_l2", "cmmc_l3", "nist_800_171"}
DEPLOYMENT_TARGETS = {"local_only", "azure", "hybrid", "multi_cloud"}
NETWORK_ISOLATIONS = {"public", "private"}
SECRETS_BACKENDS = {"dotenv_local", "key_vault", "hybrid"}
AUTH_MODELS = {"none", "api_key", "entra_id", "managed_identity", "mutual_tls"}
AI_TOOLINGS = {"none", "dev_only", "runtime_inference", "agentic"}
AZURE_SERVICES = {
    "container_apps", "functions", "app_service", "storage", "key_vault", "entra_id",
    "app_insights", "cosmos_db", "sql", "service_bus", "openai", "ai_search",
}
SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_FIELDS = [
    "project_name", "project_slug", "description", "owner", "lifecycle_stage",
    "data_classification", "data_types", "compliance_scope", "deployment_target",
    "network_isolation", "languages", "runtime_patterns", "azure_services",
    "cors_origins", "threat_model_required", "secrets_backend", "auth_model",
    "license", "ai_tooling", "review_cadence_days", "last_reviewed",
]
# Scaffold-provenance fields: bootstrap/adopt always write them, but projects
# scaffolded before they existed may lack them, so they stay optional.
OPTIONAL_FIELDS = ["hephaestus_version", "hephaestus_base"]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _parse_frontmatter(text: str) -> dict:
    """
    Parse the constrained YAML subset the schema's frontmatter layout emits:
    scalar `key: value` lines, inline `key: []`, and block lists of scalars.
    A full YAML parser is deliberately avoided (zero-dep constraint).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter must start with '---'")
    try:
        end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    except StopIteration:
        raise ValueError("frontmatter is not terminated by '---'") from None

    data: dict = {}
    key: str | None = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  - ") and key is not None:
            if not isinstance(data[key], list):
                raise ValueError(f"unexpected list item under scalar field {key!r}")
            data[key].append(raw[4:].split("#", 1)[0].strip())
            continue
        if ":" not in raw:
            raise ValueError(f"unparseable line: {raw!r}")
        k, _, rest = raw.partition(":")
        key = k.strip()
        rest = rest.split("#", 1)[0].strip()
        if rest == "":
            data[key] = []
        elif rest == "[]":
            data[key] = []
            key = None
        else:
            data[key] = rest
            key = None
    return data


def _check_list(errors: list[str], name: str, values: list, allowed: set[str], min_len: int = 1) -> None:
    if not isinstance(values, list):
        errors.append(f"{name} must be a list")
        return
    if len(values) < min_len:
        errors.append(f"{name} must have at least {min_len} entr{'y' if min_len == 1 else 'ies'}")
    if len(values) != len(set(values)):
        errors.append(f"{name}: duplicate entries are not permitted")
    bad = [v for v in values if allowed and v not in allowed]
    if bad:
        errors.append(f"{name}: invalid values {bad}")
    if "none" in values and len(values) > 1:
        errors.append(f"{name}: 'none' cannot be combined with other values")


def validate_frontmatter(text: str, check_cadence: bool = False) -> dict:
    """
    Validate PROJECT.md frontmatter: field bounds + all 11 cross-field rules
    from .claude/skills/hephaestus/references/schema.md.
    Rationale: executable twin of the prose schema so validation never relies
    on model discipline. @logic-ref: forge-ref-frontmatter-validator
    """
    errors: list[str] = []
    try:
        fm = _parse_frontmatter(text)
    except ValueError as exc:
        return {"valid": False, "errors": [str(exc)]}

    for f in REQUIRED_FIELDS:
        if f not in fm:
            errors.append(f"missing required field: {f}")
    unknown = set(fm) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if unknown:
        errors.append(f"unknown fields (extra='forbid'): {sorted(unknown)}")
    if errors:
        return {"valid": False, "errors": errors}

    if "hephaestus_version" in fm and not VERSION_RE.match(str(fm["hephaestus_version"])):
        errors.append("hephaestus_version must be semver (X.Y.Z)")
    if "hephaestus_base" in fm and not (1 <= len(str(fm["hephaestus_base"])) <= 300):
        errors.append("hephaestus_base must be 1-300 characters")

    # --- field bounds ---------------------------------------------------
    if not (1 <= len(fm["project_name"]) <= 120):
        errors.append("project_name must be 1-120 characters")
    if not SLUG_RE.match(fm["project_slug"] or "") or not (2 <= len(fm["project_slug"]) <= 64):
        errors.append("project_slug must be kebab-case, 2-64 characters")
    if not (10 <= len(fm["description"]) <= 280):
        errors.append("description must be 10-280 characters")
    if not (1 <= len(fm["owner"]) <= 120):
        errors.append("owner must be 1-120 characters")
    if fm["lifecycle_stage"] not in {"prototype", "pilot", "production", "maintenance", "sunset"}:
        errors.append("lifecycle_stage: invalid value")
    if fm["data_classification"] not in DATA_CLASSIFICATIONS:
        errors.append("data_classification: invalid value")
    _check_list(errors, "data_types", fm["data_types"], DATA_TYPES)
    _check_list(errors, "compliance_scope", fm["compliance_scope"], COMPLIANCE_SCOPES)
    if fm["deployment_target"] not in DEPLOYMENT_TARGETS:
        errors.append("deployment_target: invalid value")
    if fm["network_isolation"] not in NETWORK_ISOLATIONS:
        errors.append("network_isolation: invalid value")
    _check_list(errors, "languages", fm["languages"], set())  # free-form, dedup+min only
    _check_list(errors, "runtime_patterns", fm["runtime_patterns"], RUNTIME_PATTERNS)
    _check_list(errors, "azure_services", fm["azure_services"], AZURE_SERVICES, min_len=0)
    cors = fm["cors_origins"]
    if isinstance(cors, list):
        if len(cors) != len(set(cors)):
            errors.append("cors_origins: duplicate entries are not permitted")
        for o in cors:
            tail = o.split("://", 1)[1] if "://" in o else o
            if (not o.strip() or "*" in o
                    or not (o.startswith("https://") or o.startswith("http://localhost"))
                    or any(c in tail.rstrip("/") for c in "/?#")):
                errors.append(f"cors_origins: invalid origin {o!r}")
    else:
        errors.append("cors_origins must be a list")
    if fm["threat_model_required"] not in ("true", "false"):
        errors.append("threat_model_required must be lowercase true/false")
    if fm["secrets_backend"] not in SECRETS_BACKENDS:
        errors.append("secrets_backend: invalid value")
    if fm["auth_model"] not in AUTH_MODELS:
        errors.append("auth_model: invalid value")
    if not (1 <= len(fm["license"]) <= 64):
        errors.append("license must be 1-64 characters")
    if fm["ai_tooling"] not in AI_TOOLINGS:
        errors.append("ai_tooling: invalid value")
    try:
        cadence = int(fm["review_cadence_days"])
        if not (30 <= cadence <= 730):
            errors.append("review_cadence_days must be 30-730")
    except (ValueError, TypeError):
        cadence = None
        errors.append("review_cadence_days must be an integer")
    if not DATE_RE.match(str(fm["last_reviewed"])):
        errors.append("last_reviewed must be an ISO date (YYYY-MM-DD)")

    # Bounds errors do NOT short-circuit: report every violation in one pass
    # so a fix round-trip catches rule conflicts too.
    # --- cross-field rules 1-11 ------------------------------------------
    tmr = fm["threat_model_required"] == "true"
    patterns = fm["runtime_patterns"]
    if fm["deployment_target"] == "local_only" and fm["azure_services"]:
        errors.append("Rule 1: azure_services must be empty when deployment_target is 'local_only'")
    if fm["data_classification"] == "regulated" and fm["secrets_backend"] == "dotenv_local":
        errors.append("Rule 2: secrets_backend 'dotenv_local' not permitted for regulated data")
    if fm["secrets_backend"] == "dotenv_local":
        if fm["deployment_target"] != "local_only":
            errors.append("Rule 3: 'dotenv_local' requires deployment_target 'local_only'")
        if fm["data_classification"] not in ("public", "internal"):
            errors.append("Rule 3: 'dotenv_local' requires data_classification 'public' or 'internal'")
    has_compliance = any(s != "none" for s in fm["compliance_scope"])
    if (has_compliance or fm["data_classification"] in ("confidential", "regulated")) and not tmr:
        errors.append("Rule 4: threat_model_required must be true (classification/compliance trigger)")
    if "phi" in fm["data_types"] and "hipaa" not in fm["compliance_scope"]:
        errors.append("Rule 5: data_types 'phi' requires compliance_scope 'hipaa'")
    if "cui" in fm["data_types"] and not (CUI_SCOPES & set(fm["compliance_scope"])):
        errors.append("Rule 6: data_types 'cui' requires a CMMC level or nist_800_171")
    if "pci" in fm["data_types"] and "pci_dss" not in fm["compliance_scope"]:
        errors.append("Rule 7: data_types 'pci' requires compliance_scope 'pci_dss'")
    if fm["auth_model"] == "none":
        non_networked = all(p in ("cli", "library") for p in patterns)
        if not (non_networked or fm["deployment_target"] == "local_only"):
            errors.append("Rule 8: auth_model 'none' requires all-cli/library patterns or local_only")
    if fm["ai_tooling"] == "agentic" and not tmr:
        errors.append("Rule 9: ai_tooling 'agentic' requires threat_model_required true")
    if cors and not ({"web_app", "api_service"} & set(patterns)):
        errors.append("Rule 10: cors_origins requires runtime_patterns web_app or api_service")
    if fm["network_isolation"] == "private" and fm["deployment_target"] not in ("azure", "hybrid"):
        errors.append("Rule 11: network_isolation 'private' requires deployment_target azure/hybrid")

    if check_cadence and cadence is not None and DATE_RE.match(str(fm["last_reviewed"])):
        reviewed = datetime.date.fromisoformat(fm["last_reviewed"])
        overdue = (datetime.date.today() - reviewed).days - cadence
        if overdue > 0:
            errors.append(f"cadence: review is {overdue} days overdue (last_reviewed {reviewed}, cadence {cadence}d)")

    return {"valid": not errors, "errors": errors}


def build_schema() -> dict:
    """
    Purpose: emit the governance contract as machine-readable data so
    generated per-language validators interpret a schema.json instead of
    hardcoding rules — sync mode updates the data, validator logic never
    drifts. Single source: the same constants validate_frontmatter uses.
    @logic-ref: forge-ref-schema-as-data
    """
    version = "unknown"
    vf = ROOT.parents[2] / "VERSION"
    if vf.exists():
        version = vf.read_text().strip()
    return {
        "hephaestus_version": version,
        "required_fields": REQUIRED_FIELDS,
        "optional_fields": OPTIONAL_FIELDS,
        "fields": {
            "project_name": {"type": "str", "min_len": 1, "max_len": 120},
            "project_slug": {"type": "str", "pattern": SLUG_RE.pattern, "min_len": 2, "max_len": 64},
            "description": {"type": "str", "min_len": 10, "max_len": 280},
            "owner": {"type": "str", "min_len": 1, "max_len": 120},
            "lifecycle_stage": {"type": "enum", "values": ["prototype", "pilot", "production", "maintenance", "sunset"]},
            "data_classification": {"type": "enum", "values": sorted(DATA_CLASSIFICATIONS)},
            "data_types": {"type": "list", "values": sorted(DATA_TYPES), "min_len": 1, "no_none_mix": True, "unique": True},
            "compliance_scope": {"type": "list", "values": sorted(COMPLIANCE_SCOPES), "min_len": 1, "no_none_mix": True, "unique": True},
            "deployment_target": {"type": "enum", "values": sorted(DEPLOYMENT_TARGETS)},
            "network_isolation": {"type": "enum", "values": sorted(NETWORK_ISOLATIONS)},
            "languages": {"type": "list", "values": None, "min_len": 1, "unique": True, "comment": "free-form lowercase identifiers; first = primary"},
            "runtime_patterns": {"type": "list", "values": sorted(RUNTIME_PATTERNS), "min_len": 1, "unique": True},
            "azure_services": {"type": "list", "values": sorted(AZURE_SERVICES), "min_len": 0, "unique": True},
            "cors_origins": {"type": "list", "values": None, "min_len": 0, "unique": True,
                             "entry_rules": ["no wildcards", "https:// or http://localhost only", "bare origin (no path/query/fragment)", "non-empty"]},
            "threat_model_required": {"type": "bool"},
            "secrets_backend": {"type": "enum", "values": sorted(SECRETS_BACKENDS)},
            "auth_model": {"type": "enum", "values": sorted(AUTH_MODELS)},
            "license": {"type": "str", "min_len": 1, "max_len": 64},
            "ai_tooling": {"type": "enum", "values": sorted(AI_TOOLINGS)},
            "review_cadence_days": {"type": "int", "min": 30, "max": 730},
            "last_reviewed": {"type": "date", "pattern": DATE_RE.pattern},
            "hephaestus_version": {"type": "str", "pattern": VERSION_RE.pattern, "optional": True},
            "hephaestus_base": {"type": "str", "min_len": 1, "max_len": 300, "optional": True},
        },
        "cross_field_rules": [
            {"id": 1, "if": {"deployment_target": "local_only"}, "require": "azure_services == []",
             "message": "azure_services must be empty when deployment_target is 'local_only'"},
            {"id": 2, "if": {"data_classification": "regulated"}, "require": "secrets_backend != 'dotenv_local'",
             "message": "secrets_backend 'dotenv_local' not permitted for regulated data"},
            {"id": 3, "if": {"secrets_backend": "dotenv_local"},
             "require": "deployment_target == 'local_only' and data_classification in ('public','internal')",
             "message": "'dotenv_local' requires local_only deployment and public/internal classification"},
            {"id": 4, "if": "any compliance_scope != 'none' or data_classification in ('confidential','regulated')",
             "require": "threat_model_required == true",
             "message": "threat_model_required must be true (classification/compliance trigger)"},
            {"id": 5, "if": "'phi' in data_types", "require": "'hipaa' in compliance_scope",
             "message": "data_types 'phi' requires compliance_scope 'hipaa'"},
            {"id": 6, "if": "'cui' in data_types",
             "require": "compliance_scope intersects ('cmmc_l1','cmmc_l2','cmmc_l3','nist_800_171')",
             "message": "data_types 'cui' requires a CMMC level or nist_800_171"},
            {"id": 7, "if": "'pci' in data_types", "require": "'pci_dss' in compliance_scope",
             "message": "data_types 'pci' requires compliance_scope 'pci_dss'"},
            {"id": 8, "if": {"auth_model": "none"},
             "require": "all runtime_patterns in ('cli','library') or deployment_target == 'local_only'",
             "message": "auth_model 'none' requires all-cli/library patterns or local_only"},
            {"id": 9, "if": {"ai_tooling": "agentic"}, "require": "threat_model_required == true",
             "message": "ai_tooling 'agentic' requires threat_model_required true"},
            {"id": 10, "if": "cors_origins != []",
             "require": "runtime_patterns intersects ('web_app','api_service')",
             "message": "cors_origins requires runtime_patterns web_app or api_service"},
            {"id": 11, "if": {"network_isolation": "private"},
             "require": "deployment_target in ('azure','hybrid')",
             "message": "network_isolation 'private' requires deployment_target azure/hybrid"},
        ],
        "cadence_check": "fail when today > last_reviewed + review_cadence_days",
    }


# =============================================================================
# MCP tool definitions and dispatch
# =============================================================================

TOOLS = [
    {
        "name": "list_templates",
        "description": (
            "List canonical deep-template assets (Dockerfiles, CI/CD workflows, "
            "FastAPI/axum middleware). Optionally filter by category: docker, ci, "
            "middleware-fastapi, middleware-axum. Bicep is NOT served here — use "
            "the Bicep MCP server for Azure IaC."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"category": {"type": "string", "description": "Optional category filter"}},
        },
    },
    {
        "name": "get_template",
        "description": (
            "Render a canonical template by name. params holds string substitution "
            "vars (project_name, project_slug, auth_model; pkg/slug_upper derived) "
            "and boolean flags (is_web, is_web_app, has_cors, containerized, azure, "
            "cosign, smoke_test, private_*, ssh_server, has_auth, auth_*). "
            "See list_templates for each template's vars and flags."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Template name from list_templates"},
                "params": {"type": "object", "description": "String vars + boolean flags"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_schema",
        "description": (
            "Return the governance contract as machine-readable JSON: fields "
            "(types, bounds, enums), the 11 cross-field rules, and the kit "
            "version. Generated projects ship this as _schema/schema.json and "
            "their validators interpret it, so rule changes are data updates."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "validate_frontmatter",
        "description": (
            "Validate PROJECT.md frontmatter against the hephaestus governance "
            "schema: field bounds and all 11 cross-field rules. Pass the full "
            "PROJECT.md text (or just the frontmatter block). Set check_cadence "
            "to also fail when last_reviewed is older than review_cadence_days."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "PROJECT.md content"},
                "check_cadence": {"type": "boolean", "description": "Also enforce review cadence"},
            },
            "required": ["text"],
        },
    },
]


def call_tool(name: str, arguments: dict) -> str:
    if name == "list_templates":
        manifest = _load_manifest()
        category = arguments.get("category")
        listing = {
            n: {k: e[k] for k in ("category", "output", "description", "vars", "flags")}
            for n, e in manifest.items()
            if not category or e["category"] == category
        }
        return json.dumps(listing, indent=2)
    if name == "get_template":
        return render_template(arguments["name"], arguments.get("params") or {})
    if name == "get_schema":
        return json.dumps(build_schema(), indent=2)
    if name == "validate_frontmatter":
        result = validate_frontmatter(arguments["text"], bool(arguments.get("check_cadence")))
        return json.dumps(result, indent=2)
    raise ValueError(f"unknown tool: {name}")


# =============================================================================
# MCP stdio transport (newline-delimited JSON-RPC 2.0)
# =============================================================================


def _response(req_id, result=None, error=None) -> dict:
    msg: dict = {"jsonrpc": "2.0", "id": req_id}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    return msg


def handle(msg: dict) -> dict | None:
    method = msg.get("method", "")
    req_id = msg.get("id")
    if req_id is None:  # notification — nothing to answer
        return None
    if method == "initialize":
        return _response(req_id, {
            "protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    if method == "ping":
        return _response(req_id, {})
    if method == "tools/list":
        return _response(req_id, {"tools": TOOLS})
    if method == "tools/call":
        params = msg.get("params", {})
        try:
            text = call_tool(params.get("name", ""), params.get("arguments") or {})
            return _response(req_id, {"content": [{"type": "text", "text": text}]})
        except Exception as exc:  # tool errors go back in-band, isError=True
            return _response(req_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True})
    return _response(req_id, error={"code": -32601, "message": f"method not found: {method}"})


def selftest() -> int:
    """
    Purpose: Layer-3 integrity check for this repo (see docs/ARCHITECTURE.md).
    Verifies (1) fixture agreement with the validator per
    [schema-validator-lockstep], (2) render sanity, (3) logic-ref integrity:
    unique @logic-ref IDs in tools/mcp source, every ID referenced by an
    ACTIVE ARCHITECTURE.md entry exists, ungoverned source IDs warn only.
    Rationale: deterministic and offline so pre-commit/hooks never depend on
    model discipline or network. @logic-ref: forge-ref-selftest
    """
    failures: list[str] = []
    fixtures = ROOT / "fixtures"

    # 1. Fixture agreement.
    valid = validate_frontmatter((fixtures / "valid-project.md").read_text(), check_cadence=False)
    if not valid["valid"]:
        failures.append(f"valid-project.md rejected: {valid['errors']}")
    expected = json.loads((fixtures / "invalid-expected.json").read_text())
    invalid = validate_frontmatter(
        (fixtures / "invalid-project.md").read_text(),
        check_cadence=expected["check_cadence"],
    )
    got = sorted(e.split(":", 1)[0] for e in invalid["errors"])
    want = sorted(expected["expected_prefixes"])
    if got != want:
        failures.append(f"invalid-project.md error prefixes drifted:\n  want {want}\n  got  {got}")

    # 2. Render sanity.
    try:
        text = render_template("docker-python", {"project_name": "Fixture App", "project_slug": "fixture-app", "is_web": True})
        for marker in ("#IF", "#ELSE", "#ENDIF"):
            if marker in text:
                failures.append(f"docker-python render leaked {marker}")
        if "FIXTURE_APP_SERVER__HOST=0.0.0.0" not in text:
            failures.append("docker-python render lost the slug_upper web host line")
    except Exception as exc:
        failures.append(f"docker-python render raised: {exc}")

    # 2b. Schema-as-data agreement.
    schema = build_schema()
    if [r["id"] for r in schema["cross_field_rules"]] != list(range(1, 12)):
        failures.append("get_schema cross_field_rules must be exactly ids 1-11")
    if set(schema["required_fields"]) != set(REQUIRED_FIELDS) or set(schema["optional_fields"]) != set(OPTIONAL_FIELDS):
        failures.append("get_schema field lists drifted from validator constants")
    vf = ROOT.parents[2] / "VERSION"
    if vf.exists() and schema["hephaestus_version"] != vf.read_text().strip():
        failures.append("get_schema version drifted from VERSION file")

    # 3. Logic-ref integrity.
    ref_re = re.compile(r"@logic-ref:\s*([a-z0-9]+(?:-[a-z0-9]+)+)")
    source_ids: dict[str, int] = {}
    for path in sorted(ROOT.rglob("*.py")):
        for rid in ref_re.findall(path.read_text()):
            source_ids[rid] = source_ids.get(rid, 0) + 1
    dupes = [rid for rid, n in source_ids.items() if n > 1]
    if dupes:
        failures.append(f"duplicate @logic-ref IDs: {dupes}")
    arch = ROOT.parents[2] / "docs" / "ARCHITECTURE.md"
    governed: set[str] = set()
    if arch.exists():
        for block in arch.read_text().split("\n---\n"):
            # Exact status line only — the [template-example] block mentions
            # ACTIVE inside a choice list and must not count.
            if not re.search(r"^- Status: ACTIVE\s*$", block, re.M):
                continue
            m = re.search(r"Affected @logic-refs:\s*((?:[a-z0-9]+(?:-[a-z0-9]+)+\s*)+)", block)
            if m:
                governed.update(m.group(1).split())
        missing = governed - set(source_ids)
        if missing:
            failures.append(f"ARCHITECTURE.md ACTIVE entries reference missing @logic-refs: {sorted(missing)}")
    else:
        failures.append("docs/ARCHITECTURE.md not found")
    for rid in sorted(set(source_ids) - governed):
        print(f"warning: @logic-ref {rid} not governed by any ACTIVE ARCHITECTURE.md entry", file=sys.stderr)

    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1
    print("selftest OK: fixtures agree, renders clean, logic-refs intact")
    return 0


def main() -> None:
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(_response(None, error={"code": -32700, "message": "parse error"})) + "\n")
            sys.stdout.flush()
            continue
        reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
