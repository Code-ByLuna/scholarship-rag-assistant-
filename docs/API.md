# API

Run backend/manage.py runserver. Swagger UI: /api/docs; generated schema: /api/schema.
All routes use no trailing slash. Inputs reject unknown fields, invalid types and
oversized text; errors are structured. X-Request-ID is returned and logged.

POST /api/profile/validate: six initial fields; optional fields are not required.
POST /api/eligibility/check: {"profile": {...}, "scheme_ids": [...]}; partial profiles allowed.
POST /api/scholarships/search: question/category/scheme_ids/top_k.
GET /api/scholarships/{scheme_id}: complete source record and citation.
POST /api/sessions: {}; returns private session_id and session_token once.
GET /api/sessions/{session_id}: X-Session-Token required.
GET /api/health: database/corpus readiness, vector degraded state.
POST /api/admin/ingest and GET /api/agent/usage: authenticated Django staff only.

Public discovery is anonymous and throttled. Session access uses a randomly generated
capability token; only its SHA-256 hash is stored. Never put tokens in URLs or logs.

POST /api/rag/query and POST /api/agent/query: question, optional profile/scheme_ids/
category/top_k/session_id. Both return a Pydantic ScholarshipAnswer and run the same
grounded tool workflow. X-Session-Token is required when session_id is supplied.
DELETE /api/sessions/{session_id}: token required; deletes private profile/messages.
