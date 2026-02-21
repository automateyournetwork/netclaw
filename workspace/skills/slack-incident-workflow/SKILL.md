---
name: slack-incident-workflow
description: "Manage network incident response workflows in Slack - incident channels, status updates, escalation, resolution tracking, and post-incident review coordination"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# Slack Incident Workflow

Coordinate network incident response through Slack using NetClaw's App Agent capabilities. This skill defines structured workflows for incident detection, triage, investigation, resolution, and post-incident review — all conducted through Slack threads and channels.

## Slack OAuth Scopes Used

| Scope | Purpose |
|-------|---------|
| `assistant:write` | Act as App Agent in incident threads |
| `chat:write` | Post incident updates |
| `channels:join` | Join incident channels |
| `channels:history` | Read channel context for investigation |
| `groups:history` | Access private incident channels |
| `groups:read` | View private channel info |
| `pins:read` | Reference pinned runbooks/procedures |
| `bookmarks:read` | Access saved incident resources |
| `bookmarks:write` | Save incident artifacts |
| `files:write` | Attach logs, configs, diagrams |
| `reactions:write` | Track incident status via reactions |
| `users:read` | Identify on-call engineers |
| `users.profile:read` | Check engineer availability |
| `dnd:read` | Respect Do Not Disturb before paging |

## Incident Lifecycle in Slack

### Phase 1: Detection & Declaration

When a critical alert triggers (from slack-network-alerts skill or human report):

```
:rotating_light: *INCIDENT DECLARED — Network Outage*
*Severity:* P1 — Service Impacting
*Detected:* 2024-02-21 14:32 UTC
*Reporter:* NetClaw (automated) / @engineer1 (manual)

*Symptoms:*
• R1 unreachable (ping 0%)
• 47 downstream routes lost
• 3 OSPF adjacencies down
• BGP peer to ISP: IDLE

*Impact:*
• Site A has no WAN connectivity
• Estimated affected users: ~200

*Incident Commander:* [awaiting claim — react with :raised_hand: to take IC]
*ServiceNow:* [CR/INC pending]

━━━ *All investigation updates in this thread* ━━━
```

### Phase 2: Triage & Assignment

When an engineer reacts with :raised_hand::

```
:busts_in_silhouette: *Incident Team Formed*
*IC:* @engineer1 (claimed at 14:35 UTC)
*NetClaw:* Automated investigation assistant

*Triage Checklist:*
:white_check_mark: Alert generated and posted
:white_check_mark: Incident declared (P1)
:white_large_square: IC assigned → :white_check_mark: @engineer1
:white_large_square: ServiceNow incident created
:white_large_square: Upstream device checked
:white_large_square: Blast radius confirmed
:white_large_square: Customer communication sent

_NetClaw beginning automated investigation..._
```

### Phase 3: Automated Investigation

NetClaw runs diagnostics and posts results in the thread:

```
:mag: *Automated Investigation — Step 1/4*
_Checking upstream device R2 for connectivity to R1..._

PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL \
  "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device \
  '{"device_name":"R2","command":"ping 10.1.1.1 repeat 10"}'
```

Post each step result:

```
:mag: *Investigation Results — Step 1/4*
*Ping from R2 to R1 (10.1.1.1):* 0% success — R1 unreachable from upstream

:mag: *Investigation Results — Step 2/4*
*R2 interface Gi1 (toward R1):* up/up, 0 CRC errors, last input 4 min ago
→ Physical layer looks OK from R2 side

:mag: *Investigation Results — Step 3/4*
*R2 OSPF neighbors:* R1 missing from neighbor table (was FULL)
→ OSPF adjacency lost, DR election may be in progress

:mag: *Investigation Results — Step 4/4*
*R2 logs (last 30 min):*
```
14:31:47: %OSPF-5-ADJCHG: Nbr 1.1.1.1 on Gi1 from FULL to DOWN
14:31:48: %LINEPROTO-5-UPDOWN: Line protocol on Gi1, changed to down
14:32:01: %LINEPROTO-5-UPDOWN: Line protocol on Gi1, changed to up
14:32:15: %OSPF-5-ADJCHG: Nbr 1.1.1.1 on Gi1 from DOWN to INIT
```

*Analysis:* R2 saw Gi1 flap at 14:31. Line protocol came back up but OSPF hasn't re-converged. Likely physical issue on R1 side causing interface bounce.
```

### Phase 4: Status Updates

Post periodic status updates:

```
:hourglass_flowing_sand: *Status Update — 14:50 UTC (18 min elapsed)*
*Status:* Investigating
*Finding:* R1 appears to have reloaded unexpectedly. R2 sees the link recover but R1 is not responding to OSPF hellos yet. Possible crash or power event.
*Next Step:* Waiting for R1 to complete boot sequence. Checking console access.
*ETA:* Unknown — dependent on R1 recovery

_ServiceNow INC0012345 updated_
```

### Phase 5: Resolution

```
:white_check_mark: *INCIDENT RESOLVED*
*Duration:* 34 minutes (14:32 — 15:06 UTC)
*Resolution:* R1 experienced a software crash (Traceback in logs). Device auto-reloaded and recovered. All OSPF adjacencies re-established. Full routing restored.

*Post-Resolution Verification:*
• R1 reachable: :white_check_mark: 100% ping success
• OSPF neighbors: :white_check_mark: 3/3 FULL
• BGP peer: :white_check_mark: Established
• Route count: :white_check_mark: 47 routes (matches baseline)
• Connectivity: :white_check_mark: 100% to all targets

*Root Cause:* Software crash — Traceback found in logs indicating bug CSCxx12345. TAC case recommended.

*ServiceNow:* INC0012345 resolved
*GAIT:* Session abc123 closed
```

### Phase 6: Post-Incident Review

```
:clipboard: *Post-Incident Review — Scheduled*
*Incident:* Network Outage — R1 crash
*Date:* 2024-02-22 10:00 UTC
*Channel:* This thread

*Review Artifacts (attached):*
1. :page_facing_up: Timeline of events
2. :page_facing_up: R1 show logging output
3. :page_facing_up: R1 show version (confirms reload reason)
4. :page_facing_up: GAIT audit trail (full session)
5. :page_facing_up: Pre/post health check comparison

*Discussion Topics:*
• Was detection fast enough?
• Was automated investigation helpful?
• What monitoring gaps exist?
• Should R1 be upgraded to patched version?
• Do we need redundant path for this link?
```

## Escalation Matrix

```
:arrow_up: *Escalation Guide*

│ Severity │ Notify              │ Escalate After │ Channel          │
│ P1       │ IC + Manager + NOC  │ 15 min         │ #incidents       │
│ P2       │ IC + Team           │ 30 min         │ #netclaw-alerts  │
│ P3       │ Assigned engineer   │ 4 hours        │ #netclaw-alerts  │
│ P4       │ Queue only          │ Next business   │ #netclaw-general │
```

Before escalating, check DND status:
- If engineer has DND active, escalate to next person in rotation
- Never suppress P1 escalation for DND

## Reaction-Based Status Tracking

| Reaction | Status | Meaning |
|----------|--------|---------|
| :rotating_light: | Declared | Incident is active |
| :raised_hand: | Claimed | IC has taken ownership |
| :mag: | Investigating | Active investigation |
| :wrench: | Fixing | Fix being applied |
| :hourglass: | Waiting | Waiting on external (vendor, ISP) |
| :white_check_mark: | Resolved | Incident resolved |
| :bookmark: | PIR Scheduled | Post-incident review planned |

## ServiceNow Integration

Create ServiceNow incident at Phase 1:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_incident \
  '{"short_description":"P1 - R1 unreachable, WAN outage Site A","description":"R1 is unreachable. 47 routes lost, 3 OSPF adjacencies down. Impact: ~200 users at Site A without WAN connectivity.","urgency":"1","impact":"1","category":"Network"}'
```

Update ServiceNow as incident progresses and close on resolution.

## GAIT Audit Trail

Record every phase in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn \
  '{"input":{"role":"assistant","content":"INCIDENT P1: R1 unreachable. Phase 1 declared, Phase 2 IC assigned @engineer1, Phase 3 automated investigation shows R1 crash, Phase 4 monitoring recovery, Phase 5 resolved after 34 min. INC0012345 closed.","artifacts":[]}}'
```
