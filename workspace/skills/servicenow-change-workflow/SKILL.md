---
name: servicenow-change-workflow
description: "Full ITSM-gated change lifecycle - CR creation, pre-change incident validation, approval gate, execution via pyats-config-mgmt, post-change verification, and closure with GAIT audit trail"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["SERVICENOW_MCP_SCRIPT"] } } }
---

# ServiceNow Change Workflow

Full ITSM-gated change management lifecycle. No configuration change is ever executed without a ServiceNow Change Request in Approved state.

## Golden Rule

**NEVER execute a network change without an approved Change Request.** The only exception is an Emergency change, which still requires a CR and immediate human notification.

## How to Call the Tools

The ServiceNow MCP server provides change management and incident tools. Call them via mcp-call:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## ServiceNow Change Request States

```
New -> Assess -> Authorize -> Scheduled -> Implement -> Review -> Closed
                                                    \-> Canceled
```

- **New**: CR created, not yet submitted
- **Assess**: Submitted for review / risk assessment
- **Authorize**: Awaiting approval
- **Scheduled**: Approved and scheduled for implementation window
- **Implement**: Approved and ready for execution (this is the gate)
- **Review**: Post-implementation review
- **Closed**: Change completed and verified

## Change Types

| Type | Approval | Use When |
|------|----------|----------|
| Normal | CAB / manager approval required | Interface config, routing changes, ACL updates, any production change |
| Standard | Pre-approved template | Password rotation, NTP update, banner change |
| Emergency | Expedited (post-facto approval OK) | Active outage, security incident, critical vulnerability |

---

## Full Change Lifecycle

### Phase 0: Pre-Change Incident Check

Before creating a CR, verify no open P1/P2 incidents exist on affected CIs. Executing changes during active incidents violates ITIL best practice and risks compounding the outage.

#### 0A: Check for Open Critical Incidents

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" list_incidents '{"limit":20,"state":"1","query":"priority=1^ORpriority=2"}'
```

State `1` = New/Open. Review results for any incidents affecting the target device or service.

**Decision gate:**
- Open P1/P2 on affected CI -> STOP. Do not proceed. Notify the human.
- Open P1/P2 on unrelated CI -> Proceed with caution, note in CR description.
- No open P1/P2 -> Proceed.

#### 0B: Check for Active Change Freezes

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" list_change_requests '{"limit":10,"state":"implement","type":"normal"}'
```

Review active in-progress changes for conflicts. Two changes on the same device at the same time is a collision.

### Phase 1: Create Change Request

#### 1A: Create the CR

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_change_request '{"short_description":"Add Loopback99 to R1 for OSPF RID migration","description":"Add Loopback99 (99.99.99.99/32) to R1 as new OSPF router-id. Pre-change baseline captured. Rollback plan: no interface Loopback99. Affected CI: R1 (devnetsandboxiosxec8k.cisco.com). No open P1/P2 incidents on this CI.","type":"normal","category":"Network","risk":"moderate","impact":"3","assignment_group":"Network Engineering"}'
```

**CR description must include:**
1. What is being changed and why
2. Affected CI (device hostname, management IP)
3. Pre-change incident status (from Phase 0)
4. Rollback plan
5. Expected impact and duration
6. Verification criteria

#### 1B: Add Change Tasks

Break the change into discrete tasks for tracking:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" add_change_task '{"change_id":"CHG0000123","short_description":"Capture pre-change baseline on R1","description":"Save running config, OSPF neighbors, routing table, interface states, and connectivity baselines."}'
```

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" add_change_task '{"change_id":"CHG0000123","short_description":"Apply Loopback99 configuration on R1","description":"Apply: interface Loopback99, ip address 99.99.99.99 255.255.255.255, description OSPF-RID-Migration, no shutdown"}'
```

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" add_change_task '{"change_id":"CHG0000123","short_description":"Post-change verification on R1","description":"Verify Loopback99 up/up, OSPF neighbors stable, routing table +1 connected route, connectivity 100%."}'
```

#### 1C: Record CR Creation in GAIT

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"user_text":"Create change request for Loopback99 addition on R1","assistant_text":"Created CR CHG0000123: Add Loopback99 to R1 for OSPF RID migration. Type: normal, Risk: moderate, Impact: 3. 3 change tasks added. Pre-change incident check: CLEAR (no P1/P2 on R1)."}'
```

### Phase 2: Approval Gate

#### 2A: Submit for Approval

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" submit_change_for_approval '{"change_id":"CHG0000123","approval_comments":"Pre-change checks complete. No open P1/P2 incidents. Rollback plan documented. Ready for CAB review."}'
```

#### 2B: Wait for Approval

Poll the CR status until it reaches Implement state:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" get_change_request_details '{"change_id":"CHG0000123"}'
```

**Decision gate:**
- State = `implement` -> Proceed to Phase 3
- State = `authorize` -> Still awaiting approval. Wait.
- State = `canceled` -> CR was rejected. STOP. Notify the human with rejection reason.

**CRITICAL: Do NOT proceed to Phase 3 unless the CR state is `implement` (approved).**

#### 2C: Approve Change (when authorized to do so)

If the human operator has approval authority:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" approve_change '{"change_id":"CHG0000123","approval_comments":"Approved. Rollback plan verified. Maintenance window confirmed."}'
```

### Phase 3: Execution

This phase uses the **pyats-config-mgmt** skill for the actual device work. The ServiceNow CR gates entry to this phase.

#### 3A: Update CR to Implementation

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0000123","work_notes":"Beginning implementation. Capturing pre-change baseline."}'
```

#### 3B: Pre-Change Baseline (via pyats-config-mgmt)

Follow the pyats-config-mgmt skill Phase 1 procedure:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_running_config '{"device_name":"R1"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip ospf neighbor"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip route"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"R1","command":"ping 8.8.8.8 repeat 10"}'
```

Update the CR with baseline status:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0000123","work_notes":"Pre-change baseline captured: Running config saved, 2 OSPF neighbors FULL, 47 routes, 100% connectivity to 8.8.8.8 (23ms RTT)."}'
```

#### 3C: Apply Configuration (via pyats-config-mgmt)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_configure_device '{"device_name":"R1","config_commands":["interface Loopback99","ip address 99.99.99.99 255.255.255.255","description OSPF-RID-Migration","no shutdown"]}'
```

Update the CR:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0000123","work_notes":"Configuration applied to R1. Proceeding to post-change verification."}'
```

### Phase 4: Post-Change Verification

#### 4A: Verify the Change (via pyats-config-mgmt)

Follow the pyats-config-mgmt skill Phase 4 procedure:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_running_config '{"device_name":"R1"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip ospf neighbor"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip route"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"R1","command":"ping 8.8.8.8 repeat 10"}'
```

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"R1"}'
```

#### 4B: Verification Decision

**Compare pre-change vs post-change state:**

| Check | Pre-Change | Post-Change | Expected Delta |
|-------|-----------|-------------|----------------|
| OSPF neighbors | 2 FULL | 2 FULL | No change |
| Route count | 47 | 48 | +1 connected (99.99.99.99/32) |
| Connectivity | 100% | 100% | No change |
| New errors in log | - | %LINEPROTO-5-UPDOWN Lo99 up | Expected |

**Decision gate:**
- All checks PASS -> Proceed to Phase 5 (Close)
- Any check FAILS -> Initiate Rollback (Phase 4C), do NOT close the CR

#### 4C: Rollback (If Verification Fails)

If post-change verification fails, roll back immediately:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_configure_device '{"device_name":"R1","config_commands":["no interface Loopback99"]}'
```

Update the CR with rollback details:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0000123","work_notes":"ROLLBACK EXECUTED: Post-change verification failed. [Describe what failed]. Configuration rolled back. Device restored to baseline state. Verification of rollback: [results]."}'
```

Create an incident for the failed change:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_incident '{"short_description":"Failed change CHG0000123 on R1 - rollback executed","description":"Change CHG0000123 (Add Loopback99 to R1) failed post-change verification. Rollback executed successfully. Device restored to pre-change state. Root cause investigation required.","urgency":"2","impact":"2","category":"Network"}'
```

**CRITICAL: If rollback fails, this becomes a P1 incident. Notify the human IMMEDIATELY.**

### Phase 5: Close the Change Request

#### 5A: Update CR with Final Status

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0000123","work_notes":"Post-change verification PASSED. OSPF neighbors stable (2 FULL), route table +1 connected (99.99.99.99/32), connectivity 100%, no unexpected log entries. Change successful.","state":"review"}'
```

#### 5B: Close the CR

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0000123","state":"closed","work_notes":"Change completed successfully. All verification checks passed. No rollback required."}'
```

#### 5C: Record Full Session in GAIT

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"user_text":"Execute change CHG0000123: Add Loopback99 to R1","assistant_text":"Change CHG0000123 completed successfully.\n\nTimeline:\n- Pre-check: No open P1/P2 incidents on R1\n- CR created and approved\n- Baseline: 2 OSPF neighbors FULL, 47 routes, 100% connectivity\n- Config applied: interface Loopback99, 99.99.99.99/32\n- Verification: PASSED (2 OSPF FULL, 48 routes, 100% connectivity)\n- CR closed: successful\n\nArtifacts: Pre/post running config diff, routing table diff, log entries."}'
```

#### 5D: Display GAIT Audit Trail

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_show '{"commit":"HEAD"}'
```

---

## Emergency Change Process

Emergency changes bypass the normal approval gate but still require a CR and immediate human notification.

### When to Use Emergency Changes

- Active outage requiring immediate remediation
- Security incident requiring immediate mitigation (e.g., ACL to block attack)
- Critical vulnerability with active exploitation

### Emergency Workflow

#### E1: Create Emergency CR

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_change_request '{"short_description":"EMERGENCY: Block attack source 203.0.113.99 on R1","description":"EMERGENCY CHANGE: Active DDoS from 203.0.113.99 detected. Applying inbound ACL on GigabitEthernet1 to block source. Post-facto approval required.","type":"emergency","category":"Network","risk":"high","impact":"1","assignment_group":"Network Engineering"}'
```

#### E2: Notify Human Immediately

**CRITICAL: For emergency changes, you MUST notify the human operator before executing.** State:
- The emergency condition
- The proposed remediation
- The CR number
- Request verbal/written approval to proceed

#### E3: Execute Upon Human Approval

Follow Phase 3 (Execution) with accelerated timelines. Baseline capture is still mandatory.

#### E4: Post-Facto Approval

After execution, submit the emergency CR for post-facto approval:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" submit_change_for_approval '{"change_id":"CHG0000456","approval_comments":"EMERGENCY CHANGE - Post-facto approval requested. Change executed during active incident. Full audit trail in GAIT."}'
```

---

## Integration with Other Skills

| Skill | Integration Point |
|-------|------------------|
| **pyats-config-mgmt** | Phase 3 (Execution) and Phase 4 (Verification) - actual device configuration |
| **pyats-health-check** | Pre-change device health validation before entering Phase 3 |
| **netbox-reconcile** | Post-change: verify NetBox source of truth reflects the change (or ticket the delta) |
| **GAIT** | Every phase records to the audit trail - CR creation, approval, execution, verification, closure |
| **markmap-viz** | Generate change summary mind map for complex multi-device changes |

## Change Report Format

After every change, produce this summary:

```
Change Report - CHG0000123
Date: YYYY-MM-DD HH:MM UTC
Device: R1 (devnetsandboxiosxec8k.cisco.com)
Type: Normal | Risk: Moderate | Impact: 3

Pre-Check: No open P1/P2 incidents on R1
Approval: Approved by [approver] at HH:MM UTC

Pre-Change State:
  - OSPF neighbors: 2 (FULL)
  - Routes: 47
  - Connectivity: 100% to 8.8.8.8 (23ms)

Config Applied:
  interface Loopback99
   ip address 99.99.99.99 255.255.255.255
   description OSPF-RID-Migration
   no shutdown

Post-Change State:
  - OSPF neighbors: 2 (FULL) - no change
  - Routes: 48 (+1 connected 99.99.99.99/32)
  - Connectivity: 100% to 8.8.8.8 (23ms) - no change
  - Log: %LINEPROTO-5-UPDOWN Lo99 up/up (expected)

Verification: PASSED
Rollback Required: No
CR Status: Closed (successful)
GAIT Commit: [commit hash]
```
