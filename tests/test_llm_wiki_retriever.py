import json
import subprocess
import sys
from pathlib import Path

from auto_pattern_gen.llm_wiki.retriever import (
    HashEmbeddingIndex,
    LLMWikiRetriever,
    PersistentEmbeddingIndex,
    SentenceTransformerEmbeddingIndex,
    build_persistent_embedding_index,
    tokenize,
    reciprocal_rank_fusion,
)


ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / ".pattern_kb" / "index" / "chunks.jsonl"


def test_tokenize_normalizes_camel_case_and_underscores():
    tokens = tokenize("PF010_0310 fWriteBoosterEnable WRITE(10) START_STOP_UNIT")

    assert "pf010" in tokens
    assert "0310" in tokens
    assert "f" in tokens
    assert "write" in tokens
    assert "booster" in tokens
    assert "enable" in tokens
    assert "start" in tokens
    assert "stop" in tokens
    assert "unit" in tokens


def test_rrf_combines_ranked_lists_and_preserves_relevance():
    fused = reciprocal_rank_fusion([
        ["spec-flags", "query", "reset"],
        ["query", "spec-flags", "prop-noun"],
    ], k=60)

    assert fused[0][0] in {"spec-flags", "query"}
    assert dict(fused)["spec-flags"] > dict(fused)["reset"]
    assert dict(fused)["query"] > dict(fused)["prop-noun"]


def test_hash_embedding_index_scores_semantically_related_vector_text():
    docs = [
        "Write Booster read flag enable reset",
        "unrelated thermal protection vendor command",
    ]
    index = HashEmbeddingIndex(docs, dimensions=128)

    assert index.backend_name == "hash-embedding"
    assert index.score("Write Booster enable flag", 0) > index.score("Write Booster enable flag", 1)


class _FakeSentenceTransformer:
    def encode(self, texts, normalize_embeddings=True):
        vectors = []
        for text in texts:
            lower = text.lower()
            vectors.append([
                1.0 if "write" in lower else 0.0,
                1.0 if "booster" in lower else 0.0,
                1.0 if "reset" in lower else 0.0,
            ])
        return vectors


def test_sentence_transformer_embedding_index_accepts_injected_model():
    index = SentenceTransformerEmbeddingIndex(
        ["Write Booster reset behavior", "capacity and LUN selection"],
        model=_FakeSentenceTransformer(),
    )

    assert index.backend_name.startswith("sentence-transformer")
    assert index.score("Write Booster reset", 0) > index.score("Write Booster reset", 1)


def test_retriever_returns_metadata_and_ranks_writebooster_query():
    retriever = LLMWikiRetriever.from_chunks_file(CHUNKS, dense_backend="hash-embedding")

    results = retriever.search(
        "PF010_0310 Write Booster READ FLAG fWriteBoosterEnable SSU reset",
        top_k=5,
    )

    assert results
    assert any("ufs-writebooster-flags.md" in r.page_path for r in results)
    assert any("ufs-query-interface.md" in r.page_path for r in results)

    first = results[0]
    assert first.source_type in {"Spec", "PropNoun", "GenerationPolicy", "ModelDefault", "UserPrompt", "PyppsCode"}
    assert first.rrf_score > 0
    assert first.bm25_score >= 0
    assert first.dense_score >= 0
    assert first.page_path.startswith("llm_wiki/")


def test_metadata_filter_can_limit_to_spec_pages():
    retriever = LLMWikiRetriever.from_chunks_file(CHUNKS)

    results = retriever.search(
        "START STOP UNIT POWER CONDITION UFS-PowerDown Active",
        top_k=10,
        source_type="Spec",
    )

    assert results
    assert all(r.source_type == "Spec" for r in results)
    assert any("ufs-reset-and-start-stop-unit.md" in r.page_path for r in results)


def test_persistent_embedding_index_round_trips_and_is_used_by_retriever(tmp_path):
    out_dir = tmp_path / "hash-index"
    manifest = build_persistent_embedding_index(
        chunks_path=CHUNKS,
        out_dir=out_dir,
        dense_backend="hash-embedding",
    )

    assert (out_dir / "embeddings.npy").exists()
    assert (out_dir / "chunk_ids.json").exists()
    assert (out_dir / "metadata.json").exists()
    assert (out_dir / "manifest.json").exists()
    assert manifest["chunk_count"] == 34
    assert manifest["dense_backend"] == "hash-embedding"
    assert manifest["chunks_sha256"].startswith("sha256:")

    loaded = PersistentEmbeddingIndex.load(out_dir, chunks_path=CHUNKS)
    assert loaded.backend_name == "persistent:hash-embedding"
    assert loaded.score("Write Booster enable flag", 32) >= 0

    retriever = LLMWikiRetriever.from_chunks_file(
        CHUNKS,
        dense_backend="hash-embedding",
        embedding_index=out_dir,
    )
    results = retriever.search("Write Booster READ FLAG fWriteBoosterEnable", top_k=3)
    assert results
    assert retriever.dense_backend == "persistent:hash-embedding"
    assert any("ufs-writebooster-flags.md" in r.page_path for r in results)


def test_cli_can_build_and_query_with_persistent_embedding_index(tmp_path):
    out_dir = tmp_path / "cli-index"
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_pattern_gen.llm_wiki.retriever",
            "build-embeddings",
            "--chunks",
            str(CHUNKS),
            "--dense-backend",
            "hash-embedding",
            "--out",
            str(out_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert "embeddings.npy" in build.stdout

    query = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_pattern_gen.llm_wiki.retriever",
            "query",
            "Write Booster READ FLAG fWriteBoosterEnable",
            "--chunks",
            str(CHUNKS),
            "--embedding-index",
            str(out_dir),
            "--top-k",
            "3",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    payload = json.loads(query.stdout)
    assert payload["dense_backend"] == "persistent:hash-embedding"
    assert len(payload["results"]) == 3


def test_cli_query_outputs_json_with_ranked_results():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_pattern_gen.llm_wiki.retriever",
            "query",
            "Write Booster READ FLAG fWriteBoosterEnable",
            "--chunks",
            str(CHUNKS),
            "--top-k",
            "3",
            "--dense-backend",
            "hash-embedding",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["query"] == "Write Booster READ FLAG fWriteBoosterEnable"
    assert len(payload["results"]) == 3
    assert all("rrf_score" in item for item in payload["results"])
