# Debugging the Alert Investigation Pipeline — A Cascade of Config Failures

**Date:** 2026-07-21
**Author:** Byrn Baker (with NetClaw/Kiro assist)
**Context:** Network Guardian alert-driven investigation stopped working entirely.
This is the post-mortem of what broke and why, so we don't lose the context.

## Symptom

Prometheus alerts (`PfSenseInternalHostExcessiveBlocks`, `WifiHighTxRetries24GHz`,
etc.) were firing and reaching the `netclaw-alert-receiver` service correctly, but
**no investigation ever ran**. The receiver logged "Triggered NetClaw
investigation" with a `200 OK` from the gateway, yet no triage report appeared in
Discord and no investigation session did any work.

The frustrating part: this used to work. Dozens of historical `hook:alert:*`
sessions in `sessions.json` proved it. Something we changed during a series of
model-swapping and session-cleanup operations broke the whole chain.

## The Debugging Path

The receiver side was never the problem. It did everything right: received the
webhook, resolved the device, scoped skills (9/203, ~94% index savings), POSTed to
`/hooks/alert` → got `200 OK`, posted a Guardian event, suppressed Discord noise.

The failure was entirely inside the **OpenClaw gateway's hook → session pipeline**.
The `200 OK` was misleading — it meant "webhook accepted," not "investigation ran."

The breakthrough was reading the gateway's own logs (`journalctl --user -u
openclaw-gateway`) instead of the receiver logs. That exposed a **cascade of
config failures**, each one masking the next.

## Root Cause #1 — Model allowlist excluded Anthropic

```
[hooks] hook agent run returned non-ok status status=error
model=anthropic/claude-haiku-3.5
summary=payload.model rejected by agents.defaults.models allowlist:
not in [moonshot/kimi-k3, ollama/deepseek-v4-flash:cloud, ollama/deepseek-v4-pro:cloud]
```

`agents.defaults.models` is an **allowlist** gating which models the agent may use.
It only contained Moonshot + Ollama. Switching the brain/hook to Anthropic caused
every Anthropic-model run to be silently rejected.

**Fix:** Added `anthropic/*` and `ollama/*` wildcards. Final allowlist:
`moonshot/kimi-k3`, `anthropic/*`, `ollama/*`.

## Root Cause #2 — Anthropic provider had zero models registered

```
FailoverError: Unknown model: anthropic/claude-haiku-3.5.
Found agents.defaults.models[...], but no matching models.providers["anthropic"].models[] entry.
```

Two separate concepts, both required:
- `agents.defaults.models` — allowlist (may this model be used?)
- `models.providers.<name>.models[]` — registration (does it exist / how to route?)

The `anthropic` provider was `{}`. **Fix:** registered it with
`api: anthropic-messages`, `baseUrl: https://api.anthropic.com`,
`apiKey: ${ANTHROPIC_API_KEY}`, and a `models[]` array.

## Root Cause #3 — Wrong provider `api` value

`api: "anthropic"` failed schema validation. **Fix:** correct value is
`anthropic-messages`.

## Root Cause #4 — Non-existent model ID

```
not_found_error: model: claude-haiku-3.5
```

`claude-haiku-3.5` is not a real Anthropic model ID — we guessed. Querying the API
settled it:
```bash
curl -s https://api.anthropic.com/v1/models \
  -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01"
```
Real IDs included `claude-sonnet-5`, `claude-opus-4-8`, and the actual current
Haiku: **`claude-haiku-4-5-20251001`**. **Lesson: never guess model IDs — query
`/v1/models`.**

## Root Cause #5 — Context overflow (243K tokens)

```
Context overflow: prompt too long: 243886 tokens > 200000 maximum
model=claude-haiku-4-5-20251001
```

Even a *fresh* hook session was 243,886 tokens before doing any work — the bloat is
**MCP tool schemas** (800+ tools across nautobot, pfsense, cml, grafana,
prometheus, n2n, rag, etc.). Skill scoping shrinks the skill index, NOT the tool
catalog. Haiku's 200K can't hold it.

**Interim fix:** switched the alert hook to `claude-sonnet-5` (1M context).

## Contributing Factors (self-inflicted)

- **`kill -HUP` / `pkill` vs systemd:** the gateway is `openclaw-gateway.service`
  (systemd user unit). Manual kills created conflicting instances. **Always
  `systemctl --user restart openclaw-gateway`.**
- **Session model persistence:** sessions bake in their model at creation. A stale
  `agent:main:main` session stuck on kimi-k3 kept absorbing alert traffic and
  replying `HEARTBEAT_OK`. Had to purge it from `sessions.json`.
- **Same-fingerprint reuse:** firing the same test alert
  (`fingerprint: test-excessive-blocks-004`) reused the same bloated session.

## The Fix Checklist (for next time)

1. **Read the gateway log, not the receiver log:**
   `journalctl --user -u openclaw-gateway --since "5 min ago" | grep -iE "hook|error"`
2. Check the model allowlist includes the provider: `agents.defaults.models`
3. Check the provider is registered with models: `models.providers.<name>.models[]`
4. Verify the `api` field is a valid enum value (`anthropic-messages`, not `anthropic`)
5. Verify the model ID is real: `curl https://api.anthropic.com/v1/models`
6. Check context size vs model limit (MCP tool schemas are the hidden bloat)
7. Always restart via systemd, never `kill -HUP`
8. Purge stale sessions from `sessions.json` if stuck on the wrong model

## Follow-up Work (post-debugging)

### RESOLVED — Prompt-injection detection defeating the pipeline

The alert payload carried imperative instructions Sonnet correctly flagged as
injection from an untrusted webhook:
- `messageTemplate`: "Route ... via n2n_route, do NOT investigate directly"
- `build_investigation_prompt()`: "POST to <GUARDIAN_URL>/api/events" and
  "run via exec: openclaw message send --channel discord ..."

**Fix applied:** moved all delivery/routing into the *trusted skill files* and
stripped them from the untrusted payload:
- Hook `messageTemplate` → "A monitoring alert has fired... Follow the alert-triage
  skill to investigate and report. Alert details: {{...}}"
- `build_investigation_prompt()` no longer emits `POST to <url>` or `exec: openclaw
  message send` — it says "deliver per the alert-triage skill's delivery steps."
  The skill owns Discord (Step 7, `${DISCORD_ALERT_CHANNEL_ID}`) and Guardian
  (Step 8) as trusted content.

Principle: **facts in the payload, actions in the skill.** Untrusted webhook
content must never carry `exec`, external-URL POSTs, or "route to peer" directives.

### DEFERRED — 243K MCP tool-schema bloat

Hook mappings do **not** support per-hook tool scoping — `toolsAllow` /
`lightContext` are not valid hook-mapping keys (confirmed against the schema).
Valid mapping fields: `match, action, agentId, wakeMode, name, sessionKey,
messageTemplate, deliver, channel, to, model, thinking, timeoutSeconds, transform`.

Every session loads all 800+ MCP tools (~243K tokens) regardless of skill scoping.

Options for a proper fix (each a real architectural change):
1. **Dedicated scoped `hooks` agent** — route alert hooks to `agentId: "hooks"`
   with a minimal MCP server set. Requires defining that agent.
2. **Revive guardian-claw delegation** — the iN2N member already has a scoped
   config on cheap kimi-k3. Now that the payload injection issue is fixed,
   `n2n_route` delegation could work again.

**Interim state:** alert hook on `claude-sonnet-5` (1M context) — works, ~$0.73
input-token cost per alert. Revisit with option 1 or 2 for cost reduction.

## Working End State

- Alert fires → receiver → gateway hook → **fresh Sonnet 5 session** (1M context)
- Investigation runs the real pfSense MCP procedure (ARP, DHCP, firewall log,
  blocked-traffic analysis) — verified end-to-end
- Guardian dashboard event posted; Discord noise suppressed for noisy alerts
