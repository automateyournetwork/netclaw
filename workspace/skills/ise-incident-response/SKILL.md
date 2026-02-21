---
name: ise-incident-response
description: "Rapid ISE endpoint investigation and quarantine workflow - endpoint lookup, auth history, posture review, human-authorized quarantine, ServiceNow Security Incident"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ISE_MCP_SCRIPT", "ISE_BASE", "SERVICENOW_MCP_SCRIPT"] } } }
---

# ISE Incident Response

Rapid endpoint investigation and quarantine workflow for Cisco ISE. Provides structured steps to identify a suspect endpoint, review its authentication history and posture state, assess risk, and -- only with explicit human authorization -- move it to a quarantine group. Every action is tracked in ServiceNow and GAIT.

## Safety -- Non-Negotiable Rules

**NEVER auto-quarantine an endpoint.** Endpoint group changes require explicit human confirmation. The agent MUST present its findings, state its recommendation, and then STOP and WAIT for the human to type an affirmative response before proceeding with any ISE endpoint group modification.

**NEVER skip the investigation steps.** Even if the human says "just quarantine MAC XX:XX:XX:XX:XX:XX", the agent MUST first collect endpoint data, auth history, and posture state so the quarantine action has full context for the ServiceNow ticket and GAIT audit trail.

**NEVER modify ISE authorization policies during incident response.** This workflow changes endpoint group membership only. Policy changes require a separate Change Request via servicenow-change-workflow.

## When to Use

- Suspected compromised endpoint (SOC alert, SIEM correlation)
- Unauthorized device detected on the network
- Endpoint exhibiting anomalous behavior (port scanning, lateral movement)
- Failed posture compliance requiring immediate isolation
- Rogue access point or hub detected on a switchport

## How to Call the ISE MCP Tools

All ISE tools are called via mcp-call with the ISE MCP server command:

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

ServiceNow tools are called via:

```bash
python3 $MCP_CALL "$SERVICENOW_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## Incident Response Procedure

### Phase 1: Endpoint Identification

Locate the suspect endpoint by MAC address, IP address, or username. Start with the endpoints list and active sessions.

**Look up all endpoints:**

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" endpoints '{}'
```

**Check active sessions for the suspect:**

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" active_sessions '{}'
```

Filter the results for the target MAC/IP/username. Record:
- MAC address
- IP address (if assigned)
- Username (if 802.1X authenticated)
- Connected switch and port
- Identity group membership
- Profile classification
- Session state (active/inactive)

### Phase 2: Authentication History Review

Pull authorization and authentication rules to understand what access the endpoint was granted and why:

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" network_access_authorization_rules '{}'
```

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" network_access_authentication_rules '{}'
```

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" network_access_policy_set '{}'
```

Determine:
- Which policy set matched the endpoint
- Which authorization rule granted access
- What authorization profile was assigned (VLAN, dACL, SGT)
- Whether posture was evaluated
- Whether 802.1X or MAB was used

### Phase 3: Posture and Profile Assessment

Evaluate the endpoint's posture compliance and profiling accuracy:

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" profiler_profiles '{}'
```

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" identity_groups '{}'
```

Determine:
- Is the endpoint posture-compliant, non-compliant, or unknown?
- What profiler profile matched? What certainty factor?
- Is the endpoint in the correct identity group?
- Does the endpoint profile match expected behavior (e.g., a "printer" making HTTP requests to external sites)?

### Phase 4: Risk Assessment and Recommendation

Compile findings and present a risk assessment to the human operator:

```
ENDPOINT INVESTIGATION SUMMARY
===============================
Target: [MAC address]
IP: [IP address]
Username: [username or N/A]
Location: [switch:port]
Profile: [ISE profile] (certainty: N)
Identity Group: [current group]
Auth Method: [802.1X / MAB]
Authorization Rule: [rule name]
Authorization Profile: [profile name — VLAN, dACL, SGT]
Posture Status: [Compliant / Non-Compliant / Unknown / Not Assessed]
Session Duration: [time]

RISK INDICATORS:
  - [List specific concerns, e.g., "Profiled as printer but generating DNS queries to known C2 domains"]
  - [e.g., "MAB-only authentication — no certificate or credential validation"]
  - [e.g., "Non-compliant posture but granted production VLAN access"]

RECOMMENDATION: [QUARANTINE / MONITOR / NO ACTION]
Rationale: [Brief explanation of why this recommendation is being made]
```

---

### *** HUMAN DECISION POINT ***

**STOP HERE.** Present the investigation summary above and ask the human operator:

> "Based on this investigation, I recommend [QUARANTINE/MONITOR/NO ACTION] for endpoint [MAC]. Do you authorize me to move this endpoint to the quarantine identity group in ISE? Please confirm with YES or NO."

**Do NOT proceed to Phase 5 unless the human explicitly responds with an affirmative.**

If the human says NO or requests monitoring only, skip to Phase 6 (ServiceNow) and record the decision.

---

### Phase 5: Quarantine Execution (Human-Authorized Only)

**This phase executes ONLY after explicit human authorization.**

Move the endpoint to the quarantine identity group. The ISE MCP endpoint tools handle endpoint group membership. The specific approach depends on the ISE MCP endpoint update capabilities.

After the group change:

1. Verify the endpoint group was updated by re-querying:

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" endpoints '{}'
```

2. Verify the active session was affected (CoA should trigger reauth):

```bash
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" active_sessions '{}'
```

3. Confirm the endpoint is now in the quarantine group and receiving restricted access.

### Phase 6: Open ServiceNow Security Incident

Create a Security Incident in ServiceNow documenting the investigation and action taken:

```bash
python3 $MCP_CALL "$SERVICENOW_MCP_SCRIPT" create_incident '{"short_description":"ISE Security Incident: Endpoint [MAC] quarantined","description":"Endpoint Investigation Report\n\nTarget: [MAC]\nIP: [IP]\nUsername: [username]\nLocation: [switch:port]\nProfile: [profile]\nAuth Method: [auth method]\nPosture: [status]\n\nRisk Indicators:\n- [indicator 1]\n- [indicator 2]\n\nAction Taken: Endpoint moved to quarantine group by [human operator] authorization.\nISE Identity Group: Quarantine\nTimestamp: [ISO 8601 timestamp]","category":"Security","impact":"2","urgency":"2","assignment_group":"Network Security"}'
```

If the human chose NO ACTION or MONITOR, adjust the ticket accordingly:

```bash
python3 $MCP_CALL "$SERVICENOW_MCP_SCRIPT" create_incident '{"short_description":"ISE Security Investigation: Endpoint [MAC] — monitoring","description":"Endpoint Investigation Report\n\nTarget: [MAC]\nIP: [IP]\nUsername: [username]\nLocation: [switch:port]\n\nInvestigation completed. Human operator reviewed findings and chose MONITOR (no quarantine).\nReason: [human-provided reason if any]\n\nMonitoring actions recommended:\n- Continue session logging\n- Set SIEM alert for this MAC\n- Reassess in 24 hours","category":"Security","impact":"3","urgency":"3","assignment_group":"Network Security"}'
```

Add work notes with the full investigation timeline:

```bash
python3 $MCP_CALL "$SERVICENOW_MCP_SCRIPT" add_comment '{"incident_id":"INC0010001","comment":"Investigation timeline:\n1. Endpoint identified via [source: SOC alert / manual report]\n2. ISE data collected: profile, auth history, posture state\n3. Risk assessment: [QUARANTINE/MONITOR/NO ACTION]\n4. Human decision: [AUTHORIZED/DECLINED]\n5. Action executed: [describe]\n6. Verification: [endpoint confirmed in quarantine group / monitoring continues]","is_work_note":true}'
```

### Phase 7: GAIT Audit Trail

Record the full incident response session in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"ISE Incident Response completed. Target: [MAC]. Investigation: auth history reviewed, posture assessed, profile verified. Risk: [HIGH/MEDIUM/LOW]. Recommendation: [QUARANTINE/MONITOR]. Human decision: [AUTHORIZED/DECLINED]. Action: [endpoint quarantined / monitoring only]. ServiceNow: INC0010001 created.","artifacts":[]}}'
```

## Example: Full Investigation Flow

**Scenario:** SOC alerts on MAC AA:BB:CC:DD:EE:FF making lateral connections to finance VLAN.

```bash
# Step 1: Find the endpoint
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" endpoints '{}'

# Step 2: Check if it has an active session
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" active_sessions '{}'

# Step 3: Review what authorization it received
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" network_access_authorization_rules '{}'

# Step 4: Check its profile and posture
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" profiler_profiles '{}'

# Step 5: Check identity group
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" identity_groups '{}'

# Step 6: Check TrustSec assignment
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" trustsec_sgts '{}'
```

Present findings to operator. Wait for human decision.

If authorized:

```bash
# Verify quarantine took effect
python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" endpoints '{}'

python3 $MCP_CALL "ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 -u $ISE_MCP_SCRIPT" active_sessions '{}'
```

Then open ServiceNow incident and record in GAIT.

## Investigation Checklist

Use this checklist to ensure no step is skipped:

- [ ] Endpoint identified (MAC, IP, username, switch:port)
- [ ] Active session state checked
- [ ] Authorization rule and profile determined
- [ ] Authentication method verified (802.1X vs MAB)
- [ ] Posture compliance status confirmed
- [ ] Profiler profile and certainty factor reviewed
- [ ] Identity group membership noted
- [ ] TrustSec SGT assignment checked (if applicable)
- [ ] Risk assessment compiled and presented to human
- [ ] **Human decision received** (QUARANTINE / MONITOR / NO ACTION)
- [ ] Action executed (if authorized)
- [ ] Post-action verification completed
- [ ] ServiceNow Security Incident created
- [ ] GAIT audit trail recorded

## Integration with Other Skills

- Use **ise-posture-audit** for the comprehensive policy review that often follows an incident
- Use **pyats-security** to verify the network device-side 802.1X and port-security configuration on the affected switchport
- Use **pyats-troubleshoot** to trace the endpoint's network path and verify ACL enforcement at each hop
- Use **servicenow-change-workflow** if the incident reveals a policy gap that requires an ISE authorization rule change (separate CR required)
- Use **gait-session-tracking** to maintain the immutable audit trail across the full incident lifecycle
- Use **markmap-viz** to visualize the endpoint's access path (SGT assignment, AuthZ rule, VLAN, dACL)
