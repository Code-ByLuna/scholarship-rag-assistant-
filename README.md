# Scholarship Navigator

A conversational scholarship assistant powered by retrieval augmented generation.
Ask a question immediately, browse the 16 supplied scholarship records, and read
Gemini-generated explanations with supporting sources. No student profile or
rule-based eligibility matching is required. Eligibility criteria remain in the
unaltered scholarship dataset and are retrieved and explained like other facts.

The assistant uses sentence-transformer embeddings and the persisted FAISS index,
then sends relevant scholarship evidence and conversation history to Gemini.
The generated answer is returned directly to React after evidence and grounding
checks. Retrieval/provider failures are explicit errors, never fabricated AI answers.

## Run this Windows workspace

From `D:\social-hackthon\social-hackthon`, configure the ignored `.env`:

```dotenv
DB_ENGINE=sqlite
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=your_private_key
```

Your existing working key and SQLite configuration can be retained. Never put
credentials in `.env.example`, frontend code, or chat. Other configuration defaults
are documented in [.env.example](.env.example).

Backend terminal:

```powershell
cd D:\social-hackthon\social-hackthon
python backend/manage.py migrate
python backend/manage.py runserver 127.0.0.1:8000
```

Frontend terminal:

```powershell
cd D:\social-hackthon\social-hackthon
$env:PATH = "$PWD\var\tools\node-v24.21.0-win-x64;" + $env:PATH
npm.cmd --prefix frontend run dev
```

Open http://127.0.0.1:5173/#/assistant. API docs: http://127.0.0.1:8000/api/docs.
The migration removes saved personal profiles and strips old rule traces from
historical assistant messages. Conversation questions and sourced answer text remain.

For a fresh checkout: Python 3.10+, install `requirements.lock` in a virtual
environment, create `.env` and `var`, migrate, seed and ingest:

```powershell
python -m pip install -r requirements.lock
python backend/manage.py migrate
python backend/manage.py seed_scholarships
python backend/manage.py ingest_scholarships
npm.cmd --prefix frontend ci
```

Use an installed Node 24 LTS or `python scripts/install_node.py`. The existing
lockfile uses an HTTPS npm mirror because the default registry was unreachable in
this workspace; package integrity hashes are retained.

## Request and response

`POST /api/agent/query` and `/api/rag/query` run the same conversational RAG flow:

```json
{"question":"How much does Pragati provide?"}
```

Responses contain `answer`, `sources`, `status`, optional `error`, and request/session
identifiers. Status is `success`, `out_of_scope`, `insufficient_evidence`, or `error`.
The answer is the generated text. Source names, URLs and exact supporting excerpts
come from retrieved records, never model-invented citations. Missing links stay missing.
Failures use HTTP 503 and a clear error. Matching/profile endpoints have been removed.

The assistant can explain benefits, criteria, documents, procedures, conflicting
information, and missing deadlines. Follow-up questions use private conversation
history. Voluntarily supplied circumstances may be discussed, but the scholarship
authority makes the final eligibility/award decision.

## Verification

```powershell
python -m pytest -q
python -m ruff check backend tests scripts evaluation
python backend/manage.py check
python backend/manage.py spectacular --validate --file var/openapi.yaml
python scripts/verify_repository.py
python evaluation/run_eval.py
python evaluation/run_eval.py --live --delay 20
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run e2e
```

Unit/browser tests do not call live Gemini. Browser tests use Edge and isolated
ports 8001/5174. Live evaluation calls the configured provider for 16 acceptance
cases plus conversation setup turns; it is paced to reduce rate limiting.
[Retrieval report](evaluation/reports/latest.json),
[live report](evaluation/reports/live_rag.json), and
[refactor/verification report](docs/RAG_REFACTOR.md) record the actual results.

## Deployment and limits

MySQL is required when `DJANGO_DEBUG=false`. Docker retains the database, index,
model cache and static assets in volumes. See [deployment](docs/DEPLOYMENT.md).
Docker/MySQL runtime validation remains pending in this Windows environment.

Generated language is checked by schema validation, exact evidence membership,
and a separate model grounding review. This reduces unsupported claims but is not
a mathematical guarantee of correct paraphrases or complete discovery. Provider
quotas and network outages return errors. The dataset is a supplied snapshot, not
live official scholarship updates. English embeddings are retained; multilingual
retrieval quality has not been established.

[Architecture](docs/ARCHITECTURE.md) | [RAG](docs/RAG.md) | [API](docs/API.md) |
[Agent](docs/AGENT.md) | [Security](docs/SECURITY.md) | [Evaluation](docs/EVALUATION.md)
