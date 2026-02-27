---
name: meraki-wireless-ops
description: Cisco Meraki Wireless — SSID management, RF profiles, channel utilization, signal quality, client connectivity events
version: 1.0.0
tags: [cisco, meraki, wireless, ssid, rf, wifi, access-point, channel]
---

# Meraki Wireless Operations

Manage Cisco Meraki wireless networks via the Meraki Magic MCP server — configure SSIDs, create RF profiles, analyze channel utilization, monitor signal quality, and investigate client wireless connectivity events.

## MCP Server

- **Repository**: [CiscoDevNet/meraki-magic-mcp-community](https://github.com/CiscoDevNet/meraki-magic-mcp-community)
- **Transport**: stdio (Python via FastMCP) or HTTP
- **Requires**: `MERAKI_API_KEY`, `MERAKI_ORG_ID`

## Key Capabilities

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| List SSIDs | `getWirelessSSIDs` | All 15 SSIDs per network with auth, VLAN, band, visibility |
| Update SSID | `updateWirelessSSID` | **[WRITE]** Name, auth type, PSK, VLAN, band, splash, etc. |
| Wireless settings | `getWirelessSettings` | Network-level wireless configuration |
| List RF profiles | `getWirelessRFProfiles` | RF profiles with band selection, power, and channel settings |
| Create RF profile | `createWirelessRFProfile` | **[WRITE]** New RF profile with band/power/channel config |
| Channel utilization | `getWirelessChannelUtilization` | Per-AP channel utilization over time |
| Signal quality | `getWirelessSignalQuality` | SNR and signal strength metrics over time |
| Connection stats | `getWirelessConnectionStats` | Success/failure rates, association, auth, DHCP stats |
| Client events | `getWirelessClientConnectivityEvents` | Per-client roaming, auth, deauth, DHCP events |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **SSID** | Service Set Identifier — Meraki supports 15 per network, each independently configured |
| **RF Profile** | Radio frequency settings — band selection (dual/2.4/5/6 GHz), min/max power, channel width, DFS |
| **Channel Utilization** | Percentage of airtime used per channel — high utilization = congestion |
| **SNR** | Signal-to-Noise Ratio — measure of wireless signal quality (>25 dB is good, <15 dB is poor) |
| **Band Selection** | 2.4 GHz (range), 5 GHz (speed), 6 GHz (Wi-Fi 6E) — control which bands APs and clients use |
| **Splash Page** | Captive portal for guest auth — click-through, sign-on, sponsored, RADIUS |

## Workflow: Wireless Health Assessment

When a user asks "how's the WiFi?":

1. **SSIDs**: `getWirelessSSIDs` — which SSIDs are enabled, auth types, VLANs
2. **Connection stats**: `getWirelessConnectionStats` — success/failure rates
3. **Channel utilization**: `getWirelessChannelUtilization` — congestion hotspots
4. **Signal quality**: `getWirelessSignalQuality` — SNR trends over time
5. **RF profiles**: `getWirelessRFProfiles` — power/channel/band configuration
6. **Report**: wireless health dashboard with per-SSID and per-AP metrics

## Workflow: Client Connectivity Troubleshooting

When investigating "user X can't connect to WiFi":

1. **Find client**: `getNetworkClients` (from meraki-network-ops) filtered by MAC
2. **Client events**: `getWirelessClientConnectivityEvents` — auth failures, DHCP issues, roaming events
3. **Connection stats**: `getWirelessConnectionStats` — network-wide failure rates (is it client-specific or systemic?)
4. **AP signal**: `getWirelessSignalQuality` for the AP serving this client
5. **Channel util**: `getWirelessChannelUtilization` for the same AP — congestion?
6. **SSID config**: `getWirelessSSIDs` — check auth settings, VLAN, band restrictions
7. **Report**: root cause analysis with fix recommendation

## Workflow: RF Optimization

When optimizing wireless performance:

1. **Current RF**: `getWirelessRFProfiles` — existing band/power/channel settings
2. **Channel util**: `getWirelessChannelUtilization` across all APs — identify congestion
3. **Signal quality**: `getWirelessSignalQuality` — identify low-SNR areas
4. **Connection stats**: `getWirelessConnectionStats` — failure hotspots
5. **Recommendation**: adjust RF profiles — channel width, power levels, band steering
6. **Apply**: `createWirelessRFProfile` or update existing — **requires ServiceNow CR**

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Network/device context for wireless operations |
| `meraki-monitoring` | Live diagnostics (ping, cable test) for APs |
| `catc-client-ops` | Compare Meraki wireless vs Catalyst Center wireless client data |
| `servicenow-change-workflow` | Gate SSID and RF profile changes behind CRs |
| `gait-session-tracking` | Record all wireless investigations and changes |
| `slack-network-alerts` | Alert on wireless health degradation |

## Important Rules

- **SSID changes affect all users** — changing auth, VLAN, or band settings on a live SSID disconnects clients
- **RF profiles are network-wide** — changes propagate to all APs assigned to that profile
- **ServiceNow CR required** for any SSID modification, RF profile creation, or band/power changes
- **Channel utilization over 50%** is a warning; over 70% is critical and needs RF optimization
- **Record in GAIT** — log all wireless assessments and configuration changes

## Environment Variables

- `MERAKI_API_KEY` — Meraki Dashboard API key
- `MERAKI_ORG_ID` — Meraki organization ID
