# Requirements Document

## Introduction

This feature evolves the existing domain-based workload routing in the ollama-mcp server to support vendor-specific routing. Instead of routing by protocol domain (ospf, bgp, mpls), the system routes to distilled 7B models trained by NetClaw Foundry as vendor specialists (netclaw-cisco:7b, netclaw-arista:7b, netclaw-juniper:7b, netclaw-paloalto:7b, netclaw-f5:7b). The orchestrator already knows the vendor from device context (pyATS testbed platform, Nautobot device platform), so vendor routing eliminates redundant per-protocol configuration and enables lighter prompts since distilled models carry CLI syntax knowledge in their weights.

The migration is phased: vendor routing is additive alongside existing domain routing, with vendor taking priority when present, allowing gradual deprecation of the 20+ protocol-based ROUTE_* variables in favor of ~5 vendor routes.

## Glossary

- **Domain_Router**: The component that maps domain expert requests to a specific provider and model based on ROUTE_* environment variable configuration and provider health state
- **Vendor_Router**: The extension to the Domain_Router that resolves vendor-specific model routing using ROUTE_VENDOR_* environment variables, taking priority over domain-based routing when a vendor parameter is supplied
- **MCP_Server**: The MCP stdio server (`server.py`) exposing 10 domain expert delegation tools to orchestrating AI agents
- **Orchestrating_Agent**: The external AI agent (Claude, DeepSeek) that calls MCP tools to delegate workloads and already knows the target device vendor from pyATS testbed or Nautobot platform data
- **Vendor**: The network device manufacturer (cisco, arista, juniper, paloalto, f5) that determines which distilled specialist model serves a request
- **Platform**: The specific operating system or product line within a vendor (e.g., ios-xe, ios-xr, nx-os, eos, junos, pan-os, big-ip)
- **Distilled_Model**: A 7B parameter model trained via knowledge distillation in NetClaw Foundry that carries vendor-specific CLI syntax and configuration knowledge in its weights, requiring minimal system prompts
- **Vendor_Route**: A routing entry mapping a vendor identifier to a provider, model, and generation options via ROUTE_VENDOR_* environment variables
- **Domain_Route**: The existing routing entry mapping a protocol domain to a provider, model, and generation options via ROUTE_* environment variables (retained for backward compatibility)
- **Prompt_Template**: The prompt construction logic that builds context for LLM generation, adapted for distilled models that need lighter prompts
- **Delegation_Skill**: The SKILL.md document guiding the orchestrating agent on when and how to delegate workloads, including vendor routing parameters

## Requirements

### Requirement 1: Vendor Routing Key

**User Story:** As a network engineer, I want the routing system to accept a vendor parameter that maps to a distilled specialist model, so that requests are served by a model with deep vendor-specific knowledge.

#### Acceptance Criteria

1. THE Vendor_Router SHALL accept a `vendor` parameter with values from the set: cisco, arista, juniper, paloalto, f5 (case-insensitive, normalized to lowercase before lookup)
2. THE Vendor_Router SHALL read vendor-to-provider mappings from environment variables matching the pattern `ROUTE_VENDOR_<VENDOR>_PROVIDER=<provider-id>` where `<VENDOR>` is the uppercase vendor name
3. THE Vendor_Router SHALL read vendor-to-model mappings from environment variables matching the pattern `ROUTE_VENDOR_<VENDOR>_MODEL=<model-name>` where `<VENDOR>` is the uppercase vendor name
4. WHEN both a `vendor` parameter and a `domain` parameter are present in a request, THE Vendor_Router SHALL resolve using the vendor route and ignore the domain route
5. WHEN only a `domain` parameter is present with no `vendor` parameter, THE Domain_Router SHALL resolve using the existing domain-based routing logic
6. IF the `vendor` parameter value is not in the supported set, THEN THE Vendor_Router SHALL reject the request with an error message indicating the vendor is unsupported and listing the valid vendor values
7. IF the `ROUTE_VENDOR_<VENDOR>_PROVIDER` or `ROUTE_VENDOR_<VENDOR>_MODEL` environment variable is missing for a supported vendor, THEN THE Vendor_Router SHALL skip that vendor during route loading and log a warning identifying the missing variable
8. IF the `ROUTE_VENDOR_<VENDOR>_PROVIDER` references a provider not present in the provider registry, THEN THE Vendor_Router SHALL skip that vendor route during loading and log a warning identifying the unknown provider

### Requirement 2: Platform Context Parameter

**User Story:** As an orchestrating agent, I want to pass the device platform alongside vendor, so that the prompt construction can include platform-specific hints when needed.

#### Acceptance Criteria

1. THE MCP_Server tool input schemas SHALL accept an optional `platform` parameter of type string with a maximum length of 32 characters alongside the existing `domain` parameter
2. THE Vendor_Router SHALL pass the platform value to the Prompt_Template for inclusion in generation context
3. WHEN the `platform` parameter is absent, THE Vendor_Router SHALL resolve routing using only the vendor parameter without error
4. IF the `platform` parameter is provided and is an empty string or exceeds 32 characters, THEN THE MCP_Server SHALL reject the request with an error indicating that the platform value is invalid
5. THE MCP_Server SHALL accept platform values as case-insensitive free-form strings without restricting to a predefined set

### Requirement 3: MCP Tool Schema Updates

**User Story:** As an orchestrating agent developer, I want the MCP tool input schemas to accept `vendor` and `platform` parameters, so that vendor-aware delegation works through the existing tool interfaces.

#### Acceptance Criteria

1. THE MCP_Server SHALL add an optional `vendor` property of type string to the input schemas of `ollama_generate_config`, `ollama_validate_design`, `ollama_domain_query`, and `ollama_validate_config_against_sot`
2. THE MCP_Server SHALL add an optional `platform` property of type string to the input schemas of `ollama_generate_config`, `ollama_validate_design`, `ollama_domain_query`, and `ollama_validate_config_against_sot`
3. IF `vendor` is provided in a tool call, THEN THE MCP_Server SHALL NOT require the `domain` property in that tool's input schema validation
4. IF `domain` is provided without `vendor` in a tool call, THEN THE MCP_Server SHALL continue to route the request using the existing domain-based model routing
5. WHEN neither `vendor` nor `domain` is provided in a tool call, THE MCP_Server SHALL return an error indicating that at least one routing key (`vendor` or `domain`) is required
6. WHEN both `vendor` and `domain` are provided in a tool call, THE MCP_Server SHALL accept the request without error and use both properties for routing

### Requirement 4: Vendor Route Environment Configuration

**User Story:** As a network engineer, I want to configure vendor routes with approximately 5 environment variables instead of 20+ domain routes, so that my configuration is simpler to manage.

#### Acceptance Criteria

1. THE Vendor_Router SHALL support per-vendor generation parameters via environment variables matching the pattern `ROUTE_VENDOR_<VENDOR>_TEMPERATURE` (a float value between 0.0 and 2.0 inclusive) and `ROUTE_VENDOR_<VENDOR>_MAX_TOKENS` (a positive integer between 1 and 1,000,000 inclusive)
2. THE Vendor_Router SHALL support per-vendor fallback chains via the environment variable `ROUTE_VENDOR_<VENDOR>_FALLBACK=<provider-id-1>,<provider-id-2>` where provider identifiers are separated by commas and the chain contains at most 5 entries
3. WHEN the MCP_Server starts, THE Vendor_Router SHALL scan environment variables for vendor configuration patterns and log each discovered vendor route including the vendor name, resolved provider, model, and whether optional parameters (temperature, max_tokens, fallback) are configured
4. IF a vendor route references a provider identifier that was not discovered by the Provider_Registry, THEN THE MCP_Server SHALL log a warning including the vendor name and unresolved provider identifier, and skip that vendor route entry rather than failing to start
5. IF a `ROUTE_VENDOR_<VENDOR>_TEMPERATURE` or `ROUTE_VENDOR_<VENDOR>_MAX_TOKENS` environment variable contains a value that cannot be parsed as the expected numeric type or falls outside the valid range, THEN THE Vendor_Router SHALL log a warning identifying the vendor and invalid variable, ignore that parameter, and continue loading the vendor route with default generation settings

### Requirement 5: Vendor-Aware Prompt Construction

**User Story:** As a network engineer, I want distilled models to receive lighter prompts without verbose system instructions, so that token budget is preserved and latency is reduced.

#### Acceptance Criteria

1. WHEN a request is routed via a vendor route, THE Prompt_Template SHALL omit the system prompt from the generation request unless an explicit override is configured via `ROUTE_VENDOR_<VENDOR>_SYSTEM_PROMPT`; when an override IS configured, the Prompt_Template SHALL send its value as the system prompt to the provider API
2. WHEN a request is routed via a vendor route and a platform value is provided, THE Prompt_Template SHALL include the platform identifier as a "Platform: <value>" line at the beginning of the user prompt before the task description
3. WHEN a request is routed via a vendor route, THE Prompt_Template SHALL NOT include output format directives (e.g., "Generate ONLY the configuration block. No explanation, no markdown fences.") in the prompt
4. THE Prompt_Template SHALL retain device context fields (hostname, interfaces, router_id, ASN) in vendor-routed prompts using the same structure, inclusion logic, and formatting as domain-routed prompts
5. WHEN a request is routed via a vendor route and user-supplied constraints are present, THE Prompt_Template SHALL include those constraints in the prompt without modification
6. IF a `ROUTE_VENDOR_<VENDOR>_SYSTEM_PROMPT_FILE` is configured and the file cannot be read, THEN THE Prompt_Template SHALL log a warning and proceed without a system prompt

### Requirement 6: Backward Compatibility with Domain Routing

**User Story:** As an existing user, I want my current domain-based ROUTE_* environment variables to continue working without changes, so that I can migrate to vendor routing at my own pace.

#### Acceptance Criteria

1. WHEN no ROUTE_VENDOR_* environment variables are configured, THE Domain_Router SHALL operate using domain-based routing with no behavioral changes
2. WHEN both domain routes and vendor routes are configured, THE MCP_Server SHALL load and validate both route types at startup without either interfering with the other
3. THE existing domain-based routing resolution (primary → fallback chain → default provider) SHALL continue to function for requests that do not include a vendor parameter
4. THE MCP_Server SHALL log a count of configured domain routes and vendor routes at startup for operational visibility
5. IF ROUTE_VENDOR_* variables contain validation errors but ROUTE_* domain variables are valid, THEN THE MCP_Server SHALL continue to start and serve domain-routed requests while logging warnings about the invalid vendor routes

### Requirement 7: Vendor Route Health and Fallback

**User Story:** As a network engineer, I want vendor-routed requests to fall back to alternate providers when the primary is unavailable, so that vendor delegation remains reliable.

#### Acceptance Criteria

1. WHEN the primary provider for a vendor route is marked unhealthy by the Health_Checker, THE Vendor_Router SHALL route the request to the first healthy provider in the vendor's fallback chain in declared order
2. IF a vendor route's primary provider is unhealthy and no explicit fallback chain is configured, or all providers in the fallback chain are unhealthy, THEN THE Vendor_Router SHALL attempt to route the request to the provider specified by `ROUTE_DEFAULT_PROVIDER`
3. IF no provider in the vendor's resolution chain (primary, fallback chain, and `ROUTE_DEFAULT_PROVIDER`) is healthy, THEN THE MCP_Server SHALL return an error response containing "NO_PROVIDER_AVAILABLE" and SHALL NOT fall through to domain-based routing
4. THE Health_Checker SHALL use the same health probing logic (probe interval, consecutive failure threshold, and recovery-on-single-success rule) for providers serving vendor routes as for providers serving domain routes
5. WHEN the Vendor_Router routes a request to a fallback provider, THE Vendor_Router SHALL use the model and generation parameters from the original vendor route configuration

### Requirement 8: Delegation Skill Documentation Update

**User Story:** As an orchestrating agent, I want the delegation skill documentation to explain vendor-based routing, so that I know when and how to pass vendor and platform parameters.

#### Acceptance Criteria

1. THE Delegation_Skill document SHALL include a decision rule stating that the orchestrator SHALL use vendor routing when the target device vendor matches one of the supported values (cisco, arista, juniper, paloalto, f5) and SHALL fall back to domain routing when the device vendor is unknown or not in the supported set
2. THE Delegation_Skill document SHALL include a vendor-to-platform mapping table listing all 5 supported vendors and their corresponding platform identifiers: cisco (ios-xe, ios-xr, nx-os), arista (eos), juniper (junos), paloalto (pan-os), f5 (big-ip)
3. THE Delegation_Skill document SHALL include at least 1 example deriving the vendor parameter from a pyATS testbed `os` field and at least 1 example deriving the vendor parameter from a Nautobot device `platform` field, showing the source field value and the resulting vendor and platform tool parameters
4. THE Delegation_Skill document SHALL state that distilled models routed via vendor routes do not require system prompts, CLI syntax instructions, or configuration format guidelines, and SHALL advise the orchestrator to pass only device context fields (hostname, interfaces, router_id, ASN) and the task description when delegating to vendor routes
5. THE Delegation_Skill document SHALL state that when the orchestrator cannot determine the device vendor or the vendor is not in the supported set, the orchestrator SHALL use domain routing with the domain parameter (e.g., ospf, bgp, mpls) instead

### Requirement 9: SOUL.md Orchestrator Guidance

**User Story:** As a network engineer, I want the SOUL.md to instruct the orchestrator to prefer vendor routing when device context is available, so that distilled models are used by default for known vendors.

#### Acceptance Criteria

1. THE SOUL.md SHALL include a decision rule instructing the Orchestrating_Agent to use vendor routing when the target device vendor is one of: cisco, arista, juniper, paloalto, f5
2. THE SOUL.md SHALL instruct the Orchestrating_Agent to derive the vendor value from the pyATS testbed `os` field or the Nautobot device `platform` field, checking the pyATS testbed first and falling back to Nautobot when the pyATS testbed is unavailable or does not contain the target device
3. THE SOUL.md SHALL instruct the Orchestrating_Agent to fall back to domain routing when the device vendor value is absent from device context, or when the resolved vendor is not in the supported set (cisco, arista, juniper, paloalto, f5)
4. THE SOUL.md SHALL instruct the Orchestrating_Agent to pass the platform value (e.g., ios-xe, nx-os, eos) alongside vendor when the pyATS testbed `platform` field or Nautobot device `platform` field contains a value for the target device
5. IF no device context is available for the target device (neither pyATS testbed entry nor Nautobot device record exists), THEN THE SOUL.md SHALL instruct the Orchestrating_Agent to use domain routing and include the domain parameter derived from the task type

### Requirement 10: Vendor Route Metrics

**User Story:** As a network engineer, I want delegation metrics to include a per-vendor breakdown, so that I can evaluate the performance and accuracy of each distilled model.

#### Acceptance Criteria

1. THE Metrics_Tracker SHALL record latency (in milliseconds), token count, and success/failure for each delegation grouped by vendor in addition to the existing domain and provider groupings, such that a vendor-routed request is recorded in both the per-vendor breakdown and the per-domain breakdown (using the request's domain parameter if present)
2. WHEN the `ollama_delegation_stats` tool is called, THE MCP_Server SHALL return metrics with a per-vendor breakdown showing, for each vendor that received at least one delegation: request count, average latency in milliseconds, total tokens generated, and success rate as a value between 0.0 and 1.0
3. THE Metrics_Tracker SHALL maintain two running totals: the count of requests routed via a vendor route and the count of requests routed via a domain route, and both counts SHALL be included in the `ollama_delegation_stats` output
4. THE Metrics_Tracker SHALL record fallback events for vendor routes keyed by vendor identifier (e.g., "cisco", "arista") and SHALL store these separately from domain route fallback events which are keyed by domain name (e.g., "ospf", "bgp")
5. IF the `ollama_delegation_stats` tool is called and no delegations have been routed via vendor routes, THEN THE MCP_Server SHALL omit the per-vendor breakdown section from the response rather than returning an empty vendor section

### Requirement 11: Vendor Routing Resolution Order

**User Story:** As a developer, I want a clear resolution precedence for routing decisions, so that the system behaves predictably when multiple routing keys are available.

#### Acceptance Criteria

1. THE Domain_Router SHALL resolve routing in the following precedence order: vendor route (when vendor parameter is present and a matching ROUTE_VENDOR_* config exists), then domain route (when domain parameter is present and a matching ROUTE_* config exists), then ROUTE_DEFAULT_PROVIDER
2. WHEN a vendor parameter is present but no matching ROUTE_VENDOR_* configuration exists and a domain parameter is also present, THE Domain_Router SHALL fall through to domain-based resolution using the domain parameter
3. IF a vendor parameter is present and a matching vendor route exists but all providers in the vendor route (primary, fallback chain, and ROUTE_DEFAULT_PROVIDER) are unhealthy, THEN THE Domain_Router SHALL NOT fall through to domain routing and SHALL return a degradation response containing "NO_PROVIDER_AVAILABLE"
4. THE Domain_Router SHALL log the routing decision path at INFO level, recording one of the following values for each resolved request: vendor-hit, vendor-fallback, domain-hit, domain-fallback, default
5. IF a vendor parameter is present with no matching ROUTE_VENDOR_* configuration and no domain parameter is present, THEN THE Domain_Router SHALL resolve using ROUTE_DEFAULT_PROVIDER
