---
title: SCSI WRITE(10) and READ(10) Data Transfer
source_type: Spec
source_path: docx/Spec/chapters/39_11315_write_10_command.md
source_section: "11.3.15 WRITE (10) Command"
source_hash: sha256:fa29398d2a786d087f9b908e23a298593d9a1640599e3e52db55566e395f59be
priority: 60
authority: protocol-reference
confidence: high
applies_to:
  tc_ids: [PF010_0310]
  features: [write-booster, data-compare]
  operations: [write, read, compare]
  commands: [WRITE_10, READ_10]
  flags: []
  attributes: []
claim_types:
  - protocol-semantics
  - command-field
  - expected-behavior
---

# SCSI WRITE(10) and READ(10) Data Transfer

WRITE(10) requests that the device server transfer the specified number of logical blocks from the application client and write them to the medium. The CDB includes:
- operation code `2Ah`;
- Logical Block Address;
- Transfer Length;
- FUA and related control bits.

Spec behavior from source:
- Transfer Length is the number of contiguous logical blocks to write.
- A successful WRITE command terminates with GOOD status.
- If data goes through cache, GOOD may occur before media write completion unless FUA or other rules force media completion.

PF010_0310 uses WRITE(10), READ(10), and compare as the data integrity check around WriteBooster enable/disable and reset flows.

Generation usage:
- Use TC for exact LBA range and transfer length if explicit.
- If TC says random range/size, implementation detail may need UserPrompt or ModelDefault.
- Use GitNexus to confirm PyPPS `Write10`, `Read10`, write-record, and compare APIs.
