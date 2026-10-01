# Bounded scholarship assistant

The existing LangGraph DAG now has an early conditional exit:
plan/domain check -> (out-of-scope guidance OR semantic retrieval -> answer).
There is no profile, eligibility tool or model-based query rewrite. Graph iteration
limits, validated retrieval arguments, four worker slots, bounded timeouts/retry and
private conversation references remain. Unrelated turns preserve the last useful
scheme reference and create no retrieval/provider usage rows.

All scholarship facts still require retrieved text. Gemini uses response_json_schema
and returns the actual natural answer, status and exact support references. Ambiguous
recommendations use a constrained clarification schema: insufficient_evidence,
empty supports, optional natural-language clarification, no personal questionnaire.

LLM_GROUNDING_REVIEW=auto uses one generation for simple lookups. Conflicts, criteria,
comparisons, deadlines, multi-scheme complexity and suggested numbers trigger review.
The always option retains review for every answer. A separate review is a safeguard,
not proof; skipping it trades some scrutiny for lower cost/latency. Provider requests
never select or change deterministic eligibility rules because there are none.

Malformed/unsupported outputs can be repaired once. A configured secondary model
may be attempted. Permanent auth/config/model/quota errors are not repeated immediately.
Failures return HTTP 503 and safe operational codes; no quote dump replaces an AI answer.
Input/output budgets apply to all calls. Each actual call has provider/model/phase,
input/output tokens, status and latency records. Runtime logs add domain scores,
query fingerprint and source/context size. Raw query text is opt-in and credential
patterns are redacted; keys, raw exceptions and full prompts are never logged.
