---
name: aci-fabric-audit
description: "Comprehensive Cisco ACI fabric health audit - node status, tenant/VRF/BD/EPG policy review, contract analysis, fault triage, and endpoint learning verification"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ACI_MCP_SCRIPT", "APIC_URL"] } } }
---

# ACI Fabric Health Audit

Perform a comprehensive health audit of a Cisco ACI fabric through the APIC. This skill systematically inspects every layer of the fabric -- physical nodes, logical policy, contracts, faults, and endpoint learning -- and produces a consolidated audit report with severity ratings.

## How to Call the ACI MCP Tools

All ACI tool calls use mcp-call with environment variables set as a prefix:

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## When to Use

- Scheduled daily/weekly fabric health checks
- Pre-change baseline capture before any ACI policy modification
- Post-change validation to confirm no new faults appeared
- Incident response when ACI-related alerts fire
- Compliance audits for tenant policy and contract hygiene
- Capacity planning for leaf/spine utilization

## Audit Procedure

Always run the audit in this exact order. Each phase builds on the previous one.

### Phase 1: Fabric Node Health

Verify all leaf and spine switches are registered, healthy, and running expected firmware.

#### 1A: Enumerate Fabric Nodes

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fabric_nodes '{}'
```

**Extract and report:**
- Node ID, name, role (leaf/spine/controller), serial number
- Admin state and operational state
- Fabric firmware version
- Model and TEP address

**Flags:**
- Node operational state != "available" -> CRITICAL
- Mixed firmware versions across same role -> WARNING
- Node decommissioned or inactive -> WARNING

#### 1B: Fabric Pods

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fabric_pods '{}'
```

Verify all pods are healthy and reachable.

#### 1C: Fabric Links

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fabric_links '{}'
```

**Flags:**
- Link operState != "up" -> CRITICAL: Fabric interconnect down
- Single-homed spine (only one link) -> WARNING: No redundancy

### Phase 2: Tenant / VRF / BD / EPG Policy Audit

Systematically walk the ACI policy tree from tenant down to EPG.

#### 2A: Enumerate All Tenants

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" tenants_get '{}'
```

Record the full tenant list. Flag any unexpected tenants (not in the approved tenant registry).

#### 2B: VRF Contexts per Tenant

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvCtx_get '{}'
```

**Flags:**
- VRF with pcEnfPref set to "unenforced" -> WARNING: No contract enforcement
- VRF with no bridge domains attached -> WARNING: Orphaned VRF

#### 2C: Bridge Domains

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvBD_get '{}'
```

**Flags:**
- BD with unicastRoute disabled -> WARNING: No L3 routing
- BD with arpFlood enabled and limitIpLearnToSubnets disabled -> WARNING: Broadcast storm risk
- BD not associated with any VRF -> CRITICAL: Misconfiguration
- BD with no subnets -> WARNING: L2-only BD, verify intentional

#### 2D: Application Profiles

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAp_get '{}'
```

Enumerate application profiles to understand the logical grouping of EPGs.

#### 2E: Endpoint Groups

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" fvAEPg_get '{}'
```

**Flags:**
- EPG with no static bindings and no VMM domain -> WARNING: No path to physical or virtual infra
- EPG with no contracts (neither consumer nor provider) -> WARNING: Isolated EPG, no communication possible
- EPG with floodOnEncap enabled -> WARNING: Potential broadcast issues

### Phase 3: Contract Analysis

Audit contracts for security hygiene -- look for overly permissive rules and unused contracts.

#### 3A: List All Contracts

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" contracts_get '{}'
```

**Flags:**
- Contract with scope "global" and subject filter permitting all (ether type unspecified) -> CRITICAL: Any-to-any rule
- Contract with no subjects -> WARNING: Empty contract, no rules defined
- Contract with no consumers or no providers -> WARNING: Unused contract
- Contract scope "tenant" with cross-tenant consumer -> WARNING: Verify intent

#### 3B: Analyze Contract Subjects and Filters

For each contract returned, inspect the subjects and filters. Look for:
- Filters allowing IP protocol 0 (unspecified) -> CRITICAL: Permits all traffic
- Filters allowing TCP/UDP with dFromPort=0 and dToPort=65535 -> WARNING: Full port range open
- Taboo contracts with broad deny rules -> INFO: Document these for compliance

### Phase 4: Fault Analysis

#### 4A: Retrieve All Faults

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" faults '{}'
```

**Categorize and count by severity:**

| Severity | Action |
|----------|--------|
| critical | Immediate triage required |
| major    | Schedule remediation within 24 hours |
| minor    | Review in next maintenance window |
| warning  | Informational, track trending |

**Flags:**
- Any critical faults -> CRITICAL: Report immediately
- Major fault count > 10 -> WARNING: Systemic issue suspected
- Faults with lifecycle "raised" (not acknowledged) -> WARNING: Unacknowledged faults

#### 4B: Health Scores

```bash
APIC_URL=$APIC_URL USERNAME=$ACI_USERNAME PASSWORD=$ACI_PASSWORD python3 $MCP_CALL "python3 -u $ACI_MCP_SCRIPT" health '{}'
```

**Thresholds:**
- Health score >= 95 -> HEALTHY
- Health score 80-94 -> WARNING
- Health score 60-79 -> HIGH
- Health score < 60 -> CRITICAL

### Phase 5: Endpoint Learning Verification

Verify that endpoints are being learned correctly across the fabric.

#### 5A: Check Endpoint Learning

Look for:
- Duplicate MAC addresses learned on different leaves -> CRITICAL: Possible loop
- Endpoints bouncing between ports (frequent EP moves) -> WARNING: Instability
- Static endpoints not present in the endpoint table -> WARNING: Connectivity issue

## Audit Report Format

Always produce a consolidated summary:

```
ACI Fabric Audit Report
========================
APIC: $APIC_URL
Timestamp: YYYY-MM-DD HH:MM UTC

Fabric Summary
--------------
Pods: 1 | Nodes: 6 (2 spine, 4 leaf) | All nodes available: YES
Firmware: 6.0(3e) uniform across all nodes

Policy Summary
--------------
Tenants: 5 | VRFs: 8 | BDs: 23 | App Profiles: 12 | EPGs: 47

+--------------------+----------+----------------------------------+
| Check              | Status   | Details                          |
+--------------------+----------+----------------------------------+
| Fabric Nodes       | HEALTHY  | 6/6 nodes available              |
| Fabric Links       | HEALTHY  | All inter-switch links up        |
| Tenant Policy      | WARNING  | 2 EPGs with no contracts         |
| VRF Enforcement    | HEALTHY  | All VRFs enforced                |
| Bridge Domains     | WARNING  | 1 BD with no subnet              |
| Contracts          | CRITICAL | 1 any-to-any contract found      |
| Faults (Critical)  | HEALTHY  | 0 critical faults                |
| Faults (Major)     | WARNING  | 3 major faults (unacknowledged)  |
| Health Score       | HEALTHY  | 97/100                           |
| Endpoint Learning  | HEALTHY  | No duplicate MACs detected       |
+--------------------+----------+----------------------------------+

Overall: WARNING -- 4 items need attention, 1 CRITICAL contract issue

Critical Findings
-----------------
1. [CRITICAL] Contract "default" in tenant "prod" permits all traffic
   - Scope: global | Subject filter: implicit-allow
   - Recommendation: Replace with explicit per-port filters

2. [WARNING] EPG "web-servers" in tenant "prod" has no provider contracts
   - No inbound communication path defined
   - Recommendation: Attach appropriate provider contract

3. [WARNING] BD "legacy-bd" has no subnet configured
   - L2-only mode, verify this is intentional
   ...
```

Severity order: CRITICAL > HIGH > WARNING > HEALTHY. Overall status = worst individual status.

## Integration with Other Skills

### GAIT Audit Trail

After completing the audit, record the session in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"ACI fabric audit completed on APIC $APIC_URL: Nodes HEALTHY (6/6), Policy WARNING (2 EPGs no contracts), Contracts CRITICAL (1 any-to-any), Faults WARNING (3 major), Health 97/100. Overall: WARNING.","artifacts":[]}}'
```

### Markmap Tenant Hierarchy

Generate an interactive mind map of the tenant hierarchy:

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_generate '{"markdown_content":"# ACI Fabric\n## Tenant: prod\n### VRF: prod-vrf\n#### BD: web-bd\n##### EPG: web-servers\n##### EPG: app-servers\n#### BD: db-bd\n##### EPG: db-servers\n## Tenant: shared\n### VRF: shared-l3out\n#### BD: external-bd"}'
```

### Draw.io Fabric Topology

Generate a visual fabric topology diagram:

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD\n  subgraph \"Pod 1\"\n    APIC1[\"APIC-1\"]\n    S1[\"Spine-1\"]\n    S2[\"Spine-2\"]\n    L1[\"Leaf-1\"]\n    L2[\"Leaf-2\"]\n    L3[\"Leaf-3\"]\n    L4[\"Leaf-4\"]\n    S1 --- L1\n    S1 --- L2\n    S1 --- L3\n    S1 --- L4\n    S2 --- L1\n    S2 --- L2\n    S2 --- L3\n    S2 --- L4\n  end"}'
```

## Output

The audit produces:
1. A structured text report with severity ratings per check area
2. A list of critical findings with actionable recommendations
3. Optional markmap visualization of tenant hierarchy
4. Optional Draw.io diagram of fabric topology
5. GAIT audit trail entry for compliance records
