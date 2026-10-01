"""Separate semantic-retrieval evaluation from explicitly enabled live RAG checks."""

# ruff: noqa: E402
import argparse
import json
import os
import re
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
from apps.navigator.models import EvaluationRun
from core import corpus, memory
from core.agent.workflow import query
from core.rag.documents import prepare_documents
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call configured Gemini for 16 RAG acceptance cases and conversation setup turns.",
    )
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--only", action="append", help="Run one named acceptance case; may be repeated."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=20,
        help="Seconds between live cases/setup turns; avoids provider rate limits.",
    )
    args = parser.parse_args()
    started = time.perf_counter()
    documents = {c.chunk_id: c for c in prepare_documents()}
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus.fingerprint(),
        "index": index_status(),
        "mode": "live_rag" if args.live else "semantic_retrieval",
        "results": [],
    }
    if not args.live:
        questions = json.loads((ROOT / "evaluation/questions.json").read_text(encoding="utf-8"))
        expected = json.loads(
            (ROOT / "evaluation/expected_results.json").read_text(encoding="utf-8")
        )
        for item in questions:
            result = retrieve(item["question"])
            truth = expected[item["id"]]
            relevant = [
                c
                for c in result["chunks"]
                if c.scheme_id.startswith(truth["scheme_prefix"])
                and (truth["section"] is None or c.section == truth["section"])
            ]
            report["results"].append(
                {
                    "id": item["id"],
                    "retrieval_hit": bool(relevant),
                    "passed": bool(relevant) and not result["warnings"],
                    "chunk_ids": [c.chunk_id for c in result["chunks"]],
                    "warnings": result["warnings"],
                    "timings_ms": result["timings_ms"],
                }
            )
        report["limitations"] = (
            "Retrieval-only measurements; no generation, answer accuracy or eligibility-decision score is claimed."
        )
    else:
        cases = json.loads((ROOT / "evaluation/rag_cases.json").read_text(encoding="utf-8"))
        if args.only:
            cases = [case for case in cases if case["id"] in args.only]
            if len(cases) != len(set(args.only)):
                raise ValueError("Unknown acceptance case ID.")
        for case_index, case in enumerate(cases):
            if case_index and args.delay > 0:
                time.sleep(min(args.delay, 60))
            session, _ = memory.create_session()
            try:
                setup = None
                if case.get("prepare"):
                    setup = query(
                        QueryRequest(question=case["prepare"]),
                        "acceptance-" + case["id"] + "-setup",
                        session,
                    )
                if case.get("prepare") and args.delay > 0:
                    time.sleep(min(args.delay, 60))
                t = time.perf_counter()
                response = query(
                    QueryRequest(question=case["question"]), "acceptance-" + case["id"], session
                )
                duration = (time.perf_counter() - t) * 1000
                data = response.model_dump()
                ids = {s.scheme_id for s in response.sources}
                exact_evidence = all(
                    s.retrieved_from in documents
                    and s.excerpt
                    and s.excerpt in documents[s.retrieved_from].text
                    for s in response.sources
                )
                checked = {
                    "status": response.status in case["status"],
                    "expected_sources": not case.get("prefix")
                    or any(s.startswith(case["prefix"]) for s in ids),
                    "source_count": len(ids) >= case.get("min_schemes", 0),
                    "no_irrelevant_off_topic_sources": not case.get("no_sources") or not ids,
                    "evidence_traceable": exact_evidence,
                    "expected_facts": all(
                        re.search(pattern, response.answer, re.I)
                        for pattern in case.get("patterns", [])
                    ),
                    "setup_success": setup is None or setup.status == "success",
                }
                entry = {
                    "id": case["id"],
                    "question": case["question"],
                    "passed": all(checked.values()),
                    "checks": checked,
                    "response": data,
                    "latency_ms": round(duration, 3),
                }
                report["results"].append(entry)
                print(case["id"] + ": " + ("PASS" if entry["passed"] else "FAIL"), flush=True)
            finally:
                # Acceptance sessions are disposable; retained audit rows have no profiles/text.
                session.delete()
        report["provider"] = os.getenv("LLM_PROVIDER", "none")
        report["model"] = os.getenv("LLM_MODEL", "")
        report["limitations"] = (
            "Live source checks, factual spot checks, and model grounding review are not a proof that every paraphrase is correct. No official eligibility decisions are made."
        )
    report["passed"] = sum(r["passed"] for r in report["results"])
    report["total"] = len(report["results"])
    report["latency_ms"] = percentiles(
        [
            r.get("latency_ms", r.get("timings_ms", {}).get("retrieval_total", 0))
            for r in report["results"]
        ]
    )
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    output = ROOT / (
        args.output
        or ("evaluation/reports/live_rag.json" if args.live else "evaluation/reports/latest.json")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    EvaluationRun.objects.create(report=report)
    print(f"{report['passed']}/{report['total']} cases passed; report: {output.name}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
