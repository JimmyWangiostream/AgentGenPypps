# PF010_0310-Normalize Flow-Scoped Retrieval Report

Generated at: 2026-06-14T18:46:47.326608+00:00

## TC Source
- `TC/PF010_0310-Normalize.md`

## Generation Granularity

This report was regenerated with flow-scoped retrieval and stateful flow-level generation. Retrieval may happen per flow/action group, but code is generated per ordered flow so variables such as `write_record`, `reset_type`, `expected`, selected LUN, and flag state are not detached from their producer steps.

Dense backend: `persistent:sentence-transformer`
Embedding index: `.pattern_kb/index/embeddings/sentence-transformers--all-MiniLM-L6-v2`


## Flow 0: Write Booster setup / preconditions

- TC steps: `0.1-0.4`
- Generated method: `step1`
- Decision summary: Support check produces wb_support; dLUNumWriteBoosterBufferAllocUnits remains TODO_REVIEW because PyPPS enum mapping is unsafe.

### Ordered Step / State Dependencies

| Producer | Consumer | Variable / State | Reason |
|---|---|---|---|
| pre_process | Flow 0+ | `test_lun`, `write_record`, transfer block range | Global context for all W/R flows. |
| Step 0.2 | Flow 1/2 | `lba_range` | WRITE/READ uses 0..MAX_LBA. |
| Step 0.3 | Flow 1/2/3 | `wb_support` | Skip/non-support decision. |


### Knowledge References (LLM Wiki)

| Rank | Chunk | Source Type | BM25 | Dense | RRF | Role | Reason |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `llm_wiki/spec/ufs-writebooster-attributes.md#chunk-002` | Spec | 53.08940303 | 0.52007652 | 0.03252247 | validation | setup/support/allocation grounding |
| 2 | `llm_wiki/spec/ufs-writebooster-flags.md#chunk-002` | Spec | 42.08743029 | 0.48749236 | 0.03200205 | validation | setup/support/allocation grounding |
| 3 | `llm_wiki/spec/ufs-query-interface.md#chunk-002` | Spec | 57.72583849 | 0.31610418 | 0.03154496 | validation | setup/support/allocation grounding |
| 4 | `llm_wiki/spec/scsi-basic-commands.md#chunk-002` | Spec | 34.96097639 | 0.43472067 | 0.03149802 | validation | setup/support/allocation grounding |
| 5 | `llm_wiki/spec/ufs-reset-and-start-stop-unit.md#chunk-002` | Spec | 25.46099931 | 0.41787912 | 0.03100962 | validation | setup/support/allocation grounding |
| 6 | `llm_wiki/spec/scsi-write-read-10.md#chunk-002` | Spec | 22.96647091 | 0.36018416 | 0.03053613 | validation | setup/support/allocation grounding |
| 7 | `llm_wiki/prop-noun/ufs-proper-nouns.md#chunk-002` | PropNoun | 17.18492852 | 0.29846755 | 0.02963126 | terminology | setup/support/allocation grounding |
| 8 | `llm_wiki/model-default/auto/default-random-seed-policy.md#chunk-002` | ModelDefault | 10.99140297 | 0.27849884 | 0.02837022 | fallback | setup/support/allocation grounding |

Retriever command used:

```bash
PF010_0310 Phase 0 Write Booster initialization TEST UNIT READY READ CAPACITY READ FLAG fWriteBoosterSupport WRITE ATTRIBUTE dLUNumWriteBoosterBufferAllocUnits max allocation
```


## Flow X: FFU burn-in checkpoint

- TC steps: `X.1-X.3`
- Generated method: `_maybe_ffu_flow_checkpoint`
- Decision summary: Disabled TODO_REVIEW placeholder; TC lacks FW path/version/trigger and reviewed WRITE BUFFER implementation details.

### Ordered Step / State Dependencies

| Producer | Consumer | Variable / State | Reason |
|---|---|---|---|
| TC Phase X | _maybe_ffu_flow_checkpoint | `enable_ffu_flow` | Disabled unless user supplies FW path/version/trigger. |


### Knowledge References (LLM Wiki)

| Rank | Chunk | Source Type | BM25 | Dense | RRF | Role | Reason |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `llm_wiki/spec/scsi-basic-commands.md#chunk-002` | Spec | 33.78996398 | 0.42067035 | 0.03278689 | validation | FFU/basic command or missing-policy context |
| 2 | `llm_wiki/spec/ufs-reset-and-start-stop-unit.md#chunk-002` | Spec | 11.68927166 | 0.34501446 | 0.03200205 | validation | FFU/basic command or missing-policy context |
| 3 | `llm_wiki/spec/ufs-writebooster-attributes.md#chunk-002` | Spec | 11.94126307 | 0.31363867 | 0.03175403 | validation | FFU/basic command or missing-policy context |
| 4 | `llm_wiki/spec/ufs-writebooster-flags.md#chunk-002` | Spec | 10.75838354 | 0.31716187 | 0.03149802 | validation | FFU/basic command or missing-policy context |
| 5 | `llm_wiki/prop-noun/ufs-proper-nouns.md#chunk-002` | PropNoun | 9.31162823 | 0.25672499 | 0.03009050 | terminology | FFU/basic command or missing-policy context |
| 6 | `llm_wiki/spec/scsi-write-read-10.md#chunk-002` | Spec | 6.13701003 | 0.27152587 | 0.03009050 | validation | FFU/basic command or missing-policy context |
| 7 | `llm_wiki/user-prompt/default-lun-selection.md#chunk-002` | UserPrompt | 6.71708837 | 0.25834023 | 0.02985075 | validation | FFU/basic command or missing-policy context |
| 8 | `llm_wiki/spec/ufs-query-interface.md#chunk-002` | Spec | 9.12692259 | 0.22100929 | 0.02943723 | validation | FFU/basic command or missing-policy context |

Retriever command used:

```bash
PF010_0310 Phase X FFU burn-in WRITE BUFFER FFU mode TEST UNIT READY firmware update conditional flow
```


## Flow 1: WriteBooster enable + W/R + reset

- TC steps: `1.1-1.5`
- Generated method: `step2`
- Decision summary: Generated as one stateful flow: reset_type drives both _do_reset() and expected flag value.

### Ordered Step / State Dependencies

| Producer | Consumer | Variable / State | Reason |
|---|---|---|---|
| Step 1.1 SET FLAG | Step 1.2/1.5 | `wb_enable_state=1` | WB-enabled W/R and post-reset flag check. |
| Step 1.2 random_write | Step 1.3 compare | `write_record` | READ compare must use the same written ranges/data. |
| Step 1.4 reset loop | Step 1.5 expected | `reset_type` | Expected flag value is derived from the exact reset primitive. |


### Knowledge References (LLM Wiki)

| Rank | Chunk | Source Type | BM25 | Dense | RRF | Role | Reason |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `llm_wiki/spec/ufs-writebooster-flags.md#chunk-002` | Spec | 39.35008513 | 0.47573873 | 0.03252247 | validation | enable/reset expected-state grounding |
| 2 | `llm_wiki/spec/ufs-reset-and-start-stop-unit.md#chunk-002` | Spec | 29.55390278 | 0.51854114 | 0.03226646 | validation | enable/reset expected-state grounding |
| 3 | `llm_wiki/spec/ufs-query-interface.md#chunk-002` | Spec | 34.05979550 | 0.31245567 | 0.03105441 | validation | enable/reset expected-state grounding |
| 4 | `llm_wiki/spec/scsi-write-read-10.md#chunk-002` | Spec | 25.65245378 | 0.38695919 | 0.03100962 | validation | enable/reset expected-state grounding |
| 5 | `llm_wiki/spec/ufs-writebooster-attributes.md#chunk-002` | Spec | 15.22185512 | 0.45184503 | 0.03079839 | validation | enable/reset expected-state grounding |
| 6 | `llm_wiki/spec/scsi-basic-commands.md#chunk-002` | Spec | 9.57965342 | 0.41114785 | 0.03033088 | validation | enable/reset expected-state grounding |
| 7 | `llm_wiki/prop-noun/ufs-proper-nouns.md#chunk-002` | PropNoun | 17.48816516 | 0.29126892 | 0.02987737 | terminology | enable/reset expected-state grounding |
| 8 | `llm_wiki/model-default/auto/default-random-seed-policy.md#chunk-002` | ModelDefault | 4.12563382 | 0.30776686 | 0.02840451 | fallback | enable/reset expected-state grounding |

Retriever command used:

```bash
PF010_0310 Phase 1 Write Booster Enable SET FLAG fWriteBoosterEnable WRITE10 READ10 compare SSU POR LINKSTARTUP reset expected flag
```


## Flow 2: WriteBooster disable + W/R + reset

- TC steps: `2.1-2.5`
- Generated method: `step3`
- Decision summary: CLEAR FLAG state and write_record data dependency are preserved in one flow method.

### Ordered Step / State Dependencies

| Producer | Consumer | Variable / State | Reason |
|---|---|---|---|
| Step 2.1 random_write | Step 2.3 random_read | `write_record` | READ compare consumes data written in the same flow. |
| Step 2.2 CLEAR FLAG | Step 2.5 expected | `wb_enable_state=0` | Expected flag remains disabled after each reset. |
| Step 2.4 reset loop | Step 2.5 expected/read compare | `reset_type` | Reset primitive and post-reset checks stay coupled. |


### Knowledge References (LLM Wiki)

| Rank | Chunk | Source Type | BM25 | Dense | RRF | Role | Reason |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `llm_wiki/spec/ufs-writebooster-flags.md#chunk-002` | Spec | 32.75155897 | 0.44914582 | 0.03252247 | validation | disable/read-compare/reset grounding |
| 2 | `llm_wiki/spec/ufs-reset-and-start-stop-unit.md#chunk-002` | Spec | 27.36195974 | 0.49850789 | 0.03201844 | validation | disable/read-compare/reset grounding |
| 3 | `llm_wiki/spec/scsi-write-read-10.md#chunk-002` | Spec | 27.88392466 | 0.37705240 | 0.03125763 | validation | disable/read-compare/reset grounding |
| 4 | `llm_wiki/spec/ufs-query-interface.md#chunk-002` | Spec | 28.16569714 | 0.28768775 | 0.03105441 | validation | disable/read-compare/reset grounding |
| 5 | `llm_wiki/spec/ufs-writebooster-attributes.md#chunk-002` | Spec | 15.22185512 | 0.43391855 | 0.03102453 | validation | disable/read-compare/reset grounding |
| 6 | `llm_wiki/spec/scsi-basic-commands.md#chunk-002` | Spec | 10.99895571 | 0.39802764 | 0.03033088 | validation | disable/read-compare/reset grounding |
| 7 | `llm_wiki/prop-noun/ufs-proper-nouns.md#chunk-002` | PropNoun | 17.48816516 | 0.26997676 | 0.02987737 | terminology | disable/read-compare/reset grounding |
| 8 | `llm_wiki/model-default/auto/default-reset-coverage-policy.md#chunk-002` | ModelDefault | 3.16710934 | 0.34386185 | 0.02866503 | fallback | disable/read-compare/reset grounding |

Retriever command used:

```bash
PF010_0310 Phase 2 Clear Flag fWriteBoosterEnable disable Write Booster WRITE10 READ10 compare SSU POR LINKSTARTUP reset expected zero
```


## Flow 3: Flush enable + reset

- TC steps: `3.1-3.3`
- Generated method: `step4`
- Decision summary: Flush flag set/reset/read expected value is generated as one flow unit.

### Ordered Step / State Dependencies

| Producer | Consumer | Variable / State | Reason |
|---|---|---|---|
| Step 3.1 SET FLAG | Step 3.3 expected | `flush_enable_state=1` | Pre-reset state for flush flag. |
| Step 3.2 reset loop | Step 3.3 expected | `reset_type` | Expected flush flag value depends on reset primitive. |


### Knowledge References (LLM Wiki)

| Rank | Chunk | Source Type | BM25 | Dense | RRF | Role | Reason |
|---:|---|---|---:|---:|---:|---|---|
| 1 | `llm_wiki/spec/ufs-writebooster-flags.md#chunk-002` | Spec | 47.04568191 | 0.38197194 | 0.03252247 | validation | flush-enable/reset expected-state grounding |
| 2 | `llm_wiki/spec/ufs-reset-and-start-stop-unit.md#chunk-002` | Spec | 30.17426804 | 0.43620456 | 0.03226646 | validation | flush-enable/reset expected-state grounding |
| 3 | `llm_wiki/spec/ufs-query-interface.md#chunk-002` | Spec | 39.52778592 | 0.27179287 | 0.03128055 | validation | flush-enable/reset expected-state grounding |
| 4 | `llm_wiki/spec/ufs-writebooster-attributes.md#chunk-002` | Spec | 23.96054091 | 0.35248493 | 0.03125000 | validation | flush-enable/reset expected-state grounding |
| 5 | `llm_wiki/spec/scsi-basic-commands.md#chunk-002` | Spec | 13.08350178 | 0.37653895 | 0.03079839 | validation | flush-enable/reset expected-state grounding |
| 6 | `llm_wiki/spec/scsi-write-read-10.md#chunk-002` | Spec | 15.50984718 | 0.24766915 | 0.03007689 | validation | flush-enable/reset expected-state grounding |
| 7 | `llm_wiki/prop-noun/ufs-proper-nouns.md#chunk-002` | PropNoun | 19.28873848 | 0.21083500 | 0.02967033 | terminology | flush-enable/reset expected-state grounding |
| 8 | `llm_wiki/model-default/auto/default-reset-coverage-policy.md#chunk-002` | ModelDefault | 3.16710934 | 0.27423412 | 0.02854251 | fallback | flush-enable/reset expected-state grounding |

Retriever command used:

```bash
PF010_0310 Phase 3 SET FLAG fWriteBoosterBufferFlushEn flush enable SSU POR LINKSTARTUP reset READ FLAG expected state
```


## Code References (PyPPS /home/weikai/Script)
| Reference | Lines | Flow(s) | Role | Reason |
|---|---:|---|---|---|
| `/home/weikai/Script/pattern/pattern_template.py` | 1-220 | all | governing | `UFSTC` pattern lifecycle; numbered `step*` methods run in order. |
| `/home/weikai/Script/pattern/sample_code/read_attr_flag_sample.py` | 12-44 | flow_0/1/2/3 | governing | Query examples for ReadAttribute, SetFlag, ReadFlag, ClearFlag. |
| `/home/weikai/Script/api/ufs_api/attr_flag_functions.py` | 64-149 | flow_0/1/2/3 | governing | Exact helper behavior for `read_attribute`, `write_attribute`, `read_flag`, `set_flag`, `clear_flag`. |
| `/home/weikai/Script/pattern/sample_code/normal_rw_sample.py` | 22-47 | flow_1/2 | governing | Grounded `get_empty_write_record`, `random_write`, `random_read` usage. |
| `/home/weikai/Script/api/ufs_api/rw_functions.py` | 44-168 | flow_1/2 | governing | Exact random write/read compare signatures and `write_record` dependency. |
| `/home/weikai/Script/api/ufs_api/defines/enum_define.py` | 133-176 | flow_0/1/2/3 | validation | Verified local FlagIDN/AttributeIDN names; found IDN gaps. |
| `/home/weikai/Script/api/cmd_seq/cmds.py` | 266-274 | flow_1/2/3 | governing | `ExecuteCMD.StartStopUnit` wrapper. |
| `/home/weikai/Script/api/ufs_api/upiu/upiu.py` | 266-282 | flow_1/2/3 | governing | Exact `StartStopUnit.assign(lun, immed, power_condition, no_flush, start)` signature. |
| `/home/weikai/Script/api/ufs_api/initial_device.py` | 69-109 | flow_1/2/3 | governing | `api.init_tester_to_unit_ready(resetmode, powerdown, ...)` reset helper. |
| `/home/weikai/Script/api/ufs_api/debug_cmd/dcmd_enum.py` | 51-56 | flow_1/2/3 | validation | Verified `HW_RESET`, `ENDPOINT_RESET`, `UNIPRO_RESET`; no explicit LINKSTARTUP_RESET. |

## Decision Notes
- One TC still maps to one Pattern folder and one Pattern `.py`.
- Generation granularity is now flow-level, not whole-TC and not isolated step snippets.
- Retrieval is flow-scoped; code generation preserves ordered steps and data/state dependencies inside each flow method.
- `write_record` is treated as a global data dependency produced during random write and consumed during read/compare.
- `reset_type` is not detached from expected-value logic; it is produced by the reset loop and immediately consumed by `_expected_volatile_flag_after_reset()` and `_expect_flag()`.
- Flow X / FFU is explicitly represented as disabled TODO_REVIEW because TC lacks firmware path/version/trigger policy.
- `dLUNumWriteBoosterBufferAllocUnits`, `fWriteBoosterSupport`, and `LINKSTARTUP` remain TODO_REVIEW rather than hidden assumptions.
