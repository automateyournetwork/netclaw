---
inclusion: auto
---

# CRITICAL: Heartbeat is DISABLED on this deployment

## Why
The OpenClaw heartbeat feature sends the ENTIRE conversation context (200K+ tokens)
to the model every 5 minutes just to get "HEARTBEAT_OK" back. On Anthropic Sonnet 5
at $3/M input tokens, this costs ~$0.70 per heartbeat × 12/hour = **$8.40/hour doing
nothing**. This burned $100 in a few hours before it was caught.

## How it's disabled
All `HEARTBEAT.md` files in this project are set to empty/comments only:
- `workspace/HEARTBEAT.md` — empty (no tasks)
- `workspace/personality/HEARTBEAT.md` — empty (no tasks)
- `~/.openclaw/workspace/HEARTBEAT.md` — empty (no tasks)

## Rules for this deployment
1. **NEVER add tasks to any HEARTBEAT.md file** — it will burn through the Anthropic budget
2. **Alert-driven monitoring is the pattern** — the `netclaw-alert-receiver` service handles
   proactive monitoring via Prometheus Alertmanager webhooks (zero idle cost)
3. If upstream pulls reintroduce heartbeat tasks, immediately clear them
4. The border brain model (`anthropic/claude-sonnet-5`) is ONLY used for:
   - Interactive user conversations (TUI, Discord)
   - n2n federation routing decisions
   - NOT for heartbeat polling

## Cost model
| Activity | Model | Cost |
|----------|-------|------|
| Interactive (user asks something) | anthropic/claude-sonnet-5 | Pay per use |
| Alert triage (autonomous hook) | anthropic/claude-haiku-3.5 | ~$0.01-0.05/alert |
| iN2N members | moonshot/kimi-k3 or ollama/deepseek-v4-flash:cloud | Free or cheap |
| Heartbeat | **DISABLED** | $0 |
