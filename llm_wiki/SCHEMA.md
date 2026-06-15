---
title: LLM Wiki Schema
source_type: GenerationPolicy
source_path: llm_wiki/SCHEMA.md
source_section: schema
source_hash: manual
priority: 100
authority: policy
confidence: high
applies_to:
  tc_ids: []
  features: []
  operations: [generation, retrieval, validation]
  commands: []
  flags: []
  attributes: []
claim_types:
  - implementation-rule
  - code-style
---

# LLM Wiki Schema

Every page must start with YAML frontmatter. Required fields:

```yaml
title: string
source_type: CustomerReq | Spec | UserPrompt | ModelDefault | PropNoun | Script | GenerationPolicy | PyppsCode
source_path: string
source_section: string
source_hash: sha256:...
priority: number
authority: customer-requirement | protocol-reference | user-rule | fallback | terminology | code-reference | policy
confidence: low | medium | high
applies_to:
  tc_ids: []
  features: []
  operations: []
  commands: []
  flags: []
  attributes: []
claim_types: []
```

Optional fields:

```yaml
status: active | proposed | deprecated
default_origin: auto_generated | auto_proposed | user_reviewed | manual_seed
fallback_only: true | false
requires_recording: true | false
requires_approval: true | false
category: HARD_DEFAULT | SOFT_ASSUMPTION | BLOCKER
generation_policy:
  allow_new_implementation: true | false
  require_gitnexus_primitive_grounding: true | false
  require_human_review_if_no_script_reference: true | false
```

Allowed `claim_types`:
- customer-requirement
- protocol-semantics
- expected-behavior
- implementation-method
- implementation-rule
- command-field
- fallback-default
- terminology
- code-style

Required retriever behavior:
1. Copy page frontmatter into every chunk metadata.
2. Store `page_path`, `chunk_id`, `source_type`, `priority`, `authority`, `claim_types`, `applies_to`, and `source_hash` per chunk.
3. BM25/dense/RRF scores are relevance only and must not override source governance.
