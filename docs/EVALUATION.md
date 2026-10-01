# Evaluation and latency

Run python evaluation/run_eval.py after migrations and ingestion. It writes the
actual JSON report to evaluation/reports/latest.json and an EvaluationRun record.
Fixtures are committed separately: 33 corpus-based profiles plus one fully resolved
toy rule contract and 30 natural-language questions with manually specified expected
scheme prefixes and sections. The toy contract is explicitly not corpus knowledge.

Custom deterministic evaluation is used instead of RAGAS: retrieval scheme hit rate,
section answer relevance, context relevance, exact quote grounding, citation integrity,
eligibility accuracy, unsupported excerpt rate, failure rate. The overall score is
the unweighted mean of eligibility, retrieval hit, answer relevance, grounding,
citations, context relevance and nonfailure; target 0.80. All scores are reported.

Exact quote grounding is a narrow hallucination proxy, not a guarantee of answer
completeness or semantic relevance. Profile expected states are based on the supplied
corpus. Real records have residual verification requirements; the suite never labels
those definitely eligible merely to improve scores.

Cold model startup is recorded separately. Warm embedding, vector, retrieval-total,
and complete-request P50/P95/P99 are measured from actual questions. LLM latency is
null without a live provider. The local retrieval target of 200ms is architectural,
not an unmeasured SLA. CI tests use explicit corpus fallback for isolation; the
evaluation command uses the persisted real sentence-transformer/FAISS index.

Run python -m pytest for unit, API/database, vector persistence, tools, malformed LLM,
fallback, session continuation, and adversarial tests. Frontend: npm test; npm run build.
