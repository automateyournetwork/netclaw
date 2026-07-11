---
name: pfsense-threat-intel
version: 2.0.0
description: Analyze pfSense blocked traffic, enrich with threat intelligence, and ONLY surface IPs that require human action — filter out scanners, background noise, and already-handled blocks.
triggers:
  - blocked traffic analysis
  - threat intel lookup
  - IP reputation check
  - who is attacking
  - firewall threat report
  - enrich blocked IPs
  - security triage
  - investigate source IP
mcp_servers:
  - pfsense (analyze_blocked_traffic, search_logs_by_ip, get_firewall_log, search_firewall_rules, search_nat_port_forwards, search_aliases)
  - threatintel-mcp (threatintel_lookup_ip, abuseipdb_check, otx_get_pulses, otx_search_pulses, greynoise_ip, feodo_tracker, threatfox_iocs)
---

# pfSense Threat Intelligence — Actionable Alerts Only

## Philosophy

The firewall blocks thousands of IPs per day. Almost all of them are internet background radiation — mass scanners, bots, drive-bys. **Never alert the operator about things the firewall already handled.** Only surface threats that require a decision or action.

## Decision Framework: Alert or Silence?

Before presenting ANY blocked IP to the operator, answer these questions:

1. **Did any traffic from this IP get ALLOWED through?** (search_logs_by_ip with pass filter)
2. **Does this IP target a port we have OPEN?** (check NAT port forwards + pass rules)
3. **Is this IP part of an active campaign targeting our stack?** (OTX pulse match)
4. **Is this a known C2/ransomware infrastructure?** (Feodo Tracker, AbuseIPDB categories)

If ALL answers are NO → **silence it**. The firewall did its job. Don't waste the operator's attention.

## Workflow

### 1. Collect (pfSense MCP)

Use `analyze_blocked_traffic` to get top blocked source IPs.

### 2. Quick Filter (Before API Calls)

Immediately discard:
- RFC 1918 sources (misconfigs, not attacks)
- IPs with only 1-2 hits (random drive-bys)
- IPs targeting only port 22/23/445/3389/5900 when those ports have NO pass rules

This saves API quota for IPs that matter.

### 3. Enrich Remaining (Threat Intel MCP)

For the remaining IPs (typically 5-15 after filtering):

- **`threatintel_lookup_ip`** — unified cross-source lookup
- **`feodo_tracker`** — check against active botnet C2 list (free, no rate limit)

Only drill into `abuseipdb_check` or `greynoise_ip` if the unified lookup is ambiguous.

### 4. Correlate with Exposure

For any IP that has real threat intel (AbuseIPDB ≥ 70, OTX match, or Feodo hit):

1. `search_nat_port_forwards` — is the targeted port actually forwarded inbound?
2. `search_firewall_rules` — does a pass rule exist for this traffic?
3. `search_logs_by_ip` — has this IP appeared in ALLOWED entries (not just blocked)?

### 5. Alert Decision

| Situation | Action |
|-----------|--------|
| Known bad IP + traffic was ALLOWED | **ALERT IMMEDIATELY** — possible compromise |
| Known bad IP + targets an exposed port (NAT forward exists) + all blocked | **Daily digest** — the port is exposed, they're probing it, monitor |
| Known bad IP + all blocked + port not exposed | **Silent** — firewall handled it, log only |
| GreyNoise "benign" (Shodan, Censys, etc.) | **Silent** — internet census, ignore |
| No intel + low hit count | **Silent** — random noise |

### 6. Alert Format (When Warranted)

Only present this when the IP passes the filter:

```
⚠️ Requires Attention: 45.x.x.x
   Why: AbuseIPDB 98% (ransomware affiliate) + 3 connections ALLOWED on port 443
   Evidence: OTX "LockBit C2 infrastructure" pulse, active since 2026-07-01
   Exposure: Port 443 NAT forwarded to 192.168.1.50 (web server)
   Recommended: Check 192.168.1.50 for compromise indicators, add IP to permanent blocklist
```

### 7. What NOT to Show

Never present to the operator:
- Tables of blocked scanners with scores
- "Medium threat" IPs that were all blocked and target closed ports
- Background radiation statistics
- IPs that are already in a blocklist alias
- Anything where the correct action is "do nothing"

## Example Prompts

- "Any real threats hitting my firewall, or just noise?"
- "Is anything getting through that shouldn't be?"
- "Check if today's blocked IPs include anything I need to worry about"
- "Investigate 45.155.205.233 — is it a real threat or a scanner?"
- "Are any known C2 servers hitting exposed ports?"

## Rate Limit Strategy

- Feodo Tracker: check first (free, no limit, catches the worst stuff)
- OTX: use for campaign correlation (unlimited free tier)
- AbuseIPDB: save for IPs that pass initial filters (1,000/day)
- GreyNoise: use sparingly to classify ambiguous IPs only

## Automated Response (When Operator Confirms)

If an alert IS generated and the operator says "block it":
1. Find or create a blocklist alias in pfSense (`search_aliases`, `create_alias`)
2. Add the IP (`manage_alias_addresses`)
3. Verify a block rule references that alias (`search_firewall_rules`)
4. Confirm the block is active (`apply_firewall_changes`)

Write operations require operator confirmation — never auto-block.
