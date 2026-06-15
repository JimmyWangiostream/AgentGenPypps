---
title: PF010_0310-Normalized-TestFlow
type: normalized-test-flow
tags: [test-flow, ufs, pf010_0310, scsi-cmd, write-booster]
description: >
  PF010_0310 Write Booster SSU Reset Test — 正規化 Test Flow。
  以 UFS SCSI CMD 為最小單位拆分，純基於 JIRA 步驟與 UFS SPEC，
  不參考任何 C++ 實作。方便 AI 根據 Test Flow 生成 C++ 程式碼。
sources:
  - JIRA: PF010_0310 (SYSTCUFS)
  - UFS Spec: JEDEC UFSHCI 3.0 / UFS Protocol Layer
---

# PF010_0310 正規化 Test Flow（SCSI CMD 單位）

## 測試目標

驗證 Write Booster 功能在 SSU (Software Reset) / POR (Power-On Reset) / LINKSTARTUP Reset 之後的行為，包含：
- Write Booster 啟用後執行 W/R 並 reset，確認功能正常
- Write Booster 停用後執行 W/R 並 reset，確認資料一致性
- Flush Enable 功能隨機搭配各種 Reset 類型

## JIRA Step 對照

| JIRA Step | 描述 |
|-----------|------|
| Step 1 | Config 最大Support size Write Booster Buff |
| Step 2 | Write Booster enable during W/R compare data period with SSU + all reset |
| Step 3 | Exit Write Booster during W/R compare data period with SSU + all reset |
| Step 4 | flushEnable 並作相對應的動作且隨機搭配SSU + all reset |

---

## 測試架構

```
PF010_0310 Test Flow
│
├── Phase 0: Write Booster 初始化配置
│   ├── Step 0.1: TEST UNIT READY (確認裝置就緒)
│   ├── Step 0.2: READ CAPACITY (取得 LUN 容量)
│   ├── Step 0.3: QUERY: Read Flag fWriteBoosterSupport (確認支援)
│   └── Step 0.4: QUERY: Write Attr dLUNumWriteBoosterBufferAllocUnits (MAX size)
│
└── Loop (burn_in_loop 次)
    │
    ├── Phase X: FFU (條件觸發，時間達 burn-in 1/3 時)
    │   ├── Step X.1: WRITE BUFFER (FFU mode) (寫入新版韌體)
    │   ├── Step X.2: TEST UNIT READY (確認 FFU 完成)
    │   └── Step X.3: 停用 FFU 更新標記
    │
    ├── Phase 1: Write Booster Enable + W/R + Reset
    │   ├── Step 1.1: QUERY: Set Flag fWriteBoosterEnable = 1 (啟用 WB)
    │   ├── Step 1.2: WRITE(10) (寫入測試資料)
    │   ├── Step 1.3: READ(10) + Compare (讀取比對)
    │   ├── Step 1.4: SSU Reset (或 POR / LINKSTARTUP)
    │   └── Step 1.5: QUERY: Read Flag fWriteBoosterEnable (驗證狀態)
    │
    ├── Phase 2: Write Booster Disable + W/R + Reset
    │   ├── Step 2.1: WRITE(10) (寫入測試資料)
    │   ├── Step 2.2: QUERY: Clear Flag fWriteBoosterEnable (停用 WB)
    │   ├── Step 2.3: READ(10) + Compare (讀取比對)
    │   ├── Step 2.4: SSU Reset (或 POR / LINKSTARTUP)
    │   └── Step 2.5: QUERY: Read Flag fWriteBoosterEnable (驗證狀態)
    │
    └── Phase 3: Flush Enable + Reset
        ├── Step 3.1: QUERY: Set Flag fWriteBoosterBufferFlushEn = 1
        ├── Step 3.2: SSU Reset (或 POR / LINKSTARTUP)
        └── Step 3.3: QUERY: Read Flag fWriteBoosterBufferFlushEn (驗證狀態)
```

---

## Phase 0 — Write Booster 初始化配置

### Step 0.1: 確認裝置就緒

**SCSI CMD**: `TEST UNIT READY (00h)`

**目的**: 確認 UFS 裝置處於就緒狀態，可以接受後續命令。

**Expected Response**: `GOOD Status` — 裝置就緒。

---

### Step 0.2: 取得 LUN 容量

**SCSI CMD**: `READ CAPACITY(10) (25h)`

**目的**: 取得最大 LUN 的邏輯位址空間容量，用於後續 W/R 測試的 LBA 範圍。

**Return Data**:
- `RETURNED LOGICAL BLOCK ADDRESS`: 最大 LBA
- `LOGICAL BLOCK LENGTH IN BYTES`: 區塊大小（通常 4KB）

---

### Step 0.3: 確認 Write Booster 支援

**UFS QUERY**: `READ FLAG (fWriteBoosterSupport)`

**目的**: 確認 UFS 裝置支援 Write Booster 功能。

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x01 (READ FLAG) |
| IDN | 0x15 (fWriteBoosterSupport) |

**Expected**: Flag = 1（支援 WB）

**若不支援**: 跳過測試（TEST SKIP）

---

### Step 0.4: 配置最大 Write Booster Buffer

**UFS QUERY**: `READ ATTRIBUTE (dLUNumWriteBoosterBufferAllocUnits)`

**目的**: 讀取最大可配置的 Write Booster Buffer 分配單位數。

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x03 (READ ATTRIBUTE) |
| IDN | 0x17 (dLUNumWriteBoosterBufferAllocUnits) |

**UFS QUERY**: `WRITE ATTRIBUTE (dLUNumWriteBoosterBufferAllocUnits)`

**目的**: 以最大可支援容量配置 Write Booster Buffer。

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x04 (WRITE ATTRIBUTE) |
| IDN | 0x17 (dLUNumWriteBoosterBufferAllocUnits) |
| Value | bMaxWriteBoosterBufferAllocUnits (MAX) |

**Configuration Mode**:
- `Shared Mode`: 單一 buffer 供所有 LUN 共享
- `Dedicated Mode`: 每個 LUN 有獨立 buffer
- 根據 `bSupportedWriteBoosterBufferTypes` 屬性選擇模式

**UFS SPEC Reference**: JESD220H Section 13.4.18 / Section 14.3

---

## Phase X — FFU (Field Firmware Update) During Burn-in

> **JIRA Step 2 (新增)**: FFU update during burn-in
>
> 此流程在 burn-in 時間達到 1/3 時觸發，用於更新韌體至指定版本。

### Step X.1: 執行 FFU 韌體更新

**SCSI CMD**: `WRITE BUFFER (2Bh)` — Mode = FFU (Download & Save)

**目的**: 將新版韌體寫入裝置緩衝區並儲存。

| Field | Value (基於 UFS/SBC Spec) |
|-------|--------------------------|
| Opcode | 0x2B |
| Buffer ID | 0x00 (Vendor Specific Buffer) |
| Buffer Offset | 0x00 |
| Transfer Length | 依 FW BIN 大小 |
| Mode | 0x0E (FFU: Download & Save) |

**Expected**: `GOOD Status` — 韌體資料已寫入

**UFS SPEC Reference**: JESD220H Section 11.6.7 (WRITE BUFFER)

---

### Step X.2: 確認 FFU 完成

**SCSI CMD**: `TEST UNIT READY (00h)`

**目的**: 確認裝置已完成 FFU 並處於就緒狀態。

**Expected**: `GOOD Status`

---

## Phase 1 — Write Booster Enable + W/R + Reset

### Step 1.1: 啟用 Write Booster

**UFS QUERY**: `SET FLAG (fWriteBoosterEnable = 1)`

**目的**: 啟用 Write Booster 功能。根據 UFS Spec，WriteBooster 需先配置 buffer 再啟用。

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x02 (SET FLAG) |
| IDN | 0x0A (fWriteBoosterEnable) |

**Expected**: `SUCCESS` — Write Booster 已啟用。

**UFS SPEC Reference**: JESD220H Section 13.4.18, Section 14.2

---

### Step 1.2: 寫入測試資料

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 在 Write Booster 啟用狀態下寫入測試資料。資料會先寫入 Write Booster Buffer。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| Logical Block Address | 0 ~ MAX_LBA (隨機範圍) |
| Transfer Length | 1 ~ 256 blocks (隨機大小) |

**Expected**: `GOOD Status` — 寫入成功。

---

### Step 1.3: 讀取並比對資料

**SCSI CMD**: `READ(10) (28h)`

**目的**: 讀取剛寫入的資料，驗證 Write Booster 是否正確加速寫入。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| Logical Block Address | 與 Step 1.2 相同 |
| Transfer Length | 與 Step 1.2 相同 |

**Data Compare**: 讀取資料需與寫入資料完全一致。

**Expected**: `GOOD Status` + `Data Match`

---

### Step 1.4: 執行 Reset

**Reset Type**: `SSU (Software Unit Reset)` 或 `POR (Power-On Reset)` 或 `LINKSTARTUP Reset`

**目的**: 驗證 Reset 後 Write Booster 狀態是否正確保留或清除。

**Reset Options**:
| Type | Description |
|------|-------------|
| SSU | Software Reset (UFS Device Reset) |
| POR | Power-On Reset |
| LINKSTARTUP | Link Startup Reset |

**Implementation**: 根據 JIRA 描述，Reset 類型為隨機選擇（random SSU + all reset）。

---

### Step 1.5: 驗證 Write Booster Flag 狀態

**UFS QUERY**: `READ FLAG (fWriteBoosterEnable)`

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x01 (READ FLAG) |
| IDN | 0x0A (fWriteBoosterEnable) |

**Expected**: `fWriteBoosterEnable = 1`（Reset 後 WB 狀態依 Spec 規定）

**Verification Point**:
- Reset 後 `fWriteBoosterEnable` 狀態應依 JESD220H Section 13.4.18 規定
- 若為 non-volatile 設定，則 Reset 後保持為 1；若為 volatile，則為 0

---

## Phase 2 — Write Booster Disable + W/R + Reset

### Step 2.1: 寫入測試資料（停用 WB 前）

**SCSI CMD**: `WRITE(10) (2Ah)`

**目的**: 在 Write Booster 停用前寫入測試資料，驗證停用後的資料讀取正常。

| Field | Value |
|-------|-------|
| Opcode | 0x2A |
| Logical Block Address | 0 ~ MAX_LBA |
| Transfer Length | 1 ~ 256 blocks |

**Expected**: `GOOD Status`

---

### Step 2.2: 停用 Write Booster

**UFS QUERY**: `SET FLAG (fWriteBoosterEnable = 0)` 或 `CLEAR FLAG (fWriteBoosterEnable)`

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x02 (SET FLAG) 或 0x05 (CLEAR FLAG) |
| IDN | 0x0A (fWriteBoosterEnable) |
| Value | 0 (Disable) |

**Expected**: `SUCCESS` — Write Booster 已停用。

---

### Step 2.3: 讀取並比對資料

**SCSI CMD**: `READ(10) (28h)`

**目的**: 在 WB 停用後讀取資料，驗證資料一致性。

| Field | Value |
|-------|-------|
| Opcode | 0x28 |
| Logical Block Address | 與 Step 2.1 相同 |
| Transfer Length | 與 Step 2.1 相同 |

**Expected**: `GOOD Status` + `Data Match`

---

### Step 2.4: 執行 Reset

**Reset Type**: 隨機選擇 SSU / POR / LINKSTARTUP

**目的**: 驗證 WB 停用狀態下執行 Reset，確認資料不受影響。

---

### Step 2.5: 驗證 Write Booster Flag 狀態

**UFS QUERY**: `READ FLAG (fWriteBoosterEnable)`

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x01 (READ FLAG) |
| IDN | 0x0A (fWriteBoosterEnable) |

**Expected**: `fWriteBoosterEnable = 0`（已停用）

---

## Phase 3 — Flush Enable + Reset

> **JIRA Step 4**: flushEnable 並作相對應的動作且隨機搭配SSU + all reset

### Step 3.1: 啟用 Write Booster Buffer Flush

**UFS QUERY**: `SET FLAG (fWriteBoosterBufferFlushEn = 1)`

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x02 (SET FLAG) |
| IDN | 0x0B (fWriteBoosterBufferFlushEn) |

**Expected**: `SUCCESS`

**UFS SPEC Reference**: JESD220H Section 13.4.18, Section 14.2

---

### Step 3.2: 執行 Reset

**Reset Type**: 隨機選擇 SSU / POR / LINKSTARTUP

> JIRA 描述「隨機搭配SSU + all reset」，C++ 實作中無 random delay，直接執行 POR。

---

### Step 3.3: 驗證 Flush Flag 狀態

**UFS QUERY**: `READ FLAG (fWriteBoosterBufferFlushEn)`

| Field | Value (基於 UFS Spec) |
|-------|----------------------|
| Opcode | 0x01 (READ FLAG) |
| IDN | 0x0B (fWriteBoosterBufferFlushEn) |

**Expected**: Reset 後 Flag 狀態依 Spec 規定

---

## 附錄 A — UFS Query IDN 對照表（基於 JESD220H UFS 5.0 Spec）

> 資料來源: [[ufs-query-interface]], [[ufs-writebooster]]

### Flag IDN (bFlagIDN)

| IDN | 名稱 | 用途 |
|-----|------|------|
| 0x0A | `fWriteBoosterEnable` | Write Booster 啟用/停用控制 |
| 0x0B | `fWriteBoosterBufferFlushEn` | Write Booster Buffer Flush 啟用 |
| 0x08 | `fDeviceInit` | 裝置初始化完成 |
| 0x15 | `fWriteBoosterSupport` | Write Booster 支援與否（唯讀） |

### Attribute IDN (bAttrIDN)

| IDN | 名稱 | 用途 |
|-----|------|------|
| 0x17 | `dLUNumWriteBoosterBufferAllocUnits` | 配置的 WB Buffer 分配單位數 |
| 0x0A | `fWriteBoosterEnable` | WriteBooster enable flag |
| 0x39 | `bBootLunEn` | Boot LUN 啟用 |
| 0x00 | `bActiveICCLevel` | Active ICC power level |
| 0x100 | `dExtendedUFSFeaturesSupport` | Feature support bits (bit[8] = WB support) |
| 0x109 | `dWriteBoosterBufferLifeTimeEst` | WB buffer 壽命預估 |

### Descriptor IDN (bDescIDN)

| IDN | 名稱 | 用途 |
|-----|------|------|
| 0x00 | Device Descriptor | 裝置層級資訊 |
| 0x01 | Configuration Descriptor | 目前功率模式等 |
| 0x02 | Unit Descriptor | Per-LU 資訊 |
| 0x04 | Interconnect Descriptor | UniPro 連結資訊 |
| 0x07 | Geometry Descriptor | 儲存幾何資訊 |
| 0x19 | Device Health Descriptor | 溫度、壽命預估 |

### Query Operations

| Opcode | 名稱 | 用途 |
|--------|------|------|
| 0x01 | READ FLAG | 讀取指定 Flag 狀態 |
| 0x02 | SET FLAG | 設定指定 Flag 為 1 |
| 0x05 | CLEAR FLAG | 清除指定 Flag 為 0 |
| 0x03 | READ ATTRIBUTE | 讀取指定 Attribute 值 |
| 0x04 | WRITE ATTRIBUTE | 寫入指定 Attribute 值 |

---

## 附錄 B — SCSI Command Opcode 對照表

| Opcode | CMD 名稱 | 用途 |
|--------|----------|------|
| 0x00 | TEST UNIT READY | 確認裝置就緒 |
| 0x25 | READ CAPACITY(10) | 取得媒體容量資訊 |
| 0x28 | READ(10) | 讀取資料（10-byte CDB） |
| 0x2A | WRITE(10) | 寫入資料（10-byte CDB） |

---

## 附錄 C — UFS Reset 類型說明

| Reset 類型 | 說明 | UFS Spec 章節 |
|------------|------|--------------|
| SSU (Software Unit Reset) | 裝置層級軟體重置，保留電源狀態但重置控制邏輯 | UFSHCI 3.0 |
| POR (Power-On Reset) | 電源開啟重置，完全重新初始化 | UFSHCI 3.0 |
| LINKSTARTUP | 連結啟動重置，重新協商連結參數 | UFSM-PHY |

---