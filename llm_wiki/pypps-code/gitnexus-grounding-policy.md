---
title: GitNexus Grounding Policy for PyPPS Code
source_type: PyppsCode
source_path: llm_wiki/pypps-code/gitnexus-grounding-policy.md
source_section: code-grounding
source_hash: manual
priority: 70
authority: code-reference
confidence: high
applies_to:
  tc_ids: []
  features: [pypps, ufs]
  operations: [generation, api-grounding, code-reference]
  commands: []
  flags: []
  attributes: []
claim_types:
  - implementation-rule
  - code-style
---

# GitNexus Grounding Policy for PyPPS Code

LLM Wiki does not duplicate the PyPPS codebase. Use GitNexus for:
- exact primitive API names and signatures;
- import paths;
- existing Pattern examples;
- call graph and symbol context;
- impact analysis when modifying code.

Recommended query behavior:
- Always specify the target repo name when known, for example `-r Pypps`.
- Record GitNexus repo, query string, returned symbol/file, and relevance scores in retrieval artifacts.
- Treat GitNexus API grounding as required before emitting non-TODO concrete PyPPS API calls.

If LLM Wiki and GitNexus disagree:
- Wiki governs knowledge/source behavior according to source policy.
- GitNexus governs whether a concrete API exists and how to call it.
