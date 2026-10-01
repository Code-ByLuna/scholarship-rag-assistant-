import pytest


@pytest.fixture(autouse=True)
def no_live_model_calls(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "none")
    monkeypatch.setenv("LLM_GROUNDING_REVIEW", "always")
