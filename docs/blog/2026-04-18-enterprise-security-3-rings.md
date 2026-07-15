# Running NetClaw with Enterprise Security: A 3-Ring Architecture

*April 18, 2026*

Today we're excited to announce the **NetClaw Enterprise Security Stack** - a comprehensive security architecture that combines NVIDIA OpenShell container isolation with Cisco DefenseClaw runtime guardrails to provide defense-in-depth for AI-powered network automation.

## The Challenge: AI Agents Need Guardrails

AI agents like NetClaw are incredibly powerful - they can automate network configuration, troubleshoot issues, and orchestrate complex workflows across your infrastructure. But with great power comes great responsibility.

When you give an AI agent access to your network infrastructure, you need to ensure:
- It can't exfiltrate sensitive data
- It can't execute destructive commands
- It can't be manipulated through prompt injection
- All actions are logged for compliance

## The Solution: 3-Ring Security Architecture

We've implemented a layered security model inspired by defense-in-depth principles:

```
┌─────────────────────────────────────────────────────┐
│  Ring 1: NVIDIA OpenShell (Container Isolation)    │
│  ┌───────────────────────────────────────────────┐ │
│  │  Ring 2: Cisco DefenseClaw (Runtime Guards)  │ │
│  │  ┌─────────────────────────────────────────┐ │ │
│  │  │  Ring 3: NetClaw (AI Agent)             │ │ │
│  │  │                                         │ │ │
│  │  │  Skills | MCPs | Plugins                │ │ │
│  │  └─────────────────────────────────────────┘ │ │
│  │                                              │ │
│  │  LLM Inspection | Tool Call Filtering        │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  File System | Network | Process Isolation          │
└─────────────────────────────────────────────────────┘
```

### Ring 1: NVIDIA OpenShell (Container Isolation)

OpenShell provides kernel-level isolation using Docker containers with:
- **File system isolation**: NetClaw can only access designated directories
- **Network policies**: YAML-based rules control which APIs can be reached
- **Process namespaces**: Complete separation from the host system
- **Resource limits**: CPU and memory constraints

### Ring 2: Cisco DefenseClaw (Runtime Guardrails)

DefenseClaw sits between NetClaw and the outside world, inspecting all traffic:
- **LLM Inspection**: Monitors prompts and completions for 7 AI providers
- **Tool Call Filtering**: Enforces 6 rule categories on all tool executions
- **Component Scanning**: CodeGuard static analysis before execution
- **Audit Logging**: SQLite database with SIEM export (Splunk, OTLP)

### Ring 3: NetClaw (AI Agent)

NetClaw runs inside this protected environment with:
- Full access to your skills and MCP servers
- Slack/WebEx integration for user interaction
- All the power of Claude, GPT, and other LLMs
- Complete audit trail of all actions

## One-Command Startup

We've made deploying this entire stack trivial with a single command:

```bash
./scripts/netclaw-secure-start.sh
```

This script:
1. Starts the OpenShell gateway (K3s cluster in Docker)
2. Starts the DefenseClaw gateway (runtime guardrails)
3. Builds a custom sandbox with the latest OpenClaw
4. Migrates your config, API keys, and SOUL files
5. Applies network policies (allows Slack, LLM APIs, MCPs)

After it completes, just connect and go:

```bash
openshell sandbox connect netclaw
export HOME=/sandbox
openclaw gateway run &
openclaw tui
```

Your Slack channels connect automatically. Your skills are ready. Your network is protected.

## Network Policy: Allowlist by Default

The sandbox starts with a deny-by-default network policy. Only explicitly allowed endpoints are reachable:

| Category | Allowed Endpoints |
|----------|-------------------|
| **Messaging** | Slack, WebEx APIs |
| **LLMs** | Anthropic, OpenAI |
| **MCPs** | DevNet, Datadog, Meraki, Splunk |
| **Cloud** | AWS, Azure, GCP management APIs |
| **DevOps** | GitHub, GitLab, Terraform, Vault |

Any connection attempt to an unlisted destination is blocked and logged.

## Guardrail Modes

DefenseClaw operates in two modes:

| Mode | Behavior |
|------|----------|
| **observe** | Log violations, allow execution (default) |
| **action** | Block dangerous operations |

Start in observe mode to see what would be blocked, then switch to action mode for production:

```bash
defenseclaw setup guardrail --mode action
```

## What Gets Blocked?

DefenseClaw's 6 rule categories catch:

- **Secret exfiltration**: Sending API keys to external URLs
- **Dangerous commands**: `rm -rf /`, `curl | bash`
- **Sensitive file access**: `/etc/passwd`, `~/.ssh/`
- **C2 connections**: Known malicious IPs
- **Memory manipulation**: Writing to agent state files
- **Prompt injection**: Attempts to override system prompts

## Full Audit Trail

Every action is logged to `~/.defenseclaw/audit.db`:

```bash
# View recent alerts
defenseclaw alerts

# Export for compliance
defenseclaw alerts --export json > audit.json
```

Integrate with your SIEM:
```bash
# Splunk
defenseclaw config siem --type splunk --endpoint https://splunk.example.com:8088

# OpenTelemetry
defenseclaw config siem --type otlp --endpoint https://otel-collector.example.com:4318
```

## Getting Started

1. **Install NetClaw** (if you haven't already):
   ```bash
   ./scripts/install.sh
   # Answer 'y' to "Enable DefenseClaw + OpenShell?"
   ```

2. **Start the secure stack**:
   ```bash
   ./scripts/netclaw-secure-start.sh
   ```

3. **Connect and use**:
   ```bash
   openshell sandbox connect netclaw
   export HOME=/sandbox
   openclaw gateway run &
   openclaw tui
   ```

4. **Enable blocking mode** (when ready for production):
   ```bash
   defenseclaw setup guardrail --mode action
   ```

## Learn More

- [Full Security Guide](DEFENSECLAW.md)
- [Security Principles](SOUL-DEFENSE.md)
- [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell)
- [Cisco DefenseClaw](https://github.com/cisco-ai-defense/defenseclaw)

---

*NetClaw: AI-powered network automation with enterprise-grade security. Because your network deserves both intelligence and protection.*
