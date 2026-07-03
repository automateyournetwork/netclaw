# Implementation Plan: Full NetClaw Voice Integration

**Branch**: `043-full-voice-integration` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

## Summary

Voice is a **universal I/O channel** to Claude, who already has access to ALL 40+ MCPs and 100+ skills. We're not building voice handlers for each MCP - we're building a voice interface that passes speech to Claude and speaks the response.

```
Phone → Twilio STT → Claude (ALL tools) → Speech Formatter → Twilio TTS → Phone
```

## Technical Context

**Language/Version**: Python 3.10+ (webhook server)
**Primary Dependencies**: FastMCP, Twilio SDK, Anthropic SDK, httpx
**Storage**: Memory MCP (conversation context per caller ID)
**Target Platform**: Linux server + Twilio cloud
**Project Type**: Webhook service extension

## Architecture

### What We're Building

1. **Voice Webhook** (extend existing): Accept calls, handle STT/TTS
2. **Speech Formatter**: Format any MCP response for natural speech
3. **Context Manager**: Per-caller context in Memory MCP
4. **Alert Triggers**: Proactive outbound call configuration

### What We're NOT Building

- ❌ Voice handler for pyATS
- ❌ Voice handler for CML
- ❌ Voice handler for PagerDuty
- ❌ Voice handler for IP Fabric
- ❌ Voice handler for [any other MCP]

Claude already has all these tools. We just connect voice I/O to Claude.

## Project Structure

```text
mcp-servers/twilio-voice-mcp/
├── webhook_server.py      # EXTEND: Add universal voice → Claude → voice flow
├── speech_formatter.py    # NEW: Format any response for speech
├── context_manager.py     # NEW: Per-caller context via Memory MCP
└── alert_triggers.py      # NEW: Proactive outbound call config

~/.openclaw/voice/
├── whitelist.json         # Authorized callers
└── alert_triggers.json    # Alert trigger config
```

## Key Design Decisions

1. **Universal tool access**: Claude receives transcribed speech and decides which tools to use
2. **Generic speech formatting**: Formatter handles ANY MCP response, not just known formats
3. **Context via Memory MCP**: Conversation state stored per caller ID
4. **No per-MCP skills needed**: Claude already knows all tools

## Constitution Check

| Principle | Status |
|-----------|--------|
| V. MCP-Native Integration | PASS - Uses existing MCPs |
| VII. Skill Modularity | PASS - Voice is one skill, composes with all MCPs |
| IX. Security by Default | PASS - Caller whitelist, no secrets spoken |

## Complexity Tracking

This design is SIMPLER than the original plan:
- Original: 52 tasks with per-MCP handlers
- Revised: ~15 tasks with universal architecture
