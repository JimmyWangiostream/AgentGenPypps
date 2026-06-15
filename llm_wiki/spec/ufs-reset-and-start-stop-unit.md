---
title: UFS Reset and START STOP UNIT Power Modes
source_type: Spec
source_path: docx/Spec/chapters/07_7_reset_power-up_and_power-down.md
source_section: "7 Reset, Power-Up And Power-Down / 7.4.2 START STOP UNIT"
source_hash: sha256:37ae368b262d687d196a62db11d36b7433b3f99f75750df08a2e64491db2a436
priority: 60
authority: protocol-reference
confidence: high
applies_to:
  tc_ids: [PF010_0310]
  features: [power-management, reset, write-booster]
  operations: [reset, ssu, powerdown, active, linkstartup]
  commands: [START_STOP_UNIT]
  flags: [fWriteBoosterEnable, fWriteBoosterBufferFlushEn]
  attributes: [bCurrentPowerMode, bInitPowerMode]
claim_types:
  - protocol-semantics
  - command-field
  - expected-behavior
---

# UFS Reset and START STOP UNIT Power Modes

Spec source defines reset types and the behavior of volatile flags/attributes across reset events. Reset summary includes Power-on, HW Reset, EndPointReset, LU Reset, and Host UniPro Warm Reset.

Important validation facts:
- Power-on, HW Reset, EndPointReset, and Host UniPro Warm Reset reset volatile flags/attributes.
- LU Reset does not reset volatile flags/attributes and maintains current power mode.
- Persistent and write-once attributes/flags are kept after power cycle or reset events.

START STOP UNIT:
- Operation code: `1Bh`.
- When sent to the UFS Device well-known logical unit, it selects device power mode.
- `POWER CONDITION = 1h` causes transition to Active.
- `POWER CONDITION = 2h` causes transition to UFS-Sleep.
- `POWER CONDITION = 3h` causes transition to UFS-PowerDown.
- `NO_FLUSH = 0` means dynamic data should be flushed to non-volatile storage.
- `NO_FLUSH = 1` means no requirements regarding dynamic data.

PF010_0310 uses SSU/POR/LINKSTARTUP style reset coverage around WriteBooster operations. Use TC/UserPrompt/CustomerReq to determine which reset types to execute and Spec to validate legality and post-reset volatility.
