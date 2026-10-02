# Deployment

Local (Python 3.10+, Node 24 LTS):
1. Create a virtual environment and install `requirements.lock` for the tested pinned dependencies. `requirements.txt` records the supported dependency ranges for development; it is the input to `scripts/lock_dependencies.py`.
2. Copy .env.example to .env. Use DJANGO_DEBUG=true / DB_ENGINE=sqlite for local work.
3. Create var/; migrate; seed; ingest the corpus explicitly.
4. Run the Django development server and npm run dev from frontend/.

For MySQL deployments, configure an application database/user in MySQL 8+, utf8mb4
and strict SQL mode. Run the same migrations and ingestion with DB_ENGINE=mysql.
Use python backend/manage.py createsuperuser for authorized ingestion/usage/admin access.
See [Django MySQL guidance](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes).

Docker: set .env using .env.example, add MYSQL_ROOT_PASSWORD, and set nonempty separate
MYSQL_PASSWORD and DJANGO_SECRET_KEY. Run docker compose up --build -d. The backend
waits for MySQL readiness, migrates and seeds operational metadata. Index explicitly:
docker compose exec backend python backend/manage.py ingest_scholarships.
UI: http://localhost:8080. MySQL and backend are reachable only inside the Docker network.
Persist mysql_data and app_data, which includes the vector index. The pinned model
cache is baked into the image at /opt/huggingface, outside the app_data mount.
Never rebuild the index on ordinary requests.

Production settings are illustrated in deploy/production.env.example; copy values
into a private .env, never commit filled examples. DJANGO_DEBUG=false requires
an explicit DB_ENGINE=mysql or DB_ENGINE=sqlite and a generated secret. Omitting
DB_ENGINE still selects SQLite in debug mode and fails in production. Unknown
engine values fail explicitly. Use a TLS reverse proxy in front of the
loopback-bound frontend and configure the trusted ingress path.

The provided nginx config listens on HTTP for local use and sets forwarded protocol
from its own scheme. For production either terminate TLS in this nginx and configure
its certificate/listener, or replace the protocol header from a strictly trusted
TLS ingress. Set TRUST_PROXY_HEADERS=true only after restricting backend access to
that proxy. Never trust forwarded headers from arbitrary clients. Ensure the health
check is HTTPS-aware (HTTPS URL or trusted forwarded-proto header) when SSL redirect
is enabled. Configure CSRF_TRUSTED_ORIGINS and ALLOWED_HOSTS for the real domain.

Gunicorn serves the API; static Django admin assets are collected into a dedicated
static_data volume and served by nginx. Frontend assets are built into nginx.
Back up MySQL and vector volumes. Restrict admin ingress, schedule session retention,
and run tests/evaluation and deployment health checks before accepting traffic.

Docker is configured but could not be run here because the Docker CLI/daemon is absent.
SQLite/browser/local-vector tests do not establish MySQL or Docker runtime readiness.
Live LLM setup is optional: LLM_PROVIDER=gemini and GEMINI_API_KEY in private .env.
Measured LLM performance requires credentials and an explicit evaluation run.


Assistant generation requires LLM_PROVIDER=gemini, an available LLM_MODEL and a
backend-only GEMINI_API_KEY. The default example uses gemini-3.5-flash-lite. A normal
answer includes a second grounding-review call. Plan token budgets and provider
quotas accordingly. Index/provider failures return HTTP 503 instead of fake answers.
Migration 0002 removes the legacy personal-profile table and old profile/rule traces.
Existing corpus/vector volumes are retained; source eligibility text remains indexed.

Current demo efficiency defaults are RAG_CONTEXT_MAX_CHARS=10000,
RAG_HISTORY_MAX_CHARS=2000, LLM_GROUNDING_REVIEW=auto and RAG_LOG_QUERY_TEXT=false.
Use always review when stronger semantic scrutiny is preferred over single-call
simple lookups. No vector schema/database migration is needed for domain checks or
internal source links. Ingestion remains the documented command for a missing/stale
index; all 16 application sections are retained. See DEMO_READINESS.md.

## Render demo with SQLite

Set these variables in Render's backend service environment (see
[deploy/render.env.example](../deploy/render.env.example)):

```dotenv
DJANGO_DEBUG=false
DB_ENGINE=sqlite
DJANGO_SECRET_KEY=<generated-private-secret>
ALLOWED_HOSTS=<your-service>.onrender.com,localhost,127.0.0.1
TRUST_PROXY_HEADERS=true
SECURE_SSL_REDIRECT=true
DJANGO_SERVE_STATIC=true
```

SQLite retains the existing database location `BASE_DIR / "var" / "dev.sqlite3"`.
Settings create its parent directory before Django opens the database. Optionally
set SQLITE_PATH to a project-relative path such as `var/db.sqlite3`, or an absolute
path on persistent storage. MYSQL_* variables are ignored in SQLite mode. Keep
the service's existing CORS, CSRF and LLM variables configured for your deployment;
database selection does not change those behaviors or FAISS/model configuration.

The existing Docker image defaults to mysql, so explicitly override DB_ENGINE
with sqlite in Render. Its entrypoint already runs migrate, seed_scholarships and
collectstatic before Gunicorn. For a native Python service, run those same commands
at runtime before starting Gunicorn, for example from the project root:

```sh
python backend/manage.py migrate --noinput && python backend/manage.py seed_scholarships && python backend/manage.py collectstatic --noinput && gunicorn --chdir backend config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180
```

Run migrations at service startup when using a persistent disk: Render disks are
available only at runtime, not during build or pre-deploy commands. Without a
persistent disk, SQLite changes (including sessions and usage records) are lost
on redeploy/restart. For persistence, mount a disk at `/app/var/sqlite` in the
existing Docker image and set `SQLITE_PATH=/app/var/sqlite/db.sqlite3`. This keeps
the database inside var without hiding the packaged FAISS index. For a native
service, use a directory under that deployment's project var directory instead.
See [Render persistent disks](https://render.com/docs/disks).

Use SQLite for a simple single-instance demo. For deployments needing concurrent
writes or multiple service instances, retain DB_ENGINE=mysql and the unchanged
MYSQL_* configuration. Docker Compose continues to select its MySQL service.

## Optional offline evaluation

RAGAS dependencies are isolated in `evaluation/requirements.lock`; they are not
added to the normal image or startup command. `docker compose up` retains its
existing application behavior. Run the explicit host evaluation command documented
in [EVALUATION.md](EVALUATION.md) with the existing private Gemini configuration,
normal database and persisted FAISS index. No Docker/MySQL runtime acceptance is
claimed by the Windows/SQLite evaluation.


## Hugging Face Docker Space with Vercel

See [HUGGING_FACE.md](HUGGING_FACE.md) for the backend-only image, pinned model and
FAISS assets, runtime Secrets/Variables, separate Vercel configuration and exact
acceptance commands. The image defaults to MySQL; explicit DB_ENGINE=sqlite is
also supported for demos. Spaces outbound port restrictions block conventional
MySQL on 3306; resolve connectivity and provider TLS requirements when choosing
MySQL. The Space image
serves collected Django static files through WhiteNoise when DJANGO_SERVE_STATIC=true.
