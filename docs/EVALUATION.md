# Evaluation

`python evaluation/run_eval.py` evaluates 30 manually annotated retrieval questions
against the actual persisted FAISS index and sentence-transformer model. The report
in `evaluation/reports/latest.json` measures scheme/section hits and retrieval timing.
It does not call a language model or claim answer correctness from retrieved quotes.

`python evaluation/run_eval.py --live --delay 20` runs 16 acceptance cases against
configured Gemini, including the requested 10 examples, a second contradiction case,
and postgraduate/SC-ST/PhD/monthly/disability discovery. Conversation setup turns
precede follow-up, deadline and unsupported-amount questions. The live report records
actual generated answers, statuses, sources/excerpts, checks and measured latency.
Use `--only CASE_ID` for a focused rerun and `--output` for a separate report.

Checks include requested status, expected fact patterns, relevant source prefixes,
multiple sources for discovery, exact excerpt provenance, absence of off-topic
citations, and successful conversation setup. The checks use test facts, not a
production question-answer lookup. Model grounding review adds semantic scrutiny but
neither it nor the spot-check patterns prove all factual paraphrases correct.

Rate limits can fail acceptance cases even when the implementation is correct;
those failures remain visible in reports. Pace calls rather than conceal them with
fallback excerpts. Live runs consume provider tokens. Test sessions are deleted
at the end of each case, while content-free execution/usage audit rows remain.

Backend pytest uses mocked providers/embeddings where needed. It verifies the actual
generated answer reaches the API, evidence checks, malformed outputs, grounding
rejection/repair, input rejection, tool bounds, model errors, conversation history,
source contradictions, index integrity, and removal of profile routes. Frontend tests
verify natural-text rendering, source names, absent profiles and clear provider errors.
Browser tests on isolated ports mock provider responses; real provider acceptance
is measured separately. The previous profile evaluation and 96.7% combined legacy
score are obsolete and are not claimed for the conversational application.

## Current demo and efficiency checks

`python evaluation/check_retrieval_efficiency.py` checks actual local domain/intent
embeddings, focused sections, context budgets and all-16 indexed/application coverage.
`python evaluation/run_eval.py --live --cases evaluation/demo_cases.json --delay 15 --output evaluation/reports/demo_live.json`
runs 14 current demo scenarios, including benefits, documents, eligibility, application,
follow-up, comparison/discovery, missing dates, ambiguity and out-of-domain requests.
It records each actual model phase, tokens, latency and retrieval-call count; the
fixtures enforce zero calls outside the domain and one for simple lookups.
`--cases` selects fixtures; `--only` allows a focused rerun. Original 16-case fixtures
remain, with their old arithmetic expectation changed to scholarship-only redirection.

`retrieval_optimized.json` records the current 30-question retrieval run;
`efficiency.json` records local classifier/context measurements; `demo_initial.json`
preserves the first live run's failures; `demo_live.json` records the corrected run.
See DEMO_READINESS.md for actual results, measured savings and limits.
