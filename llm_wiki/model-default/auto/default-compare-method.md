---
title: Default Data Compare Method
source_type: ModelDefault
source_path: llm_wiki/model-default/auto/default-compare-method.md
source_section: compare-method
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
  features: [data-compare]
  operations: [write, read, compare]
  commands: [WRITE_10, READ_10]
  flags: []
  attributes: []
claim_types:
  - fallback-default
fallback_only: true
requires_recording: true
---

# Default Data Compare Method

Condition:
- TC requires read/compare or data match.
- TC does not specify hardware compare versus software compare.
- UserPrompt, CustomerReq, and GitNexus project convention do not specify compare method.

Action:
- Prefer the established project compare convention if GitNexus finds one.
- If no convention is found, emit a warning and use generator-configured default compare method.

Impact:
- Compare implementation may affect runtime performance and diagnostic detail.
