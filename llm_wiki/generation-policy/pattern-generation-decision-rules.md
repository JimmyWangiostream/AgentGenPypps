---
title: Pattern Generation Decision Rules
source_type: GenerationPolicy
source_path: llm_wiki/generation-policy/pattern-generation-decision-rules.md
source_section: pattern-generation
source_hash: manual
priority: 100
authority: policy
confidence: high
applies_to:
  operations: [generation, validation, retrieval]
  tc_ids: []
  features: []
  commands: []
  flags: []
  attributes: []
claim_types:
  - implementation-rule
  - code-style
---

# Pattern Generation Decision Rules

## Inputs

One TC markdown file produces one Pattern `.py` file.

Required output artifacts:
- Pattern `.py`
- `<pattern>.retrieval.md`
- `<pattern>.assumptions.md`
- `<pattern>.validation.json`

## Retrieval split

LLM Wiki handles stable knowledge:
- CustomerReq
- Spec
- UserPrompt
- PropNoun
- ModelDefault
- generation policy

GitNexus handles live code grounding:
- Script/Pattern reference
- primitive API names and signatures
- import paths
- symbol context
- call graph and usage examples

LLM Wiki may say `READ FLAG fWriteBoosterEnable` is required, but GitNexus must confirm the actual PyPPS API and signature before code generation emits a concrete API call.

## CustomerReq without Script reference

If CustomerReq defines behavior and an implementation method but GitNexus finds no full Script reference:
- use CustomerReq as behavior source and implementation plan;
- query GitNexus for primitive APIs;
- mark `NEW_IMPLEMENTATION_NO_SCRIPT_REFERENCE`;
- require human review;
- if primitive API grounding is missing, emit `TODO_REVIEW` instead of fabricating API calls.

## Units

All LBA and transfer length fields are interpreted as 4K blocks unless the source explicitly states otherwise.
