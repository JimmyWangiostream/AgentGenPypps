---
title: Missing Core Test Intent Blockers
source_type: ModelDefault
source_path: llm_wiki/model-default/blockers/missing-core-test-intent.md
source_section: blockers
source_hash: manual
priority: 30
authority: fallback
confidence: high
status: active
category: BLOCKER
applies_to:
  tc_ids: []
  features: []
  operations: [generation, validation]
  commands: []
  flags: []
  attributes: []
claim_types:
  - fallback-default
fallback_only: true
requires_recording: true
---

# Missing Core Test Intent Blockers

Do not use ModelDefault to invent any of the following:

- expected value for a verification step;
- command type or opcode;
- protocol-critical IDN, descriptor ID, attribute ID, flag ID, index, selector, or write data;
- LUN/LBA/length when missing would change the core data path being tested;
- pass/fail criteria;
- customer-specific expected behavior.

Action:
- Emit `BLOCKER` or `TODO_REVIEW`.
- Record missing field and source search attempts in `validation.json`.
