# LLM Wiki Agent Generation Procedure for AgentGeneratePypps

Generated for: AgentGeneratePypps
Generated at: 2026-06-14T23:48:37+08:00
Primary output wiki root: `llm_wiki/`
Index metadata root: `.pattern_kb/index/`

This document is the reproducible procedure for another agent to generate the same style of LLM Wiki for UFS/PyPPS Pattern generation from TC markdown files. It is written as an operational skill/procedure, not just a design note.

## 1. Goal

Build an LLM Wiki that supports generation of Pattern `.py` files from TC `.md` files with full source traceability.

The wiki must allow the generator to answer:

1. What does the TC explicitly require?
2. What does UserPrompt specify when TC omits implementation detail?
3. What does CustomerReq specify when present?
4. What does Spec say for protocol legality?
5. What ModelDefault may be used only as fallback?
6. What concrete PyPPS API must be verified by GitNexus before emitting code?

The output is not just vector chunks. The output is a source-governed markdown knowledge base with YAML frontmatter copied into retrieval chunks.

## 2. Hard principles

### 2.1 Clean-slate source policy

Do not treat any old skill, previous session artifact, historical path, or assumed API as fact. Verify current files from the working directory.

For this project, the relevant current source roots are:

```text
TC/
docx/CustomerReq/
docx/Spec/
docx/UserPrompt/
docx/PropNoun/
docx/ModelDefault/
docx/Script/
```

If a directory is empty, create a scaffold/README page but do not invent source content.

### 2.2 LLM Wiki does not replace GitNexus

LLM Wiki stores stable knowledge and source-governed rules:

```text
CustomerReq
Spec
UserPrompt
PropNoun
ModelDefault
GenerationPolicy
PyPPS code-writing policy
```

GitNexus stores live code grounding:

```text
existing Script/Pattern examples
primitive API names
function signatures
import paths
symbol context
call graph
impact analysis
```

The LLM Wiki may say that the generated Pattern must perform `READ FLAG fWriteBoosterEnable`, but GitNexus must confirm the actual PyPPS API name/signature before concrete code is emitted.

### 2.3 Retrieval score is relevance, not authority

BM25/dense/RRF scores only answer: “Which chunks are relevant?”

They do not answer: “Which source governs the decision?”

Authority is decided by:

```text
source_type
authority
claim_types
TC explicitness
CustomerReq vs Spec rule
UserPrompt vs ModelDefault rule
```

## 3. Required wiki layout

Create this directory structure:

```text
llm_wiki/
├── README.md
├── SCHEMA.md
├── SOURCE_PRIORITY.md
├── customer-req/
│   └── README.md
├── spec/
│   ├── ufs-query-interface.md
│   ├── ufs-writebooster-flags.md
│   ├── ufs-writebooster-attributes.md
│   ├── ufs-reset-and-start-stop-unit.md
│   ├── scsi-write-read-10.md
│   └── scsi-basic-commands.md
├── user-prompt/
│   └── default-lun-selection.md
├── prop-noun/
│   └── ufs-proper-nouns.md
├── model-default/
│   ├── auto/
│   ├── reviewed/
│   ├── proposed/
│   └── blockers/
├── generation-policy/
│   ├── model-default-policy.md
│   └── pattern-generation-decision-rules.md
└── pypps-code/
    └── gitnexus-grounding-policy.md
```

Create index metadata:

```text
.pattern_kb/
├── index/
│   ├── chunks.jsonl
│   └── manifest.json
└── logs/
    └── source_manifest.json
```

`chunks.jsonl` is index-ready metadata. Actual BM25/vector index files may be built later by the retriever implementation.

## 4. Required YAML frontmatter schema

Every wiki page must start with YAML frontmatter.

Minimum required fields:

```yaml
---
title: string
source_type: CustomerReq | Spec | UserPrompt | ModelDefault | PropNoun | Script | GenerationPolicy | PyppsCode
source_path: string
source_section: string
source_hash: sha256:...
priority: number
authority: customer-requirement | protocol-reference | user-rule | fallback | terminology | code-reference | policy
confidence: low | medium | high
applies_to:
  tc_ids: []
  features: []
  operations: []
  commands: []
  flags: []
  attributes: []
claim_types: []
---
```

Optional fields for ModelDefault:

```yaml
status: active | proposed | deprecated
default_origin: auto_generated | auto_proposed | user_reviewed | manual_seed
default_policy_mode: auto_accept | review_required
category: HARD_DEFAULT | SOFT_ASSUMPTION | BLOCKER
fallback_only: true
requires_recording: true
requires_approval: true | false
```

Optional fields for CustomerReq:

```yaml
generation_policy:
  allow_new_implementation: true
  require_gitnexus_primitive_grounding: true
  require_human_review_if_no_script_reference: true
```

## 5. Source type mapping

Map source directory to source type:

```text
docx/CustomerReq/*  -> CustomerReq, priority 90, authority customer-requirement
docx/Spec/*         -> Spec, priority 60, authority protocol-reference
docx/UserPrompt/*   -> UserPrompt, priority 100, authority user-rule
docx/PropNoun/*     -> PropNoun, priority 40, authority terminology
docx/ModelDefault/* -> ModelDefault, priority 30, authority fallback
docx/Script/*       -> Script, priority 70, authority code-reference
```

TC files are primary generation inputs. They can be referenced by wiki pages, but the wiki should not treat a TC-derived summary as stronger than the original TC parse.

## 6. Source priority and decision rules

Metadata priority:

```text
UserPrompt: 100
TC: 95
CustomerReq: 90
Script/GitNexus: 70
Spec: 60
PropNoun: 40
ModelDefault: 30
```

Do not use this as one flat priority list. Use decision paths.

### 6.1 Expected behavior / test intent

Use this path for expected response, post-reset state, pass/fail criteria, and customer/project behavior:

```text
1. UserPrompt, only if it explicitly clarifies or overrides this TC
2. TC explicit test intent
3. CustomerReq customer/project behavior
4. Spec baseline when no relevant CustomerReq exists
5. ModelDefault fallback only, recorded
```

CustomerReq may govern project expected behavior over Spec. Spec remains supporting protocol validation.

### 6.2 Implementation detail / generation choice

Use this path for LUN selection, loop count, random seed, reset coverage, LBA allocation, helper/API selection, compare method, and code style:

```text
1. TC explicit implementation detail
2. UserPrompt implementation rule if TC is missing that detail
3. CustomerReq implementation-method if relevant
4. Script/GitNexus existing Pattern or primitive API grounding
5. Project coding convention
6. ModelDefault fallback, recorded
7. BLOCKER or TODO_REVIEW
```

UserPrompt fills missing implementation details by default. UserPrompt only overrides explicit TC behavior when it explicitly declares override intent.

### 6.3 Protocol validation

Spec is always used for protocol legality validation even when TC/UserPrompt/CustomerReq governs generated behavior.

## 7. ModelDefault two-mode system

Support two modes.

### 7.1 `auto_accept`

When a new fallbackable implementation detail is missing:

```text
create ModelDefault page under llm_wiki/model-default/auto/
status: active
default_origin: auto_generated
default_policy_mode: auto_accept
allow use in current generation
record in assumptions.md and validation.json
```

### 7.2 `review_required`

When a new fallbackable implementation detail is missing:

```text
create ModelDefault page under llm_wiki/model-default/proposed/
status: proposed
default_origin: auto_proposed
default_policy_mode: review_required
ask user to approve/edit/reject
do not use unless run config allows temporary use
```

### 7.3 Category safety

```text
HARD_DEFAULT:
  behavior-neutral; may auto activate

SOFT_ASSUMPTION:
  affects implementation detail; auto_accept may activate; review_required asks

BLOCKER:
  never fills a value; records that generation must stop or emit TODO_REVIEW
```

No mode may use ModelDefault to invent:

```text
expected values
command identity
protocol-critical IDN/index/selector/write-data
pass/fail criteria
customer-specific expected behavior
```

## 8. Generation algorithm

### Step 1: inspect source tree

List files under:

```text
TC/
docx/
```

For every source file used, compute SHA256 and store in `.pattern_kb/logs/source_manifest.json`.

### Step 2: create schema and policy pages

Create:

```text
llm_wiki/README.md
llm_wiki/SCHEMA.md
llm_wiki/SOURCE_PRIORITY.md
llm_wiki/generation-policy/model-default-policy.md
llm_wiki/generation-policy/pattern-generation-decision-rules.md
llm_wiki/pypps-code/gitnexus-grounding-policy.md
```

These pages are `source_type: GenerationPolicy` except the GitNexus page, which is `source_type: PyppsCode`.

### Step 3: convert source docs to topic pages

Do not put a whole long Spec file into one giant page. Split by retrieval topic.

For the current PF010_0310 Write Booster flow, generate these Spec topic pages:

```text
llm_wiki/spec/ufs-query-interface.md
llm_wiki/spec/ufs-writebooster-flags.md
llm_wiki/spec/ufs-writebooster-attributes.md
llm_wiki/spec/ufs-reset-and-start-stop-unit.md
llm_wiki/spec/scsi-write-read-10.md
llm_wiki/spec/scsi-basic-commands.md
```

Use source paths:

```text
docx/Spec/chapters/27_1099_query_function_transport_protocol_services.md
docx/Spec/chapters/69_142_flags.md
docx/Spec/chapters/70_143_attributes.md
docx/Spec/chapters/07_7_reset_power-up_and_power-down.md
docx/Spec/chapters/39_11315_write_10_command.md
TC/PF010_0310-Normalize.md for TC-derived command summary only
```

For UserPrompt:

```text
docx/UserPrompt/user_prompt.md -> llm_wiki/user-prompt/default-lun-selection.md
```

Extract the rule:

```text
When TC does not specify LUN details, use the enabled LUN with maximum capacity.
```

For PropNoun:

```text
docx/PropNoun/proper_nouns.md -> llm_wiki/prop-noun/ufs-proper-nouns.md
```

Extract terminology and retrieval expansions such as:

```text
WB -> Write Booster
SSU + all reset -> reset, START STOP UNIT, POR, LINKSTARTUP
H8/Hibern8 -> UFS Link Hibernate
DCMD -> SDK packaged command flow
```

For CustomerReq:

If no source exists, create only:

```text
llm_wiki/customer-req/README.md
```

Do not invent CustomerReq behavior.

### Step 4: create baseline ModelDefault catalog

Create tracks:

```text
llm_wiki/model-default/auto/
llm_wiki/model-default/reviewed/
llm_wiki/model-default/proposed/
llm_wiki/model-default/blockers/
```

Create active auto defaults:

```text
llm_wiki/model-default/auto/default-random-seed-policy.md
llm_wiki/model-default/auto/default-reset-coverage-policy.md
llm_wiki/model-default/auto/default-compare-method.md
llm_wiki/model-default/auto/default-generated-file-style.md
```

Create blocker rule:

```text
llm_wiki/model-default/blockers/missing-core-test-intent.md
```

Every ModelDefault page must include:

```yaml
source_type: ModelDefault
priority: 30
authority: fallback
fallback_only: true
requires_recording: true
category: HARD_DEFAULT | SOFT_ASSUMPTION | BLOCKER
```

### Step 5: build index-ready chunks

For every `llm_wiki/**/*.md` page:

1. Read YAML frontmatter.
2. Split body by markdown headings (`#`, `##`, `###`).
3. For every chunk, write one JSON object to `.pattern_kb/index/chunks.jsonl`.

Required chunk fields:

```json
{
  "chunk_id": "llm_wiki/spec/ufs-query-interface.md#chunk-001",
  "page_path": "llm_wiki/spec/ufs-query-interface.md",
  "title": "UFS Query Interface",
  "source_type": "Spec",
  "priority": 60,
  "authority": "protocol-reference",
  "frontmatter": "...",
  "text": "..."
}
```

The retriever adds BM25 + embedding dense + RRF scores at query time. Current implementation:

```text
auto_pattern_gen/llm_wiki/retriever.py
```

Dense backends:

```text
hash-embedding         default; dependency-free fixed-size embedding vectors with cosine similarity
sentence-transformer   neural embedding backend using sentence-transformers
                         default model: sentence-transformers/all-MiniLM-L6-v2
auto                   try sentence-transformer, fall back to hash-embedding if unavailable
tfidf                  legacy lexical scorer; keep only for regression comparison
```

Default CLI usage uses embedding vectors, not TF-IDF:

```bash
python3 -m auto_pattern_gen.llm_wiki.retriever query \
  "PF010_0310 Write Booster READ FLAG fWriteBoosterEnable SSU reset" \
  --chunks .pattern_kb/index/chunks.jsonl \
  --top-k 8
```

Explicit neural embedding usage:

```bash
python3 -m auto_pattern_gen.llm_wiki.retriever query \
  "PF010_0310 Write Booster READ FLAG fWriteBoosterEnable SSU reset" \
  --dense-backend sentence-transformer \
  --embedding-model sentence-transformers/all-MiniLM-L6-v2 \
  --top-k 8
```

If `sentence-transformers` is not installed, install it first. On this WSL/Python 3.14 environment, Python is externally managed by the OS, so the installation command used was:

```bash
python3 -m pip install --user --break-system-packages --upgrade sentence-transformers
```

Installed/verified package versions in this workspace:

```text
sentence-transformers 5.5.1
transformers 5.12.0
torch 2.12.0+cu130
numpy 2.4.6
scikit-learn 1.9.0
scipy 1.17.1
```

CUDA note:

```text
torch imports successfully, but CUDA is unavailable because the NVIDIA driver is too old.
Use CPU execution for sentence-transformer retrieval unless the driver/PyTorch stack is changed.
```

JSON output includes the selected dense backend:

```bash
python3 -m auto_pattern_gen.llm_wiki.retriever query \
  "Write Booster READ FLAG fWriteBoosterEnable" \
  --json --top-k 5
```

The default `hash-embedding` backend is intentionally deterministic and offline. It embeds each page chunk into a fixed-size numeric vector using stable feature hashing over tokens, bigrams, and character trigrams, then uses cosine similarity. For higher-quality semantic retrieval, use `--dense-backend sentence-transformer` after installing the optional dependency.

Current embedding storage behavior:

```text
.persisted:
  .pattern_kb/index/chunks.jsonl
    Stores chunk text + metadata only. It does not store embedding vectors.

  /home/weikai/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/
    Stores the downloaded sentence-transformer model weights/cache.

.in_memory_only:
  document/chunk embeddings
    Built when LLMWikiRetriever initializes.
    Discarded when the Python process exits.

  query embedding
    Built per query.
    Discarded when the Python process exits.
```

Model cache snapshot observed in this environment:

```text
/home/weikai/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/
```

Current query-time flow:

```text
read .pattern_kb/index/chunks.jsonl
load sentence-transformer model from HuggingFace cache
encode all chunks into document embeddings in memory
encode query into query embedding
compute cosine similarity
fuse BM25 ranking + embedding ranking with RRF
return ranked chunks
```

Persistent embedding index is implemented. Use it for larger LLM Wiki indexes so each query only needs to encode the query instead of re-encoding every chunk.

Implemented persistent embedding index layout:

```text
.pattern_kb/index/embeddings/
└── sentence-transformers--all-MiniLM-L6-v2/
    ├── embeddings.npy
    ├── chunk_ids.json
    ├── metadata.json
    └── manifest.json
```

Build command:

```bash
CUDA_VISIBLE_DEVICES='' python3 -m auto_pattern_gen.llm_wiki.retriever build-embeddings \
  --chunks .pattern_kb/index/chunks.jsonl \
  --dense-backend sentence-transformer \
  --embedding-model sentence-transformers/all-MiniLM-L6-v2 \
  --out .pattern_kb/index/embeddings/sentence-transformers--all-MiniLM-L6-v2
```

Query using the persisted index:

```bash
CUDA_VISIBLE_DEVICES='' python3 -m auto_pattern_gen.llm_wiki.retriever query \
  "PF010_0310 Write Booster READ FLAG fWriteBoosterEnable SSU reset" \
  --chunks .pattern_kb/index/chunks.jsonl \
  --embedding-index .pattern_kb/index/embeddings/sentence-transformers--all-MiniLM-L6-v2 \
  --top-k 8
```

Implemented manifest fields:

```json
{
  "generated_at": "...",
  "chunks_path": ".pattern_kb/index/chunks.jsonl",
  "chunks_sha256": "sha256:...",
  "chunk_count": 34,
  "dense_backend": "sentence-transformer",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "dimension": 384,
  "files": {
    "embeddings": "embeddings.npy",
    "chunk_ids": "chunk_ids.json",
    "metadata": "metadata.json",
    "manifest": "manifest.json"
  }
}
```

Safety rule: query only reuses persisted embeddings when `chunks_sha256` matches the current `chunks.jsonl`. If the hash differs, the retriever raises a stale-index error and embeddings must be rebuilt before retrieval.

Implementation entry points:

```text
build_persistent_embedding_index(...)
PersistentEmbeddingIndex.load(...)
LLMWikiRetriever.from_chunks_file(..., embedding_index="...")
CLI subcommand: build-embeddings
CLI query arg: --embedding-index
```

### Step 6: write manifest

Write `.pattern_kb/index/manifest.json` with:

```json
{
  "generated_at": "...",
  "wiki_root": "llm_wiki",
  "page_count": 24,
  "chunk_count": 34,
  "index_status": "metadata_chunks_created; BM25/vector index implementation pending",
  "sources": [
    {"key": "...", "path": "...", "sha256": "sha256:..."}
  ]
}
```

Also write `.pattern_kb/logs/source_manifest.json` with the source list.

## 9. Current generated source-specific decisions

For the current workspace, the generated wiki used these sources:

```text
TC/PF010_0310-Normalize.md
docx/UserPrompt/user_prompt.md
docx/PropNoun/proper_nouns.md
docx/Spec/chapters/69_142_flags.md
docx/Spec/chapters/70_143_attributes.md
docx/Spec/chapters/39_11315_write_10_command.md
docx/Spec/chapters/07_7_reset_power-up_and_power-down.md
docx/Spec/chapters/27_1099_query_function_transport_protocol_services.md
```

No CustomerReq source was used because no CustomerReq document was found during this build.

## 10. How Pattern generation should consume this wiki

For each TC step:

1. Parse TC into Step IR.
2. Expand query terms using PropNoun.
3. Query LLM Wiki BM25.
4. Query LLM Wiki dense/vector.
5. Fuse with RRF.
6. Filter/rerank by metadata when appropriate.
7. Apply decision layer, not raw score order.
8. Query GitNexus for code grounding.
9. Generate code only when required primitive APIs are grounded.
10. Write `.retrieval.md`, `.assumptions.md`, and `.validation.json`.

Example query for PF010_0310 Step 1.5:

```text
PF010_0310 Write Booster reset READ FLAG fWriteBoosterEnable expected after SSU POR LINKSTARTUP
```

Expected LLM Wiki candidates:

```text
Spec: ufs-writebooster-flags.md
Spec: ufs-reset-and-start-stop-unit.md
Spec: ufs-query-interface.md
PropNoun: ufs-proper-nouns.md
```

If a future CustomerReq page exists and is relevant, it may become the governing source for expected behavior while Spec remains supporting validation.

## 11. Traceability requirements

Every generated Pattern must have:

```text
<pattern>.retrieval.md
<pattern>.assumptions.md
<pattern>.validation.json
```

`retrieval.md` must record:

```yaml
engine: LLMWiki | GitNexus
source_type: Spec | CustomerReq | UserPrompt | ModelDefault | PropNoun | PyppsCode
page_or_file: path
source_section: section
bm25: number|null
dense: number|null
rrf: number|null
used_as: governing | supporting | validation | fallback | rejected
reason: string
```

`assumptions.md` must record every ModelDefault use, including:

```text
field
category
condition
action
source page
why TC/UserPrompt/CustomerReq/GitNexus did not provide it
risk/impact
```

`validation.json` must record:

```text
step coverage
source coverage
GitNexus primitive grounding status
ModelDefault usage
BLOCKER/TODO_REVIEW entries
CustomerReq-vs-Spec conflicts
NEW_IMPLEMENTATION_NO_SCRIPT_REFERENCE when applicable
```

## 12. Verification checklist for another agent

After generating the wiki:

1. Confirm `llm_wiki/` exists.
2. Confirm every markdown page has YAML frontmatter.
3. Confirm source types are valid.
4. Confirm `source_hash` exists for source-derived pages.
5. Confirm `.pattern_kb/index/chunks.jsonl` exists and has at least one chunk per page.
6. Confirm `.pattern_kb/index/manifest.json` page_count equals actual markdown file count.
7. Confirm CustomerReq is scaffold-only if no CustomerReq source exists.
8. Confirm ModelDefault pages are fallback-only and have `requires_recording: true`.
9. Confirm no concrete PyPPS API is invented by LLM Wiki pages; concrete APIs must come from GitNexus.

## 13. Minimal Python generation sketch

A future implementation may automate this using the following structure:

```python
from pathlib import Path
import hashlib, json, re

SOURCE_MAP = {
    'docx/CustomerReq': ('CustomerReq', 90, 'customer-requirement'),
    'docx/Spec': ('Spec', 60, 'protocol-reference'),
    'docx/UserPrompt': ('UserPrompt', 100, 'user-rule'),
    'docx/PropNoun': ('PropNoun', 40, 'terminology'),
    'docx/ModelDefault': ('ModelDefault', 30, 'fallback'),
    'docx/Script': ('Script', 70, 'code-reference'),
}

def sha256(path):
    return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_page(path, frontmatter, body):
    text = '---\n' + frontmatter.strip() + '\n---\n\n' + body.strip() + '\n'
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding='utf-8')

def chunk_pages(wiki_root='llm_wiki'):
    chunks = []
    for p in Path(wiki_root).rglob('*.md'):
        text = p.read_text(encoding='utf-8')
        fm = re.match(r'^---\n(.*?)\n---\n', text, re.S)
        body = text[fm.end():] if fm else text
        # parse frontmatter into metadata, then split body by headings
        # write JSONL chunks with metadata copied from page
    return chunks
```

The concrete page contents should follow the files generated in `llm_wiki/`.
