---
title: UFS Query Interface
source_type: Spec
source_path: docx/Spec/chapters/27_1099_query_function_transport_protocol_services.md
source_section: "10.9.9 Query Function Transport Protocol Services"
source_hash: sha256:a49fc842208380ccc479c7ac87d3ed9aa95a1d6f41c59581ac8729c2959f9c12
priority: 60
authority: protocol-reference
confidence: high
applies_to:
  tc_ids: [PF010_0310]
  features: [ufs-query, write-booster]
  operations: [query, read-flag, set-flag, clear-flag, read-attribute, write-attribute]
  commands: []
  flags: [fWriteBoosterSupport, fWriteBoosterEnable, fWriteBoosterBufferFlushEn]
  attributes: [dLUNumWriteBoosterBufferAllocUnits]
claim_types:
  - protocol-semantics
  - command-field
---

# UFS Query Interface

UFS Query Function is used to get or set UFS-specific device-level registers and parameters that are not part of the SCSI definition.

The Query Request service includes:
- Operation: read or write operation encoding.
- Type: UFS-defined or vendor-specific.
- Identifier: descriptor, attribute, or flag identifier.
- Length, Index, Selector, and optional WriteData.

For Pattern generation:
- Use Query for `READ FLAG`, `SET FLAG`, `CLEAR FLAG`, `READ ATTRIBUTE`, and `WRITE ATTRIBUTE` steps.
- This page validates that Query is the protocol mechanism, not the PyPPS API name.
- GitNexus must still confirm the concrete PyPPS primitive API and signature.

PF010_0310 relevant operations:
- Read `fWriteBoosterSupport`.
- Set/Clear/Read `fWriteBoosterEnable`.
- Set/Read `fWriteBoosterBufferFlushEn`.
- Read/Write `dLUNumWriteBoosterBufferAllocUnits`.
