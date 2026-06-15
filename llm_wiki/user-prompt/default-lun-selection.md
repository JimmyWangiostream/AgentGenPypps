---
title: Default Test LUN Selection from UserPrompt
source_type: UserPrompt
source_path: docx/UserPrompt/user_prompt.md
source_section: "未指定時參照 / LUN"
source_hash: sha256:eaff871dc4e8263d247c997663f92b0b376620c9a493e7e2e08995c036ac5904
priority: 100
authority: user-rule
confidence: high
applies_to:
  tc_ids: []
  features: []
  operations: [write, read, compare, capacity-selection]
  commands: [WRITE_10, READ_10, READ_CAPACITY_10]
  flags: []
  attributes: []
claim_types:
  - implementation-rule
---

# Default Test LUN Selection from UserPrompt

When the TC does not specify the detailed LUN selection flow, use the UserPrompt rule:

- Select the enabled LUN with maximum capacity.

Decision use:
- This fills missing implementation detail.
- It does not override explicit TC LUN selection.
- Because this is UserPrompt, it is preferred over ModelDefault for LUN selection.
