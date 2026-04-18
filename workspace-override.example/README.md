# Workspace Override Examples

These are the default NetClaw workspace files. To customize NetClaw for your environment:

```bash
# Copy the examples to the override directory
cp -r workspace-override.example/* workspace-override/

# Also copy your credentials
cp .env.example workspace-override/.env
```

Then edit the files in `workspace-override/` to match your network:

| File | What to Customize |
|------|-------------------|
| `USER.md` | Your name, role, timezone, network details, preferences |
| `TOOLS.md` | Device IPs, subnets, platform credentials references, Slack/WebEx channels |
| `IDENTITY.md` | NetClaw's personality and role description |
| `testbed.yaml` | pyATS device inventory (SSH-accessible devices) |
| `.env` | API keys, passwords, tokens (never committed to git) |
| `CLAUDE.md` | Development guidelines (optional) |

Files you probably don't need to change:
- `SOUL.md` — Core CCIE expertise and rules
- `SOUL-SKILLS.md` — Skill procedures reference
- `SOUL-EXPERTISE.md` — Technical knowledge base
- `AGENTS.md` — Operating instructions and safety rules
- `HEARTBEAT.md` — Periodic health check behavior

The Docker container mounts `workspace-override/` read-only. Any file present there overrides the default baked into the image. Files you don't override use the built-in defaults automatically.
