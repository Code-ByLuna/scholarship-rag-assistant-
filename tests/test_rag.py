import numpy as np
import pytest
from core.rag.documents import prepare_documents
from core.rag.retrieval import filters_for, retrieve
from core.rag.vector_store import FAISSVectorStore


def test_chunk_provenance():
    chunks = prepare_documents()
    assert len(chunks) > 16
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    for c in chunks:
        assert c.citation["scheme_id"] == c.scheme_id
        assert c.citation["retrieved_from"] == c.chunk_id
        assert c.citation["original_record_key"]


def test_vector_persistence_and_filter(tmp_path):
    chunks = prepare_documents()[:3]
    vectors = np.eye(3, dtype="float32")
    store = FAISSVectorStore(vectors, chunks)
    store.save(tmp_path, {"test": True})
    loaded, metadata = FAISSVectorStore.load(tmp_path)
    hits = loaded.search(vectors[:1], 3, {"section": [chunks[0].section]})
    assert all(c.section == chunks[0].section for c, _ in hits)
    assert metadata["test"] is True


def test_empty_metadata_filter():
    store = FAISSVectorStore(np.eye(2, dtype="float32"), prepare_documents()[:2])
    assert store.search(np.eye(2, dtype="float32")[:1], 2, {"scheme_id": []}) == []


def test_index_failure_has_explicit_corpus_fallback(monkeypatch):
    monkeypatch.setattr(
        "core.rag.retrieval.index_status", lambda: {"ready": False, "reason": "missing"}
    )
    result = retrieve("documents for single girl child scholarship")
    assert result["warnings"][0]["code"] == "VECTOR_UNAVAILABLE"
    assert result["chunks"]
    assert all(c.section == "documents_required" for c in result["chunks"])


def test_category_filters_before_search():
    ids = filters_for("scholarships for OBC students")["scheme_id"]
    assert ids and all("yasasvi" in sid for sid in ids)


def test_unknown_scheme_filter_rejected():
    with pytest.raises(ValueError):
        retrieve("anything", ["invalid"])
