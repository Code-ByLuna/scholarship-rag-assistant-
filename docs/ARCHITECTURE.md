# Architecture

```mermaid
flowchart TD
    UI[React student workspace] --> API[Django REST API / Pydantic validation]
    API --> Services[Application services]
    Services --> Rules[Deterministic eligibility engine]
    Services --> Retrieval[Section chunks / semantic retrieval]
    Services --> Agent[Single bounded LangGraph agent]
    Services --> Memory[Private persistent conversation memory]
    Services --> Logs[JSON observability / request IDs / usage]
    Agent --> Rules
    Agent --> Retrieval
    Agent --> LLM[Provider abstraction / source quote selection]
    LLM --> Validation[Pydantic and exact evidence validation]
    Memory --> SQL[(MySQL; SQLite local testing)]
    Logs --> SQL
    Retrieval --> Vector[(Persisted FAISS via VectorStore)]
    Rules --> Corpus[Authoritative read-only scholarship JSON]
    Vector --> Corpus
```

```mermaid
sequenceDiagram
    participant Student
    participant API
    participant Memory
    participant Agent
    participant Retrieval
    participant Rules
    participant LLM
    Student->>API: Question, optional profile, session token
    API->>API: Validate input / request ID
    API->>Memory: Authorize session and recover context
    API->>Agent: Invoke bounded graph
    Agent->>Retrieval: Validated tool call
    Retrieval-->>Agent: Chunks + provenance or explicit fallback
    Agent->>Rules: Profile + candidate IDs
    Rules-->>Agent: Deterministic status and source rule traces
    Agent->>LLM: Retrieved evidence + independent decisions
    LLM-->>Agent: Structured evidence quotes
    Agent->>Agent: Pydantic + exact quote validation
    Note over Agent,LLM: Invalid output retries once, then fallback provider/excerpts
    Agent->>Memory: Persist messages/profile/audit/usage
    Agent-->>API: Validated answer, statuses and citations
    API-->>Student: Facts, uncertainty and next verification steps
```

Facts: corpus. Decisions: rules. Language: constrained provider. Orchestration:
single graph. SQL stores operational metadata, session profiles/messages,
executions/tool calls/usage and evaluations; corpus content is not copied into SQL.
Chunks and embeddings live in versioned index files. No microservices are needed.
