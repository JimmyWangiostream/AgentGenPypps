# PF010_0310 / UFS PyPPS Pattern Generation 詳細流程說明

本文說明目前 AgentGeneratePypps 產生 Pattern 的完整設計：從 TC markdown 解析成 IR，到 LLM Wiki retrieval、GitNexus / PyPPS code grounding、LLM model 決策、Pattern code 產生，以及 artifacts / validation 的順序與交互作用。

對應範例：

```text
TC/PF010_0310-Normalize.md
  -> generated/PF010_0310-Normalize/PF010_0310_Normalize.py
```

核心原則：

```text
一個 TC -> 一個 Pattern folder + 一個 Pattern .py
一個 flow/phase -> 一個 stateful generation unit
flow 內 steps 保持順序、state、變數依賴
retrieval 可以 per flow / per action group，但 code generation 不能 per step isolated
```

---

## 1. 整體角色分工

Pattern generation 裡有四個主要資訊來源 / 角色：

```text
1. TC markdown
   決定 WHAT to test。
   例如測什麼 flag、什麼 reset、什麼 expected result。

2. LLM Wiki
   提供 domain/spec/customer/model-default knowledge。
   例如 UFS Query、WriteBooster flag behavior、reset baseline、default policy。

3. GitNexus / PyPPS codebase
   提供 HOW to write PyPPS code。
   例如 api.read_flag() signature、random_write() signature、enum 是否存在。

4. LLM model
   不直接當作事實來源。
   它負責 parse、classify、merge、resolve conflict、生成 IR / code / artifacts。
   所有重要決策都要回指到 TC / LLM Wiki / GitNexus / ModelDefault。
```

換句話說：

```text
TC 說要測什麼。
LLM Wiki 說規格/知識上這代表什麼。
GitNexus 說目前 PyPPS 要怎麼寫。
LLM model 負責把這三者合成 Pattern，但不能憑空發明 API 或 expected value。
```

---

## 2. 完整執行順序總覽

目前預期順序如下：

```text
[0] Input TC markdown
      |
      v
[1] Markdown parser
      |
      v
[2] TC IR / Global Context / Flow IR / Step IR
      |
      v
[3] Flow boundary detection
      |
      v
[4] State & dependency analysis
      |
      v
[5] For each flow:
      |-- [5.1] Build flow-specific retrieval query
      |-- [5.2] Query LLM Wiki: BM25 + Dense + RRF
      |-- [5.3] Query GitNexus / direct PyPPS code references
      |-- [5.4] Normalize evidence into Evidence IR
      |-- [5.5] Decision Layer applies source priority
      |-- [5.6] Build Flow Plan
      |-- [5.7] Validate dependency coverage
      |
      v
[6] Assemble Pattern IR
      |
      v
[7] Generate Pattern .py
      |
      v
[8] Generate artifacts:
      |-- retrieval.md
      |-- assumptions.json
      |-- validation.json
      |
      v
[9] Run validation:
      |-- python py_compile
      |-- AST structure check
      |-- flow coverage check
      |-- dependency check
      |
      v
[10] Final report / HTML
```

重要：LLM Wiki 和 GitNexus 不是互相取代，而是回答不同問題。

```text
LLM Wiki answer: 這個 TC 的 behavior/spec/customer/default 意義是什麼？
GitNexus answer: 這個 behavior 在目前 PyPPS 裡要用哪個 API / enum / class 寫？
LLM model answer: 綜合 evidence 後，產生哪個 flow plan / code / assumptions？
```

---

## 3. Step 1：Markdown 解析成 IR

### 3.1 解析目標

Markdown parser 的第一階段不是直接產生 code，而是產生 IR。

IR 的目的是讓後續每一層都能 trace：

```text
原始 TC 文字
  -> 哪個 flow
  -> 哪個 step
  -> step action type
  -> step reads/writes 哪些 state
  -> 需要哪些 retrieval evidence
  -> 產生哪段 Pattern code
```

### 3.2 TC IR 結構

建議 TC IR 長這樣：

```json
{
  "pattern_name": "PF010_0310-Normalize",
  "source_file": "TC/PF010_0310-Normalize.md",
  "purpose": "WriteBooster reset behavior validation",
  "preconditions": [],
  "global_context": {
    "units": "4K blocks",
    "default_lun_policy": "max capacity enabled LUN",
    "missing_fields": []
  },
  "flows": []
}
```

### 3.3 Global Context

Global context 放跨 flow 共用的資訊，不屬於單一步驟：

```json
{
  "global_context": {
    "pattern_name": "PF010_0310-Normalize",
    "test_lun_policy": "max capacity enabled LUN",
    "lba_range_policy": "0..max_lba of selected LUN",
    "transfer_length_unit": "4K blocks",
    "write_record_scope": "global Pattern instance",
    "loop_policy": "burn_in_loop from tcsargs or ModelDefault",
    "reset_candidates": ["SSU", "POR", "LINKSTARTUP"]
  }
}
```

PF010_0310 例子裡，`self.test_lun`、`self.write_record`、`seed`、`cmd_count` 都是 global context。

---

## 4. Step 2：Flow boundary detection

### 4.1 為什麼不能整份 TC 一次 gen

整份 TC 一次 gen 的問題：

```text
- retrieval query 太長、太混雜
- SET FLAG / CLEAR FLAG / Flush flag 的 expected value 可能互相污染
- reset_type 對 expected value 的關聯可能被混淆
- optional flow 例如 FFU 可能被 silently dropped
```

### 4.2 為什麼不能每個 step isolated gen

每個 step 孤立 gen 的問題：

```text
- Step 1.2 random_write 產生的 write_record 會在 Step 1.3 compare 用到
- Step 1.4 reset_type 會在 Step 1.5 expected flag value 用到
- Step 2.2 CLEAR FLAG 會影響 Step 2.5 expected value
- selected LUN / LBA range / seed / cmd_count 都是跨 step state
```

所以正確 granularity 是：

```text
Flow-scoped retrieval + flow-level stateful generation
```

### 4.3 PF010_0310 Flow IR

PF010_0310 目前拆成：

```json
{
  "flows": [
    {
      "flow_id": "flow_0_setup",
      "method": "step1",
      "tc_steps": ["0.1", "0.2", "0.3", "0.4"],
      "objective": "setup, capacity, WriteBooster support, allocation attribute check"
    },
    {
      "flow_id": "flow_x_ffu",
      "method": "_maybe_ffu_flow_checkpoint",
      "tc_steps": ["X.1", "X.2", "X.3"],
      "objective": "optional FFU checkpoint during burn-in"
    },
    {
      "flow_id": "flow_1_enable_reset",
      "method": "step2",
      "tc_steps": ["1.1", "1.2", "1.3", "1.4", "1.5"],
      "objective": "WB enable, W/R compare, reset expected check"
    },
    {
      "flow_id": "flow_2_disable_reset",
      "method": "step3",
      "tc_steps": ["2.1", "2.2", "2.3", "2.4", "2.5"],
      "objective": "WB clear/disable, read compare, reset expected check"
    },
    {
      "flow_id": "flow_3_flush_reset",
      "method": "step4",
      "tc_steps": ["3.1", "3.2", "3.3"],
      "objective": "Flush enable flag, reset expected check"
    }
  ]
}
```

---

## 5. Step 3：Step IR

每個 flow 裡會有 ordered Step IR。

Step IR 建議欄位：

```json
{
  "step_id": "1.4",
  "flow_id": "flow_1_enable_reset",
  "raw_text": "Perform SSU/POR/LINKSTARTUP reset",
  "action_type": "reset_loop",
  "target": "device_reset",
  "parameters": {
    "reset_candidates": ["SSU", "POR", "LINKSTARTUP"]
  },
  "reads": ["WB_ENABLE_FLAG", "write_record"],
  "writes": ["reset_type"],
  "expected_result": null,
  "missing_fields": []
}
```

常見 action_type：

```text
TEST_UNIT_READY
READ_CAPACITY
READ_FLAG
SET_FLAG
CLEAR_FLAG
READ_ATTRIBUTE
WRITE_ATTRIBUTE
WRITE10
READ10_COMPARE
RESET
START_STOP_UNIT
FFU
SETUP
CLEANUP
ASSERT
```

PF010_0310 Flow 1 的 Step IR 概念：

```json
[
  {
    "step_id": "1.1",
    "action_type": "SET_FLAG",
    "target": "fWriteBoosterEnable",
    "writes": ["wb_enable_state"]
  },
  {
    "step_id": "1.2",
    "action_type": "WRITE10_RANDOM",
    "target": "selected_lun",
    "reads": ["test_lun", "lba_range", "transfer_length"],
    "writes": ["write_record"]
  },
  {
    "step_id": "1.3",
    "action_type": "READ10_COMPARE",
    "reads": ["write_record"]
  },
  {
    "step_id": "1.4",
    "action_type": "RESET_LOOP",
    "writes": ["reset_type"]
  },
  {
    "step_id": "1.5",
    "action_type": "READ_FLAG_EXPECT",
    "reads": ["reset_type", "wb_enable_state"],
    "target": "fWriteBoosterEnable"
  }
]
```

---

## 6. Step 4：State / Dependency Graph

### 6.1 為什麼需要 dependency graph

Dependency graph 是避免「step 拆開後變數斷掉」的關鍵。

它要回答：

```text
哪個 step 產生變數？
哪個 step 消耗變數？
變數是 flow local 還是 global？
如果某個 consumer 找不到 producer，是 blocker / TODO_REVIEW / default？
```

### 6.2 PF010_0310 dependency graph 範例

Flow 1：

```text
Step 1.1 SET FLAG
  -> produces wb_enable_state=1
  -> consumed by Step 1.5 expected value

Step 1.2 random_write
  -> produces write_record
  -> consumed by Step 1.3 read/compare

Step 1.4 reset loop
  -> produces reset_type
  -> consumed by _do_reset(reset_type)
  -> consumed by expected = _expected_volatile_flag_after_reset(reset_type)

Step 1.5 read flag expected
  -> consumes expected
  -> consumes WB_ENABLE_FLAG
```

Flow 2：

```text
Step 2.1 random_write
  -> produces write_record
  -> consumed by Step 2.3 random_read_compare

Step 2.2 CLEAR FLAG
  -> produces wb_enable_state=0
  -> consumed by Step 2.5 expected value

Step 2.4 reset loop
  -> produces reset_type
  -> consumed by _do_reset(reset_type)
  -> consumed by expected check
```

Flow 3：

```text
Step 3.1 SET FLAG fWriteBoosterBufferFlushEn
  -> produces flush_enable_state=1

Step 3.2 reset loop
  -> produces reset_type

Step 3.3 READ FLAG expected
  -> consumes flush_enable_state
  -> consumes reset_type
```

### 6.3 Dependency graph 在 code 裡的體現

Flow 1 code 應該長這樣，而不是把 reset 跟 expected 拆開：

```python
for reset_type in self.RESET_SEQUENCE:
    self._set_wb_enable()
    self._random_write_and_compare(...)
    self._do_reset(reset_type)
    expected = self._expected_volatile_flag_after_reset(reset_type)
    self._expect_flag(self.WB_ENABLE_FLAG, expected, ...)
```

這代表：

```text
reset_type 同時進入 _do_reset() 和 expected computation。
expected 不可以先在 flow 外部猜好。
```

---

## 7. Step 5：LLM Wiki retrieval 的產物與先後順序

### 7.1 LLM Wiki retrieval 什麼時候跑

LLM Wiki retrieval 不在一開始整份 TC 跑一次，而是在 Flow IR / Step IR 形成後，針對每個 flow 跑。

順序：

```text
Markdown parser
  -> Flow IR
  -> State/dependency graph
  -> 對每個 flow 建 query
  -> LLM Wiki retriever
  -> Knowledge Evidence IR
```

### 7.2 LLM Wiki retriever 產生什麼

每個 query 會回傳 ranked chunks：

```json
{
  "rank": 1,
  "chunk_id": "llm_wiki/spec/ufs-writebooster-flags.md#chunk-002",
  "page_path": "llm_wiki/spec/ufs-writebooster-flags.md",
  "title": "UFS WriteBooster Flags",
  "source_type": "Spec",
  "priority": 60,
  "authority": "protocol-reference",
  "bm25_score": 39.35008513,
  "dense_score": 0.47573873,
  "rrf_score": 0.03252247,
  "text_preview": "..."
}
```

### 7.3 BM25 / Dense / RRF 的意義

```text
BM25:
  lexical match，字面關鍵字命中。
  例如 fWriteBoosterEnable、READ FLAG、RESET。

Dense:
  semantic similarity，語意接近。
  例如 query 寫 WB enable reset，chunk 寫 WriteBooster volatile flag behavior。

RRF:
  reciprocal rank fusion，融合 BM25 rank 和 Dense rank。
  用來得到較穩定的 relevance 排序。
```

### 7.4 LLM Wiki ranking 是否就是最終權威順序？

不是。

LLM Wiki 的 BM25 / Dense / RRF 只代表「相關度」，不是最終決策權威。

最終要進 Decision Layer，再依 source priority 判斷。

例如：

```text
RRF 最高的是 Spec chunk。
但如果 CustomerReq 明確 override Spec，最後 behavior 仍要以 CustomerReq 為主。

RRF 找到 ModelDefault chunk。
但如果 TC 已明確指定 expected value，不能用 ModelDefault 覆蓋 TC。
```

所以兩層順序不同：

```text
Retrieval ranking:
  BM25 / Dense / RRF -> 找相關資料

Decision priority:
  TC / UserPrompt / CustomerReq / Spec / GitNexus / Project convention / ModelDefault -> 決定採用什麼
```

### 7.5 PF010_0310 每個 flow 的 LLM Wiki top hit

Flow 0 setup：

```text
Top chunk: llm_wiki/spec/ufs-writebooster-attributes.md#chunk-002
BM25: 53.08940303
Dense: 0.52007652
RRF: 0.03252247
用途: dLUNumWriteBoosterBufferAllocUnits / WB attributes grounding
```

Flow 1 enable/reset：

```text
Top chunk: llm_wiki/spec/ufs-writebooster-flags.md#chunk-002
BM25: 39.35008513
Dense: 0.47573873
RRF: 0.03252247
用途: fWriteBoosterEnable behavior / volatile flag expected state
```

Flow 2 disable/reset：

```text
Top chunk: llm_wiki/spec/ufs-writebooster-flags.md#chunk-002
BM25: 32.75155897
Dense: 0.44914582
RRF: 0.03252247
用途: CLEAR FLAG / expected 0 behavior
```

Flow 3 flush/reset：

```text
Top chunk: llm_wiki/spec/ufs-writebooster-flags.md#chunk-002
BM25: 47.04568191
Dense: 0.38197194
RRF: 0.03252247
用途: fWriteBoosterBufferFlushEn behavior
```

---

## 8. Step 6：GitNexus / PyPPS code grounding

### 8.1 GitNexus 什麼時候跑

GitNexus / PyPPS code retrieval 在 Flow IR 形成後跑，和 LLM Wiki retrieval 是平行的 evidence source。

順序上可以這樣：

```text
Flow IR / Step IR
  -> Build code-intent queries
  -> GitNexus query/context/impact 或 direct code search
  -> Code Evidence IR
```

### 8.2 GitNexus 回答什麼問題

GitNexus 不負責決定 spec expected behavior，它負責回答 implementation：

```text
- PyPPS 有沒有這個 API？
- function signature 是什麼？
- enum name 是什麼？
- sample code 通常怎麼用？
- reset primitive 有哪些？
- class Pattern 應該繼承誰？
- UFSTC 的 step execution lifecycle 是什麼？
```

### 8.3 PF010_0310 的 code grounding

目前 grounded references：

```text
Pattern lifecycle:
  /home/weikai/Script/pattern/pattern_template.py

Query helpers:
  /home/weikai/Script/api/ufs_api/attr_flag_functions.py
  api.read_attribute(idn, index=0, selector=0)
  api.write_attribute(idn, val, index=0, selector=0)
  api.read_flag(idn, index=0, selector=0)
  api.set_flag(idn, index=0, selector=0)
  api.clear_flag(idn, index=0, selector=0)

Random W/R helpers:
  /home/weikai/Script/api/ufs_api/rw_functions.py
  api.get_empty_write_record()
  api.random_write(..., compare_method, write_record, fua=0)
  api.random_read(..., write_record)
  api.CompareMethod.HW_COMPARE

START STOP UNIT:
  /home/weikai/Script/api/cmd_seq/cmds.py
  ExecuteCMD.StartStopUnit()
  /home/weikai/Script/api/ufs_api/upiu/upiu.py
  StartStopUnit.assign(lun, immed, power_condition, no_flush, start)

Reset:
  /home/weikai/Script/api/ufs_api/initial_device.py
  api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
  api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.UNIPRO_RESET)
```

### 8.4 GitNexus 發現衝突時怎麼辦

如果 TC / Spec 說有某個 IDN，但 PyPPS enum 不存在，不能硬寫假 enum。

PF010_0310 例子：

```text
TC says:
  dLUNumWriteBoosterBufferAllocUnits IDN = 0x17

PyPPS enum says:
  AttributeIDN 0x17 = REF_CLK_GATING_WAIT_TIME
  no exact dLUNumWriteBoosterBufferAllocUnits enum

Decision:
  do not write attribute
  mark TODO_REVIEW in .py / assumptions.json / validation.json
```

另一個例子：

```text
TC says:
  LINKSTARTUP Reset

PyPPS enum has:
  HW_RESET
  ENDPOINT_RESET
  UNIPRO_RESET

Decision:
  use UNIPRO_RESET as closest mapping only with TODO_REVIEW
  do not claim it is confirmed LINKSTARTUP_RESET
```

---

## 9. Step 7：LLM Model 的角色與限制

LLM model 的任務不是「用記憶直接寫 code」。

LLM model 在流程中的角色：

```text
1. Parse TC markdown into IR
2. Detect flow boundaries
3. Classify step action types
4. Build state/dependency graph
5. Generate retrieval queries
6. Read LLM Wiki retrieval results
7. Read GitNexus / code evidence
8. Apply Decision Layer source priority
9. Produce Flow Plan
10. Generate Pattern IR
11. Generate .py and artifacts
12. Explain assumptions and TODO_REVIEW
```

LLM model 不能做的事：

```text
- 不能憑空發明 PyPPS API
- 不能把 Spec behavior 當作 implementation signature
- 不能用 ModelDefault 補 core expected behavior
- 不能因為 retrieval rank 高就直接覆蓋 TC
- 不能 silently drop optional flow
- 不能把 step-level code isolated generation 後再硬拼在一起
```

---

## 10. Step 8：Decision Layer 詳細順序

Decision Layer 會依照「要決定什麼」分成兩條 priority path。

### 10.1 Behavior / test intent priority

用於：

```text
- expected value
- pass/fail behavior
- flag reset 後應該是 0 還是 1
- 測項真正目的
```

優先順序：

```text
1. TC explicit behavior
2. UserPrompt explicit override / clarification
3. CustomerReq project/customer behavior
4. Spec protocol baseline from LLM Wiki
5. ModelDefault fallback only if allowed
```

### 10.2 Implementation detail priority

用於：

```text
- PyPPS API
- enum name
- import style
- random_write signature
- reset primitive
- loop count
- compare method
```

優先順序：

```text
1. TC explicit implementation detail
2. UserPrompt implementation rule
3. CustomerReq implementation-method
4. GitNexus / /home/weikai/Script existing implementation
5. Project convention
6. ModelDefault fallback
7. BLOCKER or TODO_REVIEW
```

### 10.3 LLM Wiki / GitNexus / ModelDefault 如何互動

可以想成三種 evidence：

```text
LLM Wiki Spec evidence:
  behavior / protocol meaning

GitNexus Code evidence:
  implementation method / API reality

ModelDefault evidence:
  only fills safe missing implementation defaults
```

Decision Layer 合併時：

```text
if TC explicitly says expected value:
    use TC expected value
    use LLM Wiki only to validate/explain
elif CustomerReq overrides Spec:
    use CustomerReq
elif Spec gives protocol baseline:
    use Spec
elif ModelDefault allowed and field is safe default:
    use ModelDefault and record assumption
else:
    BLOCKER or TODO_REVIEW
```

Implementation 則：

```text
if GitNexus confirms API/enum:
    use grounded PyPPS API
elif TC gives numeric IDN but PyPPS enum missing:
    numeric IDN may be used only with TODO_REVIEW if safe
elif API is unknown or conflicts dangerously:
    do not write fake API
    emit TODO_REVIEW or BLOCKER
```

---


## 10A. UserPrompt 與 ModelDefault Priority 機制

這一層是補充 Decision Layer 裡最容易混淆的兩個來源：

```text
UserPrompt = 使用者在本次任務或專案中明確補充/覆寫的規則
ModelDefault = 當前面來源都沒有提供時，允許自動補的安全預設值
```

它們不是同一種東西，priority 也完全不同。

---

### 10A.1 UserPrompt 是什麼

UserPrompt 指的是使用者明確給出的規則、限制、偏好或修正，可能出現在：

```text
- 當前對話中的直接要求
- project-local .hermes.md 中記錄的使用者規則
- LLM Wiki 的 user-prompt 類頁面
- 使用者明確說「這個 project 要這樣做」的規範
```

例子：

```text
- 所有 size / LBA units 以 4K blocks 表示
- 一個 TC 只輸出一個 Pattern .py
- retrieval.md 必須保留 BM25 / Dense / RRF
- 不可以 invent PyPPS API
- flow-scoped retrieval + stateful flow-level generation
- CustomerReq 與 Spec 衝突時，CustomerReq override Spec
```

UserPrompt 的定位：

```text
UserPrompt 是 explicit instruction。
如果它和 ModelDefault 衝突，UserPrompt 永遠優先。
如果它和 Spec 衝突，要看衝突類型：
  - workflow / implementation policy：UserPrompt 可優先
  - protocol truth / device expected behavior：不能用 UserPrompt 任意改 spec，除非是明確 customer/project override，且要記錄
```

---

### 10A.2 ModelDefault 是什麼

ModelDefault 是在缺少資訊時，用來讓 generation 可以繼續的安全預設值。

ModelDefault 可以來自：

```text
- llm_wiki/model-default/auto/*.md
- 專案明確允許的 default policy
- generator 內建但必須記錄的 fallback
```

ModelDefault 的定位：

```text
ModelDefault 是最後階段 fallback，不是權威來源。
它只能補「不改變核心測項意圖」的 implementation default。
每次使用都必須寫進 assumptions.json。
```

允許用 ModelDefault 補的例子：

```text
- random seed policy
- cmd_count / burn_in_loop 的可覆寫預設值
- compare method，例如 HW_COMPARE vs SW_COMPARE
- reset coverage scheduling，例如 TC 列多個 reset 但沒說順序時，全部 deterministic cover
- generated code style / helper method layout
```

不允許用 ModelDefault 補的例子：

```text
- unknown expected value
- missing flag/attribute IDN
- unsupported reset primitive
- nonexistent PyPPS API
- TC 沒說但會改變 pass/fail intent 的 behavior
```

這些情況必須是：

```text
TODO_REVIEW 或 BLOCKER
```

---

### 10A.3 UserPrompt 與 ModelDefault 在 Behavior Priority 裡的位置

Behavior / test intent 指的是：

```text
- expected value
- pass/fail behavior
- flag reset 後該是 0 還是 1
- 測項目的
- customer-specific behavior
```

Priority：

```text
1. TC explicit behavior
2. UserPrompt explicit override / clarification
3. CustomerReq project/customer behavior
4. Spec protocol baseline from LLM Wiki
5. ModelDefault fallback only if allowed
6. BLOCKER if behavior still unknown
```

意思是：

```text
如果 TC 已經說 expected value，直接用 TC。
如果使用者本次明確補充 expected rule，用 UserPrompt。
如果 CustomerReq 有 customer behavior，用 CustomerReq。
如果以上都沒有，才看 Spec。
ModelDefault 幾乎不能補 expected value，除非這個 default 已被明確定義成安全 policy。
```

PF010_0310 例子：

```text
field: expected_volatile_flag_after_reset
value: SSU -> 1, POR/LINKSTARTUP -> 0
source: TC + LLM Wiki WriteBooster flags/reset pages
category: SOFT_ASSUMPTION
scope: flow_1, flow_3
```

這不是單純 ModelDefault；它是 TC intent + LLM Wiki spec grounding，再記成 flow-scoped assumption，因為 reset primitive mapping 仍有 TODO_REVIEW。

---

### 10A.4 UserPrompt 與 ModelDefault 在 Implementation Priority 裡的位置

Implementation detail 指的是：

```text
- PyPPS API
- enum name / numeric IDN
- reset primitive mapping
- import style
- helper function signature
- loop count
- compare method
- generated code style
```

Priority：

```text
1. TC explicit implementation detail
2. UserPrompt implementation rule
3. CustomerReq implementation-method
4. GitNexus / /home/weikai/Script existing implementation
5. Project convention
6. ModelDefault fallback
7. TODO_REVIEW or BLOCKER
```

意思是：

```text
如果 TC 寫明 API 或 IDN，先採用，但仍要用 GitNexus 驗證 PyPPS 是否支援。
如果 UserPrompt 說 project 一律用某種 style / unit / output layout，要採用。
如果 GitNexus 找不到 API，不能用 ModelDefault 發明 API。
ModelDefault 只能補安全 implementation detail，例如 seed、cmd_count、compare method。
```

PF010_0310 例子：

```text
compare_method:
  TC: Data Match, 未指定 HW/SW compare
  GitNexus: sample code 有 api.CompareMethod.HW_COMPARE
  ModelDefault: default compare method 可用 HW_COMPARE
  Decision: 使用 api.CompareMethod.HW_COMPARE，記 SOFT_ASSUMPTION

random_seed:
  TC: 未指定
  UserPrompt/Project: 需要可 trace / deterministic
  ModelDefault: seed policy
  Decision: seed=310，可由 tcsargs override，記 SOFT_ASSUMPTION

transfer_length_units:
  UserPrompt/Project: 所有 size/LBA units 以 4K blocks 表示
  Decision: 這是 HARD_DEFAULT / project decision，不讓 ModelDefault 另行猜測
```

---

### 10A.5 Priority 機制的 pseudo-code

Behavior decision：

```python
def decide_behavior(field, tc, user_prompt, customer_req, llm_wiki, model_default):
    if tc.has_explicit_behavior(field):
        return Decision(value=tc.value(field), source="TC", category="GROUNDED")

    if user_prompt.has_explicit_override(field):
        return Decision(value=user_prompt.value(field), source="UserPrompt", category="GROUNDED")

    if customer_req.has_behavior(field):
        return Decision(value=customer_req.value(field), source="CustomerReq", category="GROUNDED")

    if llm_wiki.spec_has_baseline(field):
        return Decision(value=llm_wiki.spec_value(field), source="Spec", category="GROUNDED")

    if model_default.allowed_for_behavior(field):
        return Decision(value=model_default.value(field), source="ModelDefault", category="SOFT_ASSUMPTION")

    return Decision(value=None, source=None, category="BLOCKER")
```

Implementation decision：

```python
def decide_implementation(field, tc, user_prompt, customer_req, gitnexus, project, model_default):
    if tc.has_explicit_implementation(field):
        candidate = tc.value(field)
        if gitnexus.can_confirm(candidate):
            return Decision(value=candidate, source="TC+GitNexus", category="GROUNDED")
        return Decision(value=candidate, source="TC", category="TODO_REVIEW")

    if user_prompt.has_implementation_rule(field):
        return Decision(value=user_prompt.value(field), source="UserPrompt", category="GROUNDED")

    if customer_req.has_implementation_method(field):
        return Decision(value=customer_req.value(field), source="CustomerReq", category="GROUNDED")

    if gitnexus.has_supported_api(field):
        return Decision(value=gitnexus.api(field), source="GitNexus", category="GROUNDED")

    if project.has_convention(field):
        return Decision(value=project.value(field), source="ProjectConvention", category="HARD_DEFAULT")

    if model_default.allowed_for_implementation(field):
        return Decision(value=model_default.value(field), source="ModelDefault", category="SOFT_ASSUMPTION")

    return Decision(value=None, source=None, category="TODO_REVIEW")
```

---

### 10A.6 PF010_0310 的實際 priority examples

| Decision field | Type | TC | UserPrompt / Project | LLM Wiki | GitNexus / PyPPS | ModelDefault | Final |
|---|---|---|---|---|---|---|---|
| output layout | implementation policy | one TC | generated/<PatternName>/ | n/a | n/a | n/a | UserPrompt / project rule |
| generation granularity | workflow policy | n/a | flow-scoped + stateful | n/a | n/a | n/a | UserPrompt / project rule |
| BM25/Dense/RRF recording | artifact policy | n/a | must record scores | retriever provides scores | n/a | n/a | UserPrompt / project rule |
| compare_method | implementation detail | Data Match only | n/a | n/a | HW_COMPARE exists in sample/API | allowed fallback | HW_COMPARE + SOFT_ASSUMPTION |
| random_seed | implementation detail | not specified | traceability desired | model-default page | n/a | seed policy | 310 + SOFT_ASSUMPTION |
| transfer unit | implementation policy | not fully specified | all size/LBA units use 4K blocks | n/a | n/a | n/a | HARD_DEFAULT project decision |
| dLUNumWriteBoosterBufferAllocUnits | implementation/API | IDN 0x17 in TC | no fake API | attribute concept exists | PyPPS enum conflict | not allowed | TODO_REVIEW, do not write |
| fWriteBoosterSupport enum | implementation/API | IDN 0x15 in TC | no fake enum | support flag concept exists | enum name missing | not allowed | numeric 0x15 + TODO_REVIEW |
| LINKSTARTUP reset | implementation/API | LINKSTARTUP listed | no fake primitive | reset concept exists | no LINKSTARTUP_RESET enum | not allowed | UNIPRO_RESET mapping + TODO_REVIEW |

---

### 10A.7 assumptions.json 如何記錄 priority 結果

只要用了 ModelDefault、Project convention fallback、或有 unresolved mapping，都必須記錄。

格式重點：

```json
{
  "id": "A001",
  "scope": "flow_1",
  "category": "SOFT_ASSUMPTION",
  "field": "compare_method",
  "value": "api.CompareMethod.HW_COMPARE",
  "source": "GitNexus sample + ModelDefault default-compare-method",
  "depends_on": ["flow_1.write_record", "flow_1.READ_COMPARE"],
  "reason": "TC says Data Match but does not specify HW vs SW compare."
}
```

Category 建議：

```text
GROUNDED:
  完全由 TC/UserPrompt/CustomerReq/GitNexus/Spec 支撐，通常不需要放 assumptions。

HARD_DEFAULT:
  project 明確固定規則，例如 4K blocks。

SOFT_ASSUMPTION:
  可自動接受但要記錄，例如 seed/cmd_count/compare_method。

TODO_REVIEW:
  有暫時處理方式但需要人確認，例如 LINKSTARTUP -> UNIPRO_RESET。

BLOCKER:
  核心 expected behavior 或必要 API 無法安全推導，不能生成可執行邏輯。
```

---

### 10A.8 Decision Layer 的防呆規則

```text
1. UserPrompt 永遠高於 ModelDefault。
2. ModelDefault 不能覆蓋 TC explicit behavior。
3. ModelDefault 不能發明 PyPPS API / enum / reset primitive。
4. GitNexus code evidence 優先於 ModelDefault implementation guess。
5. LLM Wiki retrieval ranking 只代表 relevance，不代表 priority。
6. CustomerReq 如果是明確 customer behavior，可以 override generic Spec。
7. 所有 ModelDefault / TODO_REVIEW / BLOCKER 都要 flow-scoped 記錄。
```

---

## 11. Step 9：Flow Plan

Decision Layer 的結果不是直接 code，而是 Flow Plan。

Flow Plan 範例：

```json
{
  "flow_id": "flow_1_enable_reset",
  "method": "step2",
  "tc_steps": ["1.1", "1.2", "1.3", "1.4", "1.5"],
  "ordered_operations": [
    "set WB_ENABLE_FLAG",
    "read flag and assert 1",
    "random_write with write_record",
    "for reset_type in RESET_SEQUENCE",
    "  set WB_ENABLE_FLAG",
    "  random_write with compare",
    "  do reset(reset_type)",
    "  expected = expected_after_reset(reset_type)",
    "  read flag and assert expected"
  ],
  "dependencies": [
    {
      "producer": "random_write",
      "consumer": "read_compare",
      "variable": "write_record"
    },
    {
      "producer": "reset loop",
      "consumer": "expected computation",
      "variable": "reset_type"
    }
  ],
  "todo_review": ["LINKSTARTUP mapped to UNIPRO_RESET"]
}
```

Flow Plan 的功能：

```text
- 讓 code generation 不是直接從 raw TC 跳到 Python
- 讓 dependency 可以先被 reviewer / validation 看見
- 讓 assumptions 可以 flow-scoped
- 讓 retrieval references 可以掛到 flow / operation
```

---

## 12. Step 10：Pattern IR 與 code generation

### 12.1 Pattern IR

所有 Flow Plan 合併成 Pattern IR：

```json
{
  "class_name": "Pattern",
  "base_class": "UFSTC",
  "imports": [
    "package_root",
    "from Script import api",
    "from Script.api import shared",
    "from Script.api import cmd_seq as ExecuteCMD",
    "from Script.pattern.pattern_template import UFSTC"
  ],
  "constants": [
    "WB_ENABLE_FLAG",
    "WB_FLUSH_ENABLE_FLAG",
    "WB_SUPPORT_FLAG_IDN",
    "RESET_SEQUENCE"
  ],
  "methods": [
    "pre_process",
    "is_support",
    "step1",
    "step2",
    "step3",
    "step4",
    "post_process"
  ]
}
```

### 12.2 Code generation 規則

```text
- one flow -> usually one step<number>() method
- helper method 可以共用，但不可讓 helper 切斷 flow dependency
- reset helper 和 expected computation 必須在同一 flow plan 中被呼叫
- TODO_REVIEW 要寫在 code comment / warning / assumptions / validation
- 不確定的 API 不要硬寫
```

PF010_0310 產出的 method mapping：

```text
pre_process:
  global state setup: seed, burn_in_loop, cmd_count, write_record, test_lun

step1:
  flow_0_setup

_maybe_ffu_flow_checkpoint:
  flow_x_ffu disabled placeholder

step2:
  flow_1_enable_reset

step3:
  flow_2_disable_reset

step4:
  flow_3_flush_reset

post_process:
  cleanup flags
```

---

## 13. Step 11：Artifacts 產生

### 13.1 retrieval.md

retrieval.md 要回答：

```text
每個 flow 查了什麼？
LLM Wiki top chunks 是什麼？
BM25 / Dense / RRF 分數是多少？
PyPPS code reference 是哪個 file / line？
每個 flow 的 state dependencies 是什麼？
決策原因是什麼？
```

PF010_0310 的 retrieval.md 現在是 flow-scoped：

```text
Flow 0: setup
Flow X: FFU checkpoint
Flow 1: enable reset
Flow 2: disable reset
Flow 3: flush reset
```

每個 flow 都有：

```text
- TC steps
- generated method
- decision summary
- ordered step/state dependencies
- Knowledge References table with BM25/Dense/RRF
```

### 13.2 assumptions.json

assumptions.json 要回答：

```text
哪些值不是 TC 明確給的？
是 ModelDefault 還是 TODO_REVIEW？
影響哪個 flow？
依賴哪些 state？
為什麼可以/不可以自動接受？
```

每筆 assumption 必須有：

```json
{
  "id": "A001",
  "scope": "flow_1",
  "category": "SOFT_ASSUMPTION",
  "field": "compare_method",
  "value": "api.CompareMethod.HW_COMPARE",
  "source": "...",
  "depends_on": ["flow_1.write_record"],
  "reason": "..."
}
```

### 13.3 validation.json

validation.json 要回答：

```text
code 語法是否 OK？
class Pattern 是否存在？
required methods 是否存在？
每個 flow 是否 covered？
每個 dependency 是否有 producer？
optional flow 是否被 represented？
TODO_REVIEW / blockers 是什麼？
```

PF010_0310 目前：

```text
syntax_check.ok = true
class_Pattern_found = true
required_methods_present = true
blockers = []
unresolved_todo_review = 4 items
```

---

## 14. Step 12：Validation 詳細流程

Validation 分多層：

### 14.1 Syntax validation

```bash
python3 -m py_compile generated/PF010_0310-Normalize/PF010_0310_Normalize.py
```

目的：確認 Python 語法正確。

### 14.2 AST structure validation

檢查：

```text
- class Pattern exists
- pre_process exists
- is_support exists
- step1 / step2 / step3 / step4 exist
- post_process exists
- run = Pattern().run exists
```

### 14.3 Flow coverage validation

檢查每個 Flow IR 是否有對應 method：

```text
flow_0_setup -> step1
flow_x_ffu -> _maybe_ffu_flow_checkpoint
flow_1_enable_reset -> step2
flow_2_disable_reset -> step3
flow_3_flush_reset -> step4
```

### 14.4 Dependency validation

檢查每個 consumer 是否有 producer：

```text
flow_1.write_record:
  producer = random_write
  consumer = compare/read helper

flow_1.reset_type:
  producer = RESET_SEQUENCE loop
  consumer = _do_reset + expected computation

flow_2.wb_enable_state:
  producer = CLEAR FLAG
  consumer = expected 0 check

flow_3.flush_enable_state:
  producer = SET FLAG
  consumer = post-reset flag check
```

### 14.5 TODO_REVIEW / blocker validation

檢查所有 unresolved item 是否記錄在：

```text
.py comment / warning
assumptions.json
validation.json
retrieval.md decision notes
```

PF010_0310 目前 TODO_REVIEW：

```text
1. dLUNumWriteBoosterBufferAllocUnits API/IDN mapping
2. fWriteBoosterSupport enum missing
3. LINKSTARTUP mapped to UNIPRO_RESET
4. FFU flow details missing / disabled placeholder
```

---

## 15. 互動順序：LLM Wiki、GitNexus、LLM model

最重要的互動順序可以寫成：

```text
LLM model parses TC
  -> produces Flow IR and Step IR

For each flow:
  LLM model builds retrieval query from Flow IR / Step IR / dependency graph

  LLM Wiki retriever returns ranked knowledge chunks
    -> BM25 / Dense / RRF
    -> source_type / priority / authority
    -> text preview

  GitNexus/code search returns code evidence
    -> API names
    -> function signatures
    -> enum names/values
    -> sample usage
    -> line references

  LLM model normalizes both into Evidence IR
    -> KnowledgeEvidence
    -> CodeEvidence
    -> ModelDefaultEvidence

  Decision Layer resolves each decision field
    -> behavior decisions use behavior priority
    -> implementation decisions use implementation priority
    -> conflicts become TODO_REVIEW or BLOCKER

  LLM model creates Flow Plan
    -> ordered operations
    -> state dependencies
    -> assumptions
    -> TODO_REVIEW

After all flows:
  LLM model assembles Pattern IR
  LLM model generates .py
  LLM model generates retrieval.md / assumptions.json / validation.json
  validation tools verify syntax/structure/coverage/dependencies
```

簡圖：

```text
                 +-------------------+
                 |   TC markdown     |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | LLM model parser  |
                 | TC/Flow/Step IR   |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 | Dependency Graph  |
                 +----+---------+----+
                      |         |
                      v         v
        +----------------+   +---------------------+
        |   LLM Wiki     |   | GitNexus / PyPPS    |
        | BM25/Dense/RRF |   | API / enum / sample |
        +--------+-------+   +----------+----------+
                 \                  /
                  \                /
                   v              v
                +----------------------+
                |   Evidence IR        |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Decision Layer       |
                | source priority      |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Flow Plan            |
                | stateful generation  |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Pattern IR / .py     |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | validation artifacts |
                +----------------------+
```

---

## 16. PF010_0310 實際例子：Flow 1 完整路徑

### 16.1 TC side

Flow 1 的 TC intent：

```text
SET fWriteBoosterEnable
random WRITE / READ compare
做 SSU / POR / LINKSTARTUP reset
reset 後 read fWriteBoosterEnable and compare expected value
```

### 16.2 IR side

```json
{
  "flow_id": "flow_1_enable_reset",
  "method": "step2",
  "steps": ["1.1", "1.2", "1.3", "1.4", "1.5"],
  "dependencies": [
    "SET FLAG produces wb_enable_state",
    "random_write produces write_record",
    "read_compare consumes write_record",
    "reset loop produces reset_type",
    "expected flag value consumes reset_type"
  ]
}
```

### 16.3 LLM Wiki side

Flow 1 retrieval query：

```text
PF010_0310 Phase 1 Write Booster Enable SET FLAG fWriteBoosterEnable WRITE10 READ10 compare SSU POR LINKSTARTUP reset expected flag
```

Top chunks：

```text
1. ufs-writebooster-flags.md#chunk-002
2. ufs-reset-and-start-stop-unit.md#chunk-002
3. ufs-query-interface.md#chunk-002
4. scsi-write-read-10.md#chunk-002
```

用途：

```text
WriteBooster flag behavior
reset behavior context
Query SET/READ FLAG semantics
WRITE(10)/READ(10) compare context
```

### 16.4 GitNexus side

Code grounding：

```text
api.set_flag(idn=...)
api.read_flag(idn=...)
api.random_write(... write_record ...)
api.random_read(... write_record ...)
api.init_tester_to_unit_ready(resetmode=...)
ExecuteCMD.StartStopUnit()
```

### 16.5 Decision Layer side

Decision：

```text
WB_ENABLE_FLAG implementation:
  use api.FlagIDN.WRITEBOOSTER_EN
  source: PyPPS enum

compare_method:
  use api.CompareMethod.HW_COMPARE
  source: PyPPS sample + ModelDefault assumption

reset sequence:
  use SSU, POR, LINKSTARTUP
  source: TC + default deterministic coverage

LINKSTARTUP implementation:
  use api.Dcmd5ResetType.UNIPRO_RESET with TODO_REVIEW
  source: PyPPS enum lacks explicit LINKSTARTUP_RESET

expected value:
  expected = 1 if reset_type == SSU else 0
  source: TC / LLM Wiki WriteBooster flag volatile behavior
```

### 16.6 Generated code side

```python
for reset_type in self.RESET_SEQUENCE:
    self.flow_state[flow]["last_reset_type"] = reset_type
    self._set_wb_enable()
    self._random_write_and_compare(f"Flow 1 loop {loop_idx}: before {reset_type}")
    self._do_reset(reset_type)
    expected = self._expected_volatile_flag_after_reset(reset_type)
    self.flow_state[flow]["expected_wb_enable"] = expected
    self._expect_flag(self.WB_ENABLE_FLAG, expected, f"Flow 1 after {reset_type} reset")
```

這就是 flow-level stateful generation 的核心：

```text
reset_type 沒有離開 flow。
expected 沒有在外部被猜好。
write_record 沒有被 step-level generation 切斷。
```

---

## 17. 最後輸出物

對一個 TC，至少輸出：

```text
generated/<PatternName>/<PatternNamePythonSafe>.py
generated/<PatternName>/<PatternNamePythonSafe>.retrieval.md
generated/<PatternName>/<PatternNamePythonSafe>.assumptions.json
generated/<PatternName>/<PatternNamePythonSafe>.validation.json
```

PF010_0310 目前輸出：

```text
/home/weikai/AgentGeneratePypps/generated/PF010_0310-Normalize/PF010_0310_Normalize.py
/home/weikai/AgentGeneratePypps/generated/PF010_0310-Normalize/PF010_0310_Normalize.retrieval.md
/home/weikai/AgentGeneratePypps/generated/PF010_0310-Normalize/PF010_0310_Normalize.assumptions.json
/home/weikai/AgentGeneratePypps/generated/PF010_0310-Normalize/PF010_0310_Normalize.validation.json
/home/weikai/AgentGeneratePypps/generated/PF010_0310-Normalize/PF010_0310_Pattern_Generation_Report.html
/home/weikai/AgentGeneratePypps/generated/PF010_0310-Normalize/PF010_0310_Detailed_Generation_Flow.md
```

---

## 18. 總結

這套方法的重點不是「讓 LLM 一次把 code 寫出來」，而是把 LLM 放在一個可追蹤的 pipeline 裡：

```text
TC -> IR -> flow/state dependency -> retrieval -> evidence -> decision -> flow plan -> Pattern IR -> code -> validation
```

最重要的三個防呆：

```text
1. 不整份 TC 一次 broad generation。
2. 不做 isolated step-level code generation。
3. 任何 unsupported API / missing enum / ambiguous reset mapping 都必須 TODO_REVIEW 或 BLOCKER。
```

最後的設計目標：

```text
產生的 Pattern 不只是能跑的 .py，還要能說清楚：
- 每個 flow 為什麼這樣寫
- 每個 expected value 從哪裡來
- 每個 API 從哪個 PyPPS code reference 來
- 每個 fallback / TODO_REVIEW 影響哪個 flow 和哪個 dependency
```
