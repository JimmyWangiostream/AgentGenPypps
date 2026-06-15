---
title: Source Priority and Decision Paths
source_type: GenerationPolicy
source_path: llm_wiki/SOURCE_PRIORITY.md
source_section: source-governance
source_hash: manual
priority: 100
authority: policy
confidence: high
applies_to:
  operations: [generation, source-resolution]
  tc_ids: []
  features: []
  commands: []
  flags: []
  attributes: []
claim_types:
  - implementation-rule
---

# Source Priority and Decision Paths

Default metadata priority:

| source_type | priority |
|---|---:|
| UserPrompt | 100 |
| TC | 95 |
| CustomerReq | 90 |
| Script/GitNexus | 70 |
| Spec | 60 |
| PropNoun | 40 |
| ModelDefault | 30 |

Do not use this as one flat priority list for every decision. Use the decision paths below.

## Expected behavior / test intent

Use for expected responses, post-reset state, pass/fail criteria, and customer/project behavior:

1. UserPrompt only when it explicitly clarifies or overrides this TC.
2. TC explicit test intent.
3. CustomerReq customer/project-specific behavior.
4. Spec protocol baseline when no relevant CustomerReq exists.
5. ModelDefault fallback only, recorded.

CustomerReq may govern project expected behavior over Spec. Spec remains the protocol validation source.

## Implementation detail / generation choice

Use for loop count, LUN selection, random seed, reset coverage strategy, LBA allocation, helper/API selection, and code style:

1. TC explicit implementation detail.
2. UserPrompt rule if TC is missing that detail.
3. CustomerReq `implementation-method`, if relevant.
4. Script/GitNexus existing Pattern or primitive API grounding.
5. Project coding convention.
6. ModelDefault fallback, recorded.
7. If none exists, emit `BLOCKER` or `TODO_REVIEW`.

UserPrompt fills missing implementation details by default. UserPrompt only overrides explicit TC behavior when it explicitly declares override intent.

## Protocol validation

Spec is always used for protocol legality validation, even if TC/UserPrompt/CustomerReq governs the generated behavior or implementation.
