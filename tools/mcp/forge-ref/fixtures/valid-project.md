---
project_name: Fixture App
project_slug: fixture-app
description: Known-good frontmatter fixture for the schema-validator lockstep selftest.
owner: Matthew
lifecycle_stage: prototype

data_classification: internal
data_types:
  - none
compliance_scope:
  - none

deployment_target: local_only
network_isolation: public
languages:
  - python
runtime_patterns:
  - cli
azure_services: []
cors_origins: []

threat_model_required: false
secrets_backend: dotenv_local
auth_model: none

license: Proprietary
ai_tooling: dev_only
review_cadence_days: 180
last_reviewed: 2026-07-02

hephaestus_version: 0.1.0
hephaestus_base: https://example.com/hephaestus.git
---

# Fixture App

Body content is ignored by the validator; only the frontmatter block matters.
