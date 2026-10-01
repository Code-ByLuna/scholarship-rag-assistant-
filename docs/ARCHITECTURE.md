# Conversational RAG architecture

```mermaid
flowchart TD
    Student[Natural-language question] --> UI[Existing React workspace]
    UI --> API[Django REST API and Pydantic validation]
    API --> Session[Token-protected conversation history]
    Session --> Query[LangGraph query processing]
    Query --> Retriever[Semantic retriever]
    Corpus[Authoritative scholarship JSON] --> Chunks[Section document chunks]
    Chunks --> Embeddings[Sentence-transformer embeddings]
    Embeddings --> FAISS[Persisted FAISS vector store]
    FAISS --> Retriever
    Retriever --> Context[Relevant evidence and conversation context]
    Context --> Gemini[Gemini natural-language generation]
    Gemini --> Validate[Schema and exact evidence validation]
    Validate --> Review[Grounding review of generated claims]
    Review --> Response[Generated answer and supporting sources]
    Response --> UI
    API --> SQL[SQLite locally or MySQL in production]
```

The bounded graph is plan -> retrieve -> answer. It does not invoke a rule engine,
create a personal profile, or adjudicate eligibility. SQL stores operational corpus
metadata, conversation messages, executions/tool audit rows, provider usage by
phase, and evaluations. The corpus and vector index retain their original roles.

The actual draft.answer survives validation unchanged into the API and React.
The server derives source metadata from verified references. Failed retrieval or
LLM calls return errors rather than replacing generated language with source dumps.
