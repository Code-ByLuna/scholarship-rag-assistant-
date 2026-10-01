"""Conversational LangGraph: query context -> semantic retrieval -> grounded LLM."""

import json
import os
import re
import time
from typing import Any, TypedDict

from apps.navigator.models import AgentExecution
from langgraph.graph import END, START, StateGraph

from core import corpus, memory
from core.agent.tools import RETRIEVAL_TOOL, ToolFailure, invoke
from core.llm import grounded_generation
from core.observability import event
from core.rag.retrieval import filters_for
from core.schemas import Citation, ScholarshipAnswer


class State(TypedDict, total=False):
    question: str
    retrieval_question: str
    context_scheme_id: str | None
    scheme_ids: list[str] | None
    category: str | None
    top_k: int
    history: dict
    execution: Any
    chunks: list
    warnings: list
    timings: dict
    answer: ScholarshipAnswer
    iterations: int


def step(state):
    if state.get("iterations", 0) >= int(os.getenv("AGENT_MAX_ITERATIONS", "6")):
        raise RuntimeError("MAX_AGENT_ITERATIONS")
    return state.get("iterations", 0) + 1


def plan(state: State):
    question = state["question"]
    previous_ids = (
        [state["context_scheme_id"]]
        if state.get("context_scheme_id")
        else state.get("history", {}).get("scheme_ids", [])
    )
    explicit = filters_for(question)
    ids = state.get("scheme_ids")
    if ids is None and explicit:
        ids = explicit["scheme_id"]
    # Query expansion uses conversation references only, never a personal profile.
    follow_up = bool(re.search(r"\b(it|this|that|these|those)\b", question, re.I)) or (
        len(question.split()) <= 10
        and not re.search(r"\b(scholarships|schemes|students)\b", question, re.I)
    )
    if ids is None and previous_ids and follow_up:
        ids = previous_ids
    retrieval_question = question
    if ids:
        names = "; ".join(s["name"] for s in corpus.records(ids))
        retrieval_question += "\nScholarships under discussion: " + names
    return {"iterations": step(state), "scheme_ids": ids, "retrieval_question": retrieval_question}


def retrieve_node(state: State):
    try:
        retrieved = invoke(
            RETRIEVAL_TOOL,
            {
                "question": state["retrieval_question"],
                "scheme_ids": state.get("scheme_ids"),
                "category": state.get("category"),
                "top_k": state["top_k"],
            },
            state["execution"],
        )
        event("retrieval_result", count=len(retrieved["chunks"]), semantic=True)
        return {
            "iterations": step(state),
            "chunks": retrieved["chunks"],
            "warnings": retrieved["warnings"],
            "timings": retrieved["timings_ms"],
        }
    except ToolFailure as exc:
        return {
            "iterations": step(state),
            "chunks": [],
            "warnings": [
                {
                    "code": exc.code,
                    "message": "Scholarship search could not complete. Please try again.",
                }
            ],
        }


def failure_answer(code, message):
    return ScholarshipAnswer(
        answer=message, sources=[], status="error", error={"code": code, "message": message}
    )


def answer_node(state: State):
    iteration = step(state)
    if state.get("warnings"):
        problem = state["warnings"][-1]
        return {
            "iterations": iteration,
            "answer": failure_answer(problem["code"], problem["message"]),
        }
    chunks = state.get("chunks", [])
    history = [
        {"role": m["role"], "text": m["content"].get("question", m["content"].get("answer", ""))}
        for m in state.get("history", {}).get("messages", [])
        if m["content"].get("status") != "error"
    ]
    context = {
        "question": state["question"],
        "focus_scheme_ids": state.get("scheme_ids"),
        "conversation": history,
        "sources": [
            {
                "chunk_id": c.chunk_id,
                "scheme_id": c.scheme_id,
                "scholarship": c.scheme_name,
                "section": c.section,
                "text": c.text,
                "source_url": c.citation.get("source_url"),
            }
            for c in chunks
        ],
    }
    max_chars = int(os.getenv("LLM_MAX_INPUT_CHARS", "24000"))
    while context["conversation"] and len(json.dumps(context, ensure_ascii=False)) > max_chars:
        context["conversation"].pop(0)
    if len(json.dumps(context, ensure_ascii=False)) > max_chars:
        return {
            "iterations": iteration,
            "answer": failure_answer(
                "LLM_CONTEXT_LIMIT",
                "The question covers too much scholarship information. Please narrow it to a few schemes.",
            ),
        }
    event(
        "rag_context",
        source_count=len(chunks),
        history_messages=len(context["conversation"]),
        context_characters=len(json.dumps(context, ensure_ascii=False)),
    )
    draft, problems, llm_ms = grounded_generation(context, chunks, state["execution"])
    if draft is None:
        problem = problems[-1]
        answer = failure_answer(problem["code"], problem["message"])
    else:
        by_id = {c.chunk_id: c for c in chunks}
        sources = []
        seen = set()
        for support in draft.supports:
            if (support.chunk_id, support.quote) not in seen:
                cited = Citation.model_validate(by_id[support.chunk_id].citation)
                cited.excerpt = support.quote
                sources.append(cited)
                seen.add((support.chunk_id, support.quote))
        # Render exactly the validated generated text; never replace it with quotes.
        answer = ScholarshipAnswer(answer=draft.answer, sources=sources, status=draft.status)
    event(
        "answer_returned",
        status=answer.status,
        source_count=len(answer.sources),
        answer_characters=len(answer.answer),
        llm_ms=llm_ms,
    )
    return {"iterations": iteration, "answer": answer}


def build_graph():
    graph = StateGraph(State)
    for name, node in [("plan", plan), ("retrieve", retrieve_node), ("answer", answer_node)]:
        graph.add_node(name, node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


GRAPH = build_graph()


def query(payload, request_id: str, session=None) -> ScholarshipAnswer:
    started = time.perf_counter()
    execution = AgentExecution.objects.create(session=session, request_id=request_id)
    execution_status = "FAILED"
    try:
        state = GRAPH.invoke(
            {
                "question": payload.question,
                "context_scheme_id": payload.context_scheme_id,
                "scheme_ids": payload.scheme_ids,
                "category": payload.category,
                "top_k": payload.top_k,
                "history": memory.context(session) if session else {},
                "execution": execution,
                "warnings": [],
                "timings": {},
                "iterations": 0,
            },
            config={"recursion_limit": max(2, int(os.getenv("AGENT_MAX_ITERATIONS", "6")) + 1)},
        )
        answer = state["answer"]
        execution_status = "SUCCESS" if answer.status != "error" else "FAILED"
    except Exception as exc:
        code = (
            "MAX_AGENT_ITERATIONS"
            if str(exc) == "MAX_AGENT_ITERATIONS" or type(exc).__name__ == "GraphRecursionError"
            else "AGENT_FAILURE"
        )
        event("agent_failure", error_type=type(exc).__name__, code=code)
        answer = failure_answer(
            code, "The assistant could not complete this question. Please try again."
        )
    finally:
        execution.status = execution_status
        execution.latency_ms = (time.perf_counter() - started) * 1000
        execution.save(update_fields=["status", "latency_ms"])
    answer.request_id = request_id
    answer.session_id = str(session.id) if session else None
    answer = ScholarshipAnswer.model_validate(answer.model_dump())
    if session:
        memory.save_turn(session, payload.question, answer.model_dump())
    event("agent_execution", status=execution_status, latency_ms=execution.latency_ms)
    return answer
