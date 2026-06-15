---
title: UFS Proper Nouns and Abbreviations
source_type: PropNoun
source_path: docx/PropNoun/proper_nouns.md
source_section: "專有名詞與定義"
source_hash: sha256:245d902e31b0c67ec2d12e4e6496f52f892068405834b4e842e14b7f0df43243
priority: 40
authority: terminology
confidence: high
applies_to:
  tc_ids: []
  features: [ufs, write-booster, power-management, background-operations]
  operations: [terminology-expansion]
  commands: []
  flags: []
  attributes: []
claim_types:
  - terminology
---

# UFS Proper Nouns and Abbreviations

Use this page to expand TC/log terms during retrieval and parsing.

Important terms:
- UFS: Universal Flash Storage.
- GC: Garbage Collection.
- FTL: Flash Translation Layer.
- WL: Wear Leveling.
- LUN: Logical Unit Number.
- BKOPS: Background Operations.
- H8 / Hibern8: UFS Link Hibernate power-saving state.
- UIC: UFS Interconnect Command.
- PA: Physical Adapter.
- DL: Data Link Layer.
- NAND: physical flash memory.
- SLC / MLC / TLC: NAND cell types.
- WB: Write Booster.
- Flush: request to write cached data to NAND.
- QD: Queue Depth.
- Link Startup: UFS host/device link establishment flow.
- Power Mode Change: UFS performance or power-state transition.
- DCMD: SDK packaged command flow used for UFS debug/test/stress validation.

Generation usage:
- Expand `WB` to `Write Booster`.
- Expand `SSU + all reset` queries with reset, power management, START STOP UNIT, POR, and LINKSTARTUP.
- Use terms only for retrieval and normalization; terminology pages do not govern expected behavior.
