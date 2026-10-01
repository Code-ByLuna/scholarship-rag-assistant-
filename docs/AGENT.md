# Stateful grounded agent

One LangGraph DAG: plan -> scholarship retrieval tool -> deterministic eligibility
tool -> response generation/validation. Every query invokes both real tools.
AGENT_MAX_ITERATIONS caps nodes; no recursive model-controlled tool loops exist.
Tools validate Pydantic inputs, time out and retry transient failures once, and
persist/log every invocation. Four worker slots bound concurrent outstanding work.
A timeout cannot kill a running Python thread; its slot remains occupied until it
finishes. API/network timeouts provide additional bounds.

Session profile and the last scheme reference are recovered from persistent memory.
Natural-language text never creates profile values. Ambiguous pronouns require
selecting a scholarship. A submitted profile replaces the saved profile; submit the
complete intended profile when updating. Session token protects all history access.

LLMProvider isolates provider code. GeminiProvider uses JSON schema output.
See [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output).
Fallback: primary provider (one repair retry) -> configured fallback Gemini model/key
(one repair retry) -> deterministic source excerpts -> insufficient-source response.
No key is required for matching or extractive assistance.

For strict grounding, the LLM selects contiguous quotes and chunk IDs. Pydantic
validates shape, and quote membership validates evidence. The server constructs
the final answer and independently attaches authoritative rule results and citations.
Free-form AI factual paraphrases are deliberately not exposed. Every frontend
response, including fallbacks, is ScholarshipAnswer-validated. Quotes and citations
are bounded by retrieved context; sources are never fabricated.

Tokens and cost are stored per call if provided/configured. Missing provider usage
is null, never invented. Input characters and output tokens are configurable.
LLM output is an evidence selector, not an eligibility authority.

Gemini requests use `response_json_schema` rather than the SDK's typed
`response_schema`. This preserves the JSON Schema `additionalProperties: false`
constraint without serializing an unsupported `additional_properties` field.
Local Pydantic validation still rejects extra fields and unsupported evidence.
Permanent request/auth/model errors and quota failures do not receive an immediate
identical retry. Output validation, transport, timeout and server failures may
retry once before proceeding to the configured fallback.
Warnings distinguish `LLM_REQUEST_INVALID`, `LLM_AUTH_FAILED`,
`LLM_MODEL_UNAVAILABLE`, `LLM_RATE_LIMITED`, `LLM_TIMEOUT`, `LLM_NETWORK_ERROR`,
`LLM_PROVIDER_UNAVAILABLE`, `LLM_PROVIDER_ERROR`, and `LLM_RESPONSE_REJECTED`.
Failure logs include a safe error code and HTTP status, never raw provider error
payloads, credentials, or model output.
