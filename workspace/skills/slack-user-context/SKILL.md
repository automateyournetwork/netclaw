---
name: slack-user-context
description: "Leverage Slack user profiles, presence, DND status, and workspace context to personalize responses, route escalations, and coordinate team operations"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# Slack User Context

Use Slack workspace awareness to make NetClaw's interactions smarter — knowing who's online, who's on-call, respecting Do Not Disturb, and personalizing responses based on user roles and expertise.

## Slack OAuth Scopes Used

| Scope | Purpose |
|-------|---------|
| `users:read` | View workspace members and their basic info |
| `users.profile:read` | View detailed profiles (title, department, timezone) |
| `users:write` | Set NetClaw's own presence status |
| `dnd:read` | Check Do Not Disturb before escalating |
| `im:read` | View DM channel info |
| `im:history` | Read DM context for personalized responses |
| `channels:read` | Know which channels exist and their purposes |
| `search:read.public` | Search public channels for relevant discussions |

## User-Aware Behaviors

### 1. Escalation Routing

Before escalating an alert to a specific person:

1. **Check DND status** — Is the engineer in Do Not Disturb mode?
2. **Check presence** — Are they active, away, or offline?
3. **Check timezone** — Is it their working hours?
4. **Check profile title** — Are they the right role for this issue?

**Escalation Decision Matrix:**

| DND | Presence | Severity | Action |
|-----|----------|----------|--------|
| Off | Active | Any | Mention directly |
| Off | Away | P1/P2 | Mention (they'll see notification) |
| Off | Away | P3/P4 | Post to channel, don't mention |
| On | Any | P1 | Mention anyway (override DND for P1) |
| On | Any | P2 | Try next person in rotation |
| On | Any | P3/P4 | Post to channel only |

### 2. Personalized Response Depth

Adjust response complexity based on who's asking:

**From user profile title/department:**

| Title Contains | Response Style |
|----------------|---------------|
| "Network Engineer", "CCIE" | Full technical detail, CLI output, protocol specifics |
| "NOC", "Operations" | Actionable steps, severity, impact summary |
| "Manager", "Director" | Executive summary, business impact, timeline |
| "Security", "InfoSec" | Focus on security implications, CVEs, compliance |
| "Developer", "DevOps" | API perspectives, connectivity impact, service mapping |
| "Help Desk", "Support" | Simple status, ETA, who to contact |

### 3. Timezone-Aware Scheduling

When scheduling reports or maintenance windows:

- Read the requesting user's timezone from their Slack profile
- Present times in THEIR timezone (not just UTC)
- Warn if proposed maintenance window is outside their business hours
- Suggest alternatives that work across timezones for multi-region teams

### 4. Context from Previous Conversations

When a user asks a follow-up question:

- Check recent DM and channel history for context
- Reference previous reports or investigations
- Don't re-explain concepts they've already discussed
- Build on previous analysis rather than starting fresh

## Team Awareness Features

### On-Call Roster Awareness

When NetClaw needs to escalate:

```
:telephone_receiver: *Escalation Attempt*
Checking team availability...

• @engineer1 — :green_circle: Active (Network Engineer) — *SELECTED*
• @engineer2 — :red_circle: DND until 08:00 EST (Senior NetEng)
• @engineer3 — :yellow_circle: Away (NOC Analyst) — last active 2h ago
• @manager1 — :green_circle: Active (Net Ops Manager) — CC'd on P1

Escalating to @engineer1...
```

### Workload Context

If NetClaw sees a user is already active in multiple incident threads:

```
:information_source: Note: @engineer1 is currently active in 2 other incident threads.
Consider routing to @engineer3 if this is non-urgent.
```

### Handoff Between Shifts

When a shift change is approaching:

```
:arrows_counterclockwise: *Shift Handoff Summary for @nightshift_engineer*

*Active Items:*
1. :warning: R2 memory trending high (78% → 82% over 8h) — monitoring
2. :wrench: SW1 firmware upgrade scheduled for 02:00 UTC — prep done
3. :white_check_mark: R1 Loopback99 change completed and verified

*Pending:*
4. :hourglass: Waiting on ISP ticket #45678 for R3 circuit
5. :clipboard: Security audit scheduled for SW2 tomorrow

_Full context in #netclaw-reports thread →_
```

## NetClaw Presence Management

Set NetClaw's own presence to reflect its status:

| NetClaw Status | Slack Presence | Meaning |
|----------------|---------------|---------|
| Idle | :green_circle: Active | Ready for requests |
| Running health check | :green_circle: Active | Processing (responsive) |
| Running fleet-wide ops | :yellow_circle: Away | Batch processing (may be slow) |
| Error / unreachable MCP | :red_circle: DND | Degraded — some skills unavailable |

## Search for Context

Before answering questions about the network, search public channels for recent discussions:

- Search for device names mentioned in recent messages
- Find previous troubleshooting threads about the same device
- Reference prior decisions about the network architecture
- Link to relevant existing threads instead of duplicating information

## Privacy and Boundaries

- **Never expose** user DND details, exact schedules, or personal info to other users
- **Only use** profile information to improve routing and response quality
- **Don't track** user activity patterns beyond immediate operational needs
- **Respect** when users don't want to be disturbed — follow the escalation matrix
- **Be transparent** about what context you're using when personalizing responses

## Integration with Other Skills

| Skill | User Context Enhancement |
|-------|-------------------------|
| slack-network-alerts | Route to active, available engineers |
| slack-incident-workflow | IC assignment based on availability |
| slack-report-delivery | Adjust detail level per audience |
| All pyATS skills | Include requestor context in GAIT trail |
