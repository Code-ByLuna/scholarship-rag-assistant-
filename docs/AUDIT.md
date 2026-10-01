# Repository audit and implementation plan

Audit performed 2026-10-01 before modifications. Repository root is the nested
social-hackthon directory. HEAD 6653d09 contains only .gitattributes; six supplied
project files are untracked. Branch main, no remote. No AGENTS.md, dependencies,
environment configuration, syllabus file, profile schema, or application exists.

The ready JSON contains 16 unique records from 18 sources with two exact duplicates.
Keep all six supplied files byte-for-byte. The preliminary engine uses scholarship
ID branches, omits substantial conditions, treats missing lateral entry as failure,
and can claim eligibility without checking institution/merit. It remains a legacy
reference; the application uses backend/core/eligibility.py.

Data risks: ST pre-matric income conflict (200000 versus 250000) must remain
verification, not a guessed threshold. Disability schemes have offline/online
wording contradictions. Eligible-region lists, admission references, twin exceptions,
institution approvals, merit and slots need conservative evaluation.

Milestones (each checked, documented, committed): foundation; validated corpus and
generic rules; Django/API/database; embeddings/vector ingestion; grounded response
and bounded agent; React UI; evaluation/adversarial checks; deployment/final audit.
Within these milestones preserve the requested dependency order. No history rewrite
or force push. Push only if a remote exists.

Python 3.10.10 available. Node/npm/Docker absent from PATH at audit.
MySQL server and live LLM credentials have not been established.
SQLite is an explicit local/test option only; production requires MySQL.
