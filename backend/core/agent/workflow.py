"""Single bounded LangGraph workflow: plan -> retrieve -> rules -> validate."""

import os
import re
import time
from typing import Any, TypedDict

from apps.navigator.models import AgentExecution
from langgraph.graph import END, START, StateGraph

from core import corpus, memory
from core.agent.tools import ELIGIBILITY_TOOL, RETRIEVAL_TOOL, ToolFailure, invoke
from core.llm import grounded_generation
from core.observability import event
from core.schemas import Citation, Evidence, ScholarshipAnswer


class State(TypedDict, total=False):
    question: str
    profile: dict | None
    scheme_ids: list[str] | None
    category: str | None
    top_k: int
    history: dict
    execution: Any
    chunks: list
    results: list
    warnings: list
    timings: dict
    answer: ScholarshipAnswer
    iterations: int


def step(state):
    if state.get("iterations", 0) >= int(os.getenv("AGENT_MAX_ITERATIONS", "6")):
        raise RuntimeError("MAX_AGENT_ITERATIONS")
    return state.get("iterations", 0) + 1


def plan(state: State):
    iteration = step(state)
    updates = {"iterations": iteration}
    question = state["question"]
    previous = state.get("history", {})
    if state.get("profile") is None and previous.get("profile"):
        updates["profile"] = previous["profile"]
    explicit = __import__("core.rag.retrieval", fromlist=["filters_for"]).filters_for(question)
    pronoun = re.search(r"\b(this|that|it|these)\b|^how (do|can) i apply", question, re.I)
    if not state.get("scheme_ids") and pronoun and not explicit:
        previous_ids = previous.get("scheme_ids", [])
        if len(previous_ids) == 1:
            updates["scheme_ids"] = previous_ids
        elif len(previous_ids) > 1:
            updates["scheme_ids"] = []
            updates["warnings"] = state["warnings"] + [
                {
                    "code": "AMBIGUOUS_REFERENCE",
                    "message": "Please select a scholarship to resolve this reference.",
                }
            ]
    return updates


def retrieve_node(state: State):
    iteration = step(state)
    try:
        retrieved = invoke(
            RETRIEVAL_TOOL,
            {
                "question": state["question"],
                "scheme_ids": state.get("scheme_ids"),
                "category": state.get("category"),
                "top_k": state["top_k"],
            },
            state["execution"],
        )
        event("retrieval_result", count=len(retrieved["chunks"]))
        return {
            "iterations": iteration,
            "chunks": retrieved["chunks"],
            "warnings": state["warnings"] + retrieved["warnings"],
            "timings": retrieved["timings_ms"],
        }
    except ToolFailure as exc:
        return {
            "iterations": iteration,
            "chunks": [],
            "warnings": state["warnings"]
            + [
                {
                    "code": exc.code,
                    "message": "Scholarship retrieval failed; no unsupported answer will be generated.",
                }
            ],
        }


def eligibility_node(state: State):
    iteration = step(state)
    # Both retrieval and deterministic eligibility are real tools on every query.
    ids = state.get("scheme_ids")
    if ids is None:
        ids = list(dict.fromkeys(c.scheme_id for c in state.get("chunks", [])))
    if (
        state.get("profile")
        and re.search(r"\b(eligible|qualify|eligibility|match)\b", state["question"], re.I)
        and state.get("scheme_ids") is None
    ):
        ids = [s["scheme_id"] for s in corpus.records()]
    try:
        results = invoke(
            ELIGIBILITY_TOOL,
            {"profile": state.get("profile") or {}, "scheme_ids": ids},
            state["execution"],
        )
        return {"iterations": iteration, "results": results}
    except ToolFailure as exc:
        return {
            "iterations": iteration,
            "results": [],
            "warnings": state["warnings"]
            + [
                {
                    "code": exc.code,
                    "message": "Eligibility could not be checked; no eligibility claim is made.",
                }
            ],
        }


def answer_node(state: State):
    iteration = step(state)
    chunks = state.get("chunks", [])
    warnings = list(state["warnings"])
    ids = list(
        dict.fromkeys(
            [c.scheme_id for c in chunks] + [r.scheme_id for r in state.get("results", [])]
        )
    )
    for sid in ids:
        for note in corpus.detail(sid).get("important_notes", []):
            if any(t in note.lower() for t in ("discrepancy", "review", "while the eligibility")):
                warnings.append({"code": "SOURCE_CONTRADICTION", "message": note})
    context = {
        "question": state["question"],
        "profile": state.get("profile"),
        "eligibility": [
            {
                "scheme_id": r.scheme_id,
                "status": r.status,
                "missing_information": r.missing_information,
            }
            for r in state.get("results", [])
        ],
        "sources": [{"chunk_id": c.chunk_id, "text": c.text} for c in chunks],
        "conversation": [
            {"role": m["role"], "question": m["content"].get("question")}
            for m in state.get("history", {}).get("messages", [])
        ],
    }
    # Approximate input size guard; provider output tokens have an independent hard limit.
    import json

    if len(json.dumps(context)) > int(os.getenv("LLM_MAX_INPUT_CHARS", "24000")):
        warnings.append(
            {
                "code": "LLM_CONTEXT_LIMIT",
                "message": "Context exceeded the LLM limit; source excerpts used.",
            }
        )
        draft, llm_ms = None, 0.0
    elif chunks:
        draft, llm_warnings, llm_ms = grounded_generation(context, chunks, state["execution"])
        warnings.extend(llm_warnings)
    else:
        draft, llm_ms = None, 0.0
    if draft:
        by_id = {c.chunk_id: c for c in chunks}
        selected = [(by_id[f.chunk_id], f.quote) for f in draft.fragments]
        mode = "GROUNDED"
    else:
        selected = [(c, c.text[:1600]) for c in chunks]
        mode = "DETERMINISTIC_FALLBACK" if chunks else "INSUFFICIENT_SOURCES"
    if selected:
        answer_text = "\n\n".join(c.scheme_name + " \u2014 " + text for c, text in selected)
    else:
        answer_text = (
            "The available scholarship data does not contain enough information to answer this."
        )
    citations = [Citation.model_validate(c.citation) for c, _ in selected]
    cited_ids = {c.scheme_id for c in citations}
    for result in state.get("results", []):
        if result.scheme_id not in cited_ids:
            citations.append(
                corpus.citation(corpus.detail(result.scheme_id), result.scheme_id + ":eligibility")
            )
    documents = {
        c.scheme_id: corpus.detail(c.scheme_id).get("documents_required", [])
        for c in chunks
        if c.section == "documents_required"
    }
    answer = ScholarshipAnswer(
        answer=answer_text,
        scheme_ids=ids,
        citations=citations,
        eligibility=state.get("results", []),
        required_documents=documents,
        evidence=[
            Evidence(chunk_id=c.chunk_id, scheme_id=c.scheme_id, section=c.section, text=t)
            for c, t in selected
        ],
        explanation_state=mode,
        warnings=warnings,
        timings_ms=dict(state.get("timings", {}), llm=llm_ms),
    )
    return {"iterations": iteration, "answer": answer}


def build_graph():
    graph = StateGraph(State)
    for name, node in [
        ("plan", plan),
        ("retrieve", retrieve_node),
        ("eligibility", eligibility_node),
        ("answer", answer_node),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "eligibility")
    graph.add_edge("eligibility", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


GRAPH = build_graph()


def query(payload, request_id: str, session=None) -> ScholarshipAnswer:
    started = time.perf_counter()
    execution = AgentExecution.objects.create(session=session, request_id=request_id)
    previous = memory.context(session) if session else {}
    profile = (
        payload.profile.model_dump() if payload.profile is not None else previous.get("profile")
    )
    status = "FAILED"
    try:
        result = GRAPH.invoke(
            {
                "question": payload.question,
                "profile": profile,
                "scheme_ids": payload.scheme_ids,
                "category": payload.category,
                "top_k": payload.top_k,
                "history": previous,
                "execution": execution,
                "warnings": [],
                "timings": {},
                "iterations": 0,
            },
            config={"recursion_limit": max(2, int(os.getenv("AGENT_MAX_ITERATIONS", "6")) + 1)},
        )
        answer = result["answer"]
        status = "SUCCESS" if not answer.warnings else "DEGRADED"
    except Exception as exc:
        code = (
            "MAX_AGENT_ITERATIONS"
            if "MAX_AGENT_ITERATIONS" in str(exc) or type(exc).__name__ == "GraphRecursionError"
            else "AGENT_FAILURE"
        )
        event("agent_failure", error_type=type(exc).__name__, code=code)
        answer = ScholarshipAnswer(
            answer="The assistant could not complete this request. Try scholarship search or profile matching.",
            scheme_ids=[],
            citations=[],
            explanation_state="INSUFFICIENT_SOURCES",
            warnings=[{"code": code, "message": "The bounded agent stopped safely."}],
        )
    finally:
        execution.status = status
        execution.latency_ms = (time.perf_counter() - started) * 1000
        execution.save(update_fields=["status", "latency_ms"])
    answer.request_id = request_id
    answer.session_id = str(session.id) if session else None
    answer.timings_ms["complete_request"] = (time.perf_counter() - started) * 1000
    # Final Pydantic validation is mandatory for both LLM and fallback responses.
    answer = ScholarshipAnswer.model_validate(answer.model_dump())
    if session:
        memory.save_turn(session, payload.question, answer.model_dump(), profile)
    event(
        "agent_execution",
        session_id=answer.session_id,
        status=status,
        latency_ms=answer.timings_ms["complete_request"],
    )
    return answer
