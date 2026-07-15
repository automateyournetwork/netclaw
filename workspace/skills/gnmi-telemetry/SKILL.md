---
name: gnmi-telemetry
description: "gNMI streaming telemetry operations for multi-vendor network devices. Query device state via structured YANG model paths, subscribe to real-time telemetry streams, apply ITSM-gated configuration changes, browse YANG capabilities, and compare gNMI data against CLI output."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# gnmi-telemetry

gNMI streaming telemetry operations for multi-vendor network devices. Query device state via structured YANG model paths, subscribe to real-time telemetry streams, apply ITSM-gated configuration changes, browse YANG capabilities, and compare gNMI data against CLI output.

## MCP Server

`gnmi-mcp` — gNMI Streaming Telemetry MCP Server (stdio transport)

## Tools Used

1. **gnmi_get** — Retrieve device state/config via gNMI Get with YANG paths
2. **gnmi_set** — Apply configuration via gNMI Set (requires ServiceNow CR)
3. **gnmi_subscribe** — Create SAMPLE or ON_CHANGE telemetry subscriptions
4. **gnmi_unsubscribe** — Cancel active subscriptions
5. **gnmi_get_subscriptions** — List all active telemetry subscriptions
6. **gnmi_get_subscription_updates** — Retrieve latest telemetry updates
7. **gnmi_capabilities** — Discover YANG models and encodings on a device
8. **gnmi_browse_yang_paths** — Explore YANG path tree under a module
9. **gnmi_compare_with_cli** — Compare gNMI vs CLI state for validation
10. **gnmi_list_targets** — List configured gNMI target devices

## Workflows

### Query Device State
1. `gnmi_list_targets` — identify available devices
2. `gnmi_capabilities` — discover supported YANG models
3. `gnmi_browse_yang_paths` — explore available paths
4. `gnmi_get` — retrieve structured state data

### Monitor Real-Time Telemetry
1. `gnmi_subscribe` — create subscription (SAMPLE or ON_CHANGE)
2. `gnmi_get_subscriptions` — verify subscription is active
3. `gnmi_get_subscription_updates` — poll for latest updates
4. `gnmi_unsubscribe` — clean up when monitoring is complete

### Apply Configuration Change
1. `gnmi_get` — capture current baseline state
2. `gnmi_set` — apply change with ServiceNow CR number
3. `gnmi_get` — verify change was applied correctly

### Validate gNMI vs CLI
1. `gnmi_compare_with_cli` — side-by-side comparison with pyATS data

## Supported Vendors

- Cisco IOS-XR (port 57400, JSON_IETF encoding)
- Juniper (port 32767, JSON_IETF encoding)
- Arista (port 6030, JSON encoding)
- Nokia SR OS (port 57400, JSON_IETF encoding)

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GNMI_TARGETS` | JSON array of target devices (name, host, port, credentials, vendor) |
| `GNMI_TLS_CA_CERT` | CA certificate for TLS server verification |
| `GNMI_TLS_CLIENT_CERT` | Client certificate for mTLS (optional) |
| `GNMI_TLS_CLIENT_KEY` | Client private key for mTLS (optional) |

## Example Usage

**Query interface state:**
> "Show me the interface status on router1 using gNMI"

**Subscribe to counters:**
> "Set up a SAMPLE telemetry subscription for interface counters on switch1 every 30 seconds"

**Apply configuration:**
> "Change the description on GigabitEthernet0/0/0/1 on router1 to 'Uplink to spine' using CR CHG0012345"

**Browse capabilities:**
> "What YANG models does router1 support?"

## Safety

- gNMI Get, Subscribe, Capabilities, and Browse are read-only (safe)
- gNMI Set is ITSM-gated: requires a ServiceNow Change Request in "Implement" state
- TLS is mandatory for all connections; mTLS is supported
- All operations are logged to the GAIT audit trail
- Maximum 50 concurrent subscriptions (configurable via GNMI_MAX_SUBSCRIPTIONS)
