# Upgrading to DefenseClaw

This guide helps existing NetClaw users enable DefenseClaw enterprise security.

## Quick Upgrade

```bash
./scripts/defenseclaw-enable.sh
```

The script installs a pinned DefenseClaw release (default `1.0.4`) after verifying its
installer checksum, configures the OpenClaw guardrail in observe mode, and prints the few
steps it leaves to you (custom providers, starting the sidecar, restarting the gateway).
These steps match what worked with DefenseClaw 1.0.4 and OpenClaw 2026.10.9 on NetClaw's
qualification VM; observe-mode production qualification (spec 167) passed for standalone, federated and denied-scope runs with ollama-cloud/minimax-m3; action mode, other providers/models, Hermes and macOS/WSL are not qualified.

---

## What Changes

### Before (Hobby Mode)
- NetClaw runs without security layer
- Full host access
- No sandbox isolation
- No audit logging

### After (DefenseClaw)
- Model traffic routed through the DefenseClaw guardrail proxy by its OpenClaw plugin
- Component scanning before execution
- Runtime guardrails for LLM and tool calls
- SQLite audit database with optional SIEM export
- Optional: OpenShell container sandbox (`INSTALL_OPENSHELL=1`). An iN2N Risk's
  production sandbox is systemd confinement of its members, not OpenShell.

---

## Prerequisites

Before upgrading, ensure you have:

| Requirement | Minimum Version | Check Command |
|-------------|-----------------|---------------|
| Python | 3.10+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| curl and sha256sum (or shasum) | any | `curl --version` |
| Docker | Running (OpenShell only) | `docker info` |

The OpenClaw gateway token must be a literal string. If `gateway.auth.token` in
`~/.openclaw/openclaw.json` is a SecretRef object, DefenseClaw 1.0.x `init` fails with
`gateway defaults: str expected, not dict`; the script detects this and stops before
installing anything. See [DEFENSECLAW.md](DEFENSECLAW.md#known-limitation-secretref-gateway-token).

---

## Step-by-Step Upgrade

### 1. Run the Enable Script

```bash
cd /path/to/netclaw
./scripts/defenseclaw-enable.sh
```

The script will:
1. Check prerequisites, including the gateway token check above
2. Back up `~/.openclaw/config/openclaw.json` and the gateway config `~/.openclaw/openclaw.json`
3. Download `install.sh` and `checksums.txt` for the pinned DefenseClaw release, verify
   the installer's SHA-256 (it refuses to run on a mismatch), and run
   `install.sh --yes --connector openclaw`
4. Run `defenseclaw init --connector openclaw --non-interactive --yes --scanner-mode local`
5. Run `defenseclaw setup guardrail --connector openclaw --mode observe --scanner-mode local --detection-strategy regex_only --non-interactive --no-restart`,
   which installs the DefenseClaw OpenClaw plugin
6. Set `security.mode: "defenseclaw"` in `~/.openclaw/config/openclaw.json`

Pick another release with `DEFENSECLAW_VERSION=<tag>`. Options are listed in
[DEFENSECLAW.md](DEFENSECLAW.md#existing-installation).

### 2. Register unknown model providers

The guardrail proxy forwards only to provider domains it knows. A provider it does not
know is blocked fail-closed, and OpenClaw receives a 403. For Ollama Cloud, for example,
register it with DefenseClaw's provider command (`custom-providers.json` is derived; do not
edit it):

```bash
defenseclaw setup provider add --name ollama-cloud --domain ollama.com \
  --env-key OLLAMA_API_KEY --profile-id ollama-cloud:default --base-provider-type ollama
defenseclaw setup provider list
```

### 3. Start the sidecar and load the plugin

```bash
# On an iN2N Risk host: durable defenseclaw-sidecar.service (proxy on 127.0.0.1:4000)
python3 scripts/in2n-services.py generate
python3 scripts/in2n-services.py enable
# Elsewhere: run defenseclaw-gateway under your service manager.

# Load the DefenseClaw plugin
openclaw gateway restart
```

### 4. Verify Installation

```bash
# Check DefenseClaw CLI
defenseclaw --version

# Check the plugin and the sidecar
ls ~/.openclaw/extensions/defenseclaw
systemctl --user status defenseclaw-sidecar.service   # Risk hosts

# Check configuration
grep -A2 security ~/.openclaw/config/openclaw.json
```

Send one model turn and confirm it appears in DefenseClaw's audit database.

### 5. (Optional) Enable Action Mode

By default, guardrails run in **observe** mode (logging only). To enable blocking:

```bash
defenseclaw setup guardrail --connector openclaw --mode action --scanner-mode local \
  --detection-strategy regex_only --non-interactive --no-restart
openclaw gateway restart
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
| `~/.defenseclaw/custom-providers.json` | Extra provider domains (derived from `defenseclaw setup provider`) |
| `~/.openclaw/extensions/defenseclaw` | DefenseClaw OpenClaw plugin |
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
node --version     # Need 20+
docker info        # Only for INSTALL_OPENSHELL=1
```

### "gateway defaults: str expected, not dict"

`defenseclaw init` cannot read a SecretRef gateway token. See the prerequisites above.

### Model calls return 403

The provider's domain is not in DefenseClaw's registry. Register it with
`defenseclaw setup provider add` (step 2) and restart the sidecar.

### Gateway won't start

Check for port conflicts:
```bash
lsof -i :4000  # Guardrail proxy port
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
