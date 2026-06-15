---
title: UFS WriteBooster Attributes
source_type: Spec
source_path: docx/Spec/chapters/70_143_attributes.md
source_section: "14.3 Attributes / Table 14.28"
source_hash: sha256:1d342f410b14f8bce6edbf84ba3704ff5aad1e98504a84285e5c32609030c940
priority: 60
authority: protocol-reference
confidence: high
applies_to:
  tc_ids: [PF010_0310]
  features: [write-booster]
  operations: [query, read-attribute, write-attribute, buffer-allocation]
  commands: []
  flags: []
  attributes: [dLUNumWriteBoosterBufferAllocUnits, bWriteBoosterBufferFlushStatus, bAvailableWriteBoosterBufferSize, dCurrentWriteBoosterBufferSize]
claim_types:
  - protocol-semantics
  - command-field
---

# UFS WriteBooster Attributes

Spec source defines Attributes as numeric parameters that can be read or written, with access properties such as persistent, volatile, read-only, and write-only.

PF010_0310 relevant attribute concept:
- `dLUNumWriteBoosterBufferAllocUnits`: TC uses this to configure maximum WriteBooster buffer allocation units.

Related WriteBooster attributes present in the Spec source include:
- `bWriteBoosterBufferFlushStatus`: reports WriteBooster buffer flush operation state.
- `bAvailableWriteBoosterBufferSize`: reports available WriteBooster buffer size in 10% granularity.
- `dCurrentWriteBoosterBufferSize`: reports current WriteBooster buffer size in allocation units.

Generation usage:
- Use this page to validate that a step involving WriteBooster buffer allocation or status is an Attribute Query operation.
- Use GitNexus to confirm the concrete PyPPS API, IDN constants, index/selector, and write-data representation.
