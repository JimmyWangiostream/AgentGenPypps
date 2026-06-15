---
title: SCSI Basic Commands for PF010_0310
source_type: Spec
source_path: TC/PF010_0310-Normalize.md
source_section: "TC appendices and normalized steps referencing UFS/SCSI Spec"
source_hash: sha256:a66971c8216235bed2ceacc11a7157ea4ee60291172d63203c5d46ad31de7c6a
priority: 60
authority: protocol-reference
confidence: medium
applies_to:
  tc_ids: [PF010_0310]
  features: [device-readiness, capacity, ffu]
  operations: [test-unit-ready, read-capacity, write-buffer]
  commands: [TEST_UNIT_READY, READ_CAPACITY_10, WRITE_BUFFER]
  flags: []
  attributes: []
claim_types:
  - protocol-semantics
  - command-field
---

# SCSI Basic Commands for PF010_0310

This page captures TC-referenced SCSI commands whose detailed Spec pages may be indexed separately.

PF010_0310 commands:
- `TEST UNIT READY (00h)`: used to confirm device readiness and FFU completion.
- `READ CAPACITY(10) (25h)`: used to obtain maximum LBA and logical block length.
- `WRITE BUFFER (2Bh)`: used for FFU download/save flow.

Generation usage:
- Treat this page as a medium-confidence protocol summary derived from normalized TC references.
- Prefer more specific Spec pages if retrieved.
- Use GitNexus to confirm actual PyPPS primitive APIs.
