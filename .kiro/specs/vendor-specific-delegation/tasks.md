# Implementation Plan: Vendor-Specific Delegation

## Overview

Extend the ollama-mcp server's domain-based routing with vendor-specific model routing. The implementation adds vendor route configuration loading, unified routing resolution with vendor-over-domain precedence, vendor-aware prompt construction, per-vendor metrics, MCP tool schema updates, and documentation updates. All changes are additive and backward-compatible with existing domain routing.

## Tasks

- [ ] 1. Add data models and validation
  - [ ] 1.1 Add VendorRouteConfig, VendorMetrics, and RoutingInput models to models.py
    - Add `VendorRouteConfig` dataclass with fields: vendor, provider_id, model, temperature, max_tokens, system_prompt, fallback_chain
    - Add `VendorMetrics` Pydantic model with fields: vendor, call_count, avg_latency_ms, total_tokens_generated, success_rate
    - Add `RoutingInput` Pydantic model with vendor, platform, domain fields; include `at_least_one_routing_key` model validator and `validate_vendor` / `validate_platform` field validators
    - Add `SUPPORTED_VENDORS` frozenset constant: {"cisco", "arista", "juniper", "paloalto", "f5"}
    - Extend `DelegationMetrics` with: per_vendor dict, vendor_fallback_events dict, vendor_routed_count int, domain_routed_count int
    - _Requirements: 1.1, 1.6, 2.4, 2.5, 3.3, 3.5, 10.1_

  - [ ]* 1.2 Write property tests for vendor input validation (Property 1)
    - **Property 1: Vendor Input Validation**
    - Test that any string is accepted iff its lowercase-normalized form is in SUPPORTED_VENDORS
    - Test that accepted values are stored as lowercase; rejected values produce error listing valid set
    - **Validates: Requirements 1.1, 1.6**

  - [ ]* 1.3 Write property tests for platform validation (Property 6)
    - **Property 6: Platform Validation**
    - Test that non-empty strings ≤ 32 chars are accepted; empty strings and strings > 32 chars are rejected
    - Test that absent platform is accepted without error
    - **Validates: Requirements 2.4, 2.5, 2.3**

  - [ ]* 1.4 Write property tests for routing key requirement (Property 5)
    - **Property 5: Routing Key Requirement**
    - Test that requests with at least one of vendor/domain are accepted; requests with neither are rejected
    - Test that vendor-only (no domain) is accepted
    - **Validates: Requirements 3.3, 3.5**

- [ ] 2. Implement vendor route loading in routing.py
  - [ ] 2.1 Add vendor route loading to DomainRouter
    - Add `_vendor_routes: Dict[str, VendorRouteConfig]` attribute
    - Add `load_vendor_routes()` method that scans `ROUTE_VENDOR_*` env vars
    - Parse PROVIDER, MODEL (required), TEMPERATURE, MAX_TOKENS, FALLBACK, SYSTEM_PROMPT, SYSTEM_PROMPT_FILE (optional)
    - Validate provider exists in registry; skip with warning if not
    - Validate temperature range (0.0–2.0), max_tokens range (1–1,000,000); use defaults on parse failure
    - Limit fallback chain to 5 entries; filter out unregistered providers
    - Log each discovered vendor route at INFO level
    - Call `load_vendor_routes()` from existing `load_routes()` method
    - _Requirements: 1.2, 1.3, 1.7, 1.8, 4.1, 4.2, 4.3, 4.4, 4.5, 6.2, 6.4, 6.5_

  - [ ]* 2.2 Write property tests for vendor route loading (Property 2)
    - **Property 2: Vendor Route Loading from Environment**
    - Test that a vendor route is loaded iff PROVIDER and MODEL are present and provider exists in registry
    - Test that missing PROVIDER/MODEL or unresolvable provider results in exclusion
    - **Validates: Requirements 1.2, 1.3, 1.7, 1.8**

  - [ ]* 2.3 Write property tests for generation parameter parsing (Property 13)
    - **Property 13: Generation Parameter Parsing with Range Validation**
    - Test temperature acceptance for 0.0–2.0, rejection for out-of-range/unparseable
    - Test max_tokens acceptance for 1–1,000,000, rejection for out-of-range/unparseable
    - **Validates: Requirements 4.1, 4.5**

  - [ ]* 2.4 Write property tests for fallback chain parsing (Property 14)
    - **Property 14: Fallback Chain Parsing**
    - Test that comma-separated provider IDs are parsed, unregistered providers filtered, chain capped at 5
    - **Validates: Requirements 4.2**

- [ ] 3. Implement vendor routing resolution in routing.py
  - [ ] 3.1 Extend DomainRouter.resolve() with vendor-aware resolution
    - Update `resolve()` signature to accept optional `vendor`, `platform`, and `domain` parameters
    - Extend `RouteDecision` with: route_type ("vendor"|"domain"|"default"), vendor, platform fields
    - Implement precedence: vendor route → domain route → ROUTE_DEFAULT_PROVIDER
    - When vendor present + matching config: resolve vendor route (primary → fallback → default)
    - When vendor present + no config + domain present: fall through to domain resolution
    - When vendor present + no config + no domain: resolve via ROUTE_DEFAULT_PROVIDER
    - When all vendor-chain providers unhealthy: return NO_PROVIDER_AVAILABLE (no domain fallthrough)
    - Log routing decision path at INFO: vendor-hit, vendor-fallback, domain-hit, domain-fallback, default
    - _Requirements: 1.4, 1.5, 7.1, 7.2, 7.3, 7.5, 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ]* 3.2 Write property tests for vendor-over-domain precedence (Property 3)
    - **Property 3: Vendor-Over-Domain Routing Precedence**
    - Test that vendor route wins when both vendor and domain are present with matching configs
    - Test that RouteDecision has route_type="vendor" and uses vendor route model/params
    - **Validates: Requirements 1.4, 3.6, 11.1**

  - [ ]* 3.3 Write property tests for domain-only backward compatibility (Property 4)
    - **Property 4: Domain-Only Backward Compatibility**
    - Test that domain-only requests resolve identically to pre-feature behavior
    - **Validates: Requirements 1.5, 3.4, 6.3**

  - [ ]* 3.4 Write property tests for vendor fallback resolution (Property 10)
    - **Property 10: Vendor Fallback Resolution Chain**
    - Test provider attempt order: primary → fallback chain → ROUTE_DEFAULT_PROVIDER
    - Test that first healthy is selected; all-unhealthy returns NO_PROVIDER_AVAILABLE
    - Test that original vendor route model/params are used regardless of selected provider
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.5, 11.3**

  - [ ]* 3.5 Write property tests for fallthrough when vendor config absent (Property 11)
    - **Property 11: Fallthrough When Vendor Config Absent**
    - Test that vendor present + no config + domain present → domain resolution
    - Test that vendor present + no config + no domain → ROUTE_DEFAULT_PROVIDER
    - **Validates: Requirements 11.2, 11.5**

- [ ] 4. Checkpoint - Ensure routing logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement vendor-aware prompt construction
  - [ ] 5.1 Add vendor prompt builder in server.py
    - Create `build_vendor_prompt()` function that:
      - Omits system prompt (returns None) unless vendor has SYSTEM_PROMPT override
      - Prepends `Platform: <value>` line when platform is provided
      - Omits output format directives ("Generate ONLY the configuration block...")
      - Retains device context fields (hostname, interfaces, router_id, ASN) and constraints with identical formatting
    - Integrate with existing `handle_generate_config` to branch on route_type
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 5.2 Write property tests for platform injection in vendor prompts (Property 7)
    - **Property 7: Platform Injection in Vendor Prompts**
    - Test that platform value appears as "Platform: <value>" before task description when present
    - Test that no platform line appears when absent
    - **Validates: Requirements 2.2, 5.2**

  - [ ]* 5.3 Write property tests for vendor prompt lightness (Property 8)
    - **Property 8: Vendor Prompt Lightness**
    - Test that system prompt is omitted unless SYSTEM_PROMPT override is configured
    - Test that output format directives are omitted
    - Test that SYSTEM_PROMPT override is used when configured
    - **Validates: Requirements 5.1, 5.3**

  - [ ]* 5.4 Write property tests for vendor prompt content retention (Property 9)
    - **Property 9: Vendor Prompt Content Retention**
    - Test that device context fields (hostname, interfaces, router_id, ASN) appear with same structure as domain prompts
    - Test that constraints appear without modification
    - **Validates: Requirements 5.4, 5.5**

- [ ] 6. Update MCP tool schemas and handlers in server.py
  - [ ] 6.1 Add vendor and platform to tool input schemas
    - Add optional `vendor` property (type string, description referencing supported vendors) to schemas of: ollama_generate_config, ollama_validate_design, ollama_domain_query, ollama_validate_config_against_sot
    - Add optional `platform` property (type string, maxLength 32) to same four tools
    - Remove `domain` from `required` array for the four updated tools
    - Add custom validation: at least one of vendor/domain must be provided
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 6.2 Update tool handlers to use vendor routing
    - Update `handle_generate_config`, `handle_validate_design`, `handle_domain_query`, `handle_validate_config_against_sot`
    - Extract vendor/platform/domain from args; validate with RoutingInput model
    - Call `router.resolve(vendor=..., platform=..., domain=...)` instead of `router.resolve(domain)`
    - Branch prompt construction: use `build_vendor_prompt()` for vendor-routed, existing builder for domain-routed
    - Pass route_type to metrics recording
    - Update degradation_response to include vendor field when applicable
    - _Requirements: 1.4, 1.5, 3.3, 3.4, 3.5, 3.6, 5.1_

- [ ] 7. Extend metrics tracking
  - [ ] 7.1 Update MetricsTracker for per-vendor metrics
    - Extend `record_delegation()` with optional `vendor` and `route_type` parameters
    - When route_type="vendor": increment vendor_routed_count, update per_vendor dict (call_count, running avg latency, total tokens, success rate)
    - When route_type="domain": increment domain_routed_count
    - Add `record_vendor_fallback_event(vendor, from_provider, to_provider)` method
    - Update `get_summary()` to include per-vendor breakdown and routing totals
    - Omit per-vendor section from stats output when vendor_routed_count == 0
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 7.2 Write property tests for per-vendor metrics recording (Property 12)
    - **Property 12: Per-Vendor Metrics Recording**
    - Test that per-vendor aggregates (call_count, avg latency, tokens, success rate) are correct for arbitrary event sequences
    - Test vendor_fallback_events keyed by vendor name
    - Test vendor_routed_count and domain_routed_count running totals
    - **Validates: Requirements 10.1, 10.3, 10.4**

- [ ] 8. Checkpoint - Ensure all unit and property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Update configuration and documentation
  - [ ] 9.1 Update config/openclaw.json with vendor route examples
    - Add ROUTE_VENDOR_CISCO_PROVIDER, ROUTE_VENDOR_CISCO_MODEL, ROUTE_VENDOR_ARISTA_PROVIDER, ROUTE_VENDOR_ARISTA_MODEL (etc.) entries alongside existing domain routes
    - Add comments or documentation noting vendor routes replace per-protocol routes
    - Retain existing domain routes for backward compatibility during migration
    - _Requirements: 4.3, 6.1, 6.2_

  - [ ] 9.2 Update SKILL.md with vendor routing guidance
    - Add "Vendor Routing" section with decision rule: use vendor routing when device vendor is in supported set
    - Add vendor-to-platform mapping table (cisco → ios-xe/ios-xr/nx-os, arista → eos, juniper → junos, paloalto → pan-os, f5 → big-ip)
    - Add examples deriving vendor from pyATS testbed `os` field and Nautobot device `platform` field
    - Document that distilled models don't need system prompts or format directives
    - Document fallback: use domain routing when vendor unknown/unsupported
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 9.3 Update SOUL.md with orchestrator vendor routing rules
    - Add decision rule: prefer vendor routing when device vendor is one of cisco/arista/juniper/paloalto/f5
    - Add derivation rule: check pyATS testbed `os` field first, fallback to Nautobot device `platform`
    - Add fallback rule: use domain routing when vendor absent or unsupported
    - Add platform passthrough rule: include platform value from pyATS/Nautobot when available
    - Add no-context rule: use domain routing derived from task type when no device context available
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 10. Write integration tests
  - [ ]* 10.1 Write integration tests for startup and end-to-end flow
    - Test full startup with mixed vendor + domain configuration
    - Test startup logging output (vendor route count, domain route count)
    - Test end-to-end request flow with mock providers (vendor route, domain route, fallthrough)
    - Test backward compatibility: domain-only requests produce identical results to pre-feature
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 11.4_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis (min 100 iterations per property)
- Unit tests validate specific examples and edge cases
- The implementation language is Python, matching the existing codebase
- All property tests should be placed in the test files specified in the design: test_vendor_routing.py, test_vendor_validation.py, test_vendor_prompts.py, test_vendor_metrics.py

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.4", "3.5", "5.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "5.4", "6.1"] },
    { "id": 5, "tasks": ["6.2", "7.1"] },
    { "id": 6, "tasks": ["7.2", "9.1", "9.2", "9.3"] },
    { "id": 7, "tasks": ["10.1"] }
  ]
}
```
