# Implementation Plan: Twitter Bidirectional Interaction

**Branch**: `040-twitter-mentions` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/040-twitter-mentions/spec.md`

## Summary

Extend the existing twitter-mcp server (feature 039) with bidirectional interaction capabilities: poll for @mentions of @John_Capobianco, process them through NetClaw for intelligent reply generation, and post replies with human approval. Uses Twitter API v2 pay-as-you-go tier for reading mentions and posting replies.

## Technical Context

**Language/Version**: Python 3.10+ (consistent with existing NetClaw MCP servers)
**Primary Dependencies**: FastMCP (MCP framework), tweepy 4.x (Twitter API v2 client), python-dotenv
**Storage**: Memory MCP (feature 033) for interaction history; in-memory tracking for processed mention IDs
**Testing**: Manual testing via Twitter mentions; pytest for unit tests
**Target Platform**: Linux server (OpenClaw gateway)
**Project Type**: MCP server extension (adds tools to existing twitter-mcp)
**Performance Goals**: Mention detection within 5 minutes; reply generation under 30 seconds
**Constraints**: Twitter API rate limits (~100 reads/15 min); pay-as-you-go cost (~$0.10/interaction)
**Scale/Scope**: Typical engagement volume (<50 mentions/day for @John_Capobianco)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **XIV. Human-in-the-Loop** | **CRITICAL** | All replies MUST require human approval before posting. Spec FR-005 enforces this. |
| V. MCP-Native Integration | PASS | Extends existing twitter-mcp server with new tools |
| VII. Skill Modularity | PASS | New skill `twitter-respond` for reply workflow |
| XI. Full-Stack Artifact Coherence | REQUIRED | Must update README, SOUL.md, TOOLS.md, install.sh, HUD |
| XII. Documentation-as-Code | REQUIRED | SKILL.md for new skill, update MCP server README |
| XIII. Credential Safety | PASS | Uses existing Twitter credentials from .env |
| XV. Backwards Compatibility | PASS | Adds new tools, doesn't modify existing ones |
| XVII. Milestone Documentation | REQUIRED | Blog post after implementation |

**Gate Status**: PASS - No violations. Principle XIV compliance is core to the design.

## Project Structure

### Documentation (this feature)

```text
specs/040-twitter-mentions/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (MCP tool schemas)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
mcp-servers/twitter-mcp/
├── server.py            # Extend with new mention/reply tools
├── guardrails.py        # Existing (reuse for reply content)
├── tweet_threading.py   # Existing (reuse for long replies)
├── mentions.py          # NEW: Mention polling and tracking
├── replies.py           # NEW: Reply generation and posting
└── README.md            # Update with new tools

workspace/skills/
├── twitter-heartbeat/   # Existing (feature 039)
├── twitter-share/       # Existing (feature 039)
└── twitter-respond/     # NEW: Mention response workflow
    ├── SKILL.md
    └── prompts/
        └── reply_generation.md

ui/netclaw-visual/src/panels/
└── TwitterPanel.js      # Update to show mentions & replies
```

**Structure Decision**: Extends existing twitter-mcp server rather than creating a new server. New functionality is modular (mentions.py, replies.py) but integrates into the single server for unified credential handling.

## Complexity Tracking

No violations requiring justification. Design follows existing patterns.
