# Implementation Plan: Multi-Provider Workload Offload

## Overview

This implementation extends the existing Ollama-only domain expert MCP server into a pluggable multi-provider workload offload system. The approach builds bottom-up: provider abstraction first, then concrete providers, registry, health checks, routing, backward compatibility, and finally server integration. All code lives in `/home/ubuntu/netclaw/mcp-servers/ollama-mcp/`.

## Tasks

- [x] 1. Provider abstraction layer
  - [x] 1.1 Create `providers/__init__.py` and `providers/base.py` with ABC and dataclasses
    - Create the `providers/` package directory
    - Define `GenerationOptions` dataclass with fields: temperature (float, default 0.1), top_p (float, default 0.9), max_tokens (int, default 4096), system_prompt (Optional[str])
    - Define `ProviderResponse` dataclass with fields: text (str), model (str), provider_id (str), token_count (int), elapsed_ms (int), raw (Optional[Dict])
    - Define `ProviderClient` ABC with abstract methods: `provider_id` property, `generate()`, `is_reachable()`, `list_models()`, and optional `close()`
    - Define custom exceptions: `ProviderAuthError`, `ProviderRateLimitError`, `NoProviderAvailableError`
    - Export public API from `providers/__init__.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Concrete provider implementations
  - [x] 2.1 Implement `providers/ollama_local.py` — OllamaProvider
    - Create OllamaProvider class implementing ProviderClient
    - Accept `provider_id`, `base_url`, and `timeout` in constructor
    - Implement `generate()` using httpx POST to `/api/generate` with stream=false
    - Translate `max_tokens` → `num_predict` in Ollama options dict
    - Include `system` field in payload when `options.system_prompt` is set
    - Implement `is_reachable()` with GET `/api/tags` and 5-second timeout
    - Implement `list_models()` parsing `/api/tags` response
    - Implement `close()` to shut down httpx client
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 11.4_

  - [x] 2.2 Implement `providers/ollama_cloud.py` — OllamaCloudProvider
    - Create OllamaCloudProvider extending OllamaProvider
    - Accept additional `api_key` parameter
    - Override HTTP client creation to include `Authorization: Bearer <key>` header
    - Override `generate()` to raise `ProviderAuthError` on 401 responses
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.3 Implement `providers/openai_compat.py` — OpenAIProvider
    - Create OpenAIProvider implementing ProviderClient
    - Accept `provider_id`, `base_url`, `api_key`, and `timeout` in constructor
    - Implement `generate()` using POST `/v1/chat/completions` with OpenAI schema
    - Build messages array: prepend system message if `options.system_prompt` set, then user message with prompt
    - Map generation options directly: temperature, max_tokens, top_p
    - Parse response: extract `choices[0].message.content` for text, `usage.completion_tokens` for token_count
    - Handle HTTP 429: raise `ProviderRateLimitError` with retry_after from Retry-After header
    - Implement `is_reachable()` with GET `/v1/models` and 5-second timeout
    - Implement `list_models()` parsing `/v1/models` response for model IDs
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 11.4_

  - [x] 2.4 Write property tests for provider option translation (Properties 3, 4)
    - **Property 3: Generation options translation** — verify OllamaProvider translates max_tokens→num_predict and OpenAIProvider passes options directly for arbitrary valid option values
    - **Property 4: OpenAI response parsing round-trip** — verify parsing of arbitrary valid OpenAI response JSON produces correct ProviderResponse
    - **Validates: Requirements 2.3, 4.3, 4.4, 11.4**

- [x] 3. Provider registry
  - [x] 3.1 Implement `providers/registry.py` — ProviderRegistry
    - Create ProviderRegistry class with `_providers: Dict[str, ProviderClient]`
    - Implement `discover()` to scan env vars for `PROVIDER_*` patterns:
      - `PROVIDER_OLLAMA_LOCAL_URL` → OllamaProvider("ollama-local", url)
      - `PROVIDER_OLLAMA_CLOUD_URL` + `PROVIDER_OLLAMA_CLOUD_API_KEY` → OllamaCloudProvider("ollama-cloud", url, key)
      - `PROVIDER_OPENAI_<NAME>_URL` + `PROVIDER_OPENAI_<NAME>_API_KEY` → OpenAIProvider("openai-<name>", url, key)
    - Derive provider_id deterministically from env var name pattern
    - Support multiple OpenAI-compatible instances (different NAMEs)
    - Implement `get()`, `has()`, `list_providers()`, `close_all()`
    - Log discovered providers at discovery time
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 12.1_

  - [x] 3.2 Write property test for provider discovery completeness (Property 5)
    - **Property 5: Provider discovery completeness** — for any set of N distinct valid PROVIDER_* env var patterns, verify registry discovers exactly N providers with unique IDs
    - **Validates: Requirements 5.1, 5.2, 5.3, 12.1**

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Health checker
  - [x] 5.1 Implement `health.py` — HealthChecker
    - Define `ProviderHealth` dataclass with fields: provider_id, healthy (bool), consecutive_failures (int), last_check (Optional[float]), last_latency_ms (Optional[int])
    - Create HealthChecker class accepting ProviderRegistry, interval_seconds (default 30), failure_threshold (default 2)
    - Read `HEALTH_CHECK_INTERVAL` and `HEALTH_FAILURE_THRESHOLD` from env vars
    - Implement `start()` to launch async background probe loop
    - Implement `stop()` to cancel the background task
    - Implement `is_healthy(provider_id)` returning bool (unknown providers assumed healthy)
    - Implement `_probe_all()` probing all providers concurrently via `asyncio.gather`
    - Implement `_probe_one()` calling `provider.is_reachable()` and updating ProviderHealth state
    - Mark unhealthy after consecutive_failures >= threshold; mark healthy on single success
    - Implement `get_health_status()` returning dict of all provider health states
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 5.2 Write property test for health state machine transitions (Property 7)
    - **Property 7: Health state machine transitions** — for any provider and any sequence of probe results, verify healthy/unhealthy transitions follow threshold rules
    - **Validates: Requirements 7.2, 7.3**

- [x] 6. Domain router refactor
  - [x] 6.1 Create `routing.py` with refactored DomainRouter
    - Define `RouteConfig` dataclass: domain, provider_id, model, temperature, top_p, max_tokens, system_prompt (Optional), fallback_chain (List[str])
    - Define `RouteDecision` dataclass: provider_id, model, options (GenerationOptions), system_prompt (Optional), is_fallback (bool), fallback_from (Optional[str])
    - Create DomainRouter class accepting ProviderRegistry and HealthChecker
    - Implement `load_routes()` parsing `ROUTE_*` env vars:
      - `ROUTE_<DOMAIN>_PROVIDER` → provider_id
      - `ROUTE_<DOMAIN>_MODEL` → model
      - `ROUTE_<DOMAIN>_TEMPERATURE` → float
      - `ROUTE_<DOMAIN>_MAX_TOKENS` → int
      - `ROUTE_<DOMAIN>_SYSTEM_PROMPT` → inline system prompt
      - `ROUTE_<DOMAIN>_SYSTEM_PROMPT_FILE` → read from file path
      - `ROUTE_<DOMAIN>_FALLBACK` → comma-separated provider IDs
      - `ROUTE_DEFAULT_PROVIDER` → default provider
    - Implement `resolve(domain)` returning RouteDecision:
      - Check primary provider health → return if healthy
      - Walk fallback chain → return first healthy
      - Try ROUTE_DEFAULT_PROVIDER → return if healthy
      - Raise NoProviderAvailableError
    - Validate routes at load time: skip routes referencing non-existent providers with log warning
    - Implement `list_configured_domains()` for backward compat
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.4, 7.5, 7.6, 11.1, 11.2, 11.3, 12.2, 12.3, 12.4_

  - [x] 6.2 Write property tests for routing resolution and fallback (Properties 6, 8)
    - **Property 6: Routing resolution correctness** — for any domain with configured ROUTE_ vars, verify resolve() returns matching provider_id, model, and options
    - **Property 8: Fallback routing under failure** — for any domain with fallback chain where primary is unhealthy, verify resolve() returns first healthy fallback
    - **Validates: Requirements 6.1, 6.2, 6.4, 6.5, 7.4, 7.5, 7.6, 11.1, 11.2, 12.2**

- [x] 7. Backward compatibility layer
  - [x] 7.1 Implement `compat.py` — LegacyConfigAdapter
    - Create LegacyConfigAdapter class with static methods
    - Implement `is_legacy_mode()`: returns True when OLLAMA_* vars present but no PROVIDER_* vars set
    - Implement `synthesize_env_vars()` converting legacy to new-style:
      - `OLLAMA_BASE_URL` → `PROVIDER_OLLAMA_LOCAL_URL`
      - `OLLAMA_MODEL_<DOMAIN>` → `ROUTE_<DOMAIN>_MODEL` + `ROUTE_<DOMAIN>_PROVIDER=ollama-local`
      - `OLLAMA_TEMP_<DOMAIN>` → `ROUTE_<DOMAIN>_TEMPERATURE`
      - `OLLAMA_MODEL_FALLBACK` → `ROUTE_DEFAULT_PROVIDER=ollama-local` with fallback model
    - Log deprecation notice when both legacy and new-style vars are detected
    - _Requirements: 13.1, 13.2, 13.3_

  - [x] 7.2 Write property test for legacy env var compatibility (Property 12)
    - **Property 12: Legacy env var backward compatibility** — for any config with only OLLAMA_* vars, verify synthesized PROVIDER_/ROUTE_ vars produce identical routing
    - **Validates: Requirements 13.1, 13.2**

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Metrics tracker update
  - [x] 9.1 Update `models.py` with new data models
    - Add `ProviderMetrics` model: provider_id, call_count, avg_latency_ms, total_tokens_generated, success_rate, estimated_cost_usd
    - Update `DelegationMetrics` model: add `per_provider` (Dict[str, ProviderMetrics]) and `fallback_events` (Dict[str, int])
    - Add `provider_used` optional field to `ConfigGenerationResponse`, `ExpertQueryResponse`, `DesignValidationResponse`
    - _Requirements: 9.1, 9.4, 8.4_

  - [x] 9.2 Refactor `metrics.py` to support per-provider tracking
    - Update `record_delegation()` signature to accept `provider_id` parameter
    - Add per-provider metrics accumulation (call_count, avg_latency, success_rate, tokens)
    - Implement `record_fallback_event(domain, from_provider, to_provider)`
    - Implement `get_provider_metrics()` returning per-provider breakdown
    - Implement `get_fallback_counts()` returning fallback event counts per domain
    - Update `get_summary()` to include provider breakdown in human-readable output
    - Maintain backward compatibility with existing `get_metrics()` and `get_summary()` format
    - _Requirements: 9.1, 9.2, 9.3, 9.5_

  - [x] 9.3 Write property test for metrics accounting (Property 9)
    - **Property 9: Metrics accounting correctness** — for any sequence of N delegation events, verify total_delegations=N, per-provider counts sum to N, success rates match actual successes
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.5**

- [x] 10. Server.py refactoring and integration
  - [x] 10.1 Refactor `server.py` to use new provider system
    - Replace global `client` + `router` with `registry`, `health_checker`, and new `DomainRouter`
    - Add initialization sequence: LegacyConfigAdapter check → ProviderRegistry.discover() → HealthChecker.start() → DomainRouter.load_routes()
    - Update each tool handler to use `router.resolve(domain)` → `registry.get(provider_id)` → `provider.generate()`
    - Add `provider_used` field to all tool handler responses
    - Implement `degradation_response()` helper returning structured JSON with `NO_PROVIDER_AVAILABLE` message
    - Wrap handler logic in try/except for NoProviderAvailableError
    - Add `health_checker.stop()` and `registry.close_all()` in server shutdown
    - Keep all 10 tool names and input schemas identical
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 10.1, 10.2, 10.3, 10.4_

  - [x] 10.2 Write property test for graceful degradation (Property 10)
    - **Property 10: Graceful degradation invariant** — for any MCP tool call when all providers unreachable, verify structured JSON response with success=false and NO_PROVIDER_AVAILABLE
    - **Validates: Requirements 10.1, 10.2, 10.3**

  - [x] 10.3 Write property test for route validation at startup (Property 11)
    - **Property 11: Route validation at startup** — for any ROUTE_ vars referencing non-existent providers, verify warning logged and route skipped without preventing startup
    - **Validates: Requirements 12.3, 12.4**

- [x] 11. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Test infrastructure and remaining property tests
  - [x] 12.1 Create `tests/conftest.py` with shared fixtures
    - Create `tests/` directory with `conftest.py`
    - Define mock provider fixtures (MockOllamaProvider, MockOpenAIProvider)
    - Define env var helper fixtures for setting/clearing PROVIDER_* and ROUTE_* vars
    - Define ProviderRegistry fixture pre-loaded with mock providers
    - Add hypothesis profile configuration (max_examples=100, deadline=5000ms)
    - Update `requirements.txt` to include `hypothesis>=6.0.0` and `pytest>=7.0.0` and `pytest-asyncio>=0.21.0`
    - _Requirements: All (testing infrastructure)_

  - [x] 12.2 Write property test for provider response contract (Property 1)
    - **Property 1: Provider response contract** — for any valid (model, prompt, options) input, verify generate() returns ProviderResponse with non-empty text, positive token_count, non-negative elapsed_ms, correct provider_id and model
    - **Validates: Requirements 1.1, 8.2**

  - [x] 12.3 Write property test for authentication header inclusion (Property 2)
    - **Property 2: Authentication header inclusion** — for any request through OllamaCloudProvider or OpenAIProvider, verify Authorization Bearer header matches configured key
    - **Validates: Requirements 3.2, 4.2**

- [x] 13. Documentation and configuration updates
  - [x] 13.1 Update `README.md` with multi-provider configuration guide
    - Add "Multi-Provider Configuration" section documenting PROVIDER_* env var patterns
    - Add "Domain Routing" section documenting ROUTE_* env var patterns
    - Add "Health Checks and Fallback" section explaining automatic failover
    - Add migration guide from legacy OLLAMA_* vars to new system
    - Document all supported provider types (Ollama Local, Ollama Cloud, OpenAI-compatible)
    - Include example `.env` configurations for common setups (local-only, local+cloud, multi-provider)
    - _Requirements: 12.1, 12.2, 13.1_

  - [x] 13.2 Update `.env.example` with new provider environment variables
    - Add commented PROVIDER_* examples for each provider type
    - Add commented ROUTE_* examples for common domain configurations
    - Add HEALTH_* configuration examples
    - Keep existing OLLAMA_* vars with deprecation note
    - Path: `/home/ubuntu/netclaw/.env.example`
    - _Requirements: 12.1, 12.2_

  - [x] 13.3 Update workspace memory-bank with new architecture context
    - Update `/home/ubuntu/netclaw/.amazonq/rules/memory-bank/tech.md` with multi-provider architecture
    - Update `/home/ubuntu/netclaw/.amazonq/rules/memory-bank/structure.md` with new file layout (providers/ directory, routing.py, health.py, compat.py)
    - Update `/home/ubuntu/netclaw/.amazonq/rules/memory-bank/progress.md` with feature status
    - _Requirements: N/A (developer experience)_

- [x] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties defined in the design document
- Unit tests validate specific examples and edge cases
- All code targets Python 3.10+ with async/await patterns
- The existing `ollama_client.py` is superseded by `providers/ollama_local.py` but kept as deprecated import redirect
- The existing `router.py` is superseded by `routing.py` but kept for one release with deprecation redirect
- Hypothesis is used for property-based testing with minimum 100 examples per property

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3"] },
    { "id": 3, "tasks": ["2.4", "3.1"] },
    { "id": 4, "tasks": ["3.2", "5.1"] },
    { "id": 5, "tasks": ["5.2", "6.1"] },
    { "id": 6, "tasks": ["6.2", "7.1"] },
    { "id": 7, "tasks": ["7.2", "9.1"] },
    { "id": 8, "tasks": ["9.2"] },
    { "id": 9, "tasks": ["9.3", "10.1"] },
    { "id": 10, "tasks": ["10.2", "10.3", "12.1"] },
    { "id": 11, "tasks": ["12.2", "12.3"] },
    { "id": 12, "tasks": ["13.1", "13.2", "13.3"] }
  ]
}
```
