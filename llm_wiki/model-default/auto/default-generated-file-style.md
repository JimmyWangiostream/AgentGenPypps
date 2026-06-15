---
title: Default Generated File Style
source_type: ModelDefault
source_path: llm_wiki/model-default/auto/default-generated-file-style.md
source_section: generated-file-style
source_hash: manual
priority: 30
authority: fallback
confidence: high
status: active
default_origin: auto_generated
default_policy_mode: auto_accept
category: HARD_DEFAULT
applies_to:
  tc_ids: []
  features: []
  operations: [generation]
  commands: []
  flags: []
  attributes: []
claim_types:
  - fallback-default
  - code-style
fallback_only: true
requires_recording: true
---

# Default Generated File Style

Condition:
- The generator writes Pattern `.py` and trace artifacts.
- No source specifies file encoding or trace header style.

Action:
- Write UTF-8 text files.
- Include a generated-from header referencing TC, retrieval, assumptions, and validation artifacts.

Impact:
- Behavior-neutral engineering default.
