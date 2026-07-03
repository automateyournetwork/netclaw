# Implementation Tasks: Full NetClaw Voice Integration

**Feature**: 043-full-voice-integration
**Revised**: 2026-06-26
**Total Tasks**: 15

## Architecture Principle

Voice is just I/O. Claude already has ALL 40+ MCPs and 100+ skills. We're building:
1. Speech-to-text input
2. Pass to Claude (who has all tools)
3. Format response for speech
4. Text-to-speech output

**NOT building**: Per-MCP voice handlers. Claude handles tool selection.

---

## Phase 1: Setup (2 tasks)

- [x] T001 Create voice config directory and whitelist template at ~/.openclaw/voice/whitelist.json
- [x] T002 Create alert triggers config template at ~/.openclaw/voice/alert_triggers.json

---

## Phase 2: Speech Formatter (3 tasks)

**Goal**: Format ANY MCP response for natural speech

- [x] T003 Create SpeechFormatter base class in mcp-servers/twilio-voice-mcp/speech_formatter.py
- [x] T004 [P] Implement generic formatters (IPs, UUIDs, numbers, lists, timestamps) in mcp-servers/twilio-voice-mcp/speech_formatter.py
- [x] T005 [P] Implement sensitive data detection (never speak credentials) in mcp-servers/twilio-voice-mcp/speech_formatter.py

---

## Phase 3: Context Manager (3 tasks)

**Goal**: Per-caller conversation context via Memory MCP

- [x] T006 Create ConversationContext dataclass in mcp-servers/twilio-voice-mcp/context_manager.py
- [x] T007 Implement ContextManager with Memory MCP load/save per caller ID in mcp-servers/twilio-voice-mcp/context_manager.py
- [x] T008 Implement context injection into Claude system prompt in mcp-servers/twilio-voice-mcp/context_manager.py

---

## Phase 4: Universal Voice Handler (4 tasks)

**Goal**: Connect voice I/O to Claude with ALL tools

- [x] T009 [US1] Extend webhook_server.py to pass transcribed speech to Claude with full MCP access in mcp-servers/twilio-voice-mcp/webhook_server.py
- [x] T010 [US1] Integrate SpeechFormatter into response pipeline in mcp-servers/twilio-voice-mcp/webhook_server.py
- [x] T011 [US1] Integrate ContextManager for per-caller state in mcp-servers/twilio-voice-mcp/webhook_server.py
- [x] T012 [US1] Add call duration tracking (warn at 25min, disconnect at 30min) in mcp-servers/twilio-voice-mcp/webhook_server.py

---

## Phase 5: Proactive Alerts (2 tasks)

**Goal**: Outbound calls for critical events

- [x] T013 [US3] Implement AlertTrigger config loading in mcp-servers/twilio-voice-mcp/alert_triggers.py
- [x] T014 [US3] Implement outbound call initiation with Twilio in mcp-servers/twilio-voice-mcp/alert_triggers.py

---

## Phase 6: Documentation (1 task)

- [x] T015 Update README.md and SOUL.md with voice integration documentation

---

## Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Formatter) + Phase 3 (Context) [parallel]
    ↓
Phase 4 (Universal Handler) - depends on 2 and 3
    ↓
Phase 5 (Alerts) - can start after T009
    ↓
Phase 6 (Docs)
```

## MVP Scope

**Phases 1-4 only** (12 tasks):
- Setup + Formatter + Context + Universal Handler
- Full access to ALL 40+ MCPs via voice
- No alerts yet, but core functionality complete

## Why This Works

Claude already knows how to:
- Query IP Fabric → just ask via voice
- Open ServiceNow tickets → just ask via voice
- Generate Blender diagrams → just ask via voice
- Use Forward Networks → just ask via voice
- Run Itential workflows → just ask via voice
- Check Datadog alerts → just ask via voice
- Everything else → just ask via voice

We're not teaching Claude new tools. We're giving Claude ears and a mouth.
