# Research: DefenseClaw Security Integration

**Feature**: 027-netshell-security
**Date**: 2026-04-16
**Updated**: Replacing original NetShell/OpenShell research with DefenseClaw findings

## Executive Summary

DefenseClaw from Cisco AI Defense provides a complete security solution that replaces the need for custom NetShell implementation. It handles OpenShell sandbox setup automatically and adds component scanning, CodeGuard analysis, LLM inspection, and SIEM integration that NetShell did not provide.

---

## 1. DefenseClaw Installation Process

### Decision
Use DefenseClaw's official curl installer with `--sandbox` flag for full protection.

### Findings

**Installation Command:**
```bash
curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash
```

**Prerequisites:**
- Python 3.10+ (required)
- Docker (required for sandbox)
- Go 1.25+ (for gateway)
- Node.js 20+ (for TypeScript plugin)
- uv package manager (auto-installed)

**Post-Installation:**
```bash
defenseclaw init --enable-guardrail --sandbox
```

**Environment Variables:**
| Variable | Purpose | Default |
|----------|---------|---------|
| `DEFENSECLAW_HOME` | Installation directory | `~/.defenseclaw` |

**Installation Output:**
- Gateway binary: `~/.local/bin/defenseclaw-gateway`
- Python CLI: `~/.local/bin/defenseclaw`
- Virtual environment: `~/.defenseclaw/.venv`
- Plugin extensions: `~/.defenseclaw/extensions/defenseclaw`

### Alternatives Considered
- Manual OpenShell setup + custom governance (NetShell) - **Rejected**: DefenseClaw handles this automatically with more features
- No security layer - **Rejected**: Enterprise users need compliance features

---

## 2. DefenseClaw CLI Commands

### Decision
Document key CLI commands for install.sh integration and user documentation.

### Findings

**Scanning:**
```bash
defenseclaw skill scan <skill-name>     # Scan a skill before execution
defenseclaw mcp scan <mcp-name>         # Scan an MCP server
defenseclaw plugin scan <plugin-name>   # Scan a plugin
```

**Tool Management:**
```bash
defenseclaw tool block <tool> --reason "<reason>"   # Block a tool
defenseclaw tool allow <tool>                        # Allow a tool
defenseclaw tool list                                # List tool rules
```

**Guardrails:**
```bash
defenseclaw setup guardrail --mode observe   # Logging only (default)
defenseclaw setup guardrail --mode action    # Active enforcement
defenseclaw setup guardrail --restart        # Restart after mode change
```

**Alerts & Audit:**
```bash
defenseclaw alerts                      # View security alerts
defenseclaw alerts --export json        # Export for SIEM
```

### Alternatives Considered
- Custom CLI wrapper - **Rejected**: DefenseClaw CLI is comprehensive

---

## 3. Integration with OpenClaw

### Decision
DefenseClaw TypeScript plugin integrates automatically with OpenClaw via extension system.

### Findings

**Integration Architecture:**
```
OpenClaw Gateway
    └── DefenseClaw TypeScript Plugin (auto-loaded)
            ├── LLM Inspection (7 providers)
            ├── Tool Inspection (6 rule categories)
            └── Audit Logging (SQLite + SIEM)
```

**No NetClaw Code Changes Required:**
- DefenseClaw installs its plugin to `~/.defenseclaw/extensions/defenseclaw`
- OpenClaw automatically loads extensions from known paths
- Plugin intercepts LLM calls and tool executions

**OpenClaw Onboarding:**
```bash
openclaw onboard --install-daemon
```

### Alternatives Considered
- Manual plugin configuration - **Rejected**: Auto-discovery is standard

---

## 4. SIEM Configuration

### Decision
Document optional SIEM setup for enterprise users.

### Findings

**Splunk HEC:**
```bash
defenseclaw config siem --type splunk \
  --endpoint https://splunk.example.com:8088 \
  --token $SPLUNK_HEC_TOKEN
```

**OTLP (OpenTelemetry):**
```bash
defenseclaw config siem --type otlp \
  --endpoint https://otel-collector.example.com:4318
```

**Webhook Notifications:**
```bash
defenseclaw config webhook --slack $SLACK_WEBHOOK_URL
defenseclaw config webhook --pagerduty $PD_ROUTING_KEY
defenseclaw config webhook --webex $WEBEX_WEBHOOK_URL
```

**Default (SQLite):**
- Audit logs stored in `~/.defenseclaw/audit.db`
- No additional configuration required
- Queryable via `defenseclaw alerts`

### Alternatives Considered
- Custom OCSF logging (NetShell) - **Rejected**: DefenseClaw SQLite is compatible and includes SIEM export

---

## 5. NetClaw install.sh Integration

### Decision
Replace NetShell section with DefenseClaw installation flow.

### Findings

**Flow:**
1. Prompt: "Enable DefenseClaw (recommended)? [y/N]"
2. If yes:
   - Check Docker is installed and running
   - Check Python 3.10+, Go 1.25+, Node.js 20+
   - Run DefenseClaw installer
   - Run `defenseclaw init --enable-guardrail`
   - Update `openclaw.json` with `security.mode: "defenseclaw"`
3. If no:
   - Log: "Skipping DefenseClaw. Running in hobby mode (no security)."
   - Update `openclaw.json` with `security.mode: "hobby"`

**Prerequisite Checks:**
```bash
# Docker check
command -v docker &> /dev/null && docker info &> /dev/null

# Python version check
python3 --version | grep -E "3\.(1[0-9]|[2-9][0-9])" &> /dev/null

# Go version check
go version | grep -E "go1\.(2[5-9]|[3-9][0-9])" &> /dev/null

# Node.js version check
node --version | grep -E "v(2[0-9]|[3-9][0-9])" &> /dev/null
```

### Alternatives Considered
- Separate install script - **Rejected**: Integrated experience is better UX

---

## 6. DefenseClaw vs NetShell Comparison

### Decision
Use DefenseClaw, remove NetShell artifacts.

### Findings

| Capability | NetShell (Original) | DefenseClaw |
|------------|---------------------|-------------|
| OpenShell Setup | Manual | Automatic |
| Component Scanning | No | Yes (skills, MCPs, plugins) |
| CodeGuard Static Analysis | No | Yes |
| LLM Prompt Inspection | No | Yes (7 providers) |
| Tool Call Inspection | No | Yes (6 rule categories) |
| Egress Policies | Yes (23 YAML files) | Built-in |
| Per-Skill Permissions | Yes (SKILL.md) | Via tool block/allow |
| Audit Logging | OCSF local | SQLite + SIEM export |
| SIEM Integration | No | Yes (Splunk HEC, OTLP) |
| Webhook Notifications | No | Yes (Slack, PagerDuty, Webex) |

**Conclusion**: DefenseClaw provides everything NetShell provides plus:
- Automatic scanning before execution
- LLM-level inspection (not possible with NetShell)
- Runtime guardrails
- Enterprise SIEM integration

---

## Summary

| Research Area | Decision | Confidence |
|---------------|----------|------------|
| Installation | Official curl installer + `--sandbox` | High |
| CLI Commands | Use DefenseClaw native CLI | High |
| OpenClaw Integration | Auto-discovery via extension system | High |
| SIEM | Optional, SQLite default | High |
| install.sh Integration | Replace NetShell section | High |
| NetShell Removal | Remove entire netshell/ directory | High |

All research complete. Ready for Phase 1 design.
