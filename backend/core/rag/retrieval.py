"""Semantic retrieval, diverse results, and evidence for source contradictions."""

import os
import re
import time
from functools import lru_cache
from pathlib import Path

from core import corpus
from core.rag.embeddings import embed_query, model_name
from core.rag.vector_store import FAISSVectorStore

COMMON = {
    "scholarship",
    "scholarships",
    "scheme",
    "for",
    "of",
    "the",
    "students",
    "student",
    "post",
    "graduate",
    "what",
    "how",
    "do",
    "i",
    "can",
    "apply",
    "required",
    "documents",
}


def index_dir() -> Path:
    path = Path(os.getenv("VECTOR_INDEX_DIR", "var/index"))
    return path if path.is_absolute() else corpus.ROOT / path


def index_status() -> dict:
    try:
        directory = index_dir()
        version = (directory / "CURRENT").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[0-9a-f]{32}", version):
            raise ValueError("Invalid pointer")
        import json

        metadata = json.loads((directory / version / "metadata.json").read_text(encoding="utf-8"))
        ready = (
            metadata["corpus_hash"] == corpus.fingerprint()
            and metadata["embedding_model"] == model_name()
        )
        return {
            "ready": ready,
            "version": version,
            "chunks": metadata["chunk_count"],
            "reason": None if ready else "Corpus or embedding model changed; re-ingest.",
        }
    except (OSError, ValueError, KeyError):
        return {"ready": False, "reason": "Index unavailable; run ingest_scholarships."}


@lru_cache(maxsize=4)
def load_store(version: str):
    store, metadata = FAISSVectorStore.load(index_dir())
    if (
        metadata["corpus_hash"] != corpus.fingerprint()
        or metadata["embedding_model"] != model_name()
    ):
        raise ValueError("Index is stale; run ingestion.")
    return store


def filters_for(question, scheme_ids=None, category=None):
    if scheme_ids is not None:
        corpus.records(scheme_ids)  # Validate even an empty list.
        return {"scheme_id": scheme_ids}
    if category:
        return {"scheme_id": [s["scheme_id"] for s in corpus.search(category=category, top_k=16)]}
    # Explicit category tokens are a corpus filter, never inferred profile facts.
    categories = [
        code
        for code in ("OBC", "EBC", "DNT", "SC", "ST", "SEBC")
        if re.search(r"\b" + code + r"\b", question, re.I)
    ]
    if categories:
        return {
            "scheme_id": list(
                dict.fromkeys(
                    s["scheme_id"]
                    for code in categories
                    for s in corpus.search(category=code, top_k=16)
                )
            )
        }
    query_terms = set(re.findall(r"[a-z]+", question.lower())) - COMMON
    scored = [
        (len(query_terms & (set(re.findall(r"[a-z]+", s["name"].lower())) - COMMON)), s)
        for s in corpus.records()
    ]
    best = max(score for score, _ in scored)
    if best >= 2 or any(
        t in query_terms for t in ("gate", "ceed", "yasasvi", "pragati", "saksham", "icar")
    ):
        return {"scheme_id": [s["scheme_id"] for score, s in scored if score == best and score]}
    return {}


def select_diverse(hits, top_k, scoped):
    """Keep nearest evidence; broad discovery gives distinct schemes a first turn."""
    if scoped:
        return [chunk for chunk, _ in hits[:top_k]]
    groups = {}
    for chunk, score in hits:
        groups.setdefault(chunk.scheme_id, []).append((chunk, score))
    selected = []
    while groups and len(selected) < top_k:
        for sid in list(groups):
            selected.append(groups[sid].pop(0)[0])
            if not groups[sid]:
                del groups[sid]
            if len(selected) == top_k:
                break
    return selected


def retrieve(question: str, scheme_ids=None, category=None, top_k=8) -> dict:
    started = time.perf_counter()
    filters = filters_for(question, scheme_ids, category)
    embed_ms = vector_ms = 0.0
    warnings = []
    chunks = []
    state = index_status()
    try:
        if not state["ready"]:
            raise ValueError(state["reason"])
        store = load_store(state["version"])
        t = time.perf_counter()
        vector = embed_query(question)
        embed_ms = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        hits = store.search(vector, min(64, top_k * 4), filters)
        vector_ms = (time.perf_counter() - t) * 1000
        hits = [(chunk, score) for chunk, score in hits if score >= 0.20]
        chunks = select_diverse(hits, top_k, len(filters.get("scheme_id", [])) == 1)
        # Fetch source notes for retrieved schemes through the same vector store.
        # This keeps conflicts visible even when their notes rank below benefits.
        ids = list(dict.fromkeys(c.scheme_id for c in chunks))
        if ids:
            t = time.perf_counter()
            notes = store.search(vector, 32, {"scheme_id": ids, "section": ["important_notes"]})
            vector_ms += (time.perf_counter() - t) * 1000
            existing = {c.chunk_id for c in chunks}
            for chunk, _ in notes:
                if chunk.chunk_id not in existing:
                    chunks.append(chunk)
                    existing.add(chunk.chunk_id)
    except Exception as exc:
        from core.observability import event

        event("vector_retrieval_failure", error_type=type(exc).__name__)
        chunks = []
        warnings.append(
            {
                "code": "VECTOR_UNAVAILABLE",
                "message": "Scholarship search is unavailable. Rebuild the scholarship index and try again.",
            }
        )
    return {
        "chunks": chunks,
        "warnings": warnings,
        "timings_ms": {
            "embedding": embed_ms,
            "vector_retrieval": vector_ms,
            "retrieval_total": (time.perf_counter() - started) * 1000,
        },
    }
