---
title: Default Reset Coverage Policy
source_type: ModelDefault
source_path: llm_wiki/model-default/auto/default-reset-coverage-policy.md
source_section: reset-coverage
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
  features: [power-management]
  operations: [reset, random-reset]
  commands: [START_STOP_UNIT]
  flags: []
  attributes: []
claim_types:
  - fallback-default
fallback_only: true
requires_recording: true
---

# Default Reset Coverage Policy

Condition:
- TC lists multiple reset candidates.
- TC does not define the exact coverage strategy.
- UserPrompt and CustomerReq do not define reset coverage.

Action:
- Cover all listed reset types across loop iterations.
- If the generator cannot implement all reset primitives, emit `TODO_REVIEW` for missing primitives.

Impact:
- This affects coverage distribution but should not change the listed TC reset intent.
