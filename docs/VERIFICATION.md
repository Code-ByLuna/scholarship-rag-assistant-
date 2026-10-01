# Current application verification

Verified on 2026-10-01 in D:/social-hackthon/social-hackthon with SQLite and live
Gemini (`gemini-3.5-flash-lite`). This report supersedes the previous profile/rule
verification and its 96.7% combined score. Personal profile matching was removed;
eligibility information, scholarship data, embeddings and FAISS retrieval remain.

The actual generated answer now passes from Gemini through the backend into React,
with sources separately. Provider/retrieval failure is explicit and never masquerades
as a generated answer. Both existing local servers responded during verification.

| Executed check | Result |
|---|---|
| Backend tests | 43 passed |
| Ruff lint and format check | Passed |
| Django check and migration drift | Passed |
| OpenAPI validation | Passed |
| TypeScript/ESLint and production build | Passed |
| Vitest | 7 passed |
| Automated Edge browser tests | 3 passed |
| Real Gemini browser response identity and restored conversation | Passed |
| Actual persisted FAISS retrieval questions | 30/30 passed |
| Full paced live Gemini acceptance run | 14/16 passed |
| Corrected deadline/conflicting-application focused rerun | 2/2 passed |
| Latest result for each scenario across live runs | All 16 passed |
| Source corpus, generated schema, tracked-file hygiene | Passed |

This is not a claim that a single final full live run passed 16/16. The original
14/16 report is preserved, and the two failures passed in the separate focused report.
Exact evidence checks and a second model grounding review reduce unsupported facts;
they do not establish universal correctness or complete discovery.

The new SQLite migration is applied: no personal-profile table remains and old
assistant messages have no profile, eligibility or rule-trace fields. Source data
is unchanged: 16 records, 139 indexed chunks, corpus SHA-256
`805a64250c4e33f7d6e116d40cc2b054cb557fe6a69a6314d179a300929042ea`.

[Full 14-part implementation and verification report](RAG_REFACTOR.md) records
files, removals, root cause, architecture, environment settings, exact run/test
commands, live scenarios, sources and remaining issues.

Run the existing workspace:

```powershell
cd D:\social-hackthon\social-hackthon
python backend/manage.py migrate
python backend/manage.py runserver 127.0.0.1:8000
```

In another terminal:

```powershell
cd D:\social-hackthon\social-hackthon
$env:PATH = "$PWD\var\tools\node-v24.21.0-win-x64;" + $env:PATH
npm.cmd --prefix frontend run dev
```

Open http://127.0.0.1:5173/#/assistant. Keep the configured key in ignored `.env`.

MySQL and Docker runtime checks remain pending. The dataset is a static snapshot
with missing URLs/dates and source contradictions; current official details require
verification. English embeddings remain; multilingual quality is not established.
No remote is configured, so commits are local only.
