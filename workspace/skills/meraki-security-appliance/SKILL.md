---
name: meraki-security-appliance
description: Cisco Meraki Security Appliance (MX) — firewall rules, site-to-site VPN, content filtering, traffic shaping, security events
version: 1.0.0
tags: [cisco, meraki, mx, firewall, vpn, security, content-filtering, traffic-shaping]
---

# Meraki Security Appliance (MX) Operations

Manage Cisco Meraki MX security appliances via the Meraki Magic MCP server — audit and modify L3/L7 firewall rules, configure site-to-site VPN, manage content filtering, set traffic shaping policies, and investigate security events.

## MCP Server

- **Repository**: [CiscoDevNet/meraki-magic-mcp-community](https://github.com/CiscoDevNet/meraki-magic-mcp-community)
- **Transport**: stdio (Python via FastMCP) or HTTP
- **Requires**: `MERAKI_API_KEY`, `MERAKI_ORG_ID`

## Key Capabilities

| Operation | API Method | What It Does |
|-----------|-----------|--------------|
| Security center | `getNetworkSecurityCenter` | Security overview: threat score, events, top threats |
| VPN status | `getNetworkVpnStatus` | VPN peer connectivity status |
| Firewall rules | `getNetworkSecurityFirewallRules` | L3 outbound firewall rules |
| Update firewall | `updateNetworkSecurityFirewallRules` | **[WRITE]** Modify L3 firewall rules |
| Site-to-site VPN | `getNetworkSecurityVpnSiteToSite` | VPN mode (hub/spoke/none), hubs, subnets |
| Update VPN | `updateNetworkSecurityVpnSiteToSite` | **[WRITE]** Modify VPN configuration |
| Content filtering | `getNetworkSecurityContentFiltering` | URL categories, blocked URLs, allowed URLs |
| Update filtering | `updateNetworkSecurityContentFiltering` | **[WRITE]** Modify blocked/allowed URL lists and categories |
| Security events | `getNetworkSecuritySecurityEvents` | IDS/IPS events, malware, C2 callbacks |
| Traffic shaping | `getNetworkSecurityTrafficShaping` | Global bandwidth limits, per-rule shaping |
| Update shaping | `updateNetworkSecurityTrafficShaping` | **[WRITE]** Modify bandwidth limits and shaping rules |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **MX** | Meraki security appliance — firewall, VPN concentrator, content filter, IDS/IPS, SD-WAN |
| **L3 Firewall** | Stateful packet filtering — source/dest IP, port, protocol, action (allow/deny) |
| **L7 Firewall** | Application-layer filtering — block by application category (P2P, gaming, social media) |
| **Auto VPN** | Meraki's zero-config site-to-site VPN mesh — IPsec tunnels auto-negotiated via Dashboard |
| **Hub/Spoke** | VPN topology — spoke sites send all VPN traffic through hub sites; hubs exchange directly |
| **Content Filtering** | URL-based filtering — block categories (adult, gambling, malware) or specific URLs |
| **Traffic Shaping** | Bandwidth management — per-rule or global limits, prioritization by application |
| **SD-WAN** | Software-Defined WAN — policy-based routing across WAN links (MPLS, Internet, cellular) |

## Workflow: Firewall Rule Audit

When a user asks "show me the firewall rules on the branch MX":

1. **Find network**: `getNetworks` (meraki-network-ops) for the branch network
2. **Firewall rules**: `getNetworkSecurityFirewallRules` — all L3 outbound rules
3. **Analyze**: check for overly permissive rules (any/any/any allow), shadowed rules, unused rules
4. **Content filtering**: `getNetworkSecurityContentFiltering` — URL category blocks
5. **Security events**: `getNetworkSecuritySecurityEvents` — recent IDS/IPS hits
6. **Report**: rule table with security assessment and recommendations

## Workflow: VPN Connectivity Troubleshooting

When investigating "VPN tunnel to HQ is down":

1. **VPN status**: `getNetworkVpnStatus` — tunnel state for all peers
2. **VPN config**: `getNetworkSecurityVpnSiteToSite` — mode, hubs, subnets
3. **Device status**: `getDeviceStatus` (meraki-network-ops) — is the MX online?
4. **Uplinks**: `getDeviceUplink` — WAN link status (is ISP up?)
5. **Security events**: `getNetworkSecuritySecurityEvents` — VPN-related errors
6. **Report**: root cause analysis (ISP outage, config mismatch, peer down)

## Workflow: Content Filtering Review

When auditing web content filtering:

1. **Current config**: `getNetworkSecurityContentFiltering` — blocked categories, blocked/allowed URLs
2. **Security events**: `getNetworkSecuritySecurityEvents` — users hitting blocked content
3. **Compare across sites**: check filtering consistency across networks
4. **Recommendations**: tighten categories, add specific URL blocks/allows
5. **Apply**: `updateNetworkSecurityContentFiltering` — **requires ServiceNow CR**

## Workflow: Security Event Investigation

When responding to a security alert:

1. **Security events**: `getNetworkSecuritySecurityEvents` — IDS/IPS detections, malware, C2
2. **Client details**: `getClientDetails` (meraki-network-ops) for involved endpoints
3. **Firewall rules**: `getNetworkSecurityFirewallRules` — is the threat being blocked?
4. **Content filtering**: check if malicious domains are in the block list
5. **Containment**: `updateClientPolicy` to quarantine the endpoint — **requires human approval**
6. **ServiceNow**: create Security Incident
7. **Report**: incident summary with timeline, IOCs, containment actions

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `meraki-network-ops` | Network/device context for MX operations |
| `meraki-monitoring` | Live diagnostics on MX appliances |
| `fmc-firewall-ops` | Cross-platform firewall audit: Meraki MX rules vs Cisco FTD rules |
| `aws-network-ops` | Hybrid security: Meraki MX on-prem + AWS Network Firewall cloud |
| `ise-posture-audit` | Meraki client policies + ISE posture for unified access control |
| `servicenow-change-workflow` | Gate all firewall, VPN, and content filtering changes |
| `gait-session-tracking` | Record all security investigations and rule changes |

## Important Rules

- **Firewall rule changes affect all traffic** — modifying L3 rules can break connectivity for the entire site
- **VPN configuration changes** can disrupt inter-site connectivity — always verify tunnel state after changes
- **Content filtering** affects user experience — coordinate with help desk before blocking new categories
- **Security events require investigation** — IDS/IPS alerts should be triaged, not ignored
- **ServiceNow CR required** for all firewall rule, VPN, content filtering, and traffic shaping changes
- **Record in GAIT** — log all security appliance audits, investigations, and changes

## Environment Variables

- `MERAKI_API_KEY` — Meraki Dashboard API key
- `MERAKI_ORG_ID` — Meraki organization ID
