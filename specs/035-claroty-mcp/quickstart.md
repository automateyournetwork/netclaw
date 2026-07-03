# Quickstart — Claroty xDome MCP Server

## Prerequisites

- An active Claroty xDome tenant.
- A Bearer token issued from xDome Admin Settings → User Management with read + write scopes for assets, alerts, vulnerabilities, and user actions.
- NetClaw checked out at `R:\netclaw` (or your repo path).

## 1. Install

```bash
cd mcp-servers/claroty-mcp/
pip install -r requirements.txt
```

Or simply re-run `./scripts/install.sh` from the repo root — it picks up the new install step automatically.

## 2. Configure

Add to `.env` (or copy from `.env.example`):

```bash
CLAROTY_API_URL=https://api.medigate.io
CLAROTY_API_TOKEN=<your-bearer-token>
CLAROTY_VERIFY_SSL=true
CLAROTY_TIMEOUT=30
CLAROTY_RATE_LIMIT_PER_MIN=2000

# Lab mode — accept any well-formed CHG\d+ CR without ServiceNow verification.
# DO NOT set in production.
NETCLAW_LAB_MODE=true
```

The MCP server is registered in `config/openclaw.json` under `mcpServers.claroty-mcp`.

## 3. Standalone smoke test

```bash
python3 -u mcp-servers/claroty-mcp/claroty_mcp_server.py
```

You should see:

```
Claroty MCP starting — api_url=https://api.medigate.io verify_ssl=True timeout=30s rate=2000/min
Claroty MCP server ready — 21 tools (15 read + 6 ITSM-gated write)
```

If you see `ERROR: Missing required environment variables: CLAROTY_API_TOKEN` — fix the env first.

## 4. End-to-end smoke (via the agent)

Start the gateway and TUI as usual:

```bash
openclaw gateway run   # terminal 1
openclaw tui           # terminal 2
```

Then run these prompts in order.

### Smoke #1 — Read path

```
"List the first 10 OT devices and show their Purdue levels"
```

Expect a GCF-encoded device table with id, name, IP, vendor, purdue_level fields. If you get an error, check the token and SSL flag.

### Smoke #2 — Topology

```
"Show me the communication map for device <id>"
```

Expect edges in the response, suitable for downstream Canvas A2UI / draw.io rendering by the `claroty-ot-topology` skill.

### Smoke #3 — ITSM gate (rejection paths)

```
"Acknowledge alert <id> as resolved"     (no cr_number)
"Acknowledge alert <id> as resolved under ABC123"   (bad format)
```

Both must return `{"itsm_gate": {"valid": false, ...}, "applied": false}` and **must not** make any POST to xDome.

### Smoke #4 — ITSM gate (lab-mode accept)

With `NETCLAW_LAB_MODE=true`:

```
"Acknowledge alert <id> as resolved under CHG0012345"
```

Expect:

```json
{
  "itsm_gate": {
    "valid": true,
    "state": "lab_mode",
    "cr_number": "CHG0012345",
    ...
  },
  "applied": true,
  "response": { ... xDome response ... }
}
```

### Smoke #5 — Rate-limit guard

From a script:

```python
import asyncio
# fire 50 list_devices calls concurrently
```

Confirm none of them surface a 429 to the user. Latency on the last few may be elevated by the sliding-window sleep — that is expected and correct.

### Smoke #6 — HUD

Open `http://localhost:3000`. Find the **Claroty xDome** node under the Security category. Click "Edit ENV" and confirm the 5 CLAROTY_* keys appear.

### Smoke #7 — Regression

```
"Run a health check on <existing pyATS device>"
```

The existing `pyats-health-check` skill must continue to pass — verifies Principle XV.

## 5. Constitution checklist

Tick every box in `specs/035-claroty-mcp/checklists/requirements.md` before opening the PR.

## 6. Blog post

Per Principle XVII, draft a WordPress blog post summarising the milestone. Present it to John for review before publishing. If the WordPress MCP is unavailable, save the draft as `docs/blog/2026-06-08-claroty-mcp.md` and ping John to publish manually.
