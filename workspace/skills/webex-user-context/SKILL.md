---
name: webex-user-context
description: "Leverage WebEx user profiles, presence status, and workspace context to personalize responses, route escalations, and coordinate team operations. Use when checking who is available, routing an escalation, personalizing responses based on user role, or determining engineer availability before paging someone."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# WebEx User Context

## WebEx API Capabilities Used

| API | Purpose |
|-----|---------|
| People -- List | Search workspace members by name, email, or orgId |
| People -- Get Details | View detailed profiles (displayName, emails, orgId, roles, avatar) |
| People -- Get My Own Details | Verify bot identity |
| Room Memberships -- List | See who is in a specific space |
| Messages -- List | Read recent messages for context |
| Webhooks | Receive real-time notifications for new messages |

## User-Aware Behaviors

### 1. Escalation Routing

Before escalating an alert to a specific person:

1. **Look up the person** -- Use People API to find them by email or displayName
2. **Check space membership** -- Verify they are a member of the relevant space
3. **Check recent activity** -- Look at recent messages to gauge availability
4. **Check profile role** -- Use displayName, title, and orgId to determine their role

**Escalation Decision Matrix:**

| Status | Severity | Action |
|--------|----------|--------|
| Active in space (recent messages) | Any | Mention directly with `<@personId>` |
| No recent activity | P1/P2 | Mention directly (they'll receive notification) |
| No recent activity | P3/P4 | Post to space, don't mention |
| Known off-hours (timezone) | P1 | Mention anyway (override for P1) |
| Known off-hours (timezone) | P2 | Try next person in rotation |
| Known off-hours (timezone) | P3/P4 | Post to space only |

### 2. Personalized Response Depth

Adjust response complexity based on who's asking.

**From user profile title/role context:**

| Role Context | Response Style |
|-------------|---------------|
| Network Engineer, CCIE | Full technical detail, CLI output, protocol specifics |
| NOC, Operations | Actionable steps, severity, impact summary |
| Manager, Director | Executive summary, business impact, timeline |
| Security, InfoSec | Focus on security implications, CVEs, compliance |
| Developer, DevOps | API perspectives, connectivity impact, service mapping |
| Help Desk, Support | Simple status, ETA, who to contact |

### 3. Timezone-Aware Scheduling

When scheduling reports or maintenance windows:

- Determine the requesting user's timezone from their profile or prior conversation context
- Present times in THEIR timezone (not just UTC)
- Warn if proposed maintenance window is outside their business hours
- Suggest alternatives that work across timezones for multi-region teams

### 4. Context from Previous Conversations

When a user asks a follow-up question:

- Check recent messages in the space and threads for context
- Reference previous reports or investigations
- Don't re-explain concepts they've already discussed
- Build on previous analysis rather than starting fresh

## Team Awareness Features

### On-Call Roster Awareness

When NetClaw needs to escalate:

```
**Escalation Attempt**
Checking team availability...

- John Smith (Network Engineer) -- Active in space (last message 5 min ago) -- **SELECTED**
- Jane Doe (Senior NetEng) -- No recent activity (last seen 3h ago)
- Bob Wilson (NOC Analyst) -- Active in Incidents space
- Alice Chen (Net Ops Manager) -- CC'd on P1

Escalating to John Smith...
```

### Workload Context

If NetClaw sees a user is already active in multiple incident threads:

```
**Note:** John Smith is currently active in 2 other incident threads.
Consider routing to Bob Wilson if this is non-urgent.
```

### Handoff Between Shifts

When a shift change is approaching:

```
**Shift Handoff Summary for @nightshift_engineer**

**Active Items:**
1. R2 memory trending high (78% -> 82% over 8h) -- monitoring
2. SW1 firmware upgrade scheduled for 02:00 UTC -- prep done
3. R1 Loopback99 change completed and verified

**Pending:**
4. Waiting on ISP ticket #45678 for R3 circuit
5. Security audit scheduled for SW2 tomorrow

_Full context in NetClaw Reports space thread_
```

## WebEx Mentions

Use `<@personId>` syntax to mention specific users in WebEx messages:

```
<@Y2lzY29zcGFyazovL3VzL1BFT1BMRS8xMjM0NTY3ODk> -- R1 is showing CRITICAL CPU at 94%. Please investigate.
```

For group notifications, mention all relevant space members or create a dedicated notification space.

## Privacy and Boundaries

- **Never expose** user activity patterns, email addresses, or personal info to other users
- **Only use** profile information to improve routing and response quality
- **Don't track** user activity beyond immediate operational needs
- **Respect** engineer availability -- follow the escalation matrix
- **Be transparent** about what context you're using when personalizing responses

## Integration with Other Skills

| Skill | User Context Enhancement |
|-------|-------------------------|
| webex-network-alerts | Route to active, available engineers |
| webex-incident-workflow | IC assignment based on availability |
| webex-report-delivery | Adjust detail level per audience |
| All pyATS skills | Include requestor context in GAIT trail |
