"""Gemini wire compatibility and safe, actionable failure diagnostics."""

import json
from types import SimpleNamespace

import httpx
import pytest
from apps.navigator.models import AgentExecution
from core.llm import GeminiProvider, grounded_generation, validate_draft
from google import genai
from google.genai import errors
from pydantic import ValidationError

pytestmark = pytest.mark.django_db


def test_gemini_sends_json_schema_and_preserves_strict_local_validation(monkeypatch):
    chunk = SimpleNamespace(chunk_id="probe:documents", text="Required: Aadhaar Card.")
    draft = {"fragments": [{"chunk_id": chunk.chunk_id, "quote": chunk.text}]}
    requests = []

    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        config = body["generationConfig"]
        assert "responseSchema" not in config
        schema = config["responseJsonSchema"]
        assert schema["additionalProperties"] is False
        assert schema["$defs"]["Quote"]["additionalProperties"] is False
        assert "additional_properties" not in json.dumps(body)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"role": "model", "parts": [{"text": json.dumps(draft)}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 8},
            },
        )

    real_client = genai.Client

    def client_with_transport(**kwargs):
        kwargs["http_options"].client_args = {"transport": httpx.MockTransport(handle)}
        return real_client(**kwargs)

    monkeypatch.setattr(genai, "Client", client_with_transport)
    result = GeminiProvider("gemini-test", "dummy-test-key").generate({"question": "Documents?"})
    assert len(requests) == 1
    assert validate_draft(result.text, [chunk]).fragments[0].quote == chunk.text
    assert (result.input_tokens, result.output_tokens) == (10, 8)
    with pytest.raises(ValidationError):
        validate_draft(json.dumps(dict(draft, invented_status="ELIGIBLE")), [chunk])
    with pytest.raises(ValidationError):
        invalid = {"fragments": [dict(draft["fragments"][0], extra="unsupported")]}
        validate_draft(json.dumps(invalid), [chunk])


@pytest.mark.parametrize(
    "status, expected",
    [
        (400, "LLM_REQUEST_INVALID"),
        (401, "LLM_AUTH_FAILED"),
        (403, "LLM_AUTH_FAILED"),
        (404, "LLM_MODEL_UNAVAILABLE"),
        (429, "LLM_RATE_LIMITED"),
        (503, "LLM_PROVIDER_UNAVAILABLE"),
    ],
)
def test_provider_errors_are_distinct_and_never_expose_details(status, expected, caplog):
    class Broken:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            raise errors.APIError(
                status, {"error": {"message": "SECRET credential and user profile"}}
            )

    provider = Broken()
    execution = AgentExecution.objects.create(request_id="diagnostics-test")
    draft, warnings, _ = grounded_generation({}, [], execution, [provider])
    assert draft is None
    assert all(w["code"] == expected for w in warnings)
    assert provider.calls == (2 if status >= 500 else 1)
    assert execution.llm_calls.count() == provider.calls
    assert "SECRET" not in json.dumps(warnings)
    for record in caplog.records:
        assert "SECRET" not in str(getattr(record, "details", {}))


def test_timeout_has_separate_warning_and_one_retry():
    class Slow:
        name, model = "gemini", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            raise httpx.ReadTimeout("SECRET request URL")

    provider = Slow()
    execution = AgentExecution.objects.create(request_id="timeout-test")
    draft, warnings, _ = grounded_generation({}, [], execution, [provider])
    assert draft is None and provider.calls == 2
    assert {w["code"] for w in warnings} == {"LLM_TIMEOUT"}
    assert "SECRET" not in json.dumps(warnings)
