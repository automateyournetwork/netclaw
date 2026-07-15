---
name: zscaler-zia
description: "Manage Zscaler Internet Access firewall rules, URL filtering, DLP, and security policies."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Zscaler Internet Access (ZIA) Skill

Manage Zscaler Internet Access firewall rules, URL filtering, DLP, and security policies.

## Tools

| Tool | Description |
|------|-------------|
| `list_firewall_rules` | List firewall filtering rules |
| `get_firewall_rule` | Get firewall rule details |
| `list_url_filtering_rules` | List URL filtering rules |
| `get_url_filtering_rule` | Get URL filtering rule details |
| `list_url_categories` | List URL categories |
| `list_dlp_dictionaries` | List DLP dictionaries |
| `get_dlp_dictionary` | Get DLP dictionary details |
| `list_dlp_engines` | List DLP engines |
| `list_locations` | List branch/location definitions |
| `get_location` | Get location details |
| `list_location_groups` | List location groups |
| `list_vpn_credentials` | List VPN credentials |
| `list_traffic_forwarding_rules` | List GRE tunnel policies |
| `create_firewall_rule` | Create firewall rule (write mode) |
| `update_firewall_rule` | Update firewall rule (write mode) |
| `delete_firewall_rule` | Delete firewall rule (write mode) |

## Example Queries

```
List all ZIA firewall rules

Show URL filtering rules that block social media

What DLP dictionaries are configured?

List all branch locations

Show traffic forwarding rules for the data center
```

## Prerequisites

- `ZSCALER_CLIENT_ID` OneAPI client ID
- `ZSCALER_CLIENT_SECRET` OneAPI client secret
- `ZSCALER_CUSTOMER_ID` Customer/tenant ID
- `ZSCALER_VANITY_DOMAIN` Vanity domain
- `ZSCALER_MCP_SERVICES` must include `zia`

## Server

This skill uses the `zscaler-mcp` server which connects to ZIA via OneAPI.
