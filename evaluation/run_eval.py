"""Reproducible corpus-based custom evaluation; no external evaluator or LLM needed."""
# ruff: noqa: E402

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

import numpy as np
from apps.navigator.models import AgentExecution, EvaluationRun
from core.agent.workflow import query
from core.corpus import fingerprint, records
from core.eligibility import evaluate_scheme
from core.rag.documents import prepare_documents
from core.rag.embeddings import model_name
from core.rag.retrieval import index_status, retrieve
from core.schemas import QueryRequest


def percentiles(values):
    return (
        {
            key: round(float(np.percentile(values, n)), 3)
            for key, n in [("p50", 50), ("p95", 95), ("p99", 99)]
        }
        if values
        else None
    )


def resolve(prefix):
    matches = [s for s in records() if s["scheme_id"].startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"Ambiguous fixture prefix: {prefix}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evaluation/reports/latest.json")
    args = parser.parse_args()
    profiles = json.loads((ROOT / "evaluation/profiles.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "evaluation/questions.json").read_text(encoding="utf-8"))
    expected = json.loads((ROOT / "evaluation/expected_results.json").read_text(encoding="utf-8"))
    chunks = {c.chunk_id: c for c in prepare_documents()}
    profile_results = []
    for case in profiles:
        scheme = resolve(case["scheme_prefix"])
        result = evaluate_scheme(scheme, case["profile"])
        profile_results.append(
            {
                "case": case["name"],
                "expected": case["expected"],
                "actual": result.status,
                "passed": result.status == case["expected"],
            }
        )
    # An evaluator contract fixture, not a scholarship added to the source corpus.
    toy = {
        "scheme_id": "operator_contract_only",
        "name": "Evaluator contract",
        "eligibility": {"gender": {"operator": "equals", "value": "female"}},
    }
    profile_results.append(
        {
            "case": "fully resolved generic rule contract",
            "expected": "ELIGIBLE",
            "actual": evaluate_scheme(toy, {"gender": "female"}).status,
            "passed": evaluate_scheme(toy, {"gender": "female"}).status == "ELIGIBLE",
        }
    )
    warm_started = time.perf_counter()
    retrieve("single girl child documents")  # Cold model/index startup is recorded separately.
    cold_ms = (time.perf_counter() - warm_started) * 1000
    metrics = {
        "embedding": [],
        "vector_retrieval": [],
        "retrieval_total": [],
        "complete_request": [],
    }
    question_results = []
    before_id = AgentExecution.objects.order_by("-id").values_list("id", flat=True).first() or 0
    for question in questions:
        truth = expected[question["id"]]
        sid = resolve(truth["scheme_prefix"])["scheme_id"]
        response = query(
            QueryRequest(question=question["question"], top_k=5), "evaluation-" + question["id"]
        )
        evidence = response.evidence
        hit = any(e.scheme_id == sid for e in evidence)
        relevant = [
            e
            for e in evidence
            if e.scheme_id == sid and (truth["section"] is None or e.section == truth["section"])
        ]
        supported = sum(
            e.chunk_id in chunks and e.text in chunks[e.chunk_id].text for e in evidence
        )
        citations_ok = bool(response.citations) and all(
            c.scheme_id in {s["scheme_id"] for s in records()}
            and (c.retrieved_from in chunks or c.retrieved_from.endswith(":eligibility"))
            and c.source_url
            == (
                next(s for s in records() if s["scheme_id"] == c.scheme_id)
                .get("source", {})
                .get("source_url")
                or None
            )
            for c in response.citations
        )
        for key in metrics:
            metrics[key].append(response.timings_ms.get(key, 0))
        failed = any(
            w.code in ("AGENT_FAILURE", "MAX_AGENT_ITERATIONS", "TOOL_TIMEOUT", "TOOL_FAILED")
            for w in response.warnings
        )
        question_results.append(
            {
                "id": question["id"],
                "question": question["question"],
                "retrieval_hit": hit,
                "answer_relevant": bool(relevant),
                "context_relevance": len(relevant) / len(evidence) if evidence else 0,
                "grounding": supported / len(evidence) if evidence else 0,
                "citation_correct": citations_ok,
                "agent_failed": failed,
                "mode": response.explanation_state,
                "warnings": [w.code for w in response.warnings],
            }
        )
    n = len(question_results)
    eligibility = sum(c["passed"] for c in profile_results) / len(profile_results)

    def average(key):
        return sum(float(r[key]) for r in question_results) / n

    scores = {
        "eligibility_correctness": eligibility,
        "retrieval_hit_rate": average("retrieval_hit"),
        "answer_relevance": average("answer_relevant"),
        "context_relevance": average("context_relevance"),
        "faithfulness_exact_source_quotes": average("grounding"),
        "citation_correctness": average("citation_correct"),
        "unsupported_excerpt_rate": 1 - average("grounding"),
        "agent_failure_rate": average("agent_failed"),
    }
    overall = np.mean(
        [
            eligibility,
            scores["retrieval_hit_rate"],
            scores["answer_relevance"],
            scores["context_relevance"],
            scores["faithfulness_exact_source_quotes"],
            scores["citation_correctness"],
            1 - scores["agent_failure_rate"],
        ]
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": fingerprint(),
        "embedding_model": model_name(),
        "vector_index": index_status(),
        "environment": {
            "database": django.db.connection.vendor,
            "llm_provider": os.getenv("LLM_PROVIDER", "none"),
            "platform": sys.platform,
        },
        "counts": {"profiles": len(profile_results), "questions": n},
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "overall_score": round(float(overall), 4),
        "target_met": bool(overall >= 0.8),
        "cold_start_ms": round(cold_ms, 3),
        "latency_ms": {key: percentiles(values) for key, values in metrics.items()},
        "llm_latency_ms": None
        if os.getenv("LLM_PROVIDER", "none") == "none"
        else percentiles(
            list(
                AgentExecution.objects.filter(id__gt=before_id).values_list(
                    "llm_calls__latency_ms", flat=True
                )
            )
        ),
        "limitations": [
            "Custom deterministic harness, not RAGAS or a human semantic assessment.",
            "Eligibility fixtures include one toy evaluator contract; it is not a source scholarship.",
            "Faithfulness tests exact quote support; they do not prove complete answers.",
            "No live LLM latency/cost measured when LLM_PROVIDER=none.",
            "Warm process measurements are local observations, not an SLA.",
        ],
        "profile_results": profile_results,
        "question_results": question_results,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    EvaluationRun.objects.create(report=report)
    print(
        json.dumps(
            {
                key: report[key]
                for key in ["counts", "scores", "overall_score", "target_met", "latency_ms"]
            },
            indent=2,
        )
    )
    return 0 if report["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
