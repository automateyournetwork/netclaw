# Known Issues

## HUD Chat Latency (Critical UX)

**Problem**: The NetClaw Visual HUD chat window has 1-2 minute lag between sending a message and seeing a response. The browser appears frozen during this time.

**Root Cause**: `ui/netclaw-visual/server.js` line ~980 uses `execFileSync` to proxy chat messages to the OpenClaw gateway. This is a synchronous, blocking call that:

1. Spawns `openclaw agent --agent main --session-id agent:main:hud --message <msg>` as a child process
2. Blocks the entire Node.js event loop until the full LLM response is returned (up to 300s timeout)
3. Only then returns the HTTP response to the browser

No streaming, no progress indication, no partial responses.

**Impact**: 
- Browser shows no feedback while waiting
- Node.js event loop is blocked — no WebSocket updates, no gateway status polling
- If the LLM takes >300s, the request times out silently

**Fix**: Replace `execFileSync` with the OpenClaw WebSocket API or HTTP streaming endpoint:
- Connect to `ws://localhost:18789` with the gateway auth token
- Send messages via WebSocket
- Stream partial responses back to the browser via the existing WebSocket broadcast (`broadcastWS`)
- Show typing indicator / streaming text in the chat UI

**Workaround**: Use the TUI for interactive chat — it streams natively:
```bash
docker compose exec -it netclaw-convergence openclaw tui
```

**Files involved**:
- `ui/netclaw-visual/server.js` — `app.post('/api/chat', ...)` handler (~line 953)
- `ui/netclaw-visual/src/main.js` — `sendChatMessage()` function

---

## GitHub MCP Response Format Incompatibility

**Problem**: The GitHub MCP server (`ghcr.io/github/github-mcp-server`) returns content items in a format that OpenClaw's MCP client can't parse, causing `get_file_contents` and potentially other tools to fail with `invalid_union` validation errors.

**Root Cause**: Version mismatch between the GitHub MCP server's response format and OpenClaw's MCP SDK content type validation. The server returns content items that don't match the expected `text`/`image`/`audio`/`resource_link` union type.

**Impact**: Some GitHub MCP tools fail. The agent falls back to `exec`/`curl` as a workaround.

**Fix**: Either pin the GitHub MCP server to a compatible version, or wait for OpenClaw to update its MCP SDK to handle the newer response format.

**Workaround**: The agent can use `exec` with `curl` and the GitHub API directly using `GITHUB_PERSONAL_ACCESS_TOKEN` from the environment.

**Files involved**:
- `config/openclaw.json` — github-mcp server definition
- `docker-compose.yml` — Docker socket mount for github-mcp

---

## Agent Uses exec/curl Instead of MCP Tools

**Problem**: The LLM agent sometimes uses `exec` to run `curl` commands against APIs (Nautobot, GitHub) instead of using the dedicated MCP tools.

**Root Cause**: 
- The LLM takes the path of least resistance — `curl` is a universal tool it knows well
- Old session context may not have the updated SOUL.md rules
- Some MCP tools may fail, causing the agent to fall back to exec

**Mitigation**: Updated `workspace-override/SOUL.md` and `workspace-override/AGENTS.md` with explicit rules:
- "Never use exec, curl, or shell commands to call APIs that have MCP servers"
- "If a tool call fails, report the error — do not retry with exec/curl"
- Rule is stated multiple times in different contexts to reinforce

**Remaining risk**: LLMs don't always follow instructions perfectly. Stronger models (Claude, GPT-4) tend to follow tool-use rules better than smaller models.

---

## Agent Takes Autonomous Actions

**Problem**: The agent proactively scans, audits, reconciles, and modifies Nautobot objects without being asked. In one session it changed device roles from `home_switch` to `access_switch`.

**Root Cause**: The original SOUL.md told the agent to "own the network" and included proactive behaviors like auto-fixing drift, running heartbeat checks, and reconciling Nautobot.

**Fix**: Rewrote `workspace-override/SOUL.md` and `workspace-override/AGENTS.md` to:
- Operate in "development mode" — user-directed only
- No autonomous actions, no proactive monitoring
- All changes require explicit user request and confirmation
- Disabled heartbeat checks

**Note**: These files are in `workspace-override/` (not tracked in git — private). The examples in `workspace-override.example/` still have the full autonomous personality for reference.

---

## Context Window Exhaustion

**Problem**: Long sessions hit the LLM's context window limit (96% usage observed), causing OpenClaw to attempt "compaction" and eventually timeout.

**Root Cause**: 
- Agent dumps large API responses (full config contexts, interface lists) into the conversation
- exec/curl responses include raw JSON that consumes many tokens
- No summarization or truncation of tool results

**Mitigation**: 
- Start new sessions frequently instead of continuing long conversations
- The TOON serialization in nautobot-mcp-v2 helps reduce token usage for tabular data
- Updated SOUL.md tells agent to be concise and not volunteer extra work

**Future fix**: Implement response truncation in MCP tools — cap large responses and offer pagination.

---

## OpenClaw Heartbeat Still Runs

**Problem**: Even with `HEARTBEAT.md` set to "disabled, reply HEARTBEAT_OK", OpenClaw's built-in heartbeat scheduler still triggers periodic sessions that consume tokens.

**Root Cause**: OpenClaw has a framework-level heartbeat (`[heartbeat] started` in logs with `intervalMs: 1800000` — every 30 minutes). The HEARTBEAT.md content controls what the agent does during heartbeat, but doesn't prevent the heartbeat session from being created.

**Workaround**: The updated HEARTBEAT.md tells the agent to immediately reply HEARTBEAT_OK and do nothing, minimizing token waste.

**Future fix**: OpenClaw may support disabling heartbeat entirely via `openclaw.json` configuration.


---

## Alert Delegation to guardian-claw Removed (needs proper re-implementation)

**Problem**: The alert-triage hook no longer delegates investigations to the
`guardian-claw` iN2N member. The border investigates directly on `claude-sonnet-5`,
which is expensive (~$0.73 input-token cost per alert due to the 243K MCP tool
schema bloat).

**Why it was removed**: The old hook `messageTemplate` said "Route this alert
investigation to the guardian-claw member via n2n_route, do NOT investigate
directly." That instruction, arriving inside an untrusted webhook payload, was
correctly flagged by Sonnet as prompt injection and refused — which broke the
whole pipeline. To get investigations working again, the routing instruction was
stripped from the payload (see docs/blog/2026-07-21-alert-investigation-debugging.md).

**The right fix**: Move the delegation instruction into the **alert-triage skill
file** (trusted content the model honors), not the webhook payload (untrusted).
Same pattern already used for Discord delivery (Step 7) and Guardian events
(Step 8). The skill should instruct: "delegate this investigation to guardian-claw
via n2n_route" — Sonnet will follow a skill directive because it is trusted, not
injected webhook content.

**Benefits of restoring delegation**:
- guardian-claw runs on cheap kimi-k3 (free) instead of the border on Sonnet 5
- guardian-claw has a scoped MCP config (observability servers only), so it does
  NOT carry the 243K tool-schema bloat — solves both the cost AND context-overflow
  problems at once
- The border's routing turn becomes small and cheap

**Status**: Flagged. Interim state works (direct investigation on Sonnet 5), but
the cost-saving delegation architecture should be restored the trusted way.
