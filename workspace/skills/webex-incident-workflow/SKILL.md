---
name: webex-incident-workflow
description: "Manage network incident response workflows in Cisco WebEx - incident spaces, status updates, escalation, resolution tracking, and post-incident review coordination. Use when declaring a network incident, coordinating outage response in WebEx, tracking incident status, or running a post-incident review."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"] } } }
---

# WebEx Incident Workflow

## WebEx API Capabilities Used

| API | Purpose |
|-----|---------|
| Messages -- Create | Post incident updates to spaces |
| Messages -- Create (Adaptive Card) | Rich incident declaration and status cards |
| Rooms -- Create | Create dedicated incident spaces |
| Rooms -- Get Details | Check space metadata |
| Memberships -- Create | Add responders to incident spaces |
| Memberships -- List | Identify who is in the incident space |
| People -- List | Look up engineers by name/email for escalation |
| People -- Get Details | Check engineer availability |
| Webhooks | Receive Adaptive Card action submissions (IC claim, status updates) |

## Incident Lifecycle in WebEx

### Phase 1: Detection & Declaration

When a critical alert triggers (from webex-network-alerts skill or human report), post an Adaptive Card to the primary alerts space:

```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    {
      "type": "Container",
      "style": "attention",
      "items": [
        {
          "type": "TextBlock",
          "text": "INCIDENT DECLARED -- Network Outage",
          "weight": "Bolder",
          "size": "Large",
          "color": "Attention"
        }
      ]
    },
    {
      "type": "FactSet",
      "facts": [
        { "title": "Severity:", "value": "P1 -- Service Impacting" },
        { "title": "Detected:", "value": "2024-02-21 14:32 UTC" },
        { "title": "Reporter:", "value": "NetClaw (automated)" }
      ]
    },
    {
      "type": "TextBlock",
      "text": "**Symptoms:**\n- R1 unreachable (ping 0%)\n- 47 downstream routes lost\n- 3 OSPF adjacencies down\n- BGP peer to ISP: IDLE",
      "wrap": true
    },
    {
      "type": "TextBlock",
      "text": "**Impact:**\n- Site A has no WAN connectivity\n- Estimated affected users: ~200",
      "wrap": true
    },
    {
      "type": "FactSet",
      "facts": [
        { "title": "Incident Commander:", "value": "Awaiting claim" },
        { "title": "ServiceNow:", "value": "CR/INC pending" }
      ]
    },
    {
      "type": "ActionSet",
      "actions": [
        {
          "type": "Action.Submit",
          "title": "Claim IC Role",
          "data": { "action": "claim_ic", "incident_id": "INC-001" }
        }
      ]
    }
  ]
}
```

Optionally create a dedicated incident space for P1 events:

```
Room Name: INC-001 -- R1 Network Outage -- 2024-02-21
```

Add the NOC team, on-call engineers, and management as members via the Memberships API.

### Phase 2: Triage & Assignment

When an engineer clicks "Claim IC Role" on the Adaptive Card (received via webhook):

```
**Incident Team Formed**
**IC:** John Smith (claimed at 14:35 UTC)
**NetClaw:** Automated investigation assistant

**Triage Checklist:**
- [x] Alert generated and posted
- [x] Incident declared (P1)
- [x] IC assigned -- John Smith
- [ ] ServiceNow incident created
- [ ] Upstream device checked
- [ ] Blast radius confirmed
- [ ] Customer communication sent

_NetClaw beginning automated investigation..._
```

### Phase 3: Automated Investigation

NetClaw runs diagnostics and posts results as threaded replies:

```
**Automated Investigation -- Step 1/4**
_Checking upstream device R2 for connectivity to R1..._
```

Post each step result:

```
**Investigation Results -- Step 1/4**
**Ping from R2 to R1 (10.1.1.1):** 0% success -- R1 unreachable from upstream

**Investigation Results -- Step 2/4**
**R2 interface Gi1 (toward R1):** up/up, 0 CRC errors, last input 4 min ago
> Physical layer looks OK from R2 side

**Investigation Results -- Step 3/4**
**R2 OSPF neighbors:** R1 missing from neighbor table (was FULL)
> OSPF adjacency lost, DR election may be in progress

**Investigation Results -- Step 4/4**
**R2 logs (last 30 min):**
```
14:31:47: %OSPF-5-ADJCHG: Nbr 1.1.1.1 on Gi1 from FULL to DOWN
14:31:48: %LINEPROTO-5-UPDOWN: Line protocol on Gi1, changed to down
14:32:01: %LINEPROTO-5-UPDOWN: Line protocol on Gi1, changed to up
14:32:15: %OSPF-5-ADJCHG: Nbr 1.1.1.1 on Gi1 from DOWN to INIT
```

**Analysis:** R2 saw Gi1 flap at 14:31. Line protocol came back up but OSPF hasn't re-converged. Likely physical issue on R1 side causing interface bounce.
```

### Phase 4: Status Updates

Post periodic status updates as Adaptive Cards:

```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    {
      "type": "TextBlock",
      "text": "Status Update -- 14:50 UTC (18 min elapsed)",
      "weight": "Bolder",
      "size": "Medium"
    },
    {
      "type": "FactSet",
      "facts": [
        { "title": "Status:", "value": "Investigating" },
        { "title": "Finding:", "value": "R1 appears to have reloaded unexpectedly. R2 sees the link recover but R1 is not responding to OSPF hellos yet." },
        { "title": "Next Step:", "value": "Waiting for R1 to complete boot sequence. Checking console access." },
        { "title": "ETA:", "value": "Unknown -- dependent on R1 recovery" }
      ]
    },
    {
      "type": "TextBlock",
      "text": "_ServiceNow INC0012345 updated_",
      "isSubtle": true
    }
  ]
}
```

### Phase 5: Resolution

```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    {
      "type": "Container",
      "style": "good",
      "items": [
        {
          "type": "TextBlock",
          "text": "INCIDENT RESOLVED",
          "weight": "Bolder",
          "size": "Large",
          "color": "Good"
        }
      ]
    },
    {
      "type": "FactSet",
      "facts": [
        { "title": "Duration:", "value": "34 minutes (14:32 -- 15:06 UTC)" },
        { "title": "Resolution:", "value": "R1 experienced a software crash. Device auto-reloaded and recovered. All OSPF adjacencies re-established. Full routing restored." },
        { "title": "Root Cause:", "value": "Software crash -- Traceback found in logs indicating bug CSCxx12345. TAC case recommended." }
      ]
    },
    {
      "type": "TextBlock",
      "text": "**Post-Resolution Verification:**\n- R1 reachable: 100% ping success\n- OSPF neighbors: 3/3 FULL\n- BGP peer: Established\n- Route count: 47 routes (matches baseline)\n- Connectivity: 100% to all targets",
      "wrap": true
    },
    {
      "type": "TextBlock",
      "text": "_ServiceNow INC0012345 resolved | GAIT session abc123 closed_",
      "isSubtle": true
    }
  ]
}
```

### Phase 6: Post-Incident Review

```
**Post-Incident Review -- Scheduled**
**Incident:** Network Outage -- R1 crash
**Date:** 2024-02-22 10:00 UTC
**Space:** This thread

**Review Artifacts (attached):**
1. Timeline of events
2. R1 show logging output
3. R1 show version (confirms reload reason)
4. GAIT audit trail (full session)
5. Pre/post health check comparison

**Discussion Topics:**
- Was detection fast enough?
- Was automated investigation helpful?
- What monitoring gaps exist?
- Should R1 be upgraded to patched version?
- Do we need redundant path for this link?
```

## Escalation Matrix

| Severity | Notify | Escalate After | Space |
|----------|--------|---------------|-------|
| P1 | IC + Manager + NOC | 15 min | Dedicated incident space |
| P2 | IC + Team | 30 min | NetClaw Alerts |
| P3 | Assigned engineer | 4 hours | NetClaw Alerts |
| P4 | Queue only | Next business day | NetClaw General |

Before escalating, check the engineer's WebEx presence/status:
- If engineer appears Away or in DND, escalate to next person in rotation
- Never suppress P1 escalation regardless of status

## Adaptive Card Actions for Incident Management

Use `Action.Submit` buttons on Adaptive Cards for interactive incident management:

| Button | Action Data | Purpose |
|--------|------------|---------|
| Claim IC Role | `{"action":"claim_ic"}` | Engineer takes ownership |
| Update Status | `{"action":"update_status"}` | Post a new status update |
| Mark Resolved | `{"action":"resolve"}` | Close the incident |
| Schedule PIR | `{"action":"schedule_pir"}` | Set up post-incident review |

These actions are received via WebEx Webhooks (`attachmentActions` resource) and processed by NetClaw to update the incident state.

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
