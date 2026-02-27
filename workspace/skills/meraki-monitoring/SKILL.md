---
name: meraki-monitoring
description: Cisco Meraki Monitoring & Diagnostics — live ping, cable test, LED blink, wake-on-LAN, camera analytics, config change tracking
version: 1.0.0
tags: [cisco, meraki, monitoring, diagnostics, ping, cable-test, camera, analytics]
---

# Meraki Monitoring & Live Diagnostics

Monitor and diagnose Cisco Meraki infrastructure via the Meraki Magic MCP server — run live ping tests from devices, cable tests on switch ports, LED blinking for physical identification, wake-on-LAN, camera analytics, and config change tracking.

## MCP Server

- **Repository**: [CiscoDevNet/meraki-magic-mcp-community](https://github.com/CiscoDevNet/meraki-magic-mcp-community)
- **Transport**: stdio (Python via FastMCP) or HTTP
- **Requires**: `MERAKI_API_KEY`, `MERAKI_ORG_ID`

## Key Capabilities

### Live Diagnostics

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| Ping from device | `createDeviceManagementInterfacePing` | Run ping test from a Meraki device to a target IP |
| Ping results | `getDeviceManagementInterfacePingResults` | Retrieve ping results (latency, loss, jitter) |
| Cable test | `createDeviceLiveToolsCableTest` | Run cable diagnostics on switch ports |
| Cable results | `getDeviceLiveToolsCableTestResults` | Cable status: OK, open, short, length estimate |
| Blink LEDs | `blinkDeviceLeds` | Flash device LEDs for physical identification |
| Wake-on-LAN | `wakeDeviceOnLan` | Send WoL magic packet to wake a device |

### Camera Analytics (MV)

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| Live analytics | `getDeviceCameraAnalyticsLive` | Real-time person/object detection counts |
| Analytics overview | `getDeviceCameraAnalyticsOverview` | Historical analytics summary over time period |
| Analytics zones | `getDeviceCameraAnalyticsZones` | Configured detection zones and their stats |
| Snapshot | `generateDeviceCameraSnapshot` | Capture a still image from a camera |
| Camera settings | `getDeviceCameraVideoSettings` | Video resolution, quality, recording mode |
| Quality profiles | `getNetworkCameraQualityRetentionProfiles` | Retention and quality settings |
| Camera Sense | `getDeviceCameraSense` | ML-based object/person detection config |
| Update Sense | `updateDeviceCameraSense` | **[WRITE]** Enable/disable Sense, MQTT, audio detection |

### Audit & Tracking

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| Config changes | `getOrganizationConfigurationChanges` | Who changed what, when, on which network/device |
| API requests | `getOrganizationApiRequests` | API call history with caller, method, response code |
| Webhook logs | `getOrganizationWebhookLogs` | Webhook delivery success/failure tracking |

## Workflow: Device Reachability Troubleshooting

When investigating "can the branch MX reach the data center?":

1. **Ping test**: `createDeviceManagementInterfacePing` from the branch MX to the DC IP
2. **Wait for results**: `getDeviceManagementInterfacePingResults` — latency, packet loss, jitter
3. **Uplinks**: `getDeviceUplink` (meraki-network-ops) — WAN link health
4. **VPN status**: `getNetworkVpnStatus` (meraki-security-appliance) — tunnel state
5. **Report**: reachability analysis with latency baseline

## Workflow: Physical Layer Troubleshooting

When investigating "port 12 isn't working on the switch":

1. **Cable test**: `createDeviceLiveToolsCableTest` on port 12
2. **Cable results**: `getDeviceLiveToolsCableTestResults` — OK, open, short, length
3. **Port status**: `getDeviceSwitchPortStatuses` (meraki-switch-ops) — speed, duplex, errors
4. **Blink LEDs**: `blinkDeviceLeds` to identify the physical switch if needed
5. **Report**: cable status (replace cable, check patch panel, bad port)

## Workflow: Camera Monitoring

When auditing camera analytics:

1. **Live analytics**: `getDeviceCameraAnalyticsLive` — current person/vehicle counts
2. **Zones**: `getDeviceCameraAnalyticsZones` — which zones are configured
3. **Overview**: `getDeviceCameraAnalyticsOverview` — trends over time
4. **Settings**: `getDeviceCameraVideoSettings` — resolution, quality
5. **Quality**: `getNetworkCameraQualityRetentionProfiles` — retention policies
6. **Report**: camera analytics dashboard with trends and alert thresholds

## Workflow: Configuration Change Audit

When investigating "who changed the firewall rules?":

1. **Config changes**: `getOrganizationConfigurationChanges` with time filter
2. **API requests**: `getOrganizationApiRequests` — was it an API call or Dashboard UI?
3. **Filter**: narrow by network, admin, or change type
4. **Correlate**: match with ServiceNow CRs — was this an approved change?
5. **Report**: change audit trail with admin identity, timestamp, and approval status

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Device/network context for diagnostics |
| `meraki-switch-ops` | Port status combined with cable test results |
| `meraki-security-appliance` | VPN status combined with ping reachability |
| `meraki-wireless-ops` | Signal quality combined with AP ping tests |
| `packet-analysis` | Meraki diagnostics + pcap analysis for deep investigation |
| `gait-session-tracking` | Record all diagnostic results and audit findings |
| `servicenow-change-workflow` | Correlate config changes with approved CRs |

## Important Rules

- **Ping tests run FROM the Meraki device** — useful for testing reachability from the device's perspective
- **Cable tests are non-disruptive** — safe to run on live ports
- **LED blinking is temporary** — LEDs blink for the specified duration, then return to normal
- **Camera analytics require MV cameras** — not available on MR/MS/MX devices
- **Config change audit is critical** — every change should map to a ServiceNow CR
- **Record in GAIT** — log all diagnostic results and audit investigations

## Environment Variables

- `MERAKI_API_KEY` — Meraki Dashboard API key
- `MERAKI_ORG_ID` — Meraki organization ID
