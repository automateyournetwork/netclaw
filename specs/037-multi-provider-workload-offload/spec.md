# Requirements Document

## Introduction

This feature expands the existing Ollama-only domain expert MCP server into a generic multi-provider workload offload system. The 10 existing MCP tool interfaces remain unchanged while the backend gains the ability to route workloads to Ollama Local, Ollama Cloud, OpenAI-compatible APIs (vLLM, Together, Groq, OpenRouter), or any future provider via a pluggable architecture. Domain-to-provider routing is configurable via environment variables, with health-check-driven fallback, provider-level metrics, and graceful degradation when no provider is available.

## Glossary

- **MCP_Server**: The MCP stdio server (`server.py`) exposing 10 domain expert delegation tools to orchestrating AI agents
- **Provider**: A backend LLM inference service that can fulfill generation requests (e.g., Ollama Local, Ollama Cloud, OpenAI-compatible endpoint)
- **Provider_Registry**: The component that discovers, instantiates, and manages configured providers from environment variables
- **Domain_Router**: The component that maps domain expert requests to a specific provider and model based on configuration and provider health
- **Provider_Client**: An abstract interface that all provider implementations must satisfy to handle generation requests
- **Health_Checker**: The component that periodically probes provider endpoints and tracks their availability status
- **Metrics_Tracker**: The component that records per-provider and per-domain delegation statistics including latency, success rate, and estimated cost
- **Fallback_Chain**: An ordered list of providers configured for a domain, used when the primary provider is unreachable
- **Domain**: A named area of expertise (e.g., ospf, bgp, graphql) that maps to a specific model and provider configuration
- **Orchestrating_Agent**: The external AI agent (Claude, GPT, etc.) that calls MCP tools to delegate workloads

## Requirements

### Requirement 1: Provider Abstraction Interface

**User Story:** As a developer, I want a common provider interface, so that new LLM backends can be added without modifying tool handlers or routing logic.

#### Acceptance Criteria

1. THE Provider_Client SHALL define an async `generate` method accepting model name, prompt, optional system prompt, and generation options, and returning a standardized response containing the generated text, token counts, and elapsed time
2. THE Provider_Client SHALL define an async `is_reachable` method that returns a boolean indicating whether the provider endpoint is responsive
3. THE Provider_Client SHALL define an async `list_models` method that returns available model identifiers for the provider
4. WHEN a new provider type is added, THE Provider_Registry SHALL discover it without requiring changes to the Domain_Router or MCP_Server tool handlers

### Requirement 2: Ollama Local Provider

**User Story:** As a network engineer, I want to continue using my local Ollama GPU box for workload offload, so that I retain low-latency local inference with no per-token cost.

#### Acceptance Criteria

1. THE Provider_Registry SHALL instantiate an Ollama Local provider WHEN the environment variable `PROVIDER_OLLAMA_LOCAL_URL` is set
2. THE Ollama Local Provider_Client SHALL communicate with the Ollama HTTP API at the configured URL using the `/api/generate` and `/api/chat` endpoints
3. THE Ollama Local Provider_Client SHALL support per-request generation options including temperature, top_p, and num_predict
4. WHEN the Ollama Local endpoint is unreachable, THE Ollama Local Provider_Client `is_reachable` method SHALL return false within 5 seconds

### Requirement 3: Ollama Cloud Provider

**User Story:** As a network engineer, I want to offload workloads to Ollama Cloud when my local GPU is busy or unavailable, so that I have a cloud fallback without changing my workflow.

#### Acceptance Criteria

1. THE Provider_Registry SHALL instantiate an Ollama Cloud provider WHEN the environment variables `PROVIDER_OLLAMA_CLOUD_URL` and `PROVIDER_OLLAMA_CLOUD_API_KEY` are set
2. THE Ollama Cloud Provider_Client SHALL include the API key in request headers as an Authorization Bearer token
3. THE Ollama Cloud Provider_Client SHALL communicate with the Ollama Cloud API using the same endpoint paths as Ollama Local
4. WHEN the Ollama Cloud API returns an authentication error, THE Ollama Cloud Provider_Client SHALL raise a descriptive error indicating invalid credentials

### Requirement 4: OpenAI-Compatible Provider

**User Story:** As a network engineer, I want to route workloads to OpenAI-compatible APIs (vLLM, Together, Groq, OpenRouter), so that I can leverage diverse inference backends without code changes.

#### Acceptance Criteria

1. THE Provider_Registry SHALL instantiate an OpenAI-compatible provider WHEN environment variables matching the pattern `PROVIDER_OPENAI_<NAME>_URL` and `PROVIDER_OPENAI_<NAME>_API_KEY` are set
2. THE OpenAI-compatible Provider_Client SHALL send requests to the `/v1/chat/completions` endpoint with the standard OpenAI request schema
3. THE OpenAI-compatible Provider_Client SHALL map the standardized generation options (temperature, max_tokens, top_p) to the OpenAI request format
4. THE OpenAI-compatible Provider_Client SHALL parse OpenAI-format responses and return a standardized response containing the generated text, token usage, and elapsed time
5. WHEN the OpenAI-compatible endpoint returns a rate limit error (HTTP 429), THE OpenAI-compatible Provider_Client SHALL include the retry-after duration in the error response

### Requirement 5: Provider Discovery and Registration

**User Story:** As a developer, I want providers to be automatically discovered from environment variables at startup, so that adding or removing providers requires only environment changes.

#### Acceptance Criteria

1. WHEN the MCP_Server starts, THE Provider_Registry SHALL scan environment variables for provider configuration patterns and instantiate matching providers
2. THE Provider_Registry SHALL support multiple instances of the same provider type (e.g., two separate OpenAI-compatible endpoints with different names)
3. THE Provider_Registry SHALL assign each provider a unique identifier derived from its configuration name (e.g., `ollama-local`, `ollama-cloud`, `openai-groq`)
4. THE Provider_Registry SHALL log the list of discovered providers and their identifiers at startup

### Requirement 6: Domain-to-Provider Routing

**User Story:** As a network engineer, I want to map domains to specific providers via environment variables, so that I can route heavy tasks to my local GPU and light tasks to cloud providers.

#### Acceptance Criteria

1. THE Domain_Router SHALL read domain-to-provider mappings from environment variables matching the pattern `ROUTE_<DOMAIN>_PROVIDER=<provider-id>`
2. THE Domain_Router SHALL read domain-to-model mappings from environment variables matching the pattern `ROUTE_<DOMAIN>_MODEL=<model-name>`
3. WHEN a domain has no explicit provider route configured, THE Domain_Router SHALL use the provider specified by `ROUTE_DEFAULT_PROVIDER`
4. THE Domain_Router SHALL support per-domain generation parameters via environment variables matching the pattern `ROUTE_<DOMAIN>_TEMPERATURE`, `ROUTE_<DOMAIN>_MAX_TOKENS`
5. THE Domain_Router SHALL resolve a domain request to a provider identifier, model name, and generation options as a single routing decision

### Requirement 7: Provider Health Checks and Fallback

**User Story:** As a network engineer, I want automatic fallback to an alternate provider when my primary is unreachable, so that workload offload continues without manual intervention.

#### Acceptance Criteria

1. THE Health_Checker SHALL probe each configured provider's `is_reachable` endpoint at a configurable interval (default 30 seconds)
2. THE Health_Checker SHALL mark a provider as unhealthy after a configurable number of consecutive failures (default 2)
3. THE Health_Checker SHALL mark a provider as healthy after a single successful probe following an unhealthy state
4. WHEN the primary provider for a domain is marked unhealthy, THE Domain_Router SHALL route the request to the next provider in the domain's Fallback_Chain
5. THE Domain_Router SHALL read fallback chain configuration from environment variables matching the pattern `ROUTE_<DOMAIN>_FALLBACK=<provider-id-1>,<provider-id-2>`
6. WHEN a domain has no explicit fallback configured, THE Domain_Router SHALL fall back to the provider specified by `ROUTE_DEFAULT_PROVIDER`

### Requirement 8: Stable MCP Tool Interfaces

**User Story:** As an orchestrating agent developer, I want the 10 existing MCP tool interfaces to remain unchanged, so that no changes are needed in orchestrating agent configurations or prompts.

#### Acceptance Criteria

1. THE MCP_Server SHALL expose the same 10 tool names with identical input schemas as the current implementation
2. THE MCP_Server SHALL return responses in the same JSON structure as the current implementation
3. WHEN a tool is called, THE MCP_Server SHALL route the request through the Domain_Router and Provider_Client without exposing provider details in the tool response schema
4. THE MCP_Server response SHALL include a `model_used` field and a `provider_used` field in tool responses for observability without changing the existing response structure

### Requirement 9: Provider-Level Metrics

**User Story:** As a network engineer, I want per-provider metrics (latency, success rate, estimated cost), so that I can evaluate which providers deliver the best performance for my workloads.

#### Acceptance Criteria

1. THE Metrics_Tracker SHALL record latency, token count, and success/failure for each delegation grouped by both domain and provider
2. THE Metrics_Tracker SHALL calculate a running success rate per provider
3. THE Metrics_Tracker SHALL calculate estimated cost savings comparing local provider cost (zero) against estimated frontier model cost
4. WHEN the `ollama_delegation_stats` tool is called, THE MCP_Server SHALL return metrics with a per-provider breakdown in addition to the existing per-domain breakdown
5. THE Metrics_Tracker SHALL track the number of fallback events per domain

### Requirement 10: Graceful Degradation

**User Story:** As an orchestrating agent, I want a clear error message when no offload provider is available, so that I know to handle the task directly rather than retrying or failing silently.

#### Acceptance Criteria

1. WHEN no configured provider for a domain is reachable and no fallback is available, THE MCP_Server SHALL return a response with `success` set to false and a message instructing the orchestrating agent to handle the task directly
2. THE degradation response SHALL include the text "NO_PROVIDER_AVAILABLE" in the error message to enable programmatic detection by the orchestrating agent
3. THE MCP_Server SHALL NOT raise an unhandled exception or return an empty response when all providers are unreachable
4. WHEN a provider becomes unreachable mid-request, THE MCP_Server SHALL attempt the next provider in the Fallback_Chain before returning a degradation response

### Requirement 11: Provider-Specific Parameters

**User Story:** As a network engineer, I want to configure provider-specific parameters (temperature, max tokens, system prompts) per domain, so that each domain expert uses optimal settings for its provider backend.

#### Acceptance Criteria

1. THE Domain_Router SHALL support per-domain system prompt configuration via the environment variable `ROUTE_<DOMAIN>_SYSTEM_PROMPT` or a file path `ROUTE_<DOMAIN>_SYSTEM_PROMPT_FILE`
2. THE Domain_Router SHALL pass provider-specific generation options (temperature, max_tokens, top_p) from route configuration to the Provider_Client
3. WHEN a domain has no explicit generation parameters configured, THE Domain_Router SHALL use provider-level defaults
4. THE Provider_Client SHALL translate generic generation options into provider-specific request parameters (e.g., `num_predict` for Ollama, `max_tokens` for OpenAI)

### Requirement 12: Environment Variable Configuration Pattern

**User Story:** As a developer, I want providers defined separately from domain routing in environment variables, so that the configuration is modular and easy to understand.

#### Acceptance Criteria

1. THE Provider_Registry SHALL read provider definitions from environment variables with the prefix `PROVIDER_` (e.g., `PROVIDER_OLLAMA_LOCAL_URL`, `PROVIDER_OPENAI_GROQ_API_KEY`)
2. THE Domain_Router SHALL read routing definitions from environment variables with the prefix `ROUTE_` (e.g., `ROUTE_OSPF_PROVIDER`, `ROUTE_BGP_MODEL`)
3. THE MCP_Server SHALL validate that all referenced provider identifiers in route configurations correspond to discovered providers at startup
4. IF a route references a provider identifier that was not discovered, THEN THE MCP_Server SHALL log a warning and skip that route entry rather than failing to start

### Requirement 13: Backward Compatibility with Existing Configuration

**User Story:** As an existing user, I want my current `OLLAMA_MODEL_*` and `OLLAMA_BASE_URL` environment variables to continue working, so that I can migrate to the new system incrementally.

#### Acceptance Criteria

1. WHEN legacy environment variables (`OLLAMA_BASE_URL`, `OLLAMA_MODEL_*`, `OLLAMA_TEMP_*`) are present and no `PROVIDER_*` variables are set, THE MCP_Server SHALL operate in legacy mode using the existing Ollama-only routing
2. WHEN both legacy and new-style environment variables are present, THE MCP_Server SHALL prefer the new-style `PROVIDER_*` and `ROUTE_*` configuration
3. THE MCP_Server SHALL log a deprecation notice when legacy environment variables are detected alongside new-style configuration
