# Optional AI layer

Phase 10 adds an isolated `LLMProvider` boundary with deterministic mock and OpenAI Responses API implementations. Prompt templates are versioned persisted records, outputs are schema-constrained JSON, and every invocation records model, provider, prompt version, input hash, token counts, latency, status, and safe failure telemetry. Supply-network, risk, and optimization decisions do not depend on AI execution.
