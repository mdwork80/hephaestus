---
project_name: Bad Fixture
project_slug: bad-fixture
description: Deliberately contradictory frontmatter; every expected violation is pinned in invalid-expected.json.
owner: Matthew
lifecycle_stage: prototype

data_classification: regulated
data_types:
  - phi
compliance_scope:
  - none

deployment_target: azure
network_isolation: private
languages:
  - python
runtime_patterns:
  - api_service
azure_services: []
cors_origins:
  - http://evil.example.com

threat_model_required: false
secrets_backend: dotenv_local
auth_model: none

license: Proprietary
ai_tooling: agentic
review_cadence_days: 180
last_reviewed: 2020-01-01
---
