# Runbook — Wire the Nautobot Intent-Reconcile Webhook to NetClaw

How to make a change in Nautobot flow to NetClaw, get compared against the live
device, and land as a human-approved proposal in Discord. This is the concrete
setup + test procedure (the design rationale lives in
`docs/architecture/intent-reconcile.md`).

> **Scope / safety:** interface changes on **switches only**. Firewalls are never
> touched. Nothing is applied without an explicit `approve <id>` in Discord.

---

## The pipeline (what talks to what)

```
Nautobot (192.168.3.253)
  │  interface create/update/delete  → Webhook (HMAC-SHA512 signed)
  ▼
Alert Receiver  http://192.168.3.252:8099/nautobot-webhook
  │  1. verify X-Hook-Signature (HMAC, shared secret)
  │  2. resolve device in Nautobot (depth=1) → gate on role == switch
  │  3. build reconcile prompt
  ▼  POST /hooks/reconcile  (Bearer OPENCLAW_HOOK_TOKEN)
OpenClaw Gateway  127.0.0.1:18789
  │  hook rule "reconcile" → action: agent, message = {{annotations.reconcile_prompt}}
  ▼
NetClaw agent  (intent-reconcile skill)
  │  read Nautobot intent + live device (pyATS)  → diff intent vs actual
  ▼  openclaw message send --channel discord
Discord  #Nautobot-Alerts   → proposal: `approve <id>` / `deny <id>`
```

Every hop must be configured. A break at any hop = no proposal.

---

## Prerequisites

- Alert Receiver running (`netclaw-alert-receiver` systemd service) and reachable
  from Nautobot on `192.168.3.252:8099`.
- OpenClaw gateway running with hooks enabled (`127.0.0.1:18789`).
- Nautobot reachable with an API token (`NAUTOBOT_TOKEN`).
- pyATS able to reach the switches over SSH (see step 4 — the old Catalyst 3850s
  need legacy algorithms).

---

## Step 1 — Alert Receiver config (`scripts/alert-receiver/.env`)

This file is gitignored. Set:

```ini
# Turn the reconcile pipeline on (default is off)
RECONCILE_ENABLED=true

# Shared HMAC secret — MUST be non-empty and MUST match the Nautobot webhook.
# An empty secret makes the receiver reject every webhook ("signature").
NAUTOBOT_WEBHOOK_SECRET=<64-hex, e.g. `openssl rand -hex 32`>

# What the agent is allowed to act on (defaults shown)
RECONCILE_ALLOWED_MODELS=interface
RECONCILE_ALLOWED_ROLES=switch

# Where proposals go (defaults to DISCORD_ALERT_CHANNEL_ID if unset)
RECONCILE_CHANNEL_ID=1426234100339048701

# Gateway hook endpoint + bearer token (must match openclaw.json hooks.token)
OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789
OPENCLAW_HOOK_TOKEN=<hooks.token from openclaw.json>

# Nautobot API (used to resolve device role/platform)
NAUTOBOT_TOKEN=<token>
```

Gotcha we hit: `NAUTOBOT_WEBHOOK_SECRET` was **empty**, so every delivery was
rejected with `{"status":"rejected","reason":"signature"}`. Generate one and use
the **same** value in Nautobot (step 3).

## Step 2 — Gateway hook rule (`~/.openclaw/openclaw.json`)

Under `hooks.rules`, a rule maps the `reconcile` path to an agent session:

```json
{
  "match": { "path": "reconcile" },
  "action": "agent",
  "wakeMode": "now",
  "name": "NetClaw Intent Reconcile",
  "sessionKey": "hook:reconcile:{{model}}:{{device.name}}",
  "messageTemplate": "{{annotations.reconcile_prompt}}"
}
```

- `hooks.enabled: true` and `hooks.token` must be set; the receiver sends that
  token as `Authorization: Bearer …`.
- `messageTemplate` pulls `annotations.reconcile_prompt` from the receiver's POST
  body — that is the instruction the agent runs.

## Step 3 — Create the Nautobot webhook

Idempotent helper (reads the secret from the receiver `.env`, nothing hard-coded):

```bash
.venv/bin/python scripts/alert-receiver/create_webhook.py
```

Or create it manually (REST / Admin → Extensibility → Webhooks) with:

| Field | Value |
|-------|-------|
| Name | `netclaw-intent-reconcile` |
| Content type(s) | `dcim \| interface` |
| Enabled | ✔ |
| Type create / update / delete | ✔ ✔ ✔ |
| URL | `http://192.168.3.252:8099/nautobot-webhook` |
| HTTP method | `POST` |
| HTTP content type | `application/json` |
| Secret | **same** value as `NAUTOBOT_WEBHOOK_SECRET` |
| SSL verification | off (receiver is plain HTTP) |

Verify it exists: `GET /api/extras/webhooks/?name=netclaw-intent-reconcile`.

## Step 4 — Device access for pyATS (required for a *real* proposal)

The agent reads the live switch to diff intent vs actual. The home Catalyst 3850s
run old IOS-XE and reject modern SSH twice (key exchange, then host key). This is
already handled in `~/.ssh/config` and the generated testbed, but if you rebuild:

```
# ~/.ssh/config
Host 192.168.3.2 192.168.3.3 HomeSwitch01 HomeSwitch02
    KexAlgorithms +diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1
    HostKeyAlgorithms +ssh-rsa
    PubkeyAcceptedAlgorithms +ssh-rsa
```

The testbed generator (`scripts/generate-testbed-from-nautobot.py`) emits the
matching `ssh_options` for IOS/IOS-XE devices, so `testbed/testbed.yaml` carries
it too. Confirm SSH negotiates: `ssh cisco@192.168.3.2` should reach a password
prompt (not "no matching key exchange / host key").

## Step 5 — Restart the receiver

```bash
sudo systemctl restart netclaw-alert-receiver
systemctl is-active netclaw-alert-receiver
```

---

## Step 6 — Test end to end

1. Make a change on a switch interface in Nautobot (a safe, unused port is ideal,
   e.g. `HomeSwitch01 Gi1/0/4`). Any create/update/delete fires the webhook.
2. Watch the receiver:
   ```bash
   sudo journalctl -u netclaw-alert-receiver -f
   ```
   A healthy run shows:
   ```
   POST /nautobot-webhook 200                       ← delivered
   GET .../devices/?name=HomeSwitch01&depth=1 200   ← role resolves
   POST http://127.0.0.1:18789/hooks/reconcile 200  ← handed to NetClaw
   Reconcile proposal triggered: interface updated on HomeSwitch01
   ```
3. Within a minute or two, a proposal (or a no-op notice) appears in the Discord
   alerts channel. Reply `approve <id>` or `deny <id>`.

Quick endpoint sanity check (no Nautobot needed):
```bash
curl -s -X POST http://192.168.3.252:8099/nautobot-webhook -d '{}'
# reconcile off      → {"status":"disabled"}
# reconcile on, unsigned → {"status":"rejected","reason":"signature"}
```

---

## Troubleshooting (symptoms we actually hit)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `{"status":"disabled"}` | `RECONCILE_ENABLED` not true | set it, restart receiver |
| `{"status":"rejected","reason":"signature"}` | secret empty or mismatched | set the **same** secret on both sides |
| `Nautobot change on X (role=) not in allowed roles — skipping` | device query missing `depth=1`, so role had no name | fixed in `server.py` (adds `depth=1` + name/display fallback) |
| Device skipped though it's a switch | role doesn't contain "switch" | check Nautobot role, or widen `RECONCILE_ALLOWED_ROLES` |
| Receiver logs 200 to `/hooks/reconcile` but no Discord post | gateway hook/agent didn't post | check `journalctl --user -u openclaw-gateway`; confirm the `reconcile` hook rule + `hooks.token` |
| Proposal is a **no-op** on a real drift | old behavior diffed webhook prechange/postchange | fixed: skill + prompt now diff **intent vs live device** |
| Real proposal can't read the device | pyATS MCP not up, or SSH rejected | check gateway MCP startup ("Connection closed"); verify `ssh cisco@192.168.3.2` (step 4) |
| Admin-state drift not flagged (port up, Nautobot `enabled: false`) | admin state not checked | fixed: `enabled → shutdown/no shutdown` is now a first-class diff field |

Gateway MCP startup: if a reconcile session logs
`failed to start server "pyats-mcp"/"nautobot-mcp" … Connection closed`, the agent
can't read intent or the device and will produce a weak/no proposal. Investigate
those MCP servers before relying on real reconciles.

---

## Turn it off / roll back

- **Pause quickly:** `RECONCILE_ENABLED=false` in `scripts/alert-receiver/.env`,
  then `sudo systemctl restart netclaw-alert-receiver`.
- **Or disable at source:** set the Nautobot webhook `enabled: false` (or delete
  it).
- Either way, nothing was ever applied without an `approve <id>`.

## Files involved

| File | Role |
|------|------|
| `scripts/alert-receiver/server.py` | `/nautobot-webhook` endpoint, HMAC verify, role gate, prompt, POST to gateway |
| `scripts/alert-receiver/.env` | reconcile flags + shared secret (gitignored) |
| `scripts/alert-receiver/create_webhook.py` | idempotent Nautobot webhook creator |
| `~/.openclaw/openclaw.json` | `hooks.rules` → `reconcile` agent mapping |
| `workspace/skills/intent-reconcile/SKILL.md` | agent behavior: intent-vs-actual diff, propose/approve/apply |
| `~/.ssh/config` + `testbed/testbed.yaml` | legacy SSH so pyATS can read the switches |
