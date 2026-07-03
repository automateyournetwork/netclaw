# Requirements Document

## Introduction

This document defines the requirements for a pfSense MCP (Model Context Protocol) server that enables NetClaw to manage pfSense firewalls. The server provides tools for diagnosing issues, monitoring logs, updating firewall rules, managing interface configurations, DNS settings, and other system configurations via the pfSense XML-RPC or REST API. This MCP server follows the same stdio transport pattern used by other NetClaw MCP integrations.

## Glossary

- **MCP_Server**: The Model Context Protocol server process that exposes pfSense management tools to the NetClaw agent via stdio transport
- **pfSense_API**: The pfSense interface used for programmatic access, either the built-in XML-RPC interface or the community pfSense REST API package (pfrest)
- **Firewall_Rule**: A packet filtering rule configured on pfSense that permits or denies traffic based on source, destination, port, and protocol criteria
- **NAT_Rule**: A Network Address Translation rule that maps traffic between internal and external addresses
- **Interface**: A network interface configured on the pfSense appliance (WAN, LAN, OPTx, VLAN, bridge, etc.)
- **DNS_Resolver**: The Unbound DNS resolver service running on pfSense that handles DNS queries for the network
- **DNS_Forwarder**: The dnsmasq-based DNS forwarding service on pfSense used as an alternative to the DNS Resolver
- **Gateway**: A next-hop router address used by pfSense for routing traffic to external networks
- **DHCP_Server**: The ISC DHCP server on pfSense that assigns IP addresses to clients on configured interfaces
- **System_Log**: The syslog entries stored on pfSense covering firewall, system, DNS, DHCP, and other service activity
- **Filter_Log**: The parsed firewall filter log entries showing pass/block actions with full packet metadata
- **Config_Backup**: An XML export of the complete pfSense configuration that can be used for restore or offline analysis
- **Connection_State**: An entry in the pfSense state table representing an active or recently closed network connection
- **Service**: A daemon process managed by pfSense (e.g., unbound, dhcpd, ntpd, openvpn, ipsec)

## Requirements

### Requirement 1: Authentication and Connection Management

**User Story:** As a network engineer, I want the MCP server to securely connect to pfSense appliances, so that I can manage firewalls without exposing credentials.

#### Acceptance Criteria

1. WHEN the MCP_Server starts, THE MCP_Server SHALL authenticate to the pfSense_API using credentials provided via environment variables (host URL, username, and password or API key)
2. IF invalid credentials are provided, THEN THE MCP_Server SHALL return an authentication error that includes the target hostname and the failure reason from the pfSense_API without including any credential values in the error output
3. THE MCP_Server SHALL support connecting to multiple pfSense instances identified by a hostname or alias parameter provided per request
4. IF a connection to the pfSense_API does not receive a response within 30 seconds, THEN THE MCP_Server SHALL return an error indicating the target host and the elapsed timeout duration
5. THE MCP_Server SHALL validate TLS certificates by default and support an environment variable to allow self-signed certificates
6. IF one or more required environment variables (host URL, username, password or API key) are missing or empty at startup, THEN THE MCP_Server SHALL fail to start and return an error message identifying each missing variable by name

### Requirement 2: Firewall Rule Management

**User Story:** As a network engineer, I want to view and modify firewall rules on pfSense, so that I can control traffic flow through the network.

#### Acceptance Criteria

1. WHEN a list firewall rules request is received, THE MCP_Server SHALL return all Firewall_Rule entries for a specified Interface including rule action, protocol, source, destination, port, description, and rule position index
2. WHEN an add firewall rule request is received with at minimum the target Interface, action (pass, block, or reject), protocol, source, and destination, THE MCP_Server SHALL create a new Firewall_Rule and apply the configuration, placing the rule at the end of the Interface ruleset unless an explicit position index is provided
3. WHEN a modify firewall rule request is received identifying a rule by Interface and position index, THE MCP_Server SHALL update the specified Firewall_Rule fields and apply the configuration
4. WHEN a delete firewall rule request is received identifying a rule by Interface and position index, THE MCP_Server SHALL remove the specified Firewall_Rule and apply the configuration
5. WHEN a firewall rule change is applied, THE MCP_Server SHALL reload the packet filter to activate the new ruleset
6. IF a firewall rule request references a non-existent Interface, THEN THE MCP_Server SHALL return an error identifying the invalid interface name
7. IF an add or modify firewall rule request contains an invalid parameter value (unrecognized protocol, malformed IP address or subnet, or port number outside the range 1–65535), THEN THE MCP_Server SHALL reject the request and return an error identifying the invalid field and the accepted values

### Requirement 3: NAT Rule Management

**User Story:** As a network engineer, I want to manage NAT rules on pfSense, so that I can control address translation for inbound and outbound traffic.

#### Acceptance Criteria

1. WHEN a list NAT rules request is received, THE MCP_Server SHALL return all NAT_Rule entries including type (port forward, 1:1, outbound), interface, source, destination, redirect target, protocol, and enabled/disabled status
2. WHEN an add NAT rule request is received with NAT type, interface, protocol, source, destination, and redirect target, THE MCP_Server SHALL create a new NAT_Rule with the specified parameters and apply the configuration
3. WHEN a delete NAT rule request is received identifying a NAT_Rule by its unique rule identifier, THE MCP_Server SHALL remove the specified NAT_Rule and apply the configuration
4. WHEN a NAT rule change is applied, THE MCP_Server SHALL reload the NAT engine to activate the new configuration
5. IF a NAT rule request specifies an invalid or missing required parameter, THEN THE MCP_Server SHALL return an error identifying the invalid parameter and the accepted values
6. IF a NAT rule request references a non-existent Interface, THEN THE MCP_Server SHALL return an error identifying the invalid interface name

### Requirement 4: Interface Configuration Management

**User Story:** As a network engineer, I want to view and configure network interfaces on pfSense, so that I can manage network connectivity and addressing.

#### Acceptance Criteria

1. WHEN a list interfaces request is received, THE MCP_Server SHALL return all configured Interface entries including name, IP address, subnet mask, status (up, down, or disabled), MAC address, and media type
2. WHEN an interface status request is received, THE MCP_Server SHALL return current statistics for the specified Interface including bytes in/out, packets in/out, errors in/out, and link state (up or down)
3. WHEN an interface configuration update is received, THE MCP_Server SHALL modify the specified Interface parameters (IP address, subnet, description, enable/disable) and apply the configuration
4. WHEN a VLAN creation request is received with a VLAN tag in the range 1 to 4094, THE MCP_Server SHALL create a VLAN interface on the specified parent Interface with the given VLAN tag
5. IF an interface configuration change would remove the management IP address, THEN THE MCP_Server SHALL reject the change and return a warning indicating potential loss of connectivity
6. IF an interface request references a non-existent Interface, THEN THE MCP_Server SHALL return an error identifying the invalid interface name
7. IF a VLAN creation request specifies a VLAN tag outside the range 1 to 4094 or references a parent Interface that does not exist, THEN THE MCP_Server SHALL return an error identifying the invalid parameter

### Requirement 5: DNS Configuration Management

**User Story:** As a network engineer, I want to manage DNS settings on pfSense, so that I can control name resolution for the network.

#### Acceptance Criteria

1. WHEN a get DNS configuration request is received, THE MCP_Server SHALL return the current DNS_Resolver settings including listening interfaces, forwarding mode, DNSSEC status, and custom options
2. WHEN a modify DNS resolver request is received, THE MCP_Server SHALL update the DNS_Resolver configuration, restart the DNS_Resolver service, and return the updated settings reflecting the applied changes
3. WHEN a list DNS host overrides request is received, THE MCP_Server SHALL return all static host entries including hostname, domain, IP address, and description
4. WHEN an add DNS host override request is received with a hostname, domain, and IP address, THE MCP_Server SHALL create a new static host entry in the DNS_Resolver and apply the configuration
5. IF an add DNS host override request specifies a hostname and domain combination that already exists, THEN THE MCP_Server SHALL return an error indicating the duplicate entry and not modify the configuration
6. WHEN a delete DNS host override request is received identifying the entry by hostname and domain, THE MCP_Server SHALL remove the matching static host entry and apply the configuration
7. WHEN a list DNS domain overrides request is received, THE MCP_Server SHALL return all domain override entries including domain name, forwarding server address, and forwarding server port
8. IF the DNS_Resolver service fails to restart after a configuration change, THEN THE MCP_Server SHALL return an error indicating the service restart failure and the configuration change that triggered it

### Requirement 6: DHCP Server Management

**User Story:** As a network engineer, I want to manage DHCP settings on pfSense, so that I can control IP address assignment on the network.

#### Acceptance Criteria

1. WHEN a get DHCP configuration request is received, THE MCP_Server SHALL return the DHCP_Server settings for the specified Interface including enable/disable status, range start, range end, DNS servers, gateway, domain name, and lease time in seconds
2. WHEN a list DHCP leases request is received, THE MCP_Server SHALL return all active leases including IP address, MAC address, hostname, lease start time, and lease end time
3. WHEN a list DHCP static mappings request is received, THE MCP_Server SHALL return all static DHCP reservations for the specified Interface including MAC address, IP address, hostname, and description
4. WHEN an add DHCP static mapping request is received, THE MCP_Server SHALL create a new static reservation with the given MAC address, IP address, and hostname, and apply the configuration to the DHCP_Server
5. IF an add DHCP static mapping request specifies a MAC address or IP address that already exists in the static mappings for that Interface, THEN THE MCP_Server SHALL return an error indicating the conflicting entry
6. IF a DHCP request references an Interface that does not have the DHCP_Server enabled, THEN THE MCP_Server SHALL return an error indicating that DHCP is not active on the specified Interface

### Requirement 7: System Log Monitoring

**User Story:** As a network engineer, I want to monitor pfSense system logs, so that I can diagnose issues and track network events.

#### Acceptance Criteria

1. WHEN a get system logs request is received, THE MCP_Server SHALL return System_Log entries filtered by log type (system, firewall, dhcp, dns, openvpn, ipsec, gateway)
2. WHEN a get filter logs request is received, THE MCP_Server SHALL return parsed Filter_Log entries including timestamp, action (pass/block), interface, protocol, source IP, source port, destination IP, destination port, and direction
3. WHEN a log query includes a line count parameter, THE MCP_Server SHALL return at most the specified number of most recent log entries, where the line count parameter accepts a value between 1 and 10,000 and defaults to 50 when not specified
4. WHEN a log query includes a search filter, THE MCP_Server SHALL return only log entries containing the filter text as a case-insensitive substring match, where the filter text is between 1 and 256 characters in length
5. THE MCP_Server SHALL support filtering Filter_Log entries by source IP, destination IP, interface, action, or protocol
6. IF a get system logs request specifies a log type not in the supported set (system, firewall, dhcp, dns, openvpn, ipsec, gateway), THEN THE MCP_Server SHALL return an error indicating the invalid log type and listing the supported log types

### Requirement 8: System Diagnostics

**User Story:** As a network engineer, I want to run diagnostic commands on pfSense, so that I can troubleshoot connectivity and performance issues.

#### Acceptance Criteria

1. WHEN a ping request is received, THE MCP_Server SHALL execute a ping from the pfSense appliance to the specified target using a default of 4 packets with a 10-second timeout and return the results including packets sent, packets received, packet loss percentage, and round-trip time minimum, average, and maximum in milliseconds
2. WHEN a traceroute request is received, THE MCP_Server SHALL execute a traceroute from the pfSense appliance to the specified target with a maximum of 30 hops and a 5-second per-hop timeout and return the hop-by-hop path including hop number, IP address, hostname (if resolvable), and round-trip time per hop
3. WHEN a DNS lookup request is received, THE MCP_Server SHALL perform a DNS resolution from the pfSense appliance and return the query results including queried name, record type, resolved addresses, TTL, and the responding DNS server
4. WHEN an ARP table request is received, THE MCP_Server SHALL return the current ARP table entries including IP address, MAC address, interface, and expiration
5. WHEN a routing table request is received, THE MCP_Server SHALL return the active routing table including destination network, gateway, interface, and flags
6. WHEN a connection states request is received, THE MCP_Server SHALL return at most 1000 Connection_State table entries with optional filtering by source, destination, or protocol
7. IF a diagnostic command target is unreachable or the hostname cannot be resolved, THEN THE MCP_Server SHALL return an error indicating the target specified and the failure reason
8. IF a diagnostic command exceeds its timeout, THEN THE MCP_Server SHALL terminate the operation and return a timeout error indicating the target and the elapsed duration

### Requirement 9: Gateway Monitoring

**User Story:** As a network engineer, I want to monitor gateway status on pfSense, so that I can detect WAN connectivity issues and failover events.

#### Acceptance Criteria

1. WHEN a get gateways request is received, THE MCP_Server SHALL return all configured Gateway entries including name, gateway IP address, interface, monitor IP, RTT in milliseconds, packet loss as a percentage from 0.0 to 100.0, and status
2. WHEN a get gateways request is received, THE MCP_Server SHALL report each Gateway status as one of: online, degraded, offline, or unknown
3. WHEN a get gateway groups request is received, THE MCP_Server SHALL return all gateway groups with their member gateways, numeric priority tiers, and trigger level for each member (member down, packet loss, high latency)
4. IF a gateway shows packet loss exceeding the pfSense-configured threshold for that gateway, THEN THE MCP_Server SHALL report that gateway status as degraded in the response
5. IF the pfSense_API returns no gateway data or the gateway monitoring subsystem is unavailable, THEN THE MCP_Server SHALL return an error indicating that gateway status could not be retrieved

### Requirement 10: Service Management

**User Story:** As a network engineer, I want to manage services on pfSense, so that I can start, stop, and monitor service health.

#### Acceptance Criteria

1. WHEN a list services request is received, THE MCP_Server SHALL return all Service entries including name, description, and running status (running or stopped)
2. WHEN a restart service request is received, THE MCP_Server SHALL restart the specified Service and return the new running status
3. WHEN a stop service request is received, THE MCP_Server SHALL stop the specified Service and return the resulting running status
4. WHEN a start service request is received, THE MCP_Server SHALL start the specified Service and return the new running status
5. IF a stop or restart request targets a critical service (sshd, webgui), THEN THE MCP_Server SHALL include a warning in the response indicating potential loss of management access and proceed with the operation
6. IF a start, stop, or restart request references a Service name that does not exist on the pfSense appliance, THEN THE MCP_Server SHALL return an error identifying the unrecognized service name
7. IF a start request targets a Service that is already running, or a stop request targets a Service that is already stopped, THEN THE MCP_Server SHALL return the current running status and indicate that no action was taken

### Requirement 11: Configuration Backup and Restore

**User Story:** As a network engineer, I want to back up and restore pfSense configurations, so that I can recover from misconfigurations and maintain change history.

#### Acceptance Criteria

1. WHEN a backup configuration request is received, THE MCP_Server SHALL return the full Config_Backup XML content of the current pfSense configuration
2. WHEN a list config history request is received, THE MCP_Server SHALL return at most 100 configuration revision history entries including timestamp, description, and user who made the change, ordered from most recent to oldest
3. WHEN a restore configuration request is received with a specific revision, THE MCP_Server SHALL restore the pfSense configuration to that revision, reboot the appliance if the restored configuration changes system-level settings (e.g., interfaces, routing, kernel parameters), and return a response indicating whether a reboot was initiated
4. IF a restore configuration request is received, THEN THE MCP_Server SHALL create a backup of the current configuration before applying the restore and include the backup revision identifier in the response
5. IF a restore configuration request specifies a revision that does not exist in the configuration history, THEN THE MCP_Server SHALL return an error identifying the invalid revision
6. IF a restore operation fails after the pre-restore backup is created, THEN THE MCP_Server SHALL return an error indicating the failure reason and the revision identifier of the pre-restore backup so the configuration can be manually recovered

### Requirement 12: VPN Status Monitoring

**User Story:** As a network engineer, I want to monitor VPN tunnel status on pfSense, so that I can verify site-to-site and remote access connectivity.

#### Acceptance Criteria

1. WHEN a get IPsec status request is received, THE MCP_Server SHALL return all IPsec tunnel entries including phase 1 status (established, connecting, or disconnected), phase 2 status (installed or inactive), remote gateway, local/remote subnets, and bytes transferred
2. WHEN a get OpenVPN status request is received, THE MCP_Server SHALL return all OpenVPN server and client instances including connection status (up, down, or reconnecting), connected clients with their common name and connected-since timestamp, virtual addresses, and bytes transferred
3. WHEN a disconnect OpenVPN client request is received, THE MCP_Server SHALL terminate the specified client connection on the specified OpenVPN server instance and return confirmation including the client identifier and server instance name
4. IF a disconnect OpenVPN client request references a non-existent client or a non-existent OpenVPN server instance, THEN THE MCP_Server SHALL return an error identifying the invalid client or server instance name
5. IF a VPN status request is received and the corresponding service (ipsec or openvpn) is not running, THEN THE MCP_Server SHALL return an error indicating the service is not active on the target pfSense appliance

### Requirement 13: System Information

**User Story:** As a network engineer, I want to retrieve pfSense system information, so that I can assess appliance health and capacity.

#### Acceptance Criteria

1. WHEN a get system info request is received, THE MCP_Server SHALL return system details comprising pfSense version, hostname, uptime in seconds, CPU usage as a percentage (0-100), memory usage as bytes used and bytes total, disk usage as a percentage (0-100), and CPU temperature in degrees Celsius
2. IF a system metric is unavailable (e.g., CPU temperature on a virtual appliance), THEN THE MCP_Server SHALL omit that field from the response and include a list of unavailable metrics with a reason for each omission
3. WHEN a get installed packages request is received, THE MCP_Server SHALL return the list of installed pfSense packages with each entry including the package name and installed version string
4. WHEN a get available updates request is received, THE MCP_Server SHALL return a response indicating whether a pfSense system update is available (with the new version string if so), and a list of packages that have updates available (each with current version and available version)

### Requirement 14: Traffic Monitoring

**User Story:** As a network engineer, I want to view real-time traffic information on pfSense, so that I can identify bandwidth consumers and unusual traffic patterns.

#### Acceptance Criteria

1. WHEN a get interface traffic request is received, THE MCP_Server SHALL return current throughput (bytes per second) for the specified Interface in both inbound and outbound directions, including packets per second and the interface name
2. WHEN a get top talkers request is received, THE MCP_Server SHALL return at most 100 active connections from the Connection_State table sorted by bandwidth consumption in descending order, including source IP, destination IP, protocol, and rate in bytes per second
3. IF a get interface traffic request specifies an Interface that does not exist, THEN THE MCP_Server SHALL return an error identifying the invalid interface name
4. IF a get top talkers request is received and no active connections exist, THEN THE MCP_Server SHALL return an empty list with a total connection count of zero

### Requirement 15: Error Handling and Response Format

**User Story:** As a network engineer, I want consistent error reporting from the MCP server, so that I can quickly understand failures and take corrective action.

#### Acceptance Criteria

1. IF the pfSense_API returns an error response, THEN THE MCP_Server SHALL return a structured error containing the following fields: the tool name invoked, the error message returned by pfSense, and a human-readable remediation hint describing a corrective action the engineer can attempt
2. IF a request references a resource that does not exist (Interface, Firewall_Rule, NAT_Rule, Service, Gateway, or DNS host override), THEN THE MCP_Server SHALL return an error containing the resource type, the identifier that was not found, and a list of valid identifiers of that resource type when fewer than 50 exist
3. THE MCP_Server SHALL format all successful responses as JSON objects using snake_case field naming consistently across all tools
4. WHEN a write operation succeeds, THE MCP_Server SHALL include a boolean success field set to true and the resulting state of the modified resource in the response
5. IF a request contains a missing required parameter or a parameter value that fails type or format validation, THEN THE MCP_Server SHALL return an error identifying the parameter name, the expected type or format, and the value that was received
