---
name: ise-posture-audit
description: "Cisco ISE posture and policy audit - authorization rules, posture compliance, profiling gaps, TrustSec SGT matrix, active session health"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ISE_MCP_SCRIPT", "ISE_BASE"] } } }
---

# ISE Posture and Policy Audit

Comprehensive security posture assessment of Cisco Identity Services Engine (ISE) deployment. Reviews authorization policies for over-permissiveness, identifies endpoints without posture compliance, detects profiling gaps, analyzes the TrustSec SGT/SGACL matrix, and validates active session health.

## When to Use

- Periodic ISE policy compliance audit (SOC2, PCI-DSS, NIST 800-53, HIPAA)
- Pre-deployment review before onboarding new endpoint types
- Post-incident review to identify policy gaps that allowed lateral movement
- TrustSec segmentation validation
- Profiling accuracy assessment after network changes
- Quarterly access control hygiene check

## How to Call the ISE MCP Tools

All ISE tools are called via mcp-call with the ISE MCP server command:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## Audit Procedure

### Step 1: Clear Cache and Establish Baseline

Start every audit with a fresh cache to ensure current data:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" clear_cache '{}'
```

Verify connectivity and cache state:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" get_cache_stats '{}'
```

### Step 2: Authorization Policy Review

Pull all policy sets, then drill into authorization rules:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" network_access_policy_set '{}'
```

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" network_access_authorization_rules '{}'
```

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" network_access_authentication_rules '{}'
```

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" network_access_conditions '{}'
```

**Authorization Policy Checks:**

| Check | What to Look For | Severity If Found |
|-------|-----------------|-------------------|
| Default Allow | Default rule granting PermitAccess or DenyAccess without conditions | CRITICAL |
| Overly permissive rules | AuthZ rules with no posture condition and full network access | CRITICAL |
| Stale rules | Rules referencing deleted/unused identity groups or conditions | HIGH |
| Rule ordering | Permissive rules ranked above restrictive rules (shadowing) | HIGH |
| Missing posture check | AuthZ rules that grant access without posture assessment | MEDIUM |
| Duplicate conditions | Multiple rules with identical match criteria | LOW |

### Step 3: Posture Compliance Assessment

Review endpoints and identity groups to identify posture gaps:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" endpoints '{}'
```

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" identity_groups '{}'
```

**Posture Compliance Checks:**

| Check | What to Look For | Severity If Found |
|-------|-----------------|-------------------|
| Endpoints bypassing posture | Endpoints with full access but no posture assessment recorded | CRITICAL |
| Non-compliant endpoints on network | Endpoints marked non-compliant but not quarantined | CRITICAL |
| Missing posture policy for endpoint type | Endpoint categories (BYOD, IoT, contractor) without posture rules | HIGH |
| Posture reassessment interval | No periodic reassessment configured (one-time posture only) | MEDIUM |
| Unknown endpoints with access | Endpoints in "Unknown" group with network access beyond guest | HIGH |

### Step 4: Profiling Coverage Analysis

Assess how well ISE is profiling connected endpoints:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" profiler_profiles '{}'
```

Cross-reference with the endpoint list from Step 3.

**Profiling Checks:**

| Check | What to Look For | Severity If Found |
|-------|-----------------|-------------------|
| Unknown endpoint ratio | More than 10% of endpoints profiled as "Unknown" | HIGH |
| Unmatched profiles | Custom profiles with zero matched endpoints (dead profiles) | LOW |
| Missing critical profiles | No profiles for known device types on the network (printers, phones, cameras) | MEDIUM |
| Profile certainty | Endpoints with low certainty factor (< 20) receiving production access | HIGH |
| Profiling probe coverage | Insufficient probe types enabled for accurate classification | MEDIUM |

### Step 5: TrustSec SGT Matrix Analysis

Review Security Group Tags and their access control:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" trustsec_sgts '{}'
```

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" trustsec_sgacls '{}'
```

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" trustsec_egress_matrix_cell '{}'
```

**TrustSec Checks:**

| Check | What to Look For | Severity If Found |
|-------|-----------------|-------------------|
| Permit-all SGACLs | SGACLs with `permit ip` (no restrictions between segments) | CRITICAL |
| Missing matrix cells | SGT-to-SGT pairs with no defined policy (defaults to permit or deny?) | HIGH |
| Unused SGTs | SGTs defined but assigned to zero endpoints | LOW |
| Overly broad SGTs | Single SGT assigned to endpoints with different trust levels | HIGH |
| No deny logging | SGACLs with deny rules but no `log` keyword | MEDIUM |
| Flat segmentation | Fewer than 3 SGTs defined (minimal micro-segmentation) | HIGH |

### Step 6: Active Session Health

Review current active sessions for anomalies:

```bash
ISE_BASE=$ISE_BASE USERNAME=$ISE_USERNAME PASSWORD=$ISE_PASSWORD python3 $MCP_CALL "python3 -u $ISE_MCP_SCRIPT" active_sessions '{}'
```

**Session Health Checks:**

| Check | What to Look For | Severity If Found |
|-------|-----------------|-------------------|
| Long-lived sessions | Sessions active for > 24 hours without reauthentication | MEDIUM |
| Failed auth spikes | Multiple failed authentications from same MAC/IP in short window | HIGH |
| Guest on production VLAN | Guest-profiled endpoints on non-guest VLANs | CRITICAL |
| Multiple MACs per port | More than expected endpoints on a single switchport (hub or rogue AP) | HIGH |
| Auth method mismatch | Endpoints using MAB when 802.1X is expected for that device type | MEDIUM |

## Severity Rating Criteria

**CRITICAL** -- Immediate risk of unauthorized access or data exfiltration:
- Default permit-all authorization rules
- Non-compliant endpoints with unrestricted access
- Guest endpoints on production VLANs
- Permit-all SGACLs between untrusted and trusted segments

**HIGH** -- Significant policy gap that could be exploited:
- Unknown endpoints with production access
- Missing TrustSec matrix entries
- Stale or shadowed authorization rules
- Low-certainty profiling with production access

**MEDIUM** -- Policy weakness that should be addressed this cycle:
- Missing posture reassessment
- Auth method mismatches
- Insufficient profiling probes
- Long-lived sessions without reauth

**LOW** -- Housekeeping and hygiene items:
- Unused SGTs or dead profiles
- Duplicate authorization conditions
- Minor documentation gaps

## Audit Report Format

```
ISE Posture Audit Report
ISE Deployment: $ISE_BASE
Audit Date: YYYY-MM-DD

CRITICAL FINDINGS (Immediate Action Required):
  1. [C-001] Default AuthZ rule grants PermitAccess — all unmatched endpoints get full access
  2. [C-002] 14 endpoints marked non-compliant but not quarantined
  3. [C-003] SGACL "Permit_All" applied to IoT-to-Server matrix cell

HIGH FINDINGS (Address This Week):
  4. [H-001] 23% of endpoints profiled as "Unknown" — profiling gap
  5. [H-002] SGT "Employees" assigned to both corporate laptops and contractor devices
  6. [H-003] 3 authorization rules shadowed by permissive rule at rank 1

MEDIUM FINDINGS (Address This Month):
  7. [M-001] No posture reassessment configured — one-time check only
  8. [M-002] 47 sessions active > 24h without reauthentication
  9. [M-003] 12 endpoints using MAB instead of expected 802.1X

LOW / INFORMATIONAL:
  10. [L-001] 5 unused SGTs: "Test_SGT", "Legacy_Printers", etc.
  11. [L-002] 3 profiler profiles with zero matched endpoints

Summary: 3 Critical | 3 High | 3 Medium | 2 Low

Policy Sets Reviewed: N
Authorization Rules Reviewed: N
Endpoints Analyzed: N
SGTs Evaluated: N
Active Sessions Checked: N
```

## Integration with Other Skills

- Use **pyats-security** to verify device-side 802.1X configuration matches ISE policy (RADIUS server config, dot1x port settings, CoPP for RADIUS traffic)
- Use **gait-session-tracking** to record the full audit in the GAIT immutable audit trail
- Use **markmap-viz** to visualize the ISE policy hierarchy (Policy Sets > AuthZ Rules > Conditions > Results)
- Use **ise-incident-response** when a CRITICAL finding requires immediate endpoint investigation
- Use **servicenow-change-workflow** to create Change Requests for ISE policy remediation

## GAIT Audit Trail

After completing the audit, record the session in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"ISE posture audit completed. ISE: $ISE_BASE. Findings: 3 CRITICAL, 3 HIGH, 3 MEDIUM, 2 LOW. Critical items: default permit-all AuthZ rule, 14 non-compliant endpoints not quarantined, permit-all SGACL on IoT-to-Server cell.","artifacts":[]}}'
```

## Markmap Visualization

Generate a policy hierarchy mind map for the audit report:

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_customize '{"markdown_content":"# ISE Policy Audit\n## CRITICAL\n### Default AuthZ permits all\n### Non-compliant endpoints active\n### Permit-all SGACL\n## HIGH\n### 23% Unknown endpoints\n### SGT overlap (employees + contractors)\n### Shadowed AuthZ rules\n## MEDIUM\n### No posture reassessment\n### Long-lived sessions\n### MAB instead of 802.1X\n## LOW\n### Unused SGTs\n### Dead profiler profiles","theme":"dark"}'
```
