# Implementation Plan: Twitter/X Integration (Free Tier)

**Branch**: `039-twitter-x-integration` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/039-twitter-x-integration/spec.md`

## Summary

Enable NetClaw to maintain a Twitter/X presence as an autonomous AI network engineering agent via @John_Capobianco's account. Implementation uses Twitter API v2 for one-way broadcast (post only) on the Free tier. Core capabilities: heartbeat tweets every 4 hours with CCIE-level content, manual tweet posting with guardrails, memory-driven content generation, and Visual HUD Twitter panel.

## Technical Context

**Language/Version**: Python 3.10+ (consistent with NetClaw MCP servers)
**Primary Dependencies**: FastMCP (MCP framework), tweepy 4.x (Twitter API v2 client), python-dotenv
**Storage**: Memory MCP (tweet history for deduplication, 30-day retention)
**Testing**: pytest with mocked Twitter API responses
**Target Platform**: Linux server (OpenClaw runtime)
**Project Type**: MCP server + 2 skills + HUD component
**Performance Goals**: ≤5 seconds tweet posting, ≤3 seconds content generation
**Constraints**: Twitter Free tier (50 tweets/24 hours), 280 chars per tweet (threads for longer)
**Scale/Scope**: ~6 heartbeat tweets/day + manual posts; minimal API usage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Safety-First Operations** | N/A | No device interaction |
| **II. Read-Before-Write** | N/A | No device state changes |
| **III. ITSM-Gated Changes** | N/A | Not a production network change |
| **IV. Immutable Audit Trail** | PASS | Tweets logged in Memory MCP; GAIT session tracking |
| **V. MCP-Native Integration** | PASS | twitter-mcp server follows MCP standard |
| **VII. Skill Modularity** | PASS | Two focused skills: twitter-heartbeat, twitter-share |
| **XI. Full-Stack Artifact Coherence** | REQUIRED | README, SOUL.md, install.sh, HUD, .env.example, TOOLS.md, openclaw.json |
| **XII. Documentation-as-Code** | REQUIRED | SKILL.md for each skill, MCP server README |
| **XIII. Credential Safety** | PASS | Credentials in ~/.openclaw/.env, never hardcoded |
| **XIV. Human-in-the-Loop** | **CRITICAL** | Twitter is external communication - requires explicit approval before posting |
| **XVII. Milestone Blog Post** | REQUIRED | Draft WordPress post after implementation |

### Principle XIV Compliance Strategy

Since Twitter is **external communication** (visible to people outside the session), the following safeguards apply:

1. **Manual tweets**: Always require explicit human approval before posting
2. **Heartbeat tweets**: Operator must explicitly enable via `TWITTER_HEARTBEAT_ENABLED=true` — disabled by default
3. **Content preview**: All tweets shown to user before posting (unless heartbeat is explicitly enabled)
4. **Guardrails**: Content screened for sensitive data before any post attempt

## Project Structure

### Documentation (this feature)

```text
specs/039-twitter-x-integration/
├── spec.md              # Feature specification (complete)
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
├── __init__.py
├── server.py            # FastMCP server with Twitter tools
├── guardrails.py        # Content validation and sanitization
├── threading.py         # Thread splitting logic for >280 chars
├── requirements.txt
└── README.md

workspace/skills/twitter-heartbeat/
├── SKILL.md             # Heartbeat skill documentation
└── prompts/             # Content generation prompts by category

workspace/skills/twitter-share/
└── SKILL.md             # Manual tweet skill documentation

ui/netclaw-visual/src/components/
└── TwitterPanel.jsx     # Visual HUD Twitter display

scripts/
└── twitter_install.sh   # Twitter MCP installation script
```

**Structure Decision**: Standard NetClaw pattern — MCP server in `mcp-servers/`, skills in `workspace/skills/`, HUD component in `ui/netclaw-visual/`.

## Complexity Tracking

No constitution violations requiring justification. Implementation follows standard patterns.

---

## Phase 0: Research

See [research.md](./research.md) for detailed findings.

### Key Decisions

1. **Twitter API Client**: tweepy 4.x — mature, well-documented, supports API v2
2. **Authentication**: OAuth 1.0a User Context (required for posting on behalf of user)
3. **Thread Strategy**: Split at sentence boundaries when possible, word boundaries otherwise
4. **History Storage**: Memory MCP with `twitter_history` namespace
5. **Guardrail Patterns**: Regex-based with configurable blocklist

---

## Phase 1: Design

See [data-model.md](./data-model.md) for entity definitions.
See [contracts/](./contracts/) for MCP tool schemas.
See [quickstart.md](./quickstart.md) for setup guide.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        NetClaw Agent                             │
├─────────────────────────────────────────────────────────────────┤
│  Skills Layer                                                    │
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │ twitter-heartbeat   │  │ twitter-share       │               │
│  │ (autonomous posts)  │  │ (manual posts)      │               │
│  └─────────┬───────────┘  └─────────┬───────────┘               │
│            │                        │                            │
│            ▼                        ▼                            │
│  ┌──────────────────────────────────────────────┐               │
│  │              twitter-mcp                      │               │
│  │  ┌──────────────────────────────────────┐    │               │
│  │  │ Tools:                               │    │               │
│  │  │ - twitter_post_tweet                 │    │               │
│  │  │ - twitter_post_thread                │    │               │
│  │  │ - twitter_post_tweet_with_media      │    │               │
│  │  │ - twitter_delete_tweet               │    │               │
│  │  │ - twitter_get_rate_limits            │    │               │
│  │  └──────────────────────────────────────┘    │               │
│  │  ┌──────────────────────────────────────┐    │               │
│  │  │ Guardrails:                          │    │               │
│  │  │ - IP address detection               │    │               │
│  │  │ - Credential pattern detection       │    │               │
│  │  │ - Customer name blocklist            │    │               │
│  │  │ - #netclaw enforcement               │    │               │
│  │  └──────────────────────────────────────┘    │               │
│  └─────────────────────┬────────────────────────┘               │
│                        │                                         │
├────────────────────────┼─────────────────────────────────────────┤
│  External Services     │                                         │
│            ┌───────────▼───────────┐                            │
│            │   Twitter API v2      │                            │
│            │   (Free Tier)         │                            │
│            └───────────────────────┘                            │
│                                                                  │
│            ┌───────────────────────┐                            │
│            │   Memory MCP          │◄── Tweet history           │
│            │   (persistence)       │    (30-day retention)      │
│            └───────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Content Generation Flow

```
Heartbeat Trigger (4-hour interval)
         │
         ▼
┌─────────────────────┐
│ Select Category     │ (tip, hot_take, til, achievement, musing, community)
│ (round-robin)       │
└─────────┬───────────┘
         │
         ▼
┌─────────────────────┐
│ Check Memory MCP    │ (recent activities for achievement category)
│ for context         │
└─────────┬───────────┘
         │
         ▼
┌─────────────────────┐
│ Generate Content    │ (CCIE persona, technical accuracy)
│ via Claude          │
└─────────┬───────────┘
         │
         ▼
┌─────────────────────┐
│ Apply Guardrails    │ (scan for IPs, secrets, customer names)
│                     │
└─────────┬───────────┘
         │
    ┌────┴────┐
    │ Pass?   │
    └────┬────┘
    Yes  │  No → Sanitize or regenerate
         │
         ▼
┌─────────────────────┐
│ Check Deduplication │ (compare against 7-day history)
│                     │
└─────────┬───────────┘
         │
    ┌────┴────┐
    │ Unique? │
    └────┬────┘
    Yes  │  No → Regenerate with different seed
         │
         ▼
┌─────────────────────┐
│ Add #netclaw        │
│ Post to Twitter     │
└─────────┬───────────┘
         │
         ▼
┌─────────────────────┐
│ Store in Memory MCP │ (tweet_id, content, timestamp)
│ Update HUD          │
└─────────────────────┘
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API credentials invalid | Medium | High | Validation on startup, clear error messages |
| Rate limit exceeded | Low | Medium | Queue tweets, exponential backoff |
| Sensitive data leakage | Low | Critical | Multi-layer guardrails, regex patterns |
| Twitter API changes | Low | Medium | tweepy library handles versioning |
| Heartbeat spam | Low | Medium | Configurable interval, disabled by default |

---

## Next Steps

1. Run `/speckit.tasks` to generate implementation task list
2. Implement twitter-mcp server
3. Implement skills (twitter-heartbeat, twitter-share)
4. Add TwitterPanel to Visual HUD
5. Update all coherence artifacts
6. Test with live credentials
7. Draft WordPress blog post
