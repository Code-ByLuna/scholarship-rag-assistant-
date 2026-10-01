# Retrieval pipeline

JSON -> section chunks (150 words) -> sentence-transformer CPU embeddings ->
normalized FAISS IndexFlatIP -> scheme metadata filtering -> section filtering ->
top-k cosine matches -> retrieved quotes -> validated response.

Default embedding model: sentence-transformers/all-MiniLM-L6-v2, selected for compact
384-dimensional English embeddings and CPU use with the small English corpus.
EMBEDDING_MODEL is configurable. See the
[SentenceTransformer API](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).
FAISS is behind a VectorStore abstract interface; a Qdrant implementation can implement
search/save with the same metadata contract. See
[FAISS persistence](https://github.com/facebookresearch/faiss/wiki/Index-IO%2C-cloning-and-hyper-parameter-tuning).

Run python backend/manage.py ingest_scholarships explicitly; never per query.
Versions are persisted without pickle; CURRENT switches atomically. Checksums bind
chunks/index to the corpus hash and model. Persist var/index between deployments.
Only trusted administrators can write indexes. Re-ingest after changing corpus/model.

Each chunk has scheme_id/name/section/chunk_id, source fields and original_record_key.
Missing URLs remain null. Searches can filter by scheme/category before similarity.
A missing/broken index produces a visible VECTOR_UNAVAILABLE warning and an extractive
corpus text-search fallback. That fallback is not reported as semantic retrieval.

Bounded query embedding caches do not contain profile-dependent decisions.
