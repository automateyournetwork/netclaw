---
name: token-tracker
description: "Track and display token consumption and cost for every NetClaw interaction."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Skill: Token Tracker

## Purpose

Track and display token consumption and cost for every NetClaw interaction.
Serialize MCP server responses in TOON format to reduce token usage by
40-60% on tabular network data.

## Tools Used

This skill uses the `netclaw_tokens` shared library (`src/netclaw_tokens/`):

| Module | Function | Purpose |
|--------|----------|---------|
| counter.py | count_tokens() | Count tokens via Anthropic API (fallback: len/4 estimate) |
| counter.py | count_message_tokens() | Count tokens for full message arrays |
| cost_calculator.py | calculate_cost() | Calculate USD cost with model-aware pricing |
| cost_calculator.py | get_pricing() | Look up model pricing (with env var override) |
| toon_serializer.py | serialize_response() | Serialize data to TOON with JSON fallback |
| session_ledger.py | SessionLedger | Cumulative session tracking with per-tool breakdown |
| footer.py | format_footer() | Format mandatory token/cost footer |
| toon_wrapper.py | wrap_json_response() | Convert JSON responses to TOON (for community servers) |

## Workflow Steps

1. **On every interaction**: Count input/output tokens using `count_tokens()` or `count_message_tokens()`
2. **Calculate cost**: Use `calculate_cost()` with the active model (Opus/Sonnet/Haiku)
3. **Record in ledger**: Call `session_ledger.record()` with tool name, token count, cost, and TOON savings
4. **Format footer**: Use `format_footer()` to produce the mandatory token/cost display line
5. **Display footer**: Append footer to every response — no exceptions

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | API key for Anthropic token counting (already used by NetClaw) |
| `NETCLAW_TOKEN_PRICING_OVERRIDE` | No | JSON string to override default model pricing |

## Model Pricing (defaults)

| Model | Input (per 1M) | Output (per 1M) |
|-------|-----------------|------------------|
| Claude Opus 4.6 | $5.00 | $25.00 |
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| Claude Haiku 4.5 | $1.00 | $5.00 |

Prompt caching discount: 90% off cached input tokens.

## Example Usage

```python
from netclaw_tokens import count_tokens, calculate_cost, format_footer, SessionLedger
from netclaw_tokens.toon_serializer import serialize_response

# Count tokens
tc = count_tokens("show BGP peers on router R1")

# Calculate cost
cost = calculate_cost(tc.input_tokens, 382, model="claude-opus-4-6")

# Serialize MCP response in TOON format
data = [{"peer": "10.0.0.1", "state": "Established", "as": 65001}]
response = serialize_response(data)

# Track in session ledger
ledger = SessionLedger()
ledger.record("pyats_show_bgp", tc, cost, toon_savings=response.savings_tokens)

# Format footer
footer = format_footer(tc, cost, toon_savings=response.savings_tokens,
                       session_summary=ledger.get_summary())
# Output: Tokens: 8 in / 382 out / 390 total | Cost: $0.0096 | TOON saved: 15 tokens ($0.0001) | Session: 390 tokens ($0.01)
```

## Session Commands

- **"show session token usage"** — Returns full session summary with per-tool breakdown
- **"show token breakdown by tool"** — Returns ranked per-tool token consumption table
- **"compare token usage with and without TOON"** — Shows TOON savings analysis

## GAIT Integration

Token summaries are automatically included in GAIT session logs via
`SessionLedger.get_gait_summary()`, providing an immutable audit trail
of token consumption per session.
