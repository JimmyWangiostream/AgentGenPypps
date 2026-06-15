---
title: ModelDefault Two-Mode Policy
source_type: GenerationPolicy
source_path: llm_wiki/generation-policy/model-default-policy.md
source_section: model-default-policy
source_hash: manual
priority: 100
authority: policy
confidence: high
applies_to:
  operations: [generation, fallback, assumption-logging]
  tc_ids: []
  features: []
  commands: []
  flags: []
  attributes: []
claim_types:
  - implementation-rule
  - fallback-default
---

# ModelDefault Two-Mode Policy

The generator supports two ModelDefault modes.

## mode: auto_accept

When a new fallbackable implementation detail is missing:
- automatically create a ModelDefault page under `llm_wiki/model-default/auto/`;
- set `status: active`;
- set `default_origin: auto_generated`;
- allow use in the current generation;
- record every use in `assumptions.md` and `validation.json`.

## mode: review_required

When a new fallbackable implementation detail is missing:
- automatically create a proposed page under `llm_wiki/model-default/proposed/`;
- set `status: proposed`;
- set `default_origin: auto_proposed`;
- ask the user to approve/edit/reject;
- do not use the proposed default unless the run config explicitly permits temporary use.

## Category policy

| category | auto_accept | review_required |
|---|---|---|
| HARD_DEFAULT | auto active and usable | may auto active if behavior-neutral |
| SOFT_ASSUMPTION | auto active and usable, but warn | proposed and ask |
| BLOCKER | record rule only; never fill value | record rule only; ask or block |

Safety invariant: no mode may use ModelDefault to invent command identity, protocol-critical fields, or expected behavior that defines the core test intent.
