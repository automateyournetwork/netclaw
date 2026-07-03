# Implementation Plan: pfSense MCP Server

## Overview

Implement a Python-based MCP server that exposes pfSense firewall management tools to the NetClaw agent over stdio transport. The server wraps the pfSense REST API v2 (pfrest package) using the FastMCP framework, organized into domain-specific tool modules with a shared HTTP client and consistent response formatting.

## Tasks

- [ ] 1. Set up project structure, dependencies, and core framework
  - [ ] 1.1 Create project directory structure and install dependencies
    - Create project at `mcp-servers/pfsense-mcp/`
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/` package with `__init__.py`
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/` subpackage with `__init__.py`
    - Create `mcp-servers/pfsense-mcp/tests/unit/`, `tests/property/`, `tests/integration/` directories
    - Create `mcp-servers/pfsense-mcp/pyproject.toml` with dependencies: `mcp>=1.4.0`, `requests>=2.31.0`, `python-dotenv>=1.0.0`, `hypothesis>=6.100.0`, `pytest>=8.0.0`, `pytest-mock>=3.12.0`
    - _Requirements: 1.1_

  - [ ] 1.2 Implement environment variable loading and validation
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/config.py` with configuration loading logic
    - Load `PFSENSE_HOST`, `PFSENSE_API_KEY`, `PFSENSE_USERNAME`, `PFSENSE_PASSWORD`, `PFSENSE_VERIFY_TLS`, `PFSENSE_TIMEOUT`
    - Validate that either `PFSENSE_API_KEY` or both `PFSENSE_USERNAME` and `PFSENSE_PASSWORD` are provided
    - Fail with an error identifying each missing variable by name if required vars are absent
    - Support multi-instance configuration via `PFSENSE_<ALIAS>_HOST` / `PFSENSE_<ALIAS>_API_KEY` pattern
    - _Requirements: 1.1, 1.3, 1.6_

  - [ ]* 1.3 Write property test for missing environment variable identification
    - **Property 3: Missing environment variable identification**
    - **Validates: Requirements 1.6**

  - [ ]* 1.4 Write property test for multi-instance alias resolution
    - **Property 2: Multi-instance alias resolution**
    - **Validates: Requirements 1.3**

  - [ ] 1.5 Implement PfSenseClient HTTP wrapper
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/client.py` with the `PfSenseClient` class
    - Implement `get()`, `post()`, `put()`, `patch()`, `delete()`, `apply()` methods
    - Support API Key auth (`X-API-Key` header) and Basic Auth
    - Handle TLS verification toggle via `PFSENSE_VERIFY_TLS`
    - Implement 30-second default timeout (configurable via `PFSENSE_TIMEOUT`)
    - Map HTTP errors (401/403, 404, 400, 409, 502/503) to structured error categories
    - Sanitize credentials from all error messages
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [ ]* 1.6 Write property test for authentication error credential exclusion
    - **Property 1: Authentication error credential exclusion**
    - **Validates: Requirements 1.2**

  - [ ] 1.7 Implement response formatter module
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/formatter.py`
    - Implement `format_success()`, `format_error()`, `format_write_success()` functions
    - Ensure all JSON responses use snake_case field naming
    - Include `tool_name`, `error`, `hint` fields in error responses
    - Include `success: true` and `resource` state in write success responses
    - Include `resource_type`, `identifier`, `valid_identifiers` in resource-not-found errors
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [ ]* 1.8 Write property tests for response formatting
    - **Property 12: snake_case response formatting**
    - **Property 13: Write success response structure**
    - **Property 14: API error response structure**
    - **Validates: Requirements 15.1, 15.3, 15.4**

  - [ ] 1.9 Create FastMCP server entry point
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/server.py` with `FastMCP` initialization
    - Configure stdio transport
    - Wire configuration loading and client initialization
    - Register tool modules
    - _Requirements: 1.1_

- [ ] 2. Checkpoint - Ensure core framework tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Implement firewall rule management tools
  - [ ] 3.1 Implement firewall rule tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/firewall.py`
    - Implement `list_firewall_rules` — return all rules for a specified interface with action, protocol, source, destination, port, description, position index
    - Implement `add_firewall_rule` — create rule with interface, action, protocol, source, destination; place at end or specified position; call apply
    - Implement `modify_firewall_rule` — update rule by interface and position index; call apply
    - Implement `delete_firewall_rule` — remove rule by interface and position index; call apply
    - Validate parameters: reject unrecognized protocol, malformed IP/subnet, port outside 1-65535
    - Return error for non-existent interfaces
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 3.2 Write property test for apply-after-write pattern (firewall)
    - **Property 5: Apply-after-write for stateful subsystems**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5**

  - [ ]* 3.3 Write property test for invalid resource identifier error format
    - **Property 6: Invalid resource identifier error format**
    - **Validates: Requirements 2.6, 3.6, 4.6, 10.6, 14.3, 15.2**

  - [ ]* 3.4 Write property test for parameter validation error format
    - **Property 7: Parameter validation error format**
    - **Validates: Requirements 2.7, 3.5, 4.7, 15.5**

  - [ ]* 3.5 Write unit tests for firewall rule tools
    - Test list rules returns complete fields
    - Test add rule with all fields, add at position, add at end
    - Test modify single field
    - Test delete by position
    - Test invalid protocol/IP/port validation errors
    - Test non-existent interface error
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 2.7_

- [ ] 4. Implement NAT rule management tools
  - [ ] 4.1 Implement NAT rule tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/nat.py`
    - Implement `list_nat_rules` — return all NAT rules with type, interface, source, destination, redirect target, protocol, enabled status
    - Implement `add_nat_rule` — create NAT rule with type, interface, protocol, source, destination, redirect target; call apply
    - Implement `delete_nat_rule` — remove NAT rule by unique ID; call apply
    - Validate parameters and return errors for invalid/missing values
    - Return error for non-existent interfaces
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 4.2 Write unit tests for NAT rule tools
    - Test list NAT rules returns complete fields for each type
    - Test add port forward rule
    - Test delete rule by ID
    - Test invalid parameter errors
    - Test non-existent interface error
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6_

- [ ] 5. Implement interface configuration tools
  - [ ] 5.1 Implement interface tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/interfaces.py`
    - Implement `list_interfaces` — return all interfaces with name, IP, subnet, status, MAC, media type
    - Implement `get_interface_status` — return statistics (bytes/packets/errors in/out, link state)
    - Implement `update_interface` — modify interface parameters (IP, subnet, description, enable/disable); call apply
    - Implement `create_vlan` — create VLAN with tag (1-4094) on parent interface
    - Reject changes that would remove management IP
    - Return error for non-existent interfaces and invalid VLAN tags
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [ ]* 5.2 Write property test for list response field completeness
    - **Property 4: List response field completeness**
    - **Validates: Requirements 2.1, 3.1, 4.1, 5.3, 6.2, 7.2, 9.1**

  - [ ]* 5.3 Write unit tests for interface tools
    - Test list interfaces returns all fields
    - Test interface status statistics
    - Test update interface with apply
    - Test create VLAN valid tag
    - Test reject management IP removal
    - Test invalid interface error
    - Test invalid VLAN tag error
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [ ] 6. Checkpoint - Ensure firewall, NAT, and interface tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement DNS configuration tools
  - [ ] 7.1 Implement DNS tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/dns.py`
    - Implement `get_dns_config` — return DNS resolver settings (listening interfaces, forwarding mode, DNSSEC, custom options)
    - Implement `modify_dns_resolver` — update resolver config, restart service, return updated settings
    - Implement `list_dns_host_overrides` — return all static host entries with hostname, domain, IP, description
    - Implement `add_dns_host_override` — create host entry; detect duplicate hostname+domain; apply config
    - Implement `delete_dns_host_override` — remove entry by hostname+domain; apply config
    - Implement `list_dns_domain_overrides` — return domain overrides with domain, server address, server port
    - Return error if DNS resolver service fails to restart
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ]* 7.2 Write unit tests for DNS tools
    - Test get DNS config returns all fields
    - Test modify resolver restarts service
    - Test add host override success and duplicate detection
    - Test delete host override by hostname+domain
    - Test list domain overrides
    - Test service restart failure error
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [ ] 8. Implement DHCP server management tools
  - [ ] 8.1 Implement DHCP tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/dhcp.py`
    - Implement `get_dhcp_config` — return DHCP settings for interface (status, range, DNS, gateway, domain, lease time)
    - Implement `list_dhcp_leases` — return active leases with IP, MAC, hostname, start/end times
    - Implement `list_dhcp_static_mappings` — return static reservations with MAC, IP, hostname, description
    - Implement `add_dhcp_static_mapping` — create reservation; detect MAC/IP conflicts; apply config
    - Return error if interface does not have DHCP enabled
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 8.2 Write unit tests for DHCP tools
    - Test get DHCP config returns all fields
    - Test list leases format
    - Test list static mappings
    - Test add static mapping success and conflict detection
    - Test DHCP not active on interface error
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 9. Implement system log monitoring tools
  - [ ] 9.1 Implement log tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/logs.py`
    - Implement `get_system_logs` — return log entries filtered by type (system, firewall, dhcp, dns, openvpn, ipsec, gateway)
    - Implement `get_filter_logs` — return parsed filter log entries with timestamp, action, interface, protocol, source/dest IP/port, direction
    - Support line count parameter (1-10000, default 50)
    - Support text search filter (case-insensitive substring match, 1-256 chars)
    - Support filter log filtering by source IP, destination IP, interface, action, protocol
    - Return error for invalid log types
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 9.2 Write property test for log filtering correctness
    - **Property 8: Log filtering correctness**
    - **Validates: Requirements 7.4, 7.5**

  - [ ]* 9.3 Write property test for result set bounded size and ordering
    - **Property 9: Result set bounded size and ordering**
    - **Validates: Requirements 7.3, 8.6, 11.2, 14.2**

  - [ ]* 9.4 Write unit tests for log tools
    - Test get system logs by type
    - Test get filter logs returns all fields
    - Test line count limiting
    - Test text search filter case-insensitive
    - Test filter by source IP, dest IP, interface, action, protocol
    - Test invalid log type error
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ] 10. Implement system diagnostics tools
  - [ ] 10.1 Implement diagnostics tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/diagnostics.py`
    - Implement `ping` — execute ping with default 4 packets, 10s timeout; return sent/received/loss/RTT stats
    - Implement `traceroute` — execute traceroute with max 30 hops, 5s per-hop timeout; return hop path
    - Implement `dns_lookup` — perform DNS resolution; return name, type, addresses, TTL, server
    - Implement `get_arp_table` — return ARP entries with IP, MAC, interface, expiration
    - Implement `get_routing_table` — return routes with destination, gateway, interface, flags
    - Implement `get_connection_states` — return at most 1000 state entries with optional filtering
    - Return error for unreachable targets or unresolvable hostnames
    - Return timeout error when operations exceed their timeout
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [ ]* 10.2 Write unit tests for diagnostics tools
    - Test ping success with all stats
    - Test traceroute hop formatting
    - Test DNS lookup response fields
    - Test ARP table parsing
    - Test routing table fields
    - Test connection states filtering and max 1000 limit
    - Test unreachable target error
    - Test timeout error
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [ ] 11. Checkpoint - Ensure DNS, DHCP, logs, and diagnostics tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement gateway monitoring tools
  - [ ] 12.1 Implement gateway tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/gateways.py`
    - Implement `get_gateways` — return gateways with name, IP, interface, monitor IP, RTT, packet loss, status (online/degraded/offline/unknown)
    - Classify gateway status: degraded if packet loss exceeds threshold, never online with high loss
    - Implement `get_gateway_groups` — return groups with members, priority tiers, trigger levels
    - Return error if gateway data unavailable
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 12.2 Write property test for gateway status classification
    - **Property 10: Gateway status classification**
    - **Validates: Requirements 9.2, 9.4**

  - [ ]* 12.3 Write unit tests for gateway tools
    - Test get gateways returns all fields
    - Test status classification for various metric combinations
    - Test gateway groups format
    - Test unavailable gateway data error
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 13. Implement service management tools
  - [ ] 13.1 Implement service tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/services.py`
    - Implement `list_services` — return all services with name, description, status (running/stopped)
    - Implement `restart_service` — restart service, return new status
    - Implement `stop_service` — stop service, return status
    - Implement `start_service` — start service, return status
    - Include warning for critical services (sshd, webgui) on stop/restart
    - Return error for non-existent service names
    - Handle idempotent operations (start already-running, stop already-stopped)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ]* 13.2 Write property test for critical service operation warning
    - **Property 11: Critical service operation warning**
    - **Validates: Requirements 10.5**

  - [ ]* 13.3 Write unit tests for service tools
    - Test list services returns all fields
    - Test restart service
    - Test stop/start service
    - Test critical service warning for sshd and webgui
    - Test non-existent service error
    - Test idempotent operations
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [ ] 14. Implement configuration backup and restore tools
  - [ ] 14.1 Implement config tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/config.py`
    - Implement `backup_config` — return full XML configuration backup
    - Implement `list_config_history` — return at most 100 revisions ordered newest-first with timestamp, description, user
    - Implement `restore_config` — create pre-restore backup, restore to specified revision, indicate if reboot initiated, include pre-restore backup revision ID
    - Return error for non-existent revision
    - Return error on restore failure with pre-restore backup revision ID for recovery
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 14.2 Write unit tests for config tools
    - Test backup returns XML content
    - Test list history respects max 100 and newest-first ordering
    - Test restore creates pre-backup and includes revision ID
    - Test non-existent revision error
    - Test restore failure includes pre-backup revision for recovery
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ] 15. Implement VPN status monitoring tools
  - [ ] 15.1 Implement VPN tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/vpn.py`
    - Implement `get_ipsec_status` — return IPsec tunnels with phase 1/2 status, remote gateway, subnets, bytes transferred
    - Implement `get_openvpn_status` — return OpenVPN instances with status, connected clients (name, connected-since, virtual addresses), bytes transferred
    - Implement `disconnect_openvpn_client` — terminate client connection, return confirmation
    - Return error for non-existent client or server instance
    - Return error if IPsec/OpenVPN service not running
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 15.2 Write unit tests for VPN tools
    - Test IPsec status parsing
    - Test OpenVPN status with connected clients
    - Test disconnect client success
    - Test non-existent client/server error
    - Test service not running error
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 16. Implement system information and traffic monitoring tools
  - [ ] 16.1 Implement system info tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/system.py`
    - Implement `get_system_info` — return version, hostname, uptime, CPU %, memory bytes, disk %, CPU temperature; omit unavailable metrics with reasons
    - Implement `get_installed_packages` — return packages with name and version
    - Implement `get_available_updates` — return system update availability and package updates with current/available versions
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ] 16.2 Implement traffic monitoring tools
    - Create `mcp-servers/pfsense-mcp/src/pfsense_mcp/tools/traffic.py`
    - Implement `get_interface_traffic` — return current throughput (bytes/sec inbound/outbound, packets/sec) for specified interface
    - Implement `get_top_talkers` — return at most 100 connections sorted by bandwidth descending with source, dest, protocol, rate
    - Return error for non-existent interface
    - Return empty list with zero count when no active connections
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ]* 16.3 Write unit tests for system info and traffic tools
    - Test system info with all fields
    - Test system info with unavailable metrics (omitted with reasons)
    - Test installed packages listing
    - Test available updates format
    - Test interface traffic response
    - Test top talkers sorting and max 100
    - Test non-existent interface error
    - Test empty connections returns empty list
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 14.1, 14.2, 14.3, 14.4_

- [ ] 17. Checkpoint - Ensure all tool tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Wire all tools together and finalize server
  - [ ] 18.1 Register all tool modules in the FastMCP server
    - Import and register all tool modules in `server.py`
    - Ensure all tools receive the shared `PfSenseClient` instance
    - Implement multi-instance target resolution (optional `target` parameter per tool)
    - Verify server starts with valid configuration and fails gracefully with missing config
    - _Requirements: 1.1, 1.3_

  - [ ]* 18.2 Write integration tests for end-to-end tool registration
    - Test that all tools are registered and callable
    - Test multi-instance target parameter routing
    - Test server startup with valid and invalid configurations
    - _Requirements: 1.1, 1.3, 1.6_

- [ ] 19. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation uses Python with FastMCP, requests, and Hypothesis as specified in the design
- All tools share a common PfSenseClient instance and response formatter for consistency

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.7"] },
    { "id": 2, "tasks": ["1.3", "1.4", "1.5", "1.8"] },
    { "id": 3, "tasks": ["1.6", "1.9"] },
    { "id": 4, "tasks": ["3.1", "4.1", "5.1"] },
    { "id": 5, "tasks": ["3.2", "3.3", "3.4", "3.5", "4.2", "5.2", "5.3"] },
    { "id": 6, "tasks": ["7.1", "8.1", "9.1", "10.1"] },
    { "id": 7, "tasks": ["7.2", "8.2", "9.2", "9.3", "9.4", "10.2"] },
    { "id": 8, "tasks": ["12.1", "13.1", "14.1", "15.1"] },
    { "id": 9, "tasks": ["12.2", "12.3", "13.2", "13.3", "14.2", "15.2"] },
    { "id": 10, "tasks": ["16.1", "16.2"] },
    { "id": 11, "tasks": ["16.3"] },
    { "id": 12, "tasks": ["18.1"] },
    { "id": 13, "tasks": ["18.2"] }
  ]
}
```
