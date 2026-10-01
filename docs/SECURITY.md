# Security and privacy

API keys, database credentials and Django secrets are backend environment variables.
`.env`, runtime databases/indexes/caches are ignored and excluded from Docker builds.
Production requires MySQL and a Django secret. Staff endpoints require authentication.
Public browsing/chat are throttled and inputs bounded. API errors do not expose stack
traces, raw provider payloads, credential values or user/model text in logs.

Sessions use random capability tokens, with only SHA-256 hashes stored in SQL.
The frontend stores the token in sessionStorage and sends it in a header, never a
URL. The former profile storage/model/routes/forms were removed. Migration 0002 drops
saved profiles and removes historical profile/rule traces from assistant message JSON.
A student may voluntarily mention circumstances in conversation; those messages
are conversation data, not a separately collected or inferred permanent profile.

Provider requests transmit the question, relevant conversation history and retrieved
scholarship evidence. Apply your deployment privacy/retention policy. New conversation
in the UI deletes the previous protected session. The inactivity cleanup command is
`python backend/manage.py purge_sessions --days 30`. Audit records contain no transcript.
Use HTTPS, protect tokens, encrypt backups, and apply appropriate CSP settings.

React renders text, never model HTML. Citation URLs are server-derived and only HTTP(S)
links render. Retrieved/user text is untrusted. Exact evidence/source checks and a
separate grounding review constrain free-form paraphrases, but do not guarantee zero
hallucinations or resistance to every possible prompt injection. The assistant cannot
issue official eligibility/award decisions. Missing dates/links remain missing.

Index/checksum files are writable only by trusted ingestion administrators. Checksums
protect against corruption, not an attacker controlling both index and manifest.
Thread timeouts cannot kill workers; occupied slots bound concurrency. Browser fonts
may contact Google Fonts. MySQL and Docker runtime verification remains pending;
repeat deployment-specific security/dependency checks before production use.
