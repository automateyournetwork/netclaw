# Upgrading to DefenseClaw

This guide helps existing NetClaw users enable DefenseClaw enterprise security.

## Quick Upgrade

```bash
./scripts/defenseclaw-enable.sh
```

That's it! The script handles everything automatically.

---

## What Changes

### Before (Hobby Mode)
- NetClaw runs without security layer
- Full host access
- No sandbox isolation
- No audit logging

### After (DefenseClaw)
- OpenShell kernel-level sandbox (Landlock, seccomp, namespaces)
- Component scanning before execution
- Runtime guardrails for LLM and tool calls
- SQLite audit database with optional SIEM export

---

## Prerequisites

Before upgrading, ensure you have:

| Requirement | Minimum Version | Check Command |
|-------------|-----------------|---------------|
| Docker | Running | `docker info` |
| Python | 3.10+ | `python3 --version` |
| Go | 1.25+ | `go version` |
| Node.js | 20+ | `node --version` |

---

## Step-by-Step Upgrade

### 1. Run the Enable Script

```bash
cd /path/to/netclaw
./scripts/defenseclaw-enable.sh
```

The script will:
1. Check all prerequisites
2. Backup your current `openclaw.json`
3. Install DefenseClaw from Cisco AI Defense
4. Initialize guardrails in observe mode
5. Update configuration to `security.mode: "defenseclaw"`

### 2. Verify Installation

```bash
# Check DefenseClaw CLI
defenseclaw --version

# Check gateway is running
pgrep defenseclaw-gateway

# Check configuration
cat ~/.openclaw/config/openclaw.json | grep -A2 security
```

### 3. (Optional) Enable Action Mode

By default, guardrails run in **observe** mode (logging only). To enable blocking:

```bash
defenseclaw setup guardrail --mode action --restart
```

---

## Configuration Changes

### openclaw.json

**Before:**
```json
{
  "netshell": {
    "enabled": false
  }
}
```

**After:**
```json
{
  "security": {
    "mode": "defenseclaw"
  }
}
```

### Environment

DefenseClaw creates:

| Path | Purpose |
|------|---------|
| `~/.defenseclaw/` | DefenseClaw home directory |
| `~/.defenseclaw/audit.db` | SQLite audit database |
| `~/.defenseclaw/extensions/` | OpenClaw plugins |
| `~/.local/bin/defenseclaw` | CLI binary |
| `~/.local/bin/defenseclaw-gateway` | Gateway binary |

---

## Migration from NetShell

If you were using the original NetShell security layer:

### Policies
- NetShell YAML policies are **not needed** - DefenseClaw handles all security
- Archive `netshell/` directory: `mv netshell netshell.bak`

### Skill Permissions
- NetShell `netshell:` sections in SKILL.md are **ignored** by DefenseClaw
- Use DefenseClaw tool management instead:
  ```bash
  defenseclaw tool block <tool-name> --reason "policy"
  defenseclaw tool allow <tool-name>
  ```

### Audit Logs
- NetShell OCSF logs are replaced by DefenseClaw SQLite database
- Export for compliance: `defenseclaw alerts --export json`

---

## Rollback

If you need to disable DefenseClaw:

```bash
./scripts/defenseclaw-disable.sh
```

This switches back to hobby mode but **does not uninstall** DefenseClaw.

To fully remove DefenseClaw:
```bash
rm -rf ~/.defenseclaw
rm ~/.local/bin/defenseclaw*
```

---

## Troubleshooting

### "defenseclaw: command not found"

Add to your shell profile:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### "Docker daemon is not running"

Start Docker:
```bash
# Linux
sudo systemctl start docker

# macOS
open -a Docker
```

### "Prerequisites not met"

Check each requirement:
```bash
python3 --version  # Need 3.10+
go version         # Need 1.25+
node --version     # Need 20+
docker info        # Must be running
```

### Gateway won't start

Check for port conflicts:
```bash
lsof -i :8080  # Default gateway port
```

---

## Next Steps

After upgrading:

1. **Read the full guide**: [DEFENSECLAW.md](DEFENSECLAW.md)
2. **Scan your skills**: `defenseclaw skill scan <skill-name>`
3. **Review security principles**: [SOUL-DEFENSE.md](SOUL-DEFENSE.md)
4. **Configure SIEM** (optional): See SIEM Integration in DEFENSECLAW.md

---

## Support

- DefenseClaw GitHub: https://github.com/cisco-ai-defense/defenseclaw
- NetClaw Issues: https://github.com/automateyournetwork/netclaw/issues
