"""Semantic retrieval with scheme metadata filters and explicit lexical fallback."""

import os
import re
import time
from functools import lru_cache
from pathlib import Path

from core import corpus
from core.rag.documents import prepare_documents
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
    for code in ("OBC", "EBC", "DNT", "SC", "ST", "SEBC"):
        if re.search(r"\b" + code + r"\b", question, re.I):
            return {"scheme_id": [s["scheme_id"] for s in corpus.search(category=code, top_k=16)]}
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


def section_filter(question):
    lower = question.lower()
    if "document" in lower:
        return ["documents_required"]
    if (
        any(t in lower for t in ("how do", "how to", "procedure", "apply", "application"))
        and "can " not in lower
    ):
        return ["application", "important_notes"]
    if any(t in lower for t in ("how much", "benefit", "amount", "provide")):
        return ["benefits", "important_notes"]
    if any(
        t in lower
        for t in ("income", "require", "qualify", "eligible", "eligibility", "gate", "ceed", "year")
    ):
        return ["eligibility", "exclusions", "important_notes"]
    return None


def lexical_fallback(question, filters, top_k):
    terms = set(re.findall(r"[a-z0-9]+", question.lower())) - COMMON
    chunks = [c for c in prepare_documents() if all(getattr(c, k) in v for k, v in filters.items())]
    scored = [(sum(t in (c.scheme_name + " " + c.text).lower() for t in terms), c) for c in chunks]
    return [c for score, c in sorted(scored, key=lambda p: p[0], reverse=True)[:top_k] if score > 0]


def retrieve(question: str, scheme_ids=None, category=None, top_k=5) -> dict:
    started = time.perf_counter()
    filters = filters_for(question, scheme_ids, category)
    sections = section_filter(question)
    if sections:
        filters["section"] = sections
    embed_ms = 0.0
    vector_ms = 0.0
    warnings = []
    state = index_status()
    try:
        if not state["ready"]:
            raise ValueError(state["reason"])
        store = load_store(state["version"])
        t = time.perf_counter()
        vector = embed_query(question)
        embed_ms = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        hits = store.search(vector, top_k, filters)
        vector_ms = (time.perf_counter() - t) * 1000
        chunks = [chunk for chunk, score in hits if score >= 0.12]
    except Exception as exc:
        from core.observability import event

        event("vector_retrieval_failure", error_type=type(exc).__name__)
        warnings.append(
            {
                "code": "VECTOR_UNAVAILABLE",
                "message": "Semantic retrieval unavailable; corpus text search used.",
            }
        )
        chunks = lexical_fallback(question, filters, top_k)
    return {
        "chunks": chunks,
        "warnings": warnings,
        "timings_ms": {
            "embedding": embed_ms,
            "vector_retrieval": vector_ms,
            "retrieval_total": (time.perf_counter() - started) * 1000,
        },
    }
