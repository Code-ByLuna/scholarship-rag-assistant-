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


def test_index_failure_is_explicit_and_never_uses_keyword_answers(monkeypatch):
    monkeypatch.setattr(
        "core.rag.retrieval.index_status", lambda: {"ready": False, "reason": "missing"}
    )
    result = retrieve("documents for single girl child scholarship")
    assert result["warnings"][0]["code"] == "VECTOR_UNAVAILABLE"
    assert result["chunks"] == []


def test_category_filters_before_search():
    ids = filters_for("scholarships for OBC students")["scheme_id"]
    assert ids and all("yasasvi" in sid for sid in ids)


def test_unknown_scheme_filter_rejected():
    with pytest.raises(ValueError):
        retrieve("anything", ["invalid"])


def test_semantic_search_keeps_conflicting_notes(monkeypatch):
    chunks = prepare_documents()
    sid = "pre_matric_scholarship_for_scheduled_tribe_students"
    eligible = next(c for c in chunks if c.scheme_id == sid and c.section == "eligibility")
    note = next(c for c in chunks if c.scheme_id == sid and c.section == "important_notes")
    searches = []

    class Store:
        def search(self, vector, count, filters):
            searches.append(filters)
            return [(note, 0.25)] if filters.get("section") else [(eligible, 0.9)]

    monkeypatch.setattr(
        "core.rag.retrieval.index_status", lambda: {"ready": True, "version": "test"}
    )
    monkeypatch.setattr("core.rag.retrieval.load_store", lambda version: Store())
    monkeypatch.setattr(
        "core.rag.retrieval.embed_query", lambda question: np.zeros((1, 2), dtype="float32")
    )
    result = retrieve("income limit", scheme_ids=[sid])
    assert result["chunks"] == [eligible, note]
    assert len(searches) == 2 and "2.00 lakh" in note.text and "2.50 lakh" in note.text


def test_discovery_diversifies_semantic_results():
    from core.rag.retrieval import select_diverse

    chunks = prepare_documents()
    first = chunks[0]
    same = next(c for c in chunks[1:] if c.scheme_id == first.scheme_id)
    other = next(c for c in chunks if c.scheme_id != first.scheme_id)
    selected = select_diverse([(first, 0.9), (same, 0.8), (other, 0.7)], 2, False)
    assert selected == [first, other]


def test_sc_st_filter_includes_both_categories():
    ids = filters_for("scholarships for SC/ST students")["scheme_id"]
    assert any("scheduled_tribe_students" in sid for sid in ids)
    assert any("scheduled_caste" in sid for sid in ids)
