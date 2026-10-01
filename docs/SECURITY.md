# Security and privacy

API keys, database credentials and Django secret keys are environment-only. .env,
runtime databases, indexes and caches are ignored; Docker excludes them too.
Production refuses to start without a secret key and a MySQL configuration.
Use a dedicated MySQL user, TLS and encrypted database/volume backups.

Admin ingestion and usage endpoints require authenticated Django staff; Django admin
uses normal CSRF protection. Public read/match/chat endpoints are throttled, inputs
are bounded and validated, and no internal traceback is returned.

Session access requires a random 256-bit capability token. Only its hash is stored.
The frontend stores its token/profile in sessionStorage and sends the token in an
HTTP header. Tokens are bearer capabilities: possession grants access. Keep the UI
same-origin over HTTPS and apply a deployment content-security policy. The frontend
never renders model HTML or executes source URLs; only HTTP(S) citation links work.

Logs exclude question/profile/key contents. Provider calls may transmit the relevant
student profile and question: configure a provider only under your deployment's
privacy policy. Local deterministic assistance works without sending data to an LLM.
Browser fonts can contact Google Fonts; use local fonts for strictly offline hosting.

Schedule python backend/manage.py purge_sessions --days 30 for inactivity retention.
Students can delete a session via DELETE /api/sessions/{id} with its token.
Execution audit records retain no transcript; purge related audit records separately
according to deployment retention policy.

Prompt injection cannot alter profiles, decision statuses or facts. The provider
only selects exact retrieved quotes; Pydantic shape validation alone would be
insufficient, so exact quote/source membership is checked too. Input text remains
untrusted. Residual source clauses and contradictions always need verification.

FAISS/chunk files must be writable only by trusted ingestion administrators.
Checksums detect corruption, not a malicious writer replacing the manifest.
Python threads cannot be killed at timeout; bounded slots prevent unbounded growth.

MySQL, Docker and live-provider verification must be completed before describing
this installation as production-ready. Dependency locks capture the tested versions;
repeat vulnerability scanning before each deployment.
