from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Tokenize wiki text for UFS/PyPPS retrieval.

    The tokenizer is intentionally dependency-free and normalizes common TC/code forms:
    - camelCase: fWriteBoosterEnable -> f write booster enable
    - snake/constant case: START_STOP_UNIT -> start stop unit
    - command punctuation: WRITE(10) -> write 10
    """

    spaced = _CAMEL_RE.sub(" ", text.replace("_", " ").replace("-", " "))
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(spaced)]


def reciprocal_rank_fusion(ranked_lists: Sequence[Sequence[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


@dataclass(frozen=True)
class WikiChunk:
    chunk_id: str
    page_path: str
    title: str
    source_type: str
    priority: int | None
    authority: str
    frontmatter: str
    text: str

    @classmethod
    def from_json(cls, payload: dict) -> "WikiChunk":
        return cls(
            chunk_id=str(payload.get("chunk_id", "")),
            page_path=str(payload.get("page_path", "")),
            title=str(payload.get("title", "")),
            source_type=str(payload.get("source_type", "")),
            priority=payload.get("priority"),
            authority=str(payload.get("authority", "")),
            frontmatter=str(payload.get("frontmatter", "")),
            text=str(payload.get("text", "")),
        )


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _doc_text(chunk: WikiChunk) -> str:
    return "\n".join([
        chunk.title,
        chunk.page_path,
        chunk.source_type,
        chunk.authority,
        chunk.frontmatter,
        chunk.text,
    ])


def load_chunks(path: str | Path) -> list[WikiChunk]:
    chunks: list[WikiChunk] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                chunks.append(WikiChunk.from_json(json.loads(line)))
    return chunks


class EmbeddingEncoder:
    def encode_one(self, text: str) -> list[float]:
        raise NotImplementedError


class HashEmbeddingEncoder(EmbeddingEncoder):
    def __init__(self, dimensions: int = 512):
        self.index = HashEmbeddingIndex([], dimensions=dimensions)

    def encode_one(self, text: str) -> list[float]:
        return self.index.embed(text)


class SentenceTransformerEncoder(EmbeddingEncoder):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError(
                "sentence-transformers is not installed. Install it with "
                "`python3 -m pip install sentence-transformers`, or use "
                "--dense-backend hash-embedding."
            ) from exc
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode_one(self, text: str) -> list[float]:
        encoded = self.model.encode([text], normalize_embeddings=True)[0]
        if hasattr(encoded, "tolist"):
            encoded = encoded.tolist()
        return [float(value) for value in encoded]


@dataclass(frozen=True)
class SearchResult:
    rank: int
    chunk_id: str
    page_path: str
    title: str
    source_type: str
    priority: int | None
    authority: str
    bm25_score: float
    dense_score: float
    rrf_score: float
    text_preview: str

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("bm25_score", "dense_score", "rrf_score"):
            data[key] = round(float(data[key]), 8)
        return data


class BM25Index:
    def __init__(self, tokenized_docs: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = len(tokenized_docs)
        self.doc_lengths = [len(doc) for doc in tokenized_docs]
        self.avg_doc_len = sum(self.doc_lengths) / self.doc_count if self.doc_count else 0.0
        self.term_freqs = [Counter(doc) for doc in tokenized_docs]
        doc_freq: Counter[str] = Counter()
        for doc in tokenized_docs:
            doc_freq.update(set(doc))
        self.idf = {
            term: math.log(1.0 + (self.doc_count - freq + 0.5) / (freq + 0.5))
            for term, freq in doc_freq.items()
        }

    def score(self, query_tokens: Sequence[str], doc_index: int) -> float:
        if not query_tokens or self.doc_count == 0:
            return 0.0
        freqs = self.term_freqs[doc_index]
        doc_len = self.doc_lengths[doc_index] or 1
        denom_norm = self.k1 * (1.0 - self.b + self.b * doc_len / (self.avg_doc_len or 1.0))
        score = 0.0
        for term in query_tokens:
            tf = freqs.get(term, 0)
            if not tf:
                continue
            score += self.idf.get(term, 0.0) * (tf * (self.k1 + 1.0)) / (tf + denom_norm)
        return score

    def search(self, query_tokens: Sequence[str]) -> list[tuple[int, float]]:
        scored = [(idx, self.score(query_tokens, idx)) for idx in range(self.doc_count)]
        return sorted(scored, key=lambda item: (-item[1], item[0]))


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _stable_bucket(token: str, dimensions: int) -> int:
    # Python's built-in hash is salted per process; use sha256 for stable indexes.
    import hashlib

    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % dimensions


class HashEmbeddingIndex:
    """Dependency-free embedding index based on feature hashing.

    This is a real vector embedding backend in the sense that every document/query is
    embedded into a fixed-size numeric vector and compared with cosine similarity.
    It is deterministic and works without external packages. For semantic neural
    embeddings, use SentenceTransformerEmbeddingIndex via --dense-backend sentence-transformer.
    """

    backend_name = "hash-embedding"

    def __init__(self, docs: Sequence[str], dimensions: int = 512):
        self.dimensions = dimensions
        self.doc_vectors = [self.embed(doc) for doc in docs]

    def _features(self, text: str) -> Iterable[str]:
        tokens = tokenize(text)
        for token in tokens:
            yield f"tok:{token}"
        for left, right in zip(tokens, tokens[1:]):
            yield f"bi:{left}:{right}"
        for token in tokens:
            if len(token) >= 4:
                for i in range(len(token) - 2):
                    yield f"tri:{token[i:i+3]}"

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for feature in self._features(text):
            bucket = _stable_bucket(feature, self.dimensions)
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    def score(self, query: str, doc_index: int) -> float:
        return _cosine(self.embed(query), self.doc_vectors[doc_index])

    def search(self, query: str) -> list[tuple[int, float]]:
        scored = [(idx, self.score(query, idx)) for idx in range(len(self.doc_vectors))]
        return sorted(scored, key=lambda item: (-item[1], item[0]))


class SentenceTransformerEmbeddingIndex:
    """Neural embedding index backed by sentence-transformers.

    The model argument is injectable for tests. Without an injected model, this class
    imports sentence_transformers lazily so the rest of the package remains usable in
    minimal environments.
    """

    def __init__(
        self,
        docs: Sequence[str],
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        model: object | None = None,
    ):
        self.model_name = model_name
        self.backend_name = f"sentence-transformer:{model_name}"
        if model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except Exception as exc:  # pragma: no cover - depends on optional package
                raise RuntimeError(
                    "sentence-transformers is not installed. Install it with "
                    "`python3 -m pip install sentence-transformers`, or use "
                    "--dense-backend hash-embedding for a dependency-free embedding backend."
                ) from exc
            model = SentenceTransformer(model_name)
        self.model = model
        self.doc_vectors = self._encode(list(docs))

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        encoded = self.model.encode(list(texts), normalize_embeddings=True)
        vectors: list[list[float]] = []
        for row in encoded:
            if hasattr(row, "tolist"):
                row = row.tolist()
            vector = [float(value) for value in row]
            vectors.append(vector)
        return vectors

    def score(self, query: str, doc_index: int) -> float:
        query_vector = self._encode([query])[0]
        return _cosine(query_vector, self.doc_vectors[doc_index])

    def search(self, query: str) -> list[tuple[int, float]]:
        query_vector = self._encode([query])[0]
        scored = [(idx, _cosine(query_vector, vec)) for idx, vec in enumerate(self.doc_vectors)]
        return sorted(scored, key=lambda item: (-item[1], item[0]))


class TfidfCosineIndex:
    """Legacy lexical scorer retained only for explicit --dense-backend tfidf."""

    backend_name = "tfidf"

    def __init__(self, tokenized_docs: Sequence[Sequence[str]]):
        self.doc_count = len(tokenized_docs)
        df: Counter[str] = Counter()
        for doc in tokenized_docs:
            df.update(set(doc))
        self.idf = {
            term: math.log((1.0 + self.doc_count) / (1.0 + freq)) + 1.0
            for term, freq in df.items()
        }
        self.doc_vectors = [self._vector(doc) for doc in tokenized_docs]
        self.doc_norms = [self._norm(vec) for vec in self.doc_vectors]

    def _vector(self, tokens: Sequence[str]) -> dict[str, float]:
        counts = Counter(tokens)
        if not counts:
            return {}
        total = sum(counts.values())
        return {term: (count / total) * self.idf.get(term, 0.0) for term, count in counts.items()}

    @staticmethod
    def _norm(vec: dict[str, float]) -> float:
        return math.sqrt(sum(value * value for value in vec.values()))

    def score(self, query: str | Sequence[str], doc_index: int) -> float:
        query_tokens = tokenize(query) if isinstance(query, str) else list(query)
        qvec = self._vector(query_tokens)
        qnorm = self._norm(qvec)
        dnorm = self.doc_norms[doc_index]
        if not qnorm or not dnorm:
            return 0.0
        dvec = self.doc_vectors[doc_index]
        dot = sum(qval * dvec.get(term, 0.0) for term, qval in qvec.items())
        return dot / (qnorm * dnorm)

    def search(self, query: str | Sequence[str]) -> list[tuple[int, float]]:
        scored = [(idx, self.score(query, idx)) for idx in range(self.doc_count)]
        return sorted(scored, key=lambda item: (-item[1], item[0]))


class PersistentEmbeddingIndex:
    """Dense index backed by persisted embeddings.npy + manifest files."""

    def __init__(
        self,
        embeddings,
        chunk_ids: Sequence[str],
        metadata: Sequence[dict],
        manifest: dict,
        encoder: EmbeddingEncoder,
    ):
        self.embeddings = embeddings
        self.chunk_ids = list(chunk_ids)
        self.metadata = list(metadata)
        self.manifest = dict(manifest)
        self.encoder = encoder
        self.backend_name = f"persistent:{self.manifest.get('dense_backend', 'unknown')}"
        self._query_cache: dict[str, list[float]] = {}

    @classmethod
    def load(
        cls,
        index_dir: str | Path,
        chunks_path: str | Path,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> "PersistentEmbeddingIndex":
        import numpy as np

        index_dir = Path(index_dir)
        manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        expected_hash = manifest.get("chunks_sha256")
        actual_hash = _sha256_file(chunks_path)
        if expected_hash != actual_hash:
            raise ValueError(
                f"Persistent embedding index is stale: chunks_sha256 {expected_hash} != {actual_hash}. "
                "Rebuild embeddings."
            )
        embeddings = np.load(index_dir / "embeddings.npy")
        chunk_ids = json.loads((index_dir / "chunk_ids.json").read_text(encoding="utf-8"))
        metadata = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
        if len(chunk_ids) != int(manifest.get("chunk_count", -1)):
            raise ValueError("chunk_ids count does not match manifest chunk_count")
        if embeddings.shape[0] != len(chunk_ids):
            raise ValueError("embeddings row count does not match chunk_ids count")

        backend = manifest.get("dense_backend")
        if backend == "hash-embedding":
            encoder = HashEmbeddingEncoder(dimensions=int(manifest.get("dimension", embeddings.shape[1])))
        elif backend == "sentence-transformer":
            encoder = SentenceTransformerEncoder(model_name=str(manifest.get("embedding_model", embedding_model_name)))
        else:
            raise ValueError(f"Unsupported persistent dense_backend: {backend}")
        return cls(embeddings, chunk_ids, metadata, manifest, encoder)

    def _encode_query(self, query: str) -> list[float]:
        if query not in self._query_cache:
            self._query_cache[query] = self.encoder.encode_one(query)
        return self._query_cache[query]

    def score(self, query: str, doc_index: int) -> float:
        query_vector = self._encode_query(query)
        return _cosine(query_vector, self.embeddings[doc_index].tolist())

    def search(self, query: str) -> list[tuple[int, float]]:
        query_vector = self._encode_query(query)
        scored = [(idx, _cosine(query_vector, row.tolist())) for idx, row in enumerate(self.embeddings)]
        return sorted(scored, key=lambda item: (-item[1], item[0]))


def build_persistent_embedding_index(
    chunks_path: str | Path,
    out_dir: str | Path,
    dense_backend: str = "sentence-transformer",
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> dict:
    """Build and persist a document embedding matrix for chunks.jsonl."""

    import numpy as np

    chunks_path = Path(chunks_path)
    out_dir = Path(out_dir)
    chunks = load_chunks(chunks_path)
    docs = [_doc_text(chunk) for chunk in chunks]

    if dense_backend == "hash-embedding":
        dense_index = HashEmbeddingIndex(docs)
        vectors = dense_index.doc_vectors
        dimension = dense_index.dimensions
        embedding_model = "hash-embedding:stable-feature-hash"
    elif dense_backend == "sentence-transformer":
        dense_index = SentenceTransformerEmbeddingIndex(docs, model_name=embedding_model_name)
        vectors = dense_index.doc_vectors
        dimension = len(vectors[0]) if vectors else 0
        embedding_model = embedding_model_name
    else:
        raise ValueError("Persistent embeddings support dense_backend hash-embedding or sentence-transformer")

    out_dir.mkdir(parents=True, exist_ok=True)
    embeddings = np.asarray(vectors, dtype="float32")
    np.save(out_dir / "embeddings.npy", embeddings)

    chunk_ids = [chunk.chunk_id for chunk in chunks]
    metadata = [
        {
            "chunk_id": chunk.chunk_id,
            "page_path": chunk.page_path,
            "title": chunk.title,
            "source_type": chunk.source_type,
            "priority": chunk.priority,
            "authority": chunk.authority,
        }
        for chunk in chunks
    ]
    (out_dir / "chunk_ids.json").write_text(json.dumps(chunk_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunks_path": str(chunks_path),
        "chunks_sha256": _sha256_file(chunks_path),
        "chunk_count": len(chunks),
        "dense_backend": dense_backend,
        "embedding_model": embedding_model,
        "dimension": int(dimension),
        "files": {
            "embeddings": "embeddings.npy",
            "chunk_ids": "chunk_ids.json",
            "metadata": "metadata.json",
            "manifest": "manifest.json",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


class LLMWikiRetriever:
    def __init__(
        self,
        chunks: Sequence[WikiChunk],
        dense_backend: str = "hash-embedding",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_index: str | Path | None = None,
        chunks_path: str | Path | None = None,
    ):
        self.chunks = list(chunks)
        self._doc_texts = [_doc_text(c) for c in self.chunks]
        self._doc_tokens = [tokenize(text) for text in self._doc_texts]
        self._bm25 = BM25Index(self._doc_tokens)
        self._dense = self._build_dense_index(dense_backend, embedding_model_name, embedding_index, chunks_path)
        if isinstance(self._dense, PersistentEmbeddingIndex):
            expected_ids = [chunk.chunk_id for chunk in self.chunks]
            if self._dense.chunk_ids != expected_ids:
                raise ValueError("Persistent embedding index chunk_ids do not match chunks file order")
        self.dense_backend = getattr(self._dense, "backend_name", dense_backend)

    def _build_dense_index(
        self,
        dense_backend: str,
        embedding_model_name: str,
        embedding_index: str | Path | None = None,
        chunks_path: str | Path | None = None,
    ):
        if embedding_index is not None:
            if chunks_path is None:
                raise ValueError("chunks_path is required when embedding_index is provided")
            return PersistentEmbeddingIndex.load(
                embedding_index,
                chunks_path=chunks_path,
                embedding_model_name=embedding_model_name,
            )
        if dense_backend == "hash-embedding":
            return HashEmbeddingIndex(self._doc_texts)
        if dense_backend == "sentence-transformer":
            return SentenceTransformerEmbeddingIndex(self._doc_texts, model_name=embedding_model_name)
        if dense_backend == "tfidf":
            return TfidfCosineIndex(self._doc_tokens)
        if dense_backend == "auto":
            try:
                return SentenceTransformerEmbeddingIndex(self._doc_texts, model_name=embedding_model_name)
            except RuntimeError:
                return HashEmbeddingIndex(self._doc_texts)
        raise ValueError(f"Unsupported dense_backend: {dense_backend}")

    @classmethod
    def from_chunks_file(
        cls,
        path: str | Path,
        dense_backend: str = "hash-embedding",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_index: str | Path | None = None,
    ) -> "LLMWikiRetriever":
        chunks = load_chunks(path)
        return cls(
            chunks,
            dense_backend=dense_backend,
            embedding_model_name=embedding_model_name,
            embedding_index=embedding_index,
            chunks_path=path,
        )

    def search(self, query: str, top_k: int = 10, source_type: str | None = None) -> list[SearchResult]:
        query_tokens = tokenize(query)
        candidate_indices = [
            idx for idx, chunk in enumerate(self.chunks)
            if source_type is None or chunk.source_type == source_type
        ]
        if not candidate_indices:
            return []

        bm25_scores = {idx: self._bm25.score(query_tokens, idx) for idx in candidate_indices}
        dense_scores = {idx: self._dense.score(query, idx) for idx in candidate_indices}

        bm25_ranked = [
            self.chunks[idx].chunk_id
            for idx in sorted(candidate_indices, key=lambda i: (-bm25_scores[i], i))
        ]
        dense_ranked = [
            self.chunks[idx].chunk_id
            for idx in sorted(candidate_indices, key=lambda i: (-dense_scores[i], i))
        ]
        fused = reciprocal_rank_fusion([bm25_ranked, dense_ranked])
        id_to_idx = {chunk.chunk_id: idx for idx, chunk in enumerate(self.chunks)}

        results: list[SearchResult] = []
        for rank, (chunk_id, rrf_score) in enumerate(fused[:top_k], start=1):
            idx = id_to_idx[chunk_id]
            chunk = self.chunks[idx]
            preview = re.sub(r"\s+", " ", chunk.text).strip()[:500]
            results.append(
                SearchResult(
                    rank=rank,
                    chunk_id=chunk.chunk_id,
                    page_path=chunk.page_path,
                    title=chunk.title,
                    source_type=chunk.source_type,
                    priority=chunk.priority,
                    authority=chunk.authority,
                    bm25_score=bm25_scores[idx],
                    dense_score=dense_scores[idx],
                    rrf_score=rrf_score,
                    text_preview=preview,
                )
            )
        return results


def _print_text(results: Sequence[SearchResult]) -> None:
    for result in results:
        print(f"[{result.rank}] {result.title}")
        print(f"    page: {result.page_path}")
        print(f"    source_type: {result.source_type} priority={result.priority} authority={result.authority}")
        print(
            f"    bm25={result.bm25_score:.4f} dense={result.dense_score:.4f} "
            f"rrf={result.rrf_score:.6f}"
        )
        print(f"    preview: {result.text_preview}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query AgentGeneratePypps LLM Wiki chunks")
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("query", help="Run BM25 + embedding dense + RRF retrieval")
    q.add_argument("query", help="Query text")
    q.add_argument("--chunks", default=".pattern_kb/index/chunks.jsonl", help="Path to chunks.jsonl")
    q.add_argument("--top-k", type=int, default=10)
    q.add_argument("--source-type", default=None)
    q.add_argument(
        "--dense-backend",
        choices=["hash-embedding", "sentence-transformer", "auto", "tfidf"],
        default="hash-embedding",
        help="Dense retrieval backend. Use sentence-transformer for neural embeddings if installed.",
    )
    q.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name when --dense-backend sentence-transformer or auto is used.",
    )
    q.add_argument(
        "--embedding-index",
        default=None,
        help="Path to a persistent embedding index directory built with build-embeddings.",
    )
    q.add_argument("--json", action="store_true", help="Emit JSON")

    b = sub.add_parser("build-embeddings", help="Precompute and persist chunk embeddings")
    b.add_argument("--chunks", default=".pattern_kb/index/chunks.jsonl", help="Path to chunks.jsonl")
    b.add_argument("--out", required=True, help="Output embedding index directory")
    b.add_argument(
        "--dense-backend",
        choices=["hash-embedding", "sentence-transformer"],
        default="sentence-transformer",
        help="Embedding backend to persist.",
    )
    b.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name when --dense-backend sentence-transformer is used.",
    )

    args = parser.parse_args(argv)
    if args.command == "query":
        retriever = LLMWikiRetriever.from_chunks_file(
            args.chunks,
            dense_backend=args.dense_backend,
            embedding_model_name=args.embedding_model,
            embedding_index=args.embedding_index,
        )
        results = retriever.search(args.query, top_k=args.top_k, source_type=args.source_type)
        if args.json:
            print(
                json.dumps(
                    {
                        "query": args.query,
                        "dense_backend": retriever.dense_backend,
                        "results": [r.to_dict() for r in results],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            _print_text(results)
        return 0
    if args.command == "build-embeddings":
        manifest = build_persistent_embedding_index(
            chunks_path=args.chunks,
            out_dir=args.out,
            dense_backend=args.dense_backend,
            embedding_model_name=args.embedding_model,
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "out": str(Path(args.out)),
                    "embeddings": str(Path(args.out) / "embeddings.npy"),
                    "manifest": manifest,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
