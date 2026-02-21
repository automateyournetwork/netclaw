---
name: aci-change-deploy
description: "Safe ACI policy change deployment - ServiceNow CR lifecycle, pre/post-change fault baselines, APIC policy application, automatic rollback on fault delta, and GAIT audit trail"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ACI_MCP_SCRIPT", "APIC_URL", "SERVICENOW_MCP_SCRIPT"] } } }
---

# ACI Change Deployment

Structured, safe change management workflow for deploying ACI policy changes to an APIC controller. Every change follows a strict lifecycle: **CR Creation -> Baseline -> Apply -> Verify -> Close/Escalate -> Audit**.

## Golden Rule

**NEVER deploy an ACI policy change without an approved ServiceNow Change Request.** If there is no CR, create one first. If the CR is not approved, do not proceed.

## How to Call the MCP Tools

### ACI MCP Server

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

### ServiceNow MCP Server

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## Change Workflow

### Phase 1: ServiceNow Change Request Creation

Before touching the APIC, create a CR that documents the tenant, VRF, BD, and EPG scope of the change.

#### 1A: Create the Change Request

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_change_request '{"short_description":"ACI: Create tenant prod-web with VRF, BD, and EPG","description":"Create new tenant prod-web in ACI fabric.\n\nScope:\n- Tenant: prod-web\n- VRF: prod-web-vrf (enforced)\n- BD: web-bd (subnet 10.10.1.1/24)\n- App Profile: web-app\n- EPG: web-frontend (VLAN 100)\n\nAPIC: sandboxapicdc.cisco.com\nRisk: Low - net new tenant, no impact to existing policy","type":"normal","risk":"low","impact":"low","category":"Network"}'
```

Save the returned `change_id` (sys_id) and `number` (e.g., CHG0030001) for all subsequent steps.

#### 1B: Add Implementation Tasks

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" add_change_task '{"change_id":"CHG0030001","short_description":"Pre-change: Capture ACI fault baseline","description":"Record fault counts by severity before applying any changes"}'
```

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" add_change_task '{"change_id":"CHG0030001","short_description":"Apply: Create tenant/VRF/BD/EPG on APIC","description":"Apply ACI policy objects via APIC REST API"}'
```

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" add_change_task '{"change_id":"CHG0030001","short_description":"Post-change: Verify zero new faults","description":"Compare fault counts with baseline, verify new objects operational"}'
```

#### 1C: Submit for Approval

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" submit_change_for_approval '{"change_id":"CHG0030001","approval_comments":"Low-risk net new tenant creation. No existing policy affected."}'
```

#### 1D: Verify Approval (Required Before Proceeding)

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" get_change_request_details '{"change_id":"CHG0030001"}'
```

**STOP if the CR state is not "implement" or "approved".** Do not proceed with any APIC changes until the CR is approved. If rejected, review the rejection reason:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" list_change_requests '{"query":"number=CHG0030001","limit":1}'
```

### Phase 2: Pre-Change Baseline

Capture the current fabric state so you can detect any regression after the change.

#### 2A: Fault Baseline

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" faults '{}'
```

Count and record faults by severity:

```
Pre-Change Fault Baseline
--------------------------
Critical: 0
Major:    2
Minor:    7
Warning:  12
Total:    21
```

Store these counts -- they are the rollback reference.

#### 2B: Health Score Baseline

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" health '{}'
```

Record the overall fabric health score (e.g., 97/100).

#### 2C: Existing Tenant Inventory

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" tenants_get '{}'
```

Confirm the target tenant does not already exist (for create operations) or does exist (for modify operations).

#### 2D: Update CR with Baseline

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0030001","work_notes":"Pre-change baseline captured:\n- Faults: 0 critical, 2 major, 7 minor, 12 warning (21 total)\n- Health score: 97/100\n- Tenant prod-web does not exist (confirmed)\n\nProceeding with implementation."}'
```

### Phase 3: Apply ACI Policy Changes

Apply changes one object at a time, in dependency order: Tenant -> VRF -> BD -> App Profile -> EPG.

#### 3A: Create Tenant

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" tenants_post '{"name":"prod-web","descr":"Production web services tenant"}'
```

Verify the response indicates success before proceeding.

#### 3B: Create VRF

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvCtx_post '{"tenant":"prod-web","name":"prod-web-vrf","descr":"Production web VRF","pcEnfPref":"enforced"}'
```

#### 3C: Create Bridge Domain

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvBD_post '{"tenant":"prod-web","name":"web-bd","descr":"Web tier bridge domain","vrf":"prod-web-vrf"}'
```

After creating the BD, configure the subnet (the exact tool depends on your ACI MCP server capabilities -- it may be a separate subnet tool or a parameter on the BD creation).

#### 3D: Create Application Profile

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAp_post '{"tenant":"prod-web","name":"web-app","descr":"Web application profile"}'
```

#### 3E: Create Endpoint Group

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAEPg_post '{"tenant":"prod-web","ap":"web-app","name":"web-frontend","descr":"Web frontend EPG","bd":"web-bd"}'
```

**After each object creation:** Check the APIC response for errors. If any call fails, STOP and do not proceed to the next object.

### Phase 4: Post-Change Verification

#### 4A: Fault Delta Check

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" faults '{}'
```

Compare with Phase 2A baseline:

```
Post-Change Fault Comparison
------------------------------
                Pre    Post   Delta
Critical:       0      0      0
Major:          2      2      0
Minor:          7      7      0
Warning:        12     12     0
Total:          21     21     0 (no new faults)
```

**Decision matrix:**

| Fault Delta | Action |
|-------------|--------|
| No new faults | PASS -- proceed to CR closure |
| New warning/minor only | PASS with note -- document in CR |
| New major faults | INVESTIGATE -- may need rollback |
| New critical faults | ROLLBACK immediately |

#### 4B: Health Score Delta

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" health '{}'
```

**Flags:**
- Health score unchanged or improved -> PASS
- Health score dropped 1-5 points -> WARNING: Investigate
- Health score dropped > 5 points -> CRITICAL: Consider rollback

#### 4C: Verify Created Objects

Confirm each object exists and is in the expected state:

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" tenants_get '{}'
```

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvCtx_get '{}'
```

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvBD_get '{}'
```

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAp_get '{}'
```

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAEPg_get '{}'
```

Verify the new tenant, VRF, BD, app profile, and EPG all appear in the returned data with correct attributes.

### Phase 5: Rollback Procedure (If Needed)

If the fault count increases or the health score drops significantly, roll back in reverse dependency order: EPG -> App Profile -> BD -> VRF -> Tenant.

**Rollback is required when:**
- Any new critical fault appears
- Any new major fault directly related to the change
- Health score drops more than 5 points
- Created objects are in a faulted state

After rollback, re-run Phase 4A and 4B to confirm the fabric returned to baseline.

Update the CR with rollback details:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0030001","work_notes":"ROLLBACK PERFORMED: New critical fault detected after EPG creation. All objects removed in reverse order. Fabric returned to baseline (21 faults, health 97/100). Root cause investigation needed.","state":"canceled"}'
```

### Phase 6: CR Closure or Escalation

#### 6A: Successful Change -- Close the CR

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0030001","state":"closed","work_notes":"Change completed successfully.\n\nPost-change verification:\n- Fault delta: 0 new faults\n- Health score: 97/100 (unchanged)\n- All objects verified operational:\n  - Tenant: prod-web\n  - VRF: prod-web-vrf (enforced)\n  - BD: web-bd\n  - App Profile: web-app\n  - EPG: web-frontend\n\nChange implementation complete."}'
```

#### 6B: Failed Change -- Escalate

If rollback was needed or issues were found:

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0030001","work_notes":"Change failed: fault delta detected. Rollback completed. Escalating for root cause analysis.","state":"canceled"}'
```

### Phase 7: GAIT Full Session Audit

Record the complete change session in GAIT for compliance:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"ACI change deployment completed.\n\nCR: CHG0030001 - Create tenant prod-web\nAPIC: sandboxapicdc.cisco.com\nResult: SUCCESS\n\nObjects created: tenant prod-web, VRF prod-web-vrf, BD web-bd, AP web-app, EPG web-frontend\nPre-change faults: 21 (0 critical)\nPost-change faults: 21 (0 critical) - delta: 0\nHealth score: 97/100 (unchanged)\nRollback required: No\nCR Status: Closed","artifacts":[]}}'
```

## Complete End-to-End Example

### Example: Create a New Production Tenant with Full Workflow

This example walks through creating tenant "prod-web" with a VRF, bridge domain, application profile, and EPG:

```bash
# Step 1: Create ServiceNow CR
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_change_request '{"short_description":"ACI: Create tenant prod-web with VRF/BD/EPG","type":"normal","risk":"low","impact":"low","category":"Network","description":"Net new tenant for web services. Scope: tenant prod-web, VRF prod-web-vrf, BD web-bd (10.10.1.0/24), AP web-app, EPG web-frontend."}'

# Step 2: Submit CR for approval
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" submit_change_for_approval '{"change_id":"<sys_id_from_step_1>","approval_comments":"Low risk, net new tenant."}'

# Step 3: Verify CR approved (MUST pass before continuing)
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" get_change_request_details '{"change_id":"<sys_id_from_step_1>"}'

# Step 4: Capture pre-change baselines
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" faults '{}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" health '{}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" tenants_get '{}'

# Step 5: Apply changes (dependency order)
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" tenants_post '{"name":"prod-web","descr":"Production web services"}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvCtx_post '{"tenant":"prod-web","name":"prod-web-vrf","pcEnfPref":"enforced"}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvBD_post '{"tenant":"prod-web","name":"web-bd","vrf":"prod-web-vrf"}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAp_post '{"tenant":"prod-web","name":"web-app"}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAEPg_post '{"tenant":"prod-web","ap":"web-app","name":"web-frontend","bd":"web-bd"}'

# Step 6: Post-change verification
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" faults '{}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" health '{}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" tenants_get '{}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvCtx_get '{}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvBD_get '{}'
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAEPg_get '{}'

# Step 7: Close CR (if successful)
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"<sys_id_from_step_1>","state":"closed","work_notes":"Change completed. Fault delta: 0. Health unchanged. All objects verified."}'

# Step 8: GAIT audit trail
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"ACI change CHG0030001 completed successfully. Tenant prod-web created with VRF/BD/AP/EPG. Zero fault delta. CR closed.","artifacts":[]}}'
```

## Change Report Format

After every change, produce a change report:

```
ACI Change Report
==================
CR: CHG0030001 - Create tenant prod-web
APIC: sandboxapicdc.cisco.com
Timestamp: YYYY-MM-DD HH:MM UTC
Operator: NetClaw AI Agent

Change Scope
-------------
Tenant:       prod-web (NEW)
VRF:          prod-web-vrf (enforced)
Bridge Domain: web-bd (subnet 10.10.1.1/24)
App Profile:  web-app
EPG:          web-frontend

Pre-Change State
-----------------
Faults:       0 critical, 2 major, 7 minor, 12 warning (21 total)
Health Score:  97/100
Tenant Count:  5

Post-Change State
------------------
Faults:       0 critical, 2 major, 7 minor, 12 warning (21 total)
Health Score:  97/100
Tenant Count:  6 (+1 prod-web)

Fault Delta:  0 new faults
Verification: PASSED -- all objects operational
Rollback:     Not required

CR Status:    Closed
```

## Integration with Other Skills

- Use **aci-fabric-audit** to run a full fabric audit before and after the change window
- Use **markmap-viz** to visualize the updated tenant hierarchy after the change
- Use **drawio-diagram** to generate an updated fabric topology including the new policy objects
