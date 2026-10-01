"""Domain policy with semantic scores; actual model quality is evaluated separately."""

import numpy as np
import pytest
from core.rag import query as semantic


@pytest.mark.parametrize(
    "positive,negative,outside",
    [(0.8, 0.2, False), (0.15, 0.7, True), (0.19, 0.26, True), (0.5, 0.5, False)],
)
def test_embedding_domain_margin_policy(monkeypatch, positive, negative, outside):
    labels = ["domain", "other"] + list(semantic.INTENTS)
    vectors = np.zeros((len(labels), 2), dtype="float32")
    vectors[0, 0] = positive
    vectors[1, 0] = negative
    vectors[2, 0] = positive
    monkeypatch.setattr(semantic, "prototypes", lambda name: (labels, vectors))
    monkeypatch.setattr(semantic, "embed_query", lambda text: np.array([[1, 0]], dtype="float32"))
    monkeypatch.setattr("core.rag.retrieval.filters_for", lambda question: {})
    result = semantic.classify_query("semantic probe")
    assert result["out_of_scope"] is outside
    assert result["intent"] == ("benefits" if positive >= 0.28 else "general")
