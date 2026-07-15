---
name: fmc-firewall-ops
description: "Cisco Secure Firewall FMC — access policy search, rule inspection, FTD device targeting, multi-FMC profile management. Use when searching firewall rules by IP or FQDN, checking if host A can reach host B through the firewall, auditing FMC access policies, or reviewing SGT-based segmentation rules."
version: 1.0.0
license: Apache-2.0
tags: [cisco, fmc, firewall, ftd, security, access-policy, firepower]
---

# Cisco FMC Firewall Operations

## MCP Server

- **Repository**: [CiscoDevNet/CiscoFMC-MCP-server-community](https://github.com/CiscoDevNet/CiscoFMC-MCP-server-community)
- **Transport**: HTTP (`http://<host>:8000/mcp`) — requires HTTPS reverse proxy for production
- **Install**: `git clone` + `pip install -r requirements.txt` + `python -m sfw_mcp_fmc.server` (or Docker)
- **Requires**: `FMC_BASE_URL`, `FMC_USERNAME`, `FMC_PASSWORD`

## Available Tools (4)

| Tool | What It Does |
|------|-------------|
| `list_fmc_profiles` | Discover all configured FMC instances (single or multi-FMC mode). Returns profile IDs, display names, and aliases. Use this first to select which FMC to query. |
| `find_rules_by_ip_or_fqdn` | Search rules within a specific access policy by IP address or FQDN. Matches source/destination network objects against the given indicator. |
| `find_rules_for_target` | Resolve FTD devices or HA clusters to their assigned access policies, then search those policies. Use when you know the firewall device name but not the policy name. |
| `search_access_rules` | FMC-wide rule search with multiple filter types: network indicators (IP, FQDN), identity indicators (SGT tags, realm users/groups), and policy name filters. The most powerful search tool. |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **FMC** | Firepower Management Center — centralized management for Cisco Secure Firewalls (FTD) |
| **FTD** | Firepower Threat Defense — the firewall appliance/virtual managed by FMC |
| **Access Policy** | Collection of access rules (ACLs) applied to FTD devices — permit/deny by source/dest/port/app |
| **Access Rule** | Individual rule within a policy — source zones, dest zones, source/dest networks, ports, action (allow/block/monitor) |
| **SGT** | Security Group Tag — TrustSec identity-based tag for micro-segmentation |
| **HA Cluster** | High Availability pair of FTD devices sharing the same policy |
| **Profile** | FMC connection configuration (URL, credentials) — supports multi-FMC environments |

## Workflow: Firewall Rule Audit

When a user asks "what firewall rules exist for 10.1.1.0/24?":

1. **Discover FMCs**: `list_fmc_profiles` — identify which FMCs manage this network
2. **Search rules**: `search_access_rules` with network indicator `10.1.1.0/24`
3. **For each match**: Extract rule name, action (allow/block), source/dest zones, source/dest networks, ports, logging settings
4. **Cross-reference**: Check if rules are overly permissive (any/any), redundant, or shadowed
5. **Report**: Formatted rule table with security assessment

## Workflow: "Can Host A Reach Host B?"

When investigating connectivity through the firewall:

1. **Identify FTD**: Which firewall sits between source and destination?
2. **Resolve policy**: `find_rules_for_target` with the FTD device name
3. **Search source IP**: `find_rules_by_ip_or_fqdn` for the source IP in the resolved policy
4. **Search dest IP**: Same for destination IP
5. **Analyze**: Do the matching rules permit the required port/protocol?
6. **Report**: "Traffic from 10.1.1.50 to 10.2.1.100:443 is ALLOWED by rule 'Web-Servers-Inbound' (line 47)" or "BLOCKED by implicit deny"

## Workflow: Security Group Tag (SGT) Policy Review

When auditing TrustSec/SGT-based policies:

1. **Search by SGT**: `search_access_rules` with identity indicator for a specific SGT value
2. **List matching rules**: Which rules reference this SGT in source or destination?
3. **Check actions**: Are SGT-based rules enforcing proper segmentation?
4. **Cross-reference**: Use `ise-posture-audit` to verify SGT assignment policies in ISE
5. **Report**: SGT policy coverage analysis

## Workflow: Multi-FMC Environment Audit

When managing multiple FMC instances:

1. **List all FMCs**: `list_fmc_profiles` — see all managed FMC instances
2. **For each FMC**: `search_access_rules` with common indicators
3. **Compare policies**: Are policies consistent across FMCs?
4. **Identify drift**: Rules present in one FMC but not another
5. **Report**: Cross-FMC policy consistency analysis

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `pyats-security` | FMC rule audit + device-level ACL verification via pyATS |
| `ise-posture-audit` | FMC SGT rules + ISE SGT assignment and TrustSec matrix |
| `ise-incident-response` | FMC rules for quarantine verification + ISE endpoint investigation |
| `aws-security-audit` | Cross-platform security: FMC on-prem + AWS cloud security posture |
| `gcp-cloud-logging` | FMC firewall logs vs GCP firewall logs for hybrid environments |
| `nso-device-ops` | FMC policies + NSO device config for end-to-end policy view |
| `servicenow-change-workflow` | ServiceNow CR gating before any FMC policy modifications |
| `github-ops` | Commit FMC rule snapshots to Git for config-as-code tracking |

## Multi-FMC Configuration

Single FMC mode (set in `.env`):
```
FMC_BASE_URL=https://fmc.example.com
FMC_USERNAME=api-user
FMC_PASSWORD=changeme
FMC_VERIFY_SSL=false
```

Multi-FMC mode (profile directory):
```
profiles/
  dc-east.env    # FMC for DC East
  dc-west.env    # FMC for DC West
  dmz.env        # FMC for DMZ firewalls
```

Each profile `.env` contains:
```
FMC_PROFILE_ID=dc-east
FMC_PROFILE_DISPLAY_NAME=DC East FMC
FMC_PROFILE_ALIASES=10.1.1.10,fmc-east
FMC_BASE_URL=https://fmc-east.example.com
FMC_USERNAME=api-user
FMC_PASSWORD=changeme
FMC_VERIFY_SSL=false
```

## Important Rules

- **Read-only** — all 4 tools are search/query operations; no rule modifications
- **HTTP transport** — server runs on port 8000, front with HTTPS proxy for production
- **Multi-FMC** — always call `list_fmc_profiles` first to select the right FMC instance
- **FMC API rate limits** — FMC REST API has per-user rate limits; avoid rapid-fire queries
- **Record in GAIT** — log all firewall policy investigations for audit trail

## Environment Variables

- `FMC_BASE_URL` — FMC URL (e.g., `https://fmc.example.com`)
- `FMC_USERNAME` — FMC API username
- `FMC_PASSWORD` — FMC API password
- `FMC_VERIFY_SSL` — SSL verification (true/false)
- `FMC_PROFILES_DIR` — path to multi-FMC profiles directory (optional)
- `FMC_PROFILE_DEFAULT` — default profile name (optional)
