# Hugging Face Docker Space deployment

This packages the existing Django/LangGraph/FAISS/Gemini backend. React remains a
separate Vercel application. MySQL is the image default; explicit DB_ENGINE=sqlite
is supported for single-instance demos. The selected SQL database stores sessions,
AgentExecution, ToolExecution and LLMUsageLog; FAISS does not replace those records.

## Readiness and blockers

Docker is not installed in the inspected Windows environment. No Linux image build,
container startup, remote MySQL connection or deployed Space has been verified.
The production entrypoint runs migrations, seed_scholarships and collectstatic
before starting Gunicorn; a failed database connection stops startup before any
health endpoint can respond. Placeholder credentials cannot establish readiness.

Spaces permit outbound connections only on ports 80, 443 and 8080. A conventional
remote MySQL endpoint on 3306 is therefore a deployment blocker. Obtain a provider
endpoint that supports the actual MySQL protocol on an allowed port and verify
reachability, or choose backend hosting that supports that database connection.
Changing a port number alone does not establish connectivity. For a simple demo,
explicitly select DB_ENGINE=sqlite instead; see the SQLite and persistence guidance
in [DEPLOYMENT.md](DEPLOYMENT.md#render-demo-with-sqlite).
[Spaces networking](https://huggingface.co/docs/hub/spaces-overview#networking).

The existing database OPTIONS specify utf8mb4 and strict SQL mode, but no explicit
TLS/CA configuration. Verify the remote provider's TLS requirements and certificate
validation before production use. A provider requiring explicit client TLS/CA
settings needs a separate reviewed configuration change. No such environment
variable is currently implemented. Restrict the database user to this application
and ensure its permissions allow Django migrations. MYSQL_ROOT_PASSWORD belongs
only to the local Compose MySQL service; the Space does not need it.

## Packaged runtime assets

| Asset | Image location and verification |
|---|---|
| Backend and migrations | /app/backend; existing production entrypoint retained |
| Runtime corpus | /app/data/scholarship_dataset_ready.json and combined_scholarship_schemes_cleaned.json |
| Active FAISS bundle | /app/var/index/CURRENT and version faac7d4df3034bafae61db8e52553481 containing vectors.faiss, chunks.json and metadata.json |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2; immutable revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 |
| Model cache | /opt/huggingface/hub; outside the Compose /app/var mount |
| Django static assets | /app/var/static, collected at startup and served by WhiteNoise when DJANGO_SERVE_STATIC=true |

The index contains 139 chunks in 384 dimensions; vectors.faiss is 213,549 bytes
and the entire four-file bundle is 363,705 bytes. The pinned model's 11 required
snapshot files total 91,578,415 bytes. Model files are downloaded during image build,
not committed to Git or copied from the developer's Windows cache. Build needs
internet access to Debian/PyPI/Hugging Face. Build requires no Django/MySQL/Gemini
credentials. Runtime generation still needs Gemini HTTPS access.

scripts/provision_rag_assets.py verifies exact corpus/index/model SHA-256 hashes
against deploy/rag-assets.json. Docker downloads only the pinned model's reviewed
files, writes its offline main reference and performs a real local embedding plus
FAISS search during build. HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 are restored
for normal execution; the unchanged query path uses local_files_only=True.
The original index records the model name but not its revision, so its creation
revision cannot be recovered from metadata. The corpus and index are preserved;
the packaged current snapshot is pinned without rebuilding or relabeling vectors.

Use Python 3.11-slim for this image. Local checks run on Python 3.10.10; those checks
do not prove Linux/Python 3.11 native dependency or Gunicorn compatibility. Budget
roughly 2-4 GiB RAM for two CPU workers as an estimate, not a container measurement.
The dependency lock retains the existing dependency closure; it is not a minimal
CPU-only image lock. No frontend node_modules or optional RAGAS environment enters
the image. Gunicorn retains two workers, two threads and a 180-second timeout.

Only the four reviewed index files are allowed through .gitignore/.dockerignore.
.gitattributes preserves their exact bytes across platforms. Local databases, old
indexes, tools, caches, logs and environments stay excluded. To package a future
index, review the new manifest, allowlists and Docker COPY version together.

## Space settings

Create a Space using the Docker SDK and the repository Dockerfile. README metadata
already specifies sdk: docker and app_port: 8000. Use CPU hardware; the model does
not require a GPU. Current documentation lists CPU Basic as 2 cores/16 GB RAM, but
creating a Docker Space requires an eligible paid account plan. Choose public or
protected app access for an ordinary public Vercel client; a private Space requires
an additional authentication integration that this frontend does not implement.
Use the actual assigned https://<space-subdomain>.hf.space address, not a guessed
hostname. [Space setup](https://huggingface.co/docs/hub/spaces-overview) and
[Docker configuration](https://huggingface.co/docs/hub/spaces-sdks-docker).

The image runs as UID 1000, listens on 0.0.0.0:8000 and creates writable static/index
and cache directories. Secrets are runtime environment variables from Space
Settings, never Docker build arguments. No local .env is copied. load_dotenv remains
available for local development and does not override existing environment values.

## Secrets and variables

Add secrets through Space Settings > Secrets. Required for the intended deployment:

```text
DJANGO_SECRET_KEY=
MYSQL_PASSWORD=
GEMINI_API_KEY=
```

DJANGO_SECRET_KEY is mandatory when DEBUG=false, without a production fallback.
MYSQL_PASSWORD is used only in MySQL mode. It is not explicitly checked for
nonemptiness by settings but is normally required by a remote password-authenticated
MySQL provider. SQLite needs no MYSQL_* credentials; DJANGO_SECRET_KEY remains required. GEMINI_API_KEY
is needed for generated answers, not Django startup or the new health probes.
LLM_FALLBACK_API_KEY is an optional secret only when enabling a fallback provider.
Treat MYSQL_USER/host/database as secrets too if your provider considers them
sensitive; they are identifiers rather than API keys/passwords.

Set deployment-specific variables (names only below; populate real values privately):

```text
ALLOWED_HOSTS=
CORS_ALLOWED_ORIGINS=
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_HOST=
MYSQL_PORT=
LLM_PROVIDER=
```

| Variable | Requirement and safe configuration |
|---|---|
| DJANGO_DEBUG | Image defaults false; keep false for production. Application alone defaults true. |
| DB_ENGINE | Image defaults mysql; explicitly set sqlite for a single-instance demo with DEBUG=false. Omitting the variable in production outside the image fails. |
| ALLOWED_HOSTS | Actual assigned Space hostname, localhost and 127.0.0.1, comma-separated without spaces; no scheme/wildcard. Loopback names allow the internal Docker probe. App's loopback-only default cannot accept public Space requests. |
| CORS_ALLOWED_ORIGINS | Exact HTTPS Vercel origin(s), comma-separated without spaces or trailing slashes; existing localhost default does not allow Vercel. Custom X-Session-Token and X-Request-ID headers are permitted for preflights. |
| CSRF_TRUSTED_ORIGINS | Optional for token-based public API calls; configure actual HTTPS trusted origins for cross-origin session/cookie-authenticated POSTs. Default is empty, not a wildcard. CORS does not replace CSRF. |
| MYSQL_DATABASE, MYSQL_USER | Actual provisioned application database/user; local scholarship defaults exist but are not a remote provider configuration. |
| MYSQL_HOST, MYSQL_PORT | Actual reachable MySQL endpoint; app defaults 127.0.0.1:3306, unusable for a normal Space remote database. Never supply an empty port. |
| LLM_PROVIDER | Set gemini for generated answers; app default none permits startup but returns generation errors. |
| LLM_MODEL | Optional; current app default gemini-3.5-flash-lite. Verify availability/quota in the configured Gemini project; no provider/model migration is performed. |
| LLM_FALLBACK_PROVIDER | Optional; default none. Only implemented enabled provider is gemini. |
| LLM_FALLBACK_MODEL | Optional when fallback enabled; omitted value uses current app model default. Do not set an empty model name when enabled. |
| LLM_FALLBACK_API_KEY | Optional secret; needed when enabling an independently configured fallback Gemini provider. |
| TRUST_PROXY_HEADERS | Image defaults true for the Space HTTPS proxy. Accept forwarded protocol only through the trusted platform ingress. |
| SECURE_SSL_REDIRECT | App defaults true when DEBUG=false; preserve it. Internal HTTP probes send X-Forwarded-Proto: https. |
| DJANGO_SERVE_STATIC | Image defaults true; enables collected Django static files without nginx. Local app default false. |
| EMBEDDING_MODEL | Optional override; image/app default MiniLM name above. Must match packaged vector/model manifest. |
| VECTOR_INDEX_DIR | Image defaults /app/var/index. Changing it requires a matching complete index at the new runtime path. |
| HF_HOME | Image defaults /opt/huggingface. Do not point at an empty/unprovisioned cache. |
| HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE | Image defaults 1; keep for offline model assets. Gemini HTTP is unaffected. |
| RAG_CONTEXT_MAX_CHARS | Optional, default 10000; retained evidence budget. |
| RAG_HISTORY_MAX_CHARS | Optional, default 2000; retained history budget. |
| LLM_TIMEOUT_SECONDS | Optional, default 30; per-provider-call timeout. |
| LLM_TOTAL_TIMEOUT_SECONDS | Optional, default 90; bounded generation/review budget. |
| TOOL_TIMEOUT_SECONDS | Optional, default 30; tool timeout. |
| LLM_MAX_INPUT_CHARS, LLM_MAX_OUTPUT_TOKENS | Optional, defaults 24000/2400; retained request/output limits. |
| LLM_MAX_ATTEMPTS | Optional, default 3, capped at 3; transient failures only. |
| LLM_RETRY_BASE_SECONDS, LLM_RETRY_MAX_SECONDS | Optional, defaults 5/20; bounded transient backoff. |
| LLM_GROUNDING_REVIEW | Optional, default auto; always is also supported. |
| RAG_LOG_QUERY_TEXT | Optional, default false; retain private query logging policy. |
| AGENT_MAX_ITERATIONS | Optional, default 6; graph/tool iteration limit. |
| LLM_INPUT_COST_PER_MILLION, LLM_OUTPUT_COST_PER_MILLION | Optional, no prices assumed; reporting only, not startup requirements. |
| PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED | Image defaults 1; Python process settings. |

HF_HUB_CACHE is not read directly by application code but Hugging Face libraries
honor it; do not override it away from the provisioned cache. No HF_TOKEN is needed
for this public model. MYSQL_ROOT_PASSWORD, evaluation judge variables and
VITE_API_BASE are not backend Space startup requirements.

## Vercel frontend

Set VITE_API_BASE in the Vercel project's build environment to the exact assigned
Space HTTPS origin, with no trailing slash and no /api suffix. frontend/src/api.ts
adds /api itself. Rebuild/redeploy Vercel after changing it. Set the same Vercel
HTTPS origin in the Space's CORS_ALLOWED_ORIGINS. Keep Gemini/database credentials
exclusively in backend Secrets. CSRF_TRUSTED_ORIGINS is conditional as above.

## Local Docker commands

Run from the repository root after installing a functioning Docker daemon. Create
an ignored .env.hf from deploy/huggingface.env.example and configure real nonempty
production secrets, allowed hosts and a reachable MySQL endpoint privately. This
new file does not replace the existing local .env. The template is intentionally
not runnable until those deployment-specific values are supplied.

```powershell
Copy-Item deploy/huggingface.env.example .env.hf
docker build -t scholarship-rag-hf .
# Asset-only acceptance: no network, database or Gemini required.
docker run --rm --network none --entrypoint python scholarship-rag-hf scripts/provision_rag_assets.py --check-model
# Full production startup requires real database connectivity and credentials.
docker run --rm --name scholarship-rag-hf --env-file .env.hf -p 127.0.0.1:8002:8000 scholarship-rag-hf
```

In another shell, with localhost/127.0.0.1 included in ALLOWED_HOSTS:

```powershell
curl.exe --fail -H "X-Forwarded-Proto: https" http://127.0.0.1:8002/api/health/live
curl.exe --fail -H "X-Forwarded-Proto: https" http://127.0.0.1:8002/api/health/ready
docker exec scholarship-rag-hf python scripts/provision_rag_assets.py --check-model
```

/api/health/live verifies Django responds without database/Gemini/query dependencies.
/api/health/ready verifies SELECT 1, CURRENT/index integrity via the normal loader,
and a local cached model with matching dimensions. It returns 503 with fixed safe
error codes when a dependency fails. The first readiness request loads model/index
into that worker's RAM; it does not call Gemini. The unchanged /api/health remains
available. A 200 readiness response does not guarantee provider quota or answer
quality. Docker HEALTHCHECK uses the cheap liveness probe; monitor readiness
separately. [WhiteNoise configuration](https://whitenoise.readthedocs.io/en/stable/django.html).

## Persistence and next steps

The baked model and reviewed index are present on every clean image start. Runtime
changes to index/static/cache files live on ephemeral disk unless explicitly
persisted. Use a supported attached storage bucket for intentionally persistent
runtime assets; plan its mount and initialize the reviewed bundle before changing
VECTOR_INDEX_DIR. Mounting an empty directory over /app/var or the cache hides the
baked assets. An existing Compose app_data volume may retain an older index;
inspect it before replacing anything. Do not delete volumes blindly.
[Spaces storage](https://huggingface.co/docs/hub/spaces-storage).

1. Resolve and validate remote MySQL networking and TLS requirements first.
2. Run the local Docker build, isolated offline-asset check and real MySQL startup
   acceptance commands above; inspect sanitized failures if any.
3. Create the Docker Space with eligible account/hardware/app visibility. Configure
   Secrets/Variables before accepting traffic. Use its actual assigned hostname.
4. Review the local changes, then commit/upload the source, runtime datasets,
   deploy/rag-assets.json, scripts/provision_rag_assets.py and all four allowlisted
   index files along with Dockerfile/README. No commit/push/upload is performed by
   this preparation task. Do not upload .env files, tools, caches or local databases.
5. Inspect the Space build/start logs. Check the actual HTTPS /api/health/live and
   /api/health/ready routes, then a controlled genuine Gemini query. Do not mark
   deployment complete while database/build/provider requirements remain unmet.
6. Set Vercel VITE_API_BASE and backend CORS_ALLOWED_ORIGINS and redeploy the frontend.
   Verify queries, private follow-ups and existing scheme-detail navigation.

## File changes and validation scope

| Files | Reason |
|---|---|
| Dockerfile | Python 3.11 image, native dependencies, exact FAISS COPY, pinned model build, UID 1000, port 8000 and existing entrypoint |
| .dockerignore, .gitignore, .gitattributes | Four-file index allowlist and unchanged asset bytes; exclude private/runtime material |
| deploy/rag-assets.json, scripts/provision_rag_assets.py | Immutable model revision and checksums; offline embedding/FAISS acceptance |
| var/index/CURRENT and three active version files | Existing runtime bundle made eligible for packaging; contents preserved |
| backend/api/health.py, backend/api/urls.py | Isolated liveness and dependency readiness endpoints |
| backend/config/settings.py, requirements.txt, requirements.lock | Conditional WhiteNoise static serving; allow existing frontend session/request headers |
| docker-compose.yml | Keep build-provisioned model cache outside the existing /app/var volume |
| .env.example, deploy/huggingface.env.example | Document new static switch and deployment-specific configuration without credentials |
| tests/test_deployment.py, scripts/verify_repository.py | Deployment isolation/proxy/cache/integrity coverage and exact index hygiene |
| README.md, docs/DEPLOYMENT.md, docs/API.md, this guide | Space metadata, setup, backend probes and truthful validation limits |

Completed locally: fresh pinned snapshot download and checksum verification;
model load, embedding and actual FAISS search with socket networking blocked.
That validation used Windows/Python 3.10, not an image or a deployment.
Local probes returned HTTP 200 for /api/health/live, /api/health/ready and the
existing /api/health; readiness checked the local SQLite database, index and model.
All 30 retrieval cases passed using the fresh offline cache. Production WSGI
settings initialized and Django deploy checks passed with ephemeral synthetic
configuration; this did not connect to MySQL. Lint, formatting, OpenAPI validation,
migration checks and configured-secret/repository hygiene scans passed. The
final full suite passed 124/124 tests in the existing optional evaluation
environment, including all nine deployment regressions. Static collection
completed successfully for 154 files. No live Gemini calls or remote MySQL acceptance were performed.
The existing local .env and RAG corpus/index contents were not modified.
