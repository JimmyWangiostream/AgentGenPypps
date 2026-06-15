---
title: UFS WriteBooster Flags
source_type: Spec
source_path: docx/Spec/chapters/69_142_flags.md
source_section: "14.2 Flags / Table 14.26"
source_hash: sha256:83e76b49724492c61a7017829becfde101172db821dcaacdaeb971d1250571a2
priority: 60
authority: protocol-reference
confidence: high
applies_to:
  tc_ids: [PF010_0310]
  features: [write-booster]
  operations: [query, reset, read-flag, set-flag, clear-flag]
  commands: []
  flags: [fWriteBoosterEn, fWriteBoosterEnable, fWriteBoosterBufferFlushEn, fWriteBoosterBufferFlushDuringHibernate]
  attributes: []
claim_types:
  - protocol-semantics
  - command-field
  - expected-behavior
---

# UFS WriteBooster Flags

Spec source states that a flag is a Boolean value that can be read and, depending on its access properties, written through set/clear/toggle operations.

Relevant WriteBooster flags from the Spec source:

| IDN in source | Name in source | Type | Default | Meaning |
|---|---|---|---|---|
| 0Eh | fWriteBoosterEn | Read / Volatile | 0 | WriteBooster Enable: 0 means disabled, 1 means enabled. |
| 0Fh | fWriteBoosterBufferFlushEn | Read / Volatile | 0 | Flush data in WriteBooster Buffer to user area. |
| 10h | fWriteBoosterBufferFlushDuringHibernate | Read / Volatile | 0 | Allow flush during link hibernate state. |

TC PF010_0310 uses names `fWriteBoosterEnable` and `fWriteBoosterBufferFlushEn`. Treat `fWriteBoosterEnable` as the TC naming for the WriteBooster enable flag; use PropNoun / Spec normalization and GitNexus constants to confirm the concrete code symbol.

Protocol implication:
- Volatile flags are set to default after power cycle or reset events according to access-property rules.
- Expected post-reset behavior must be resolved through TC and CustomerReq first; Spec remains validation baseline when no CustomerReq exists.
