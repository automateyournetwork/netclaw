# Implementation Plan: Twilio Voice MCP Integration

**Branch**: `042-twilio-voice-mcp` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/042-twilio-voice-mcp/spec.md`

## Summary

Add bidirectional phone call capabilities to NetClaw for emergency alerts, situation updates, daily check-ins, on-demand calls, AND the ability to call NetClaw for voice conversations. Uses official @twilio-alpha/mcp NPM package for outbound calls, custom webhook handler for inbound calls with STT/TTS, and strict guardrails for call safety.

## Technical Context

**Language/Version**: Node.js 18+ (for @twilio-alpha/mcp), Python 3.10+ (for webhook server and skills)
**Primary Dependencies**: @twilio-alpha/mcp (NPM), FastMCP (Python webhook), Twilio SDK, openai-whisper-api (existing skill for STT)
**Storage**: Memory MCP (feature 033) for call logging and audit trail
**Testing**: pytest (Python components), manual integration testing with Twilio
**Target Platform**: Linux server (OpenClaw gateway)
**Project Type**: MCP integration + webhook service + skills
**Performance Goals**: Emergency calls initiated within 60 seconds, inbound call connection within 5 seconds
**Constraints**: Max 3 outbound calls/hour, 10/day; inbound calls max 15 minutes; content guardrails (no IPs/credentials)
**Scale/Scope**: Single user (John), single whitelisted number (+1-873-455-0127)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | Voice calls don't modify devices; verbal confirmation required for network commands |
| II. Read-Before-Write | PASS | No device writes via voice without explicit confirmation |
| III. ITSM-Gated Changes | PASS | Voice commands that trigger changes still require CR approval |
| IV. Immutable Audit Trail | PASS | All calls logged to Memory MCP with full transcripts |
| V. MCP-Native Integration | PASS | Using @twilio-alpha/mcp + custom webhook MCP server |
| VI. Multi-Vendor Neutrality | N/A | Twilio is the sole voice provider |
| VII. Skill Modularity | PASS | Separate skills for outbound, inbound, emergency calls |
| VIII. Verify After Every Change | PASS | Call success/failure logged and reported |
| IX. Security by Default | PASS | Caller ID whitelist, rate limits, content guardrails |
| X. Observability | PASS | All calls logged with duration, status, transcript |
| XI. Full-Stack Artifact Coherence | PENDING | Will update all artifacts during implementation |
| XII. Documentation-as-Code | PENDING | SKILL.md files to be created |
| XIII. Credential Safety | PASS | Twilio credentials in .env only |
| XIV. Human-in-the-Loop | PASS | Non-emergency calls require approval; verbal confirmation for actions |
| XV. Backwards Compatibility | PASS | New capability, no breaking changes |
| XVI. Spec-Driven Development | PASS | Following SDD workflow |
| XVII. Milestone Documentation | PENDING | Blog post after implementation |

**Gate Result**: PASS - No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/042-twilio-voice-mcp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (webhook API)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
mcp-servers/
└── twilio-voice-mcp/           # New: Webhook server for inbound calls
    ├── server.py               # FastMCP webhook handler
    ├── voice_handler.py        # Inbound call processing (STT → Claude → TTS)
    ├── guardrails.py           # Content filtering, rate limiting
    ├── requirements.txt
    └── README.md

workspace/skills/
├── twilio-emergency-call/      # New: P1 incident auto-call skill
│   └── SKILL.md
├── twilio-outbound-call/       # New: On-demand outbound call skill
│   └── SKILL.md
├── twilio-inbound-voice/       # New: Inbound voice conversation skill
│   └── SKILL.md
└── twilio-daily-briefing/      # New: Daily check-in call skill
    └── SKILL.md

config/
└── twilio-voice.json           # Whitelist, quiet hours, rate limits config
```

**Structure Decision**: Hybrid approach - uses official @twilio-alpha/mcp for outbound call initiation, custom FastMCP server for inbound call webhook handling. Skills orchestrate the calling workflows.

## Complexity Tracking

> No violations requiring justification. Constitution gates passed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |
