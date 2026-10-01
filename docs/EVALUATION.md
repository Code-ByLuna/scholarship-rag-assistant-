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
