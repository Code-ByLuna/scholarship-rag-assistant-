# Bounded conversational assistant

One LangGraph DAG: plan -> semantic scholarship retrieval -> grounded generation.
The previous deterministic eligibility tool and profile recovery were removed.
`AGENT_MAX_ITERATIONS` caps graph steps. Four retrieval worker slots bound concurrent
outstanding tools; timeout cannot kill a Python thread, so a running worker keeps
its slot until completion. Tool arguments are Pydantic-validated and failures logged.

Private sessions retain messages and the last cited scheme references. The history
contains both questions and generated responses. An off-topic/error turn does not
erase the last useful scholarship reference. No permanent personal profile is
created or updated. Session access requires the secret capability token header.

Gemini remains behind `LLMProvider`. `response_json_schema` preserves strict JSON
Schema without the SDK's invalid `additional_properties` typed-schema serialization.
The draft has `answer`, `status`, `supports`; natural answer text is returned unchanged.
Evidence membership and source URLs are checked locally, followed by a separate
`GroundingReview`. Provider usage is recorded separately for generation and verification.
Only provider/model/phase/status/counts/timing/error codes are logged, not prompt text,
answers, raw provider exceptions or credentials.

One repair retry corrects malformed evidence or grounding issues. Auth/config/model
and quota failures are not immediately retried with the identical request. A configured
secondary Gemini model/key can be attempted. No provider success means an explicit
HTTP 503 response, never an extractive fake AI answer. Input character/output token
limits apply to generation and verification. A normal successful turn uses two model
calls; a repair/fallback can use more, increasing latency and token consumption.

Errors distinguish missing configuration/key, invalid request, authentication,
unavailable model, quota, timeout, network/server outage and rejected generation.
`LLM_NOT_CONFIGURED`, `MISSING_API_KEY`, `LLM_REQUEST_INVALID`, `LLM_AUTH_FAILED`,
`LLM_MODEL_UNAVAILABLE`, `LLM_RATE_LIMITED`, `LLM_TIMEOUT`, `LLM_NETWORK_ERROR`,
`LLM_PROVIDER_UNAVAILABLE`, `LLM_PROVIDER_ERROR`, `LLM_CONTEXT_LIMIT`, and
`LLM_RESPONSE_REJECTED` are safe operational codes.
