# Retrieval and grounded generation

Retained: authoritative JSON, 150-word section chunking, source provenance,
`sentence-transformers/all-MiniLM-L6-v2` CPU embeddings, normalized cosine search
with FAISS IndexFlatIP, version/checksum validation, atomic CURRENT pointer, and
explicit ingestion. Existing 139 indexed chunks remain usable; the corpus and
chunking were not edited. Every scholarship question queries the semantic store.

Scheme/category metadata constraints narrow candidates before similarity search.
Name/category detection assists retrieval only; it never generates an answer or
infers a permanent personal profile. Broad queries diversify nearest matches across
schemes. Hard keyword section routing and lexical failure answers were removed.
Additional important-notes chunks for retrieved schemes are fetched from the same
vector store, keeping contradictions visible beside amounts and application facts.

Conversation references expand the retrieval query with the previously discussed
scholarship names. Both user questions and assistant answers reach the prompt.
Off-topic questions still pass through the bounded flow; Gemini recognizes their
scope and returns a natural response with no unrelated scholarship sources.

Generation receives the question, limited conversation history and actual retrieved
source text, including scheme/section identities. Gemini returns natural answer
text, a status, and supporting quote references. The quotes are exact evidence,
not the display answer. The server rejects unknown references, unsupported quotes,
extra output fields and invented links. A second model call reviews the meaning of
paraphrased claims against cited information and checks relevant contradictions.
A failed review supplies correction feedback for one bounded generation retry.

A missing/stale/corrupted index is an explicit error. No keyword replacement or
ungrounded chatbot bypass is used. Ingestion remains an explicit management command.
A missing API key, provider refusal, rate limit, timeout, network failure or rejected
answer is also explicit; configured fallback models may be tried, but source excerpts
are never presented as a generated answer after generation fails.

The review is a useful safeguard, not proof of factual entailment. Human verification
and official sources remain necessary for current requirements and deadlines.
