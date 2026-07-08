# NetClaw MCP Servers

This directory contains MCP (Model Context Protocol) servers for NetClaw integrations.

## Overview

MCP servers provide tool interfaces for AI agents to interact with network platforms, observability systems, and infrastructure services.

## Available Servers

This table covers every server vendored under this directory (54 as of this writing). Servers that are Remote HTTP endpoints or installed on demand via pip/npm without a local vendored directory (e.g. GitHub, Microsoft Graph, Datadog, AWS/GCP, Grafana) are documented in the top-level [README.md](../README.md#mcp-servers-108) MCP Servers table instead, not here. Run `python3 ../scripts/verify-inventory-counts.py` to confirm this list is current.

| Server | Description | Type |
|--------|-------------|------|
| `AAP-Enterprise-MCP-Server` | Red Hat Ansible Automation Platform — Controller, EDA, ansible-lint, Red Hat Docs (4 servers) | Community |
| `ACI_MCP` | Cisco ACI — APIC interaction, policy management, fabric health | Local |
| `CiscoFMC-MCP-server-community` | Cisco Secure Firewall (FMC) access policy search, FTD targeting | Community |
| `ISE_MCP` | Cisco ISE identity policy, posture, TrustSec, endpoint control | Local |
| `Wikipedia_MCP` | Standards and technology context lookup | Local |
| `aruba-cx-mcp` | HPE Aruba CX switch management | Community |
| `atlassian-mcp` | Jira/Confluence | Community |
| `azure-network-mcp` | Azure networking — VNets, NSGs, ExpressRoute, VPN Gateways, Firewalls | Local |
| `batfish-mcp` | Batfish offline configuration analysis | Local |
| `catalyst-center-mcp` | Cisco Catalyst Center (DNA-C) — devices, clients, sites, interfaces | Community |
| `checkpoint-mcp-servers` | Check Point Security (15 MCPs: policy, threat intel, gateway, SASE) | Local |
| `cisco-sdwan-mcp` | Cisco SD-WAN vManage read-only fabric monitoring | Community |
| `clab-mcp-server` | ContainerLab containerized network lab lifecycle | Community |
| `claroty-mcp` | Claroty xDome OT/IoT/IoMT asset visibility and threat detection | Local |
| `eve-ng-mcp-server` | EVE-NG lab management, topology, node/console operations | Community |
| `f5-mcp-server` | F5 BIG-IP iControl REST — virtuals, pools, iRules, profiles, stats | Community |
| `forward-mcp` | Forward Networks digital twin and Network Query Engine (NQE) | Local |
| `fwrule-mcp` | Multi-vendor firewall rule overlap/shadowing/conflict analysis | Community |
| `gait_mcp` | GAIT — Git-based AI tracking and audit trail | Local |
| `gitlab-mcp` | GitLab DevOps | Community |
| `gnmi-mcp` | gNMI telemetry streaming | Local |
| `gns3-mcp-server` | GNS3 network lab simulation | Local |
| `infrahub-mcp` | OpsMill Infrahub schema-driven source of truth | Community |
| `ipfix-mcp` | IPFIX/NetFlow (v5/v9) flow telemetry receiver | Local |
| `jenkins-mcp` | Jenkins CI/CD — job monitoring, build triggering, log analysis | Community (Java plugin) |
| `junos-mcp-server` | Juniper JunOS PyEZ/NETCONF device automation | Community |
| `markmap_mcp` | Hierarchical mind map generation | Local |
| `mcp-cvp-fun` | Arista CloudVision Portal device inventory, events, tag management | Community |
| `mcp-nautobot` | Nautobot IPAM source of truth (community, 5 tools, alternative to NetBox) | Community |
| `mcp-nvd` | NIST NVD vulnerability database with CVSS scoring | Community |
| `memory-mcp` | Hybrid persistent memory — SQLite facts, ChromaDB semantic search, entity graph | Local |
| `meraki-magic-mcp-community` | Cisco Meraki Dashboard API (~804 endpoints) | Community |
| `nautobot-golden-config-mcp` | Nautobot golden-config compliance job runner | Local |
| `nautobot-mcp-v2` | Enhanced Nautobot 3.1.0 — GraphQL reads, REST writes, ITSM-gated changes | Local |
| `nautobot-routing-mcp` | Nautobot BGP/routing data queries | Local |
| `netbox-mcp-server` | Read-write DCIM/IPAM source of truth | Community |
| `nmap-mcp` | Network scanning — host discovery, port scanning, NSE scripts | Community |
| `ollama-mcp` | Local LLM domain-expert delegation via Ollama | Local |
| `packet-buddy-mcp` | pcap/pcapng deep analysis via tshark | Local |
| `prisma-sdwan-mcp` | Palo Alto Prisma SD-WAN read-only visibility | Local |
| `protocol-mcp` | Live BGP/OSPF/GRE control-plane participation | Local |
| `pyATS_MCP` | Device CLI, Genie parsers, config push, dynamic test execution | Local |
| `radkit-mcp-server-community` | Cisco RADKit cloud-relayed remote device access | Community |
| `servicenow-mcp` | Incidents, change requests, CMDB | Community |
| `sketchfab-mcp-server` | Real 3D model search/download for Three.js real-stencil mode | Community |
| `snmptrap-mcp` | SNMP trap (v1/v2c/v3) receiver | Local |
| `subnet-calculator-mcp` | IPv4 + IPv6 CIDR subnet calculator | Local |
| `suzieq-mcp` | SuzieQ network observability | Local |
| `syslog-mcp` | Syslog (RFC 5424/RFC 3164) receiver | Local |
| `thousandeyes-mcp-community` | Cisco ThousandEyes tests, agents, path visualization (read-only) | Community |
| `tts-mcp` | Text-to-speech (Microsoft Edge TTS) for Slack/WebEx voice replies | Local |
| `twilio-voice-mcp` | Universal voice interface — inbound/outbound calls, alerts | Local |
| `twitter-mcp` | Twitter/X posting, mention monitoring, reply generation | Local |
| `uml-mcp` | 27+ UML/diagram types via Kroki | Community |

Servers documented in the top-level README but not vendored here (Remote HTTP endpoints or pip/npm-installed on demand): GitHub, Microsoft Graph, Itential IAP, Cisco CML, Cisco NSO, AWS (6 servers), GCP (4 servers), Datadog, PagerDuty, Splunk, Terraform Cloud, HashiCorp Vault, Zscaler, Cloudflare (5 servers), Blender, Unreal Engine 5, DevNet Content Search, HumanRail, gtrace, Grafana, Prometheus, Kubeshark, draw.io, RFC Lookup — see the [README.md MCP Servers table](../README.md#mcp-servers-108) for the complete set.

## Security with DefenseClaw

When DefenseClaw is enabled, all MCP servers are automatically scanned before use.

### Automatic Scanning

DefenseClaw's CodeGuard performs static analysis on MCP server code:

```bash
# Scan an MCP server
defenseclaw mcp scan meraki-mcp

# Expected output:
# Scanning MCP: meraki-mcp
# ✓ No HIGH/CRITICAL findings
# Status: ALLOWED
```

### What CodeGuard Checks

| Finding Type | Severity | Description |
|--------------|----------|-------------|
| `credential` | HIGH | Hardcoded API keys, passwords |
| `eval` | CRITICAL | Dynamic code execution |
| `shell` | HIGH | Shell command injection |
| `sqli` | CRITICAL | SQL injection |
| `path_traversal` | MEDIUM | Directory traversal |
| `weak_crypto` | MEDIUM | MD5, SHA1 for security |
| `unsafe_deser` | HIGH | Unsafe pickle/yaml |

### Tool Management

Control which MCP tools are allowed:

```bash
# Block a specific tool
defenseclaw tool block "meraki_delete_network" --reason "destructive"

# Block all delete operations for an MCP
defenseclaw tool block "meraki_delete_*" --reason "no deletions"

# Allow a tool
defenseclaw tool allow "meraki_get_networks"
```

### Adding New MCP Servers

When adding a new MCP server:

1. **Scan before deployment**:
   ```bash
   defenseclaw mcp scan <new-mcp-server>
   ```

2. **Review findings** - Fix any HIGH/CRITICAL issues

3. **Configure tool rules** - Block dangerous operations if needed:
   ```bash
   defenseclaw tool block "<mcp>_delete_*" --reason "policy"
   defenseclaw tool block "<mcp>_destroy_*" --reason "policy"
   ```

4. **Test in observe mode** first:
   ```bash
   defenseclaw setup guardrail --mode observe
   # Run tests...
   defenseclaw alerts  # Review any security events
   ```

## Security Best Practices for MCP Development

### Do

- Use environment variables for credentials
- Validate all inputs before use
- Log operations for audit trails
- Return structured errors
- Use official SDKs when available

### Don't

- Hardcode API keys or passwords
- Use eval/exec on user input
- Execute shell commands with user input
- Store credentials in code or logs
- Bypass SSL verification in production

### Example: Secure MCP Server Pattern

```python
import os
from mcp.server import Server

# Good: Credentials from environment
api_key = os.environ.get("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable required")

# Good: Input validation
def validate_device_id(device_id: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9-]+$', device_id))

# Good: Structured error handling
@server.tool()
async def get_device(device_id: str):
    if not validate_device_id(device_id):
        return {"error": "Invalid device ID format"}
    # ... implementation
```

## Documentation

- [DefenseClaw Guide](../docs/DEFENSECLAW.md) - Full security documentation
- [Security Principles](../docs/SOUL-DEFENSE.md) - Security posture guidance
- [SKILL-SCHEMA.md](../workspace/skills/SKILL-SCHEMA.md) - Skill definition schema
