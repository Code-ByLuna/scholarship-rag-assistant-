# Final verification report

Verified on 2026-10-01 in D:/social-hackthon/social-hackthon (Windows, Python 3.10.10).
The application runs end-to-end locally. Full production acceptance is still pending
MySQL, Docker and live-provider verification. Those checks are not claimed complete.

## Starting state and implementation

Present: six user-supplied dataset/QA/reference files; Git initial commit 6653d09.
Absent: backend, frontend, database schema/migrations, profile schema, RAG/agent,
tests, dependency/deployment files and a configured remote. Legacy engine is preserved.

Implemented: a generic conservative eligibility compiler/evaluator; validated profiles;
Django/DRF API and MySQL operational models; private persistent sessions; explicit
sentence-transformer/FAISS indexing; metadata-aware retrieval; one bounded LangGraph
agent; two real tools; Gemini provider abstraction; exact source quote validation;
provider retry/fallback; JSON logs/request IDs/usage; React profile/results/details/chat;
custom evaluation; adversarial tests; Docker/static/proxy/retention configuration;
documentation, Mermaid diagrams and reproducible setup commands.

Architecture: React -> DRF/Pydantic -> eligibility/RAG/LangGraph/memory/observability ->
MySQL (SQLite for local tests) and versioned FAISS -> read-only source corpus.
The LLM selects evidence; it never changes profile facts, statuses or scholarship rules.

## Actual executed checks

| Check | Result |
|---|---|
| Corpus count/provenance and generated schema | 16 records pass; every original_record equals its source record |
| Explicit ingestion | 139 chunks embedded with all-MiniLM-L6-v2 and persisted in FAISS |
| python -m pytest -q | 53 passed |
| Ruff lint and format check | Passed |
| Django system check | No issues |
| Migration drift check | No changes detected |
| OpenAPI generation/validation | Passed without warnings |
| React TypeScript check/production build | Passed |
| Vitest component tests | 5 passed |
| Headless Edge end-to-end flows | 2 passed |
| Docker Compose YAML/static entrypoint checks | Passed; actual containers not run |
| Repository secret-pattern/file hygiene | Passed for staged/tracked files |
| Git source-preservation diff | No source/reference files modified |

Browser flows exercise profile -> matching -> explicit uncertainty panels ->
source/document detail -> real local semantic assistant -> persistent chat after reload,
plus a 390px mobile overview without horizontal overflow. Screenshots are in ignored
var/dashboard.png and var/mobile.png; browser JSON report is var/browser-report.json.

## Measured custom evaluation

Cases: 34 profile/contract cases and 30 questions.
The 34 profile cases consist of 33 corpus cases and one toy evaluator contract;
the toy is not corpus knowledge. Overall score includes context relevance.

| Metric | Observed |
|---|---:|
| eligibility_correctness | 100.00% |
| retrieval_hit_rate | 100.00% |
| answer_relevance | 100.00% |
| context_relevance | 76.89% |
| faithfulness_exact_source_quotes | 100.00% |
| citation_correctness | 100.00% |
| unsupported_excerpt_rate | 0.00% |
| agent_failure_rate | 0.00% |
| Overall custom score | 96.70% |

Exact source excerpt checks are a narrow hallucination proxy, not a human
assessment of completeness. Results are from SQLite with LLM_PROVIDER=none.

| Warm latency (ms) | P50 | P95 | P99 |
|---|---:|---:|---:|
| embedding | 20.447 | 37.155 | 41.601 |
| vector_retrieval | 0.284 | 1.033 | 1.566 |
| retrieval_total | 22.358 | 42.852 | 49.536 |
| complete_request | 388.463 | 1042.711 | 1257.661 |

Cold model/index startup: 11091.114 ms. Live LLM latency and real
provider token/cost measurements are unavailable; mocked calls verify accounting.

## Agent and recovery behavior

Every query invokes validated scholarship retrieval and deterministic eligibility
tools. Each invocation is persisted with attempt/status/latency and logged with
request correlation. Invalid arguments are rejected; transient failures retry once;
timeouts are bounded with four outstanding worker slots. The graph has no cyclic
model-controlled loop and enforces a maximum iteration count.

Provider output must pass Pydantic plus exact chunk/quote support. Primary provider
gets one repair attempt, then configured secondary Gemini provider, then deterministic
source excerpts. Empty or failed retrieval returns insufficient-source output.
Missing API keys, unavailable vectors, tool failures, malformed JSON and
source contradictions are visible. Staff-only usage exposes recorded tokens/cost;
secrets are never sent to the frontend.

## Remaining setup and acceptance limits

- MySQL service exists, but the user chose SQLite validation. Configure dedicated
  database credentials in private .env, migrate/ingest and run integration tests
  against MySQL before production acceptance.
- Docker CLI/daemon is unavailable. Build/run Compose and verify static assets,
  persistent volumes and container health; configure the trusted HTTPS ingress.
- No Gemini API key is configured. Live SDK/provider quality, tokens, cost and latency
  are unverified. Deterministic matching and source-excerpt assistance work now.
- Configure production secrets, TLS, hostname/CSRF settings, retention and backups.
- Dataset deadlines/freshness and source contradictions need official verification.
  Real records retain residual external conditions; these are never removed to
  create artificial ELIGIBLE results.
- Full dependency vulnerability scanning and Linux deployment verification remain.
  Local npm installation used an HTTPS mirror due to official-registry TLS resets.
- No Git remote is configured. All commits are local; none were pushed. No history
  rewrite or force push occurred.

## Exact commands for this existing workspace

Terminal 1:
```powershell
cd D:\social-hackthon\social-hackthon
python backend/manage.py runserver 127.0.0.1:8000
```

Terminal 2:
```powershell
cd D:\social-hackthon\social-hackthon
$env:PATH = "$PWD\var\tools\node-v24.21.0-win-x64;" + $env:PATH
npm.cmd --prefix frontend run dev
```

Open http://127.0.0.1:5173. API docs: http://127.0.0.1:8000/api/docs.
Fresh-checkout installation, migrations, ingestion and Docker commands are in README.

## Incremental Git milestones

These commits preceded the final documentation commit; inspect git log for that
final commit. No remote was available at any milestone.

- d3fa3e6 chore: initialize scholarship navigator architecture
- 38597ab feat: preserve scholarship corpus and add validated profile schemas
- 358b64d feat: implement conservative generic eligibility rules
- 4343ea4 test: cover missing values contradictions and rule operators
- 54b263d feat: add Django APIs MySQL models and private session memory
- c621563 feat: index provenance-preserving scholarship chunks in FAISS
- 0c0e414 feat: add bounded grounded agent with validated provider fallbacks
- 4df5aa9 fix: harden source integrity uncertainty session access and API schemas
- b909c08 feat: build React scholarship workspace with tested browser flows
- f043784 test: add reproducible scholarship RAG evaluation and latency report
- 12d3d58 chore: add Docker deployment and tested dependency locks
- d108f1a refactor: split scholarship workspace into focused screen components

## Preserved source checksums (SHA-256)

| Source file | SHA-256 |
|---|---|
| scholarship_dataset_ready.json | 805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea |
| scholarship_dataset_ready.jsonl | 418250461189ebccf5e4dde463fe10e51bc26abf308fab4a567c6e86ba430d49 |
| combined_scholarship_schemes_cleaned.json | 206416eeb61194a0b9d0086e8e2a81beb47484bb433fe69f2824a1e793a56d92 |
| scholarship_dataset_QA_report.json | e4fe8ad4d6f05fd5b13d986282353004291024a490110aa9e10c3e473bff41c6 |
| eligibility_engine.py | 66d4c1ddf2b81f6d95769117f6df18fe30c7261463d9fcd6094335179b04b67d |
| README (1).md | 6f0e454f383f4ac2b33a64c8fd8a093a37c3ce7d93876e21e26fde2d6376fdbb |

## Files created or modified

The six supplied files were added to Git without editing. .gitattributes was extended
for Unix shell endings. README.md and application/config/test files were created;
later milestones updated them incrementally.

- .dockerignore
- .env.example
- .gitignore
- Dockerfile
- README.md
- backend/api/__init__.py
- backend/api/assistant.py
- backend/api/common.py
- backend/api/urls.py
- backend/api/views.py
- backend/apps/__init__.py
- backend/apps/navigator/__init__.py
- backend/apps/navigator/admin.py
- backend/apps/navigator/management/__init__.py
- backend/apps/navigator/management/commands/__init__.py
- backend/apps/navigator/management/commands/ingest_scholarships.py
- backend/apps/navigator/management/commands/purge_sessions.py
- backend/apps/navigator/management/commands/seed_scholarships.py
- backend/apps/navigator/migrations/0001_initial.py
- backend/apps/navigator/migrations/__init__.py
- backend/apps/navigator/models.py
- backend/config/__init__.py
- backend/config/settings.py
- backend/config/urls.py
- backend/config/wsgi.py
- backend/core/__init__.py
- backend/core/agent/__init__.py
- backend/core/agent/tools.py
- backend/core/agent/workflow.py
- backend/core/corpus.py
- backend/core/eligibility.py
- backend/core/llm.py
- backend/core/memory.py
- backend/core/observability.py
- backend/core/rag/__init__.py
- backend/core/rag/documents.py
- backend/core/rag/embeddings.py
- backend/core/rag/retrieval.py
- backend/core/rag/vector_store.py
- backend/core/schemas.py
- backend/entrypoint.sh
- backend/manage.py
- deploy/nginx.conf
- deploy/production.env.example
- docker-compose.yml
- docs/AGENT.md
- docs/API.md
- docs/AUDIT.md
- docs/DEPLOYMENT.md
- docs/ELIGIBILITY_ENGINE.md
- docs/EVALUATION.md
- docs/RAG.md
- evaluation/expected_results.json
- evaluation/profiles.json
- evaluation/questions.json
- evaluation/reports/latest.json
- evaluation/run_eval.py
- frontend/Dockerfile
- frontend/e2e/navigator.spec.ts
- frontend/index.html
- frontend/package-lock.json
- frontend/package.json
- frontend/playwright.config.ts
- frontend/src/App.tsx
- frontend/src/Assistant.tsx
- frontend/src/Dashboard.tsx
- frontend/src/ProfileForm.tsx
- frontend/src/ScholarshipDetail.tsx
- frontend/src/ScholarshipList.tsx
- frontend/src/Workspace.tsx
- frontend/src/api.ts
- frontend/src/components.test.tsx
- frontend/src/components.tsx
- frontend/src/main.tsx
- frontend/src/navigation.ts
- frontend/src/style.css
- frontend/src/test-setup.ts
- frontend/src/types.ts
- frontend/src/vite-env.d.ts
- frontend/tsconfig.json
- frontend/vite.config.ts
- pyproject.toml
- requirements.lock
- requirements.txt
- scripts/install_node.py
- scripts/lock_dependencies.py
- student_profile_schema.json
- tests/test_agent.py
- tests/test_api.py
- tests/test_eligibility.py
- tests/test_foundation.py
- tests/test_rag.py
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/SECURITY.md
- docs/VERIFICATION.md
- scripts/verify_repository.py
