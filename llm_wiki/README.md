---
title: LLM Wiki for AgentGeneratePypps
source_type: GenerationPolicy
source_path: llm_wiki/README.md
source_section: overview
source_hash: manual
priority: 100
authority: policy
confidence: high
applies_to:
  tc_ids: []
  features: [ufs, pypps, pattern-generation]
  operations: [generation, retrieval, validation]
  commands: []
  flags: []
  attributes: []
claim_types:
  - implementation-rule
---

# LLM Wiki for AgentGeneratePypps

Generated at: 2026-06-14T23:48:37+08:00

Purpose: source-governed knowledge base for generating UFS/PyPPS Pattern `.py` files from TC markdown flows.

This wiki separates knowledge by source type. Retrieval scores (BM25/dense/RRF) only indicate relevance; final decisions must be made by the decision layer using `source_type`, `claim_types`, `authority`, and TC explicitness.

Directories:
- `spec/`: protocol reference and legality validation.
- `user-prompt/`: user rules that fill missing implementation details.
- `prop-noun/`: terminology expansion and normalization.
- `model-default/`: fallback catalog with `auto`, `reviewed`, `proposed`, and `blockers` tracks.
- `generation-policy/`: decision and traceability rules.
- `customer-req/`: CustomerReq pages. Currently scaffolded because no CustomerReq source file was found during this build.
- `pypps-code/`: stable code-writing conventions and GitNexus integration notes, not a copy of the codebase.

Index artifacts are under `.pattern_kb/index/`.
