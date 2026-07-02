# PROJECT.md frontmatter schema — the governance contract

Ported from `tools/project-forge/template/_schema/project_frontmatter.py` (Pydantic, v0.11.0 line). Every field bound and cross-field rule below is authoritative. Unknown frontmatter fields are a bug, not a feature (the old schema used `extra="forbid"`). Changing a rule is a governance decision — edit this file deliberately, never ad hoc during a scaffold.

## Fields

### Identity

| Field | Type | Bounds / pattern | Default |
|---|---|---|---|
| `project_name` | str | 1–120 chars | infer from task, else directory name |
| `project_slug` | str | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, 2–64 chars | derived: name → lowercase, spaces/underscores → hyphens |
| `description` | str | 10–280 chars, one sentence | infer from task |
| `owner` | str | 1–120 chars, accountable individual | `git config user.name` |
| `lifecycle_stage` | enum | `prototype` `pilot` `production` `maintenance` `sunset` | `prototype` |

### Classification and compliance

| Field | Type | Values | Default |
|---|---|---|---|
| `data_classification` | enum | `public` `internal` `confidential` `regulated` | `internal` |
| `data_types` | list, min 1 | `none` `pii` `phi` `pci` `cui` `ferpa` `financial` `credentials` `source_code` | `[none]` |
| `compliance_scope` | list, min 1 | `none` `hipaa` `pci_dss` `cmmc_l1` `cmmc_l2` `cmmc_l3` `soc2_type1` `soc2_type2` `fedramp_moderate` `fedramp_high` `iso_27001` `nist_800_171` `nist_csf` | `[none]` |

List rules (both fields): no duplicates; `none` cannot be combined with real values.

### Deployment and runtime

| Field | Type | Values / bounds | Default |
|---|---|---|---|
| `deployment_target` | enum | `local_only` `azure` `hybrid` `multi_cloud` | `local_only` |
| `network_isolation` | enum | `public` `private` | `public`; only relevant when target is azure/hybrid |
| `languages` | list of str, min 1 | **free-form** lowercase identifiers — any programming or scripting language (`python`, `rust`, `go`, `typescript`, `dotnet`, `powershell`, `bash`, `ruby`, …); no duplicates; first entry = primary | infer from task |
| `runtime_patterns` | list of enum, min 1 | `cli` `web_app` `api_service` `background_worker` `scheduled_job` `agent_pipeline` `library`; no duplicates | infer from task, else `[cli]` |
| `azure_services` | list | `container_apps` `functions` `app_service` `storage` `key_vault` `entra_id` `app_insights` `cosmos_db` `sql` `service_bus` `openai` `ai_search`; no duplicates | `[]` |
| `cors_origins` | list of str | see CORS rules below | `[]` |

CORS entry rules: no duplicates; no empty/whitespace entries; **no wildcards anywhere in an entry**; must start `https://` (or `http://localhost` for local dev); bare origin only — scheme://host[:port], no path/query/fragment. Rationale: makes `allow_origins=['*']` + credentials unexpressible.

Multi-language semantics: EVERY entry in `languages` gets its full toolchain block (manifest, lockfile, lint/format, SAST, dep audit, CI jobs — see invariants.md §Language mapping). `runtime_patterns` lists every pattern the project serves; each pattern's artifacts are emitted for whichever language implements it (state the language→pattern assignment in the decisions report).

### Security posture

| Field | Type | Values | Default |
|---|---|---|---|
| `threat_model_required` | bool | — | `false`, but see Rules 4 & 9 |
| `secrets_backend` | enum | `dotenv_local` `key_vault` `hybrid` | `dotenv_local` |
| `auth_model` | enum | `none` `api_key` `entra_id` `managed_identity` `mutual_tls` | `none` |

### Governance

| Field | Type | Bounds | Default |
|---|---|---|---|
| `license` | str | 1–64 chars; SPDX identifier or `Proprietary` | `Proprietary` |
| `ai_tooling` | enum | `none` `dev_only` `runtime_inference` `agentic` | `dev_only` |
| `review_cadence_days` | int | 30–730 | `180` |
| `last_reviewed` | date | ISO `YYYY-MM-DD` | today (generation date) |

`last_reviewed` semantics: CI cadence check fails when today > `last_reviewed` + `review_cadence_days`. An update/regeneration is not a review — preserve the existing date when regenerating over an existing project.

## Cross-field rules (all 11 — enforce at inference time AND in the generated validator)

1. `deployment_target: local_only` ⇒ `azure_services` must be `[]`.
2. `data_classification: regulated` ⇒ `secrets_backend` must NOT be `dotenv_local` (use `key_vault` or `hybrid`).
3. `secrets_backend: dotenv_local` ⇒ requires `deployment_target: local_only` AND `data_classification` in (`public`, `internal`).
4. Any non-`none` `compliance_scope` OR `data_classification` in (`confidential`, `regulated`) ⇒ `threat_model_required: true`.
5. `phi` in `data_types` ⇒ `hipaa` in `compliance_scope`.
6. `cui` in `data_types` ⇒ `compliance_scope` includes at least one of `cmmc_l1`, `cmmc_l2`, `cmmc_l3`, `nist_800_171`.
7. `pci` in `data_types` ⇒ `pci_dss` in `compliance_scope`.
8. `auth_model: none` ⇒ requires ALL `runtime_patterns` in (`cli`, `library`) OR `deployment_target: local_only`.
9. `ai_tooling: agentic` ⇒ `threat_model_required: true`.
10. `cors_origins` non-empty ⇒ `runtime_patterns` includes `web_app` or `api_service`.
11. `network_isolation: private` ⇒ `deployment_target` in (`azure`, `hybrid`).

Resolution policy (no interviews): rules 4 and 9 auto-correct (`threat_model_required: true`). All other violations resolve toward the SAFER value (rule 2/3 conflict ⇒ upgrade `secrets_backend`, never downgrade `data_classification`; rule 8 violation ⇒ pick `api_key` over dropping the deployment). Every resolution goes in the decisions report. Only stop for input when the conflict has no safe resolution (contradictory explicit user statements).

## Generation-only options (NOT frontmatter)

These steer what gets generated but are deliberately excluded from the cross-language governance contract — they are CI/CD or scaffold mechanics, not governance decisions. Never write them into PROJECT.md.

| Option | Values | Default | When relevant |
|---|---|---|---|
| `network_exposure` | `front_door` (Front Door Premium + WAF, Private Link origin) / `app_gateway` (App Gateway WAF_v2 in VNet) / `internal` (no public ingress) | `front_door` | only when `network_isolation: private` |
| `image_signing` | `cosign_keyless` (GHCR publish + Sigstore keyless signing + CycloneDX SBOM + SLSA provenance attestations + `cosign verify` deploy gate) / `none` | `cosign_keyless` | only when `deployment_target != local_only` |
| `ssh_scaffold` | `none` / `client` / `server` / `both` | `none` | only when the task calls for SSH functionality; generalization of the old Rust-only `rust_ssh`. Server mode is network-exposed attack surface: key-based auth only (ed25519, no passwords), and recommend `threat_model_required: true` + a real `auth_model` |

Derived (never asked): per-language package/module/crate identifier = `project_slug` with hyphens → underscores, adjusted to the language's naming convention.

## Frontmatter layout (emit exactly this shape)

```yaml
---
project_name: <str>
project_slug: <str>
description: <str>
owner: <str>
lifecycle_stage: <enum>

data_classification: <enum>
data_types:
  - <value>
compliance_scope:
  - <value>

deployment_target: <enum>
network_isolation: <enum>
languages:
  - <str>                 # first entry = primary
runtime_patterns:
  - <enum>
azure_services: []        # or YAML list
cors_origins: []          # or YAML list

threat_model_required: <true|false>
secrets_backend: <enum>
auth_model: <enum>

license: <str>
ai_tooling: <enum>
review_cadence_days: <int>
last_reviewed: <YYYY-MM-DD>
---
```

Booleans lowercase. Empty lists as `[]` inline; non-empty as block lists. The generated validator must parse exactly this layout.
