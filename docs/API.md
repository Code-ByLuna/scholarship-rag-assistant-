# RAG API

Swagger UI: `/api/docs`; OpenAPI 3.1: `/api/schema`. Routes have no trailing slash.
Unknown fields and oversized/invalid inputs are rejected. X-Request-ID correlates logs.

| Route | Purpose |
|---|---|
| POST /api/agent/query | Conversational RAG answer |
| POST /api/rag/query | Same grounded workflow |
| POST /api/scholarships/search | Browse corpus records; question/category/scheme_ids/top_k |
| GET /api/scholarships/{scheme_id} | Full source record including eligibility criteria |
| POST /api/sessions | Create private conversation; returns token once |
| GET /api/sessions/{session_id} | Read conversation with X-Session-Token |
| DELETE /api/sessions/{session_id} | Delete conversation with its token |
| GET /api/health | SQL/corpus/vector readiness and whether LLM is configured |
| POST /api/admin/ingest | Authenticated staff ingestion |
| GET /api/agent/usage | Authenticated staff aggregate usage |

Query fields: required question; optional scheme_ids, category, top_k (1-16, default
8), session_id and context_scheme_id. The latter supplies a selected scheme for implicit
follow-ups; explicit named questions can change topic. scheme_ids remains an explicit filter. A session_id requires X-Session-Token. No profile field is accepted.
`/api/profile/validate` and `/api/eligibility/check` have been removed and return 404.

Response: answer, sources, status, optional error, request_id, session_id. Sources
carry scheme/source identities, available official URL, the supporting reference and
exact excerpt. Frontend displays distinct cited scholarship names and safe source links.
`success`, `out_of_scope`, `insufficient_evidence` return 200; `error` returns 503.
An empty deadline is not a guessed deadline. An off-topic response has no sources.
No deterministic eligibility statuses, rules, traces or profiles are returned.

Health checks configuration, not a live model call. Provider outages can occur even
when health reports configured. API keys are never returned. Browsing remains useful
without a provider, but assistant generation requires one.
