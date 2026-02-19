# NetClaw

A CCIE-level AI network engineering coworker. Built on [OpenClaw](https://github.com/openclaw/openclaw) with Anthropic Claude, 11 skills, and 5 tool backends for complete network automation.

## What It Does

NetClaw is an autonomous network engineering agent powered by Claude Opus that can:

- **Monitor** device health — CPU, memory, interfaces, hardware, NTP, logs
- **Troubleshoot** connectivity, routing adjacencies, performance, and flapping interfaces using OSI-layer methodology
- **Analyze** routing protocols — OSPF (LSDB, LSA types, area design), BGP (path selection, NOTIFICATION codes), EIGRP (DUAL states)
- **Audit** security posture — ACLs, AAA, CoPP, management plane hardening, routing protocol authentication, CIS benchmarks
- **Discover** network topology via CDP/LLDP, ARP, routing peers, and interface-to-subnet mapping
- **Configure** devices with full change management — baseline, apply, verify, rollback, document
- **Scan** for CVE vulnerabilities against the NVD database using discovered software versions
- **Diagram** your network with Draw.io topology maps
- **Visualize** protocol hierarchies as interactive Markmap mind maps
- **Reference** IETF RFCs for standards-compliant configuration
- **Report** findings in natural language via Slack or WebChat

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  OpenClaw Gateway                    │
│            (anthropic/claude-opus-4-6)               │
├─────────────────────────────────────────────────────┤
│  Chat Channels: Slack | WebChat Dashboard           │
└────────────────────────┬────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │     11 OpenClaw Skills      │
          │    (exec → MCP oneshot)     │
          ├─────────────────────────────┤
          │                             │
          │  ┌────────────────────────┐ │
          │  │  7 pyATS Skills        │ │
          │  │  network, health,      │ │
          │  │  routing, security,    │ │
          │  │  topology, config-mgmt,│ │
          │  │  troubleshoot          │ │
          │  └────────────────────────┘ │
          │                             │
          │  ┌────────────────────────┐ │
          │  │  4 Tool Skills         │ │
          │  │  markmap, drawio,      │ │
          │  │  rfc, nvd-cve          │ │
          │  └────────────────────────┘ │
          └──────────────┬──────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
┌───┴────┐  ┌───────────┴──┐  ┌──────────────┴──┐
│ pyATS  │  │ Markmap MCP  │  │  npx Servers    │
│  MCP   │  │ (clone+npm)  │  │  Draw.io        │
│(clone  │  └──────────────┘  │  RFC             │
│ +pip)  │                    │  NVD CVE         │
│        │                    └─────────────────-┘
│ Cisco  │
│Devices │
│via SSH │
└────────┘
```

## How Skills Work

NetClaw uses **OpenClaw Skills** — not `mcpServers` config — to give the agent its capabilities. Each skill is a `SKILL.md` file that teaches the agent how to call a specific tool via shell exec.

```
User asks question via Slack/WebChat
       │
       ▼
OpenClaw loads all 11 SKILL.md files into agent context
       │
       ▼
Agent picks the right skill, constructs JSON-RPC request
       │
       ▼
echo '{"jsonrpc":"2.0",...}' | <mcp-server> --oneshot
       │
       ▼
MCP server processes request, returns structured response
       │
       ▼
Agent analyzes result using CCIE-level expertise from skills
       │
       ▼
Responds to user with findings, recommendations, or diagrams
```

Every tool call is a single shell command — no persistent server connections, no port management.

## Skills (11 Total)

### pyATS Device Skills (7)

These skills give NetClaw deep Cisco IOS-XE/NX-OS expertise through the [pyATS MCP server](https://github.com/automateyournetwork/pyATS_MCP):

| Skill | What the Agent Knows |
|-------|---------------------|
| **pyats-network** | All 8 pyATS MCP tools: `show commands` with Genie structured parsing (100+ IOS-XE parsers cataloged), `ping` from device, `configure`, `running-config`, `logging`, `device list`, `Linux commands`, `dynamic AEtest scripts`. Direct Python pyATS with Genie Learn (34 features) and Genie Diff for state comparison. |
| **pyats-health-check** | 8-step health procedure: version/uptime → CPU utilization (with top-process analysis for BGP, OSPF, SNMP, Crypto) → memory → interface status and error counters → hardware/environment → NTP synchronization → syslog pattern matching (11 critical patterns) → connectivity. Threshold tables per metric. Produces severity-rated report card. |
| **pyats-routing** | Full routing table analysis with route source codes and ECMP. OSPF: neighbor states (FULL through DOWN with stuck-state diagnosis), LSA types 1-7, LSDB red flags, SPF run analysis. BGP: all FSM states, 11-step best path selection, NOTIFICATION error codes, policy verification. EIGRP: DUAL states, SIA detection, metric components. Redistribution audit checklist. Route filtering verification. |
| **pyats-security** | 9-step audit: running-config scan → management plane hardening (12 checks: SSH, VTY ACL, timeouts, banners, HTTP) → AAA (TACACS+/RADIUS with local fallback) → ACL analysis with hit counts → control plane policing → routing protocol authentication (OSPF MD5, BGP MD5/GTSM, EIGRP key-chain) → infrastructure security (14 controls: uRPF, CDP restriction, ICMP redirects, proxy-ARP, IP source-route) → encryption/credentials → SNMP. CIS benchmark severity output. |
| **pyats-topology** | 7-step discovery: CDP neighbors (platform, IP, local↔remote interface mapping) → LLDP (multi-vendor) → ARP table (IP-to-MAC, incomplete entries) → routing protocol peers (OSPF/BGP/EIGRP) → interface-to-subnet mapping → VRF topology (RD/RT/interfaces) → FHRP groups (HSRP/VRRP virtual IPs, active/standby). Builds unified model for Draw.io and Markmap. |
| **pyats-config-mgmt** | 5-phase change workflow: **Baseline** (running-config + relevant state + connectivity pings) → **Plan** (what/why/risk/rollback) → **Apply** (with config patterns for interfaces, OSPF, BGP, ACLs, route-maps, NTP, static routes) → **Verify** (logs for new errors, config diff, state comparison, connectivity re-test) → **Document** (change report template). Includes compliance templates for security baseline and VTY hardening. |
| **pyats-troubleshoot** | Structured methodology for 4 symptom types: **Connectivity loss** (L1 physical → L2 ARP → L3 routing/ping → L4 ACL/NAT, with advanced ping options: source, size, df-bit). **Routing adjacency down** (OSPF 9-item checklist, BGP 9-item checklist with NOTIFICATION error code table). **Slow performance** (CPU → interface utilization → QoS drops → path verification → routing loops). **Interface flapping** (cause analysis with log pattern matching). |

### Tool Integration Skills (4)

| Skill | Tool Backend | Purpose |
|-------|-------------|---------|
| **markmap-viz** | [markmap-mcp](https://github.com/automateyournetwork/markmap_mcp) (Node) | Interactive mind maps from markdown — OSPF area hierarchies, BGP peer trees, VLAN structures |
| **drawio-diagram** | [@drawio/mcp](https://github.com/jgraph/drawio-mcp) (npx) | Network topology diagrams from discovery data — Mermaid, XML, or CSV format |
| **rfc-lookup** | [@mjpitz/mcp-rfc](https://github.com/mjpitz/mcp-rfc) (npx) | IETF RFC search, retrieval, and section extraction — BGP (4271), OSPF (2328), NTP (5905) |
| **nvd-cve** | [nvd-cve-mcp-server](https://github.com/SOCTeam-ai/nvd-cve-mcp-server) (npx) | NVD vulnerability database — search by keyword, get CVE details with CVSS scores |

### Skill Anatomy

Each `SKILL.md` has YAML frontmatter and markdown instructions:

```markdown
---
name: pyats-health-check
description: "Comprehensive device health monitoring..."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Device Health Check

(Step-by-step procedures, show command examples, threshold tables,
 report templates — everything the agent needs to work autonomously)
```

The `metadata.openclaw.requires` block declares binary and environment variable dependencies. The markdown body is the agent's playbook.

## Prerequisites

- Node.js >= 18 (>= 22 recommended for OpenClaw)
- Python 3.x with pip3
- git
- Network devices accessible via SSH (for pyATS)
- Anthropic API key

## Quick Start

```bash
# 1. Clone NetClaw
git clone https://github.com/yourusername/netclaw.git
cd netclaw

# 2. Run the installer (installs OpenClaw, clones repos, builds tools, deploys all 11 skills)
./scripts/install.sh

# 3. Configure your devices
nano testbed/testbed.yaml

# 4. Onboard OpenClaw (if first time)
openclaw onboard --install-daemon

# 5. Start the gateway (foreground mode for WSL2)
openclaw gateway

# 6. Chat with NetClaw
openclaw chat --new
```

## Project Structure

```
netclaw/
├── workspace/
│   └── skills/                    # Skill definitions (source of truth)
│       ├── pyats-network/         # Core device automation (8 MCP tools)
│       ├── pyats-health-check/    # CPU, memory, interfaces, NTP, logs
│       ├── pyats-routing/         # OSPF, BGP, EIGRP, IS-IS deep analysis
│       ├── pyats-security/        # ACL, AAA, CoPP, hardening audit
│       ├── pyats-topology/        # CDP/LLDP discovery, subnet mapping
│       ├── pyats-config-mgmt/     # Change control, baseline, rollback
│       ├── pyats-troubleshoot/    # OSI-layer troubleshooting methodology
│       ├── markmap-viz/           # Mind map visualization
│       ├── drawio-diagram/        # Draw.io network diagrams
│       ├── rfc-lookup/            # IETF RFC search and retrieval
│       └── nvd-cve/               # CVE vulnerability search
├── testbed/
│   └── testbed.yaml               # pyATS testbed (your network devices)
├── config/
│   └── openclaw.json              # OpenClaw model config (template)
├── mcp-servers/                   # Created by install.sh (gitignored)
│   ├── pyATS_MCP/                 # Cloned from GitHub
│   └── markmap_mcp/               # Cloned from GitHub
├── examples/
│   ├── 01_health_check.md
│   ├── 02_vulnerability_audit.md
│   ├── 03_topology_diagram.md
│   ├── 04_ospf_mindmap.md
│   ├── 05_rfc_config.md
│   └── 06_full_audit.md
├── scripts/
│   └── install.sh                 # Full bootstrap installer
├── .env.example
├── .gitignore
└── README.md
```

### What Goes Where

| Location | Purpose |
|----------|---------|
| `workspace/skills/` | Skill source files. `install.sh` copies these to `~/.openclaw/workspace/skills/` |
| `testbed/testbed.yaml` | pyATS device inventory. Referenced by `PYATS_TESTBED_PATH` env var |
| `config/openclaw.json` | Model config template. Sets primary/fallback model only — no MCP config |
| `mcp-servers/` | Tool backends cloned by `install.sh`. Gitignored — rebuilt on install |

## What install.sh Does

1. **Checks prerequisites** — Node.js >= 18, Python 3, pip3, git, npx
2. **Installs OpenClaw** — `npm install -g openclaw@latest`
3. **Clones pyATS MCP** — `git clone` + `pip3 install -r requirements.txt`
4. **Clones Markmap MCP** — `git clone` + `npm install` + `npm run build` + `npm link`
5. **Caches npx packages** — `npm cache add` for Draw.io, RFC, and NVD CVE servers
6. **Deploys all 11 skills** — Copies `workspace/skills/*` to `~/.openclaw/workspace/skills/`
7. **Sets environment** — Writes `PYATS_TESTBED_PATH` to `~/.openclaw/.env`

## Testbed Configuration

Edit `testbed/testbed.yaml` to define your network devices:

```yaml
devices:
  R1:
    alias: "Core Router"
    type: router
    os: iosxe
    platform: CSR1kv
    credentials:
      default:
        username: admin
        password: "%ENV{NETCLAW_PASSWORD}"
    connections:
      cli:
        protocol: ssh
        ip: your-device-hostname-or-ip
        port: 22
```

The `%ENV{NETCLAW_PASSWORD}` syntax pulls credentials from environment variables so they stay out of version control.

## Safety

NetClaw has built-in safety guardrails at multiple layers:

**pyATS MCP Server (tool level):**
- Blocks destructive commands: `erase`, `reload`, `write erase`, `delete`, `format`
- Show command validation: must start with "show", no pipes or redirects
- Dynamic test sandboxing: no filesystem, network, or subprocess access

**Skills (agent level):**
- **pyats-config-mgmt** requires pre-change baselines before any configuration
- **pyats-health-check** checks logs for tracebacks and crash events before changes
- **pyats-troubleshoot** follows structured methodology — never guesses device state
- All skills instruct the agent to escalate to human engineers for unexpected errors

**Change workflow:**
1. Capture baseline (config + state + connectivity)
2. Plan change with risk assessment and rollback procedure
3. Apply one logical change at a time
4. Verify immediately (logs, state diff, connectivity)
5. Document results

## Example Conversations

Ask NetClaw anything you'd ask a senior network engineer:

```
"Run a health check on R1"
→ Uses pyats-health-check: 8-step assessment, severity-rated report card

"Is R1 vulnerable to any known CVEs?"
→ Uses pyats-network (show version) + nvd-cve (search by IOS-XE version)

"Show me the OSPF topology as a mind map"
→ Uses pyats-routing (OSPF neighbors/database) + markmap-viz (generate mind map)

"Draw a network diagram from CDP neighbors"
→ Uses pyats-topology (CDP discovery) + drawio-diagram (Mermaid diagram)

"Add a Loopback99 interface with IP 99.99.99.99/32"
→ Uses pyats-config-mgmt: baseline → apply → verify → document

"BGP peer 10.1.1.2 is down, help me fix it"
→ Uses pyats-troubleshoot: 9-item BGP checklist, NOTIFICATION error code analysis

"Audit R1's security posture"
→ Uses pyats-security: 9-step audit, CIS benchmark severity output

"What does RFC 4271 say about BGP hold timers?"
→ Uses rfc-lookup: fetch RFC 4271, extract relevant section
```

See `examples/` for detailed workflow walkthroughs:

1. [Device Health Check](examples/01_health_check.md)
2. [Vulnerability Audit](examples/02_vulnerability_audit.md)
3. [Topology Diagram](examples/03_topology_diagram.md)
4. [OSPF Mind Map](examples/04_ospf_mindmap.md)
5. [RFC-Informed Config](examples/05_rfc_config.md)
6. [Full Autonomous Audit](examples/06_full_audit.md)
