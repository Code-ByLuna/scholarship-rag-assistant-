import json
import time

import pytest
from apps.navigator.models import AgentExecution, LLMUsageLog
from core import memory
from core.agent.tools import RETRIEVAL_TOOL, Tool, ToolFailure, invoke
from core.agent.workflow import query
from core.llm import Generation, grounded_generation, validate_draft
from core.rag.documents import prepare_documents
from core.schemas import QueryRequest, SearchRequest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def rag(monkeypatch):
    chunks = [
        c
        for c in prepare_documents()
        if c.scheme_id == "pragati_scholarship_scheme_for_girl_students_technical_degree"
        and c.section == "benefits"
    ]
    contexts = []

    def retrieve(**kwargs):
        contexts.append(kwargs)
        return {"chunks": chunks, "warnings": [], "timings_ms": {}}

    monkeypatch.setattr("core.agent.tools.retrieve", retrieve)
    return chunks, contexts


@pytest.fixture
def generated(rag, monkeypatch):
    chunks, calls = rag
    seen = []
    text = "Pragati provides INR 50,000 per year to support educational expenses."

    class Good:
        name, model = "mock", "test"

        def generate(self, context):
            seen.append(context)
            if context.get("task") == "verify_grounding":
                return Generation(json.dumps({"supported": True, "issues": []}), 20, 5)
            return Generation(
                json.dumps(
                    {
                        "answer": text,
                        "status": "success",
                        "supports": [{"chunk_id": chunks[0].chunk_id, "quote": chunks[0].text}],
                    }
                ),
                20,
                50,
            )

    monkeypatch.setattr("core.llm.configured_providers", lambda: [Good()])
    return text, seen


def test_generated_answer_reaches_api_and_private_conversation(rag, generated):
    text, seen = generated
    client = APIClient()
    session = client.post("/api/sessions", {}, format="json").json()
    headers = {"HTTP_X_SESSION_TOKEN": session["session_token"]}
    first = client.post(
        "/api/agent/query",
        {"question": "Tell me about Pragati.", "session_id": session["session_id"]},
        format="json",
        **headers,
    )
    assert first.status_code == 200
    data = first.json()
    assert data["answer"] == text and data["status"] == "success"
    assert len(data["sources"]) == 1
    assert "profile" not in seen[0] and "eligibility" not in seen[0]
    assert seen[0]["sources"][0]["text"] == rag[0][0].text
    assert set(AgentExecution.objects.first().tools.values_list("name", flat=True)) == {
        "scholarship_retrieval"
    }
    assert set(LLMUsageLog.objects.values_list("phase", flat=True)) == {
        "generation",
        "verification",
    }
    second = client.post(
        "/api/agent/query",
        {"question": "How much does it provide?", "session_id": session["session_id"]},
        format="json",
        **headers,
    )
    assert second.status_code == 200
    assert rag[1][-1]["scheme_ids"] == [rag[0][0].scheme_id]
    assert any(m["role"] == "assistant" and m["text"] == text for m in seen[2]["conversation"])
    ctx = client.get("/api/sessions/" + session["session_id"], **headers).json()["context"]
    assert "profile" not in ctx and len(ctx["messages"]) == 4


def test_invalid_tool_arguments_persist_failure():
    execution = AgentExecution.objects.create(request_id="test")
    with pytest.raises(ToolFailure, match="INVALID_TOOL_ARGUMENTS"):
        invoke(RETRIEVAL_TOOL, {"top_k": -1}, execution)
    assert execution.tools.get().error_code == "INVALID_TOOL_ARGUMENTS"


def test_tool_timeout_is_bounded():
    execution = AgentExecution.objects.create(request_id="test")
    with pytest.raises(ToolFailure, match="TOOL_TIMEOUT"):
        invoke(Tool("slow", SearchRequest, lambda p: time.sleep(0.1)), {}, execution, timeout=0.001)
    assert execution.tools.count() == 2


def test_max_iterations_stops_safely(monkeypatch, rag):
    monkeypatch.setenv("AGENT_MAX_ITERATIONS", "1")
    result = query(QueryRequest(question="Pragati benefits"), "test")
    assert result.status == "error" and result.error.code == "MAX_AGENT_ITERATIONS"


@pytest.mark.parametrize(
    "support",
    [
        {"chunk_id": "invented", "quote": "invented"},
        {
            "chunk_id": "pragati_scholarship_scheme_for_girl_students_technical_degree:benefits:0",
            "quote": "Everyone receives INR 999999.",
        },
    ],
)
def test_unknown_or_unsupported_evidence_rejected(rag, support):
    with pytest.raises(ValueError):
        validate_draft(
            json.dumps({"answer": "Invented claim", "status": "success", "supports": [support]}),
            rag[0],
        )


def test_malformed_output_retries_then_returns_error(rag):
    class Broken:
        name, model = "mock", "test"
        calls = 0

        def generate(self, context):
            self.calls += 1
            return Generation("invalid-json", 12, 4)

    provider = Broken()
    execution = AgentExecution.objects.create(request_id="test")
    draft, warnings, _ = grounded_generation({}, rag[0], execution, [provider])
    assert draft is None and provider.calls == 2
    assert all(w["code"] == "LLM_RESPONSE_REJECTED" for w in warnings)
    assert execution.llm_calls.count() == 2


def test_correct_quote_cannot_hide_an_unsupported_paraphrase(rag):
    chunk = rag[0][0]

    class Misleading:
        name, model = "mock", "test"

        def generate(self, context):
            if context.get("task") == "verify_grounding":
                return Generation(
                    json.dumps({"supported": False, "issues": ["Unsupported amount and guarantee"]})
                )
            return Generation(
                json.dumps(
                    {
                        "answer": "You are guaranteed INR 10 lakh.",
                        "status": "success",
                        "supports": [{"chunk_id": chunk.chunk_id, "quote": chunk.text}],
                    }
                )
            )

    execution = AgentExecution.objects.create(request_id="test")
    draft, warnings, _ = grounded_generation({}, rag[0], execution, [Misleading()])
    assert draft is None and warnings[-1]["code"] == "LLM_RESPONSE_REJECTED"
    assert execution.llm_calls.filter(phase="verification", status="FAILED").count() == 2


def test_missing_key_is_explicit_error_without_a_fake_answer(monkeypatch, rag):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    answer = query(QueryRequest(question="Pragati benefits"), "test")
    assert answer.status == "error" and answer.error.code == "MISSING_API_KEY"
    assert answer.sources == [] and "50000" not in answer.answer


def test_off_topic_is_generated_even_without_sources(monkeypatch):
    monkeypatch.setattr(
        "core.agent.tools.retrieve",
        lambda **kwargs: {"chunks": [], "warnings": [], "timings_ms": {}},
    )

    class Maths:
        name, model = "mock", "test"

        def generate(self, context):
            if context.get("task") == "verify_grounding":
                return Generation('{"supported":true,"issues":[]}')
            return Generation(
                '{"answer":"1 + 2 = 3. You can also ask me about scholarships.","status":"out_of_scope","supports":[]}'
            )

    monkeypatch.setattr("core.llm.configured_providers", lambda: [Maths()])
    answer = query(QueryRequest(question="What is 1+2?"), "test")
    assert answer.status == "out_of_scope" and "3" in answer.answer and answer.sources == []


def test_vector_outage_does_not_bypass_rag(monkeypatch):
    monkeypatch.setattr(
        "core.agent.tools.retrieve",
        lambda **kwargs: {
            "chunks": [],
            "warnings": [
                {"code": "VECTOR_UNAVAILABLE", "message": "Scholarship search is unavailable."}
            ],
            "timings_ms": {},
        },
    )

    def never_called(*args):
        pytest.fail("LLM must not bypass failed semantic retrieval")

    monkeypatch.setattr("core.agent.workflow.grounded_generation", never_called)
    answer = query(QueryRequest(question="Pragati"), "test")
    assert answer.status == "error" and answer.error.code == "VECTOR_UNAVAILABLE"


def test_llm_disabled_returns_service_error(rag):
    client = APIClient()
    response = client.post("/api/agent/query", {"question": "Pragati"}, format="json")
    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "LLM_NOT_CONFIGURED"


def test_session_reference_survives_off_topic_turn(rag):
    session, _ = memory.create_session()
    source = dict(rag[0][0].citation)
    memory.save_turn(
        session, "Pragati?", {"answer": "Information", "sources": [source], "status": "success"}
    )
    memory.save_turn(session, "1+2?", {"answer": "3", "sources": [], "status": "out_of_scope"})
    assert memory.context(session)["scheme_ids"] == [rag[0][0].scheme_id]


def test_grounding_feedback_is_used_for_the_single_repair(rag):
    chunk = rag[0][0]
    contexts = []

    class Repair:
        name, model = "mock", "test"

        def generate(self, context):
            contexts.append(context)
            if context.get("task") == "verify_grounding":
                correct = (
                    context["proposed_answer"]["answer"] == "Pragati provides INR 50,000 per year."
                )
                return Generation(
                    json.dumps(
                        {"supported": correct, "issues": [] if correct else ["Unsupported amount"]}
                    )
                )
            text = (
                "Pragati provides INR 50,000 per year."
                if context.get("review_feedback")
                else "Pragati provides INR 10 lakh."
            )
            return Generation(
                json.dumps(
                    {
                        "answer": text,
                        "status": "success",
                        "supports": [{"chunk_id": chunk.chunk_id, "quote": chunk.text}],
                    }
                )
            )

    execution = AgentExecution.objects.create(request_id="repair-test")
    draft, warnings, _ = grounded_generation({}, rag[0], execution, [Repair()])
    assert draft.answer == "Pragati provides INR 50,000 per year."
    assert contexts[2]["repair"] and contexts[2]["review_feedback"]["issues"] == [
        "Unsupported amount"
    ]
    assert execution.llm_calls.count() == 4


def test_selected_scheme_context_does_not_override_a_new_named_topic(rag, generated):
    from core.corpus import records

    other = next(s["scheme_id"] for s in records() if "indira" in s["scheme_id"])
    result = query(
        QueryRequest(question="Tell me about Pragati.", context_scheme_id=other), "context-test"
    )
    assert result.status == "success"
    assert all("pragati" in sid for sid in rag[1][-1]["scheme_ids"])


def test_implicit_detail_question_uses_selected_scheme(rag, generated):
    sid = rag[0][0].scheme_id
    result = query(
        QueryRequest(question="How much does it provide?", context_scheme_id=sid), "context-test"
    )
    assert result.status == "success" and rag[1][-1]["scheme_ids"] == [sid]


def test_missing_fact_keeps_a_source_for_the_discussed_scholarship(rag):
    text = json.dumps(
        {
            "answer": "The application deadline is not specified.",
            "status": "insufficient_evidence",
            "supports": [],
        }
    )
    with pytest.raises(ValueError, match="source reference"):
        validate_draft(text, rag[0], [rag[0][0].scheme_id])


def test_grounding_review_must_examine_retrieved_source_notes():
    from core.llm import GroundingRejected, validate_review

    context = {
        "sources": [
            {
                "chunk_id": "notes:0",
                "section": "important_notes",
                "text": "Conflicting income limits.",
            }
        ]
    }
    with pytest.raises(GroundingRejected):
        validate_review('{"supported":true,"issues":[],"notes_examined":[]}', context)
    assert validate_review(
        '{"supported":true,"issues":[],"notes_examined":["notes:0"]}', context
    ).supported
