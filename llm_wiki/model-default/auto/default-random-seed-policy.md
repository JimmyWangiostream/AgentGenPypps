---
title: Default Random Seed Policy
source_type: ModelDefault
source_path: llm_wiki/model-default/auto/default-random-seed-policy.md
source_section: random-seed
source_hash: manual
priority: 30
authority: fallback
confidence: medium
status: active
default_origin: auto_generated
default_policy_mode: auto_accept
category: SOFT_ASSUMPTION
applies_to:
  tc_ids: []
  features: []
  operations: [random-write, random-read, random-reset, random-selection]
  commands: [WRITE_10, READ_10, START_STOP_UNIT]
  flags: []
  attributes: []
claim_types:
  - fallback-default
fallback_only: true
requires_recording: true
---

# Default Random Seed Policy

Condition:
- TC requires random behavior.
- TC does not specify random seed.
- UserPrompt and CustomerReq do not specify random seed.

Action:
- Generate a runtime seed or deterministic per-run seed according to generator implementation.
- Record the actual seed in Pattern logs and `assumptions.md`.

Impact:
- Reproducibility depends on recording the seed.
