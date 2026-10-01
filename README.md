# Scholarship Eligibility Navigator

A scholarship discovery and matching application for students. Enter a profile,
understand every eligibility result, inspect benefits/documents/application steps,
and ask questions with persistent conversation memory and source citations.

Facts come from the supplied dataset. Decisions come from a deterministic rule
engine. A single LangGraph agent calls retrieval and eligibility tools. The optional
Gemini provider selects verified source excerpts; Pydantic and exact quote checks
prevent unsupported AI facts from reaching the React frontend.

The repository originally contained only six supplied data/reference files and an
initial Git commit. Those files are preserved. The application, schemas, migrations,
API, React UI, retrieval/agent services, tests and deployment documentation are new.
See [audit](docs/AUDIT.md) for the inspected starting state and milestone plan.

## Run locally

Python 3.10+, Node 24 LTS. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
Copy-Item .env.example .env
New-Item -ItemType Directory -Force var
python backend/manage.py migrate
python backend/manage.py seed_scholarships
python backend/manage.py ingest_scholarships
python backend/manage.py runserver 127.0.0.1:8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/api/docs.
For this Windows workspace, a portable runtime was installed into ignored var/tools.
If Node is not on PATH, use the actual printed path from python scripts/install_node.py:

```powershell
$env:PATH = "$PWD\var\tools\node-v24.21.0-win-x64;" + $env:PATH
npm.cmd --prefix frontend run dev
```

The initial npm registry was unreachable here; installation used the HTTPS npmmirror
registry with package integrity hashes. The committed lockfile records that registry.
A normal npm ci follows those locked URLs. Use your approved registry policy for
deployment and regenerate the lockfile deliberately if required.

Defaults: DJANGO_DEBUG=true, DB_ENGINE=sqlite, LLM_PROVIDER=none. No provider key is
needed for deterministic matching and source-excerpt assistance. Private .env is
ignored. Set DB_ENGINE=mysql and MYSQL_* values to use MySQL. A configured local
MySQL service was detected, but the user selected SQLite validation for this run.

Important configuration:
- EMBEDDING_MODEL: sentence-transformers/all-MiniLM-L6-v2 (compact CPU English embeddings).
- VECTOR_INDEX_DIR: persisted var/index; explicitly re-ingest on corpus/model changes.
- LLM_PROVIDER / LLM_MODEL / GEMINI_API_KEY: optional Gemini provider.
- LLM_FALLBACK_PROVIDER / MODEL / API_KEY: optional secondary Gemini model/key.
- TOOL_TIMEOUT_SECONDS / LLM_TIMEOUT_SECONDS / AGENT_MAX_ITERATIONS: bounded failures.
- LLM_MAX_OUTPUT_TOKENS / LLM_MAX_INPUT_CHARS: per-query limits.
- LLM_INPUT_COST_PER_MILLION / OUTPUT_COST_PER_MILLION: optional configured pricing.
- DJANGO_SECRET_KEY / ALLOWED_HOSTS / CORS_ALLOWED_ORIGINS: deployment settings.
- CSRF_TRUSTED_ORIGINS / TRUST_PROXY_HEADERS / SECURE_SSL_REDIRECT: trusted TLS ingress.

## Architecture and behavior

React -> Django REST Framework -> modular application services -> MySQL and FAISS.
SQLite is an explicit local/test option. Production requires MySQL and a secret key.
The corpus stays in JSON; SQL stores operational metadata, profiles, messages,
agent/tool executions, usage and evaluation records.

Matching returns ELIGIBLE, NOT_ELIGIBLE or NEEDS_VERIFICATION, with every rule trace.
Unknown values are never assumed. Unmapped clauses, institution-specific conditions,
selection constraints and source contradictions remain verification requirements.
Only the six initial fields are required for profile creation; relevant optional
fields are requested from candidate traces. Partial profiles can be checked by the API.

RAG uses section chunks, configurable sentence-transformer embeddings, scheme and
section metadata filters, cosine search in persisted FAISS, then grounded generation.
Missing indexes/provider keys return explicit fallback warnings. The source record,
scheme ID and chunk ID remain traceable. Empty source URLs remain unavailable.

The agent recovers private session context across HTTP requests. Tokens protect
session access. Tools validate arguments, time out, retry bounded failures and log
each invocation. Requests have correlation IDs; provider calls record available
tokens/cost. All assistant responses pass the public Pydantic schema.

## Checks and evaluation

```powershell
python -m ruff check backend tests scripts evaluation
python -m ruff format --check backend tests scripts evaluation
python -m pytest -q
python backend/manage.py check
python backend/manage.py spectacular --validate --file var/openapi.yaml
python evaluation/run_eval.py
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run e2e
```

Browser tests use installed Edge by default. Override PLAYWRIGHT_BROWSER_CHANNEL
or install Chromium and use that browser on another operating system.
The evaluation uses 33 real-corpus profile cases plus one isolated rule contract and
30 questions. Reports contain actual eligibility, retrieval, grounding, citation,
failure and P50/P95/P99 measurements. Read
[evaluation report](evaluation/reports/latest.json) and [methodology](docs/EVALUATION.md).
Metrics describe this corpus and local runtime; live LLM latency is not measured
without credentials. No SLA or general hallucination-free completeness is claimed.

## Docker and deployment

```powershell
# Fill .env with separate MySQL passwords and a generated Django secret.
docker compose up --build -d
docker compose exec backend python backend/manage.py ingest_scholarships
```

Open http://localhost:8080. MySQL, index/model cache and static assets have persistent
volumes. Ingestion is explicit. Production TLS/proxy settings and health checks are
documented in [deployment](docs/DEPLOYMENT.md).

Docker files were statically checked; no Docker runtime is available here.
MySQL execution and live Gemini calls remain unverified. Complete those checks,
configure TLS/secrets and review dependencies before a production rollout.

## Documentation

[Architecture and diagrams](docs/ARCHITECTURE.md) ? [API](docs/API.md) ?
[Dataset](docs/DATASET.md) ? [Eligibility](docs/ELIGIBILITY_ENGINE.md) ?
[RAG](docs/RAG.md) ? [Agent](docs/AGENT.md) ? [Evaluation](docs/EVALUATION.md) ?
[Deployment](docs/DEPLOYMENT.md) ? [Security](docs/SECURITY.md) ?
[Final verification](docs/VERIFICATION.md).

Known limits: dataset freshness/deadlines are unverified; all real records include
some residual external condition, so complete automation cannot guarantee an award.
Some free-text conditions need official review. The LLM uses constrained quotations
instead of unrestricted factual prose. Timed-out Python workers finish in the
background within a fixed capacity. Conversation history is limited to eight recent
messages per context window. Source contradictions are preserved. No Git remote is
configured, so commits are local.
