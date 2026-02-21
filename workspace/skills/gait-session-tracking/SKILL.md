---
name: gait-session-tracking
description: "GAIT session lifecycle management - branch creation, turn recording, audit logging for every NetClaw operation"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["GAIT_MCP_SCRIPT"] } } }
---

# GAIT Session Tracking

Track every NetClaw session with full audit history using the GAIT version control system. Every network engineering action -- configuration changes, health checks, troubleshooting steps, reconciliation runs -- is recorded as a Git-backed audit trail.

**This skill is mandatory.** Every NetClaw session MUST begin with `gait_branch` and end with `gait_log`.

## How to Call the Tools

The GAIT MCP server provides 9 tools. Call them via mcp-call:

### Check Repository Status

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_status '{}'
```

Returns current branch, uncommitted changes, and repository state.

### Initialize a New GAIT Repository

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_init '{}'
```

Creates a new GAIT repository if one does not already exist. Run this once during initial NetClaw setup.

### Create a New Branch (SESSION START)

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_branch '{"branch_name":"health-check-r1-2026-02-21"}'
```

**Every session begins here.** Use a descriptive branch name that includes the action type, target device(s), and date. Examples:
- `health-check-r1-2026-02-21`
- `ospf-troubleshoot-core-2026-02-21`
- `config-deploy-acl-update-2026-02-21`
- `netbox-reconcile-site-hq-2026-02-21`
- `security-audit-dmz-2026-02-21`

### Switch to an Existing Branch

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_checkout '{"branch_name":"health-check-r1-2026-02-21"}'
```

Use this to resume a previous session or switch context between parallel investigations.

### Record an AI Turn (PRIMARY RECORDING TOOL)

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"User asked to check CPU on R1","response":"Ran show processes cpu sorted. CPU 5-min avg: 12%. Status: HEALTHY.","artifacts":["show_proc_cpu_r1.txt"]}'
```

**Record a turn after every significant action.** Each turn captures:
- **prompt**: What was asked or what triggered the action
- **response**: What data was collected and what the result was
- **artifacts**: List of files produced (optional)

### View Commit History (SESSION END)

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_log '{}'
```

**Every session ends here.** Display the full audit log before concluding. This provides the user with a complete record of everything that happened.

### Show Commit Details

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_show '{"commit_ref":"HEAD"}'
```

Inspect a specific commit to see its full content. Use `HEAD`, `HEAD~1`, or a commit hash.

### Pin Important Commits

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_pin '{"commit_ref":"HEAD","label":"pre-change-baseline"}'
```

Mark critical moments in a session so they can be easily found later. Common pin labels:
- `pre-change-baseline` -- state before any modifications
- `post-change-verified` -- state after changes are validated
- `critical-finding` -- an important discovery during investigation
- `rollback-point` -- safe state to return to if needed

### Summarize and Squash Turns

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_summarize_and_squash '{}'
```

Consolidate multiple granular turns into a single summary commit. Use at the end of a long session to create a clean audit record.

## Mandatory Session Lifecycle

Every NetClaw session follows this exact lifecycle:

### 1. Session Start -- Create Branch

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_branch '{"branch_name":"ACTION-TYPE-TARGET-DATE"}'
```

### 2. During Session -- Record Every Turn

After each meaningful action (show command, config change, API call, verification), record a turn:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"WHAT_WAS_ASKED","response":"WHAT_DATA_COLLECTED_AND_WHAT_CHANGED_AND_VERIFICATION_RESULT","artifacts":[]}'
```

**Record format guidelines:**
- **prompt**: State clearly what the user asked or what triggered the action
- **response**: Include three parts:
  1. What data was collected (commands run, API responses)
  2. What changed (config applied, ticket created, NetBox updated)
  3. Verification result (HEALTHY/WARNING/CRITICAL, pass/fail, before/after diff)
- **artifacts**: List any files generated (logs, configs, diagrams, reports)

### 3. Session End -- Display Log

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_log '{}'
```

Always show the session log to the user so they have a complete record.

## Recording Examples by Skill Type

### Health Check Turn

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"Run full health check on R1","response":"Collected: show version, show processes cpu sorted, show processes memory sorted, show ip interface brief, show interfaces, show ntp associations, show logging. Results: CPU 12% HEALTHY, Memory 45% HEALTHY, Interfaces 4/5 up WARNING (Gi2 down), NTP synced HEALTHY, no critical log patterns. Overall: WARNING.","artifacts":["health-report-r1.txt"]}'
```

### Configuration Change Turn

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"Apply ACL update to block 192.168.50.0/24 on R1 Gi1","response":"Pre-change: captured running-config. Applied: ip access-list extended BLOCK-LIST, permit/deny entries. Post-change: verified ACL in show access-lists, tested with ping from blocked subnet -- dropped as expected. Change verified successfully.","artifacts":["pre-change-config-r1.txt","post-change-config-r1.txt","acl-diff.txt"]}'
```

### Troubleshooting Turn

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"Investigate OSPF adjacency failure between R1 and R3","response":"Checked show ip ospf neighbor on R1 -- R3 missing. Checked show ip ospf interface on both -- area mismatch: R1 area 0, R3 area 1 on shared link. Root cause identified: area misconfiguration on R3 Gi0/1.","artifacts":["ospf-neighbor-r1.txt","ospf-interface-r1.txt","ospf-interface-r3.txt"]}'
```

### NetBox Reconciliation Turn

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"Reconcile R1 interfaces against NetBox","response":"Live state: 5 interfaces discovered via show ip interface brief. NetBox state: 4 interfaces documented. Drift detected: Gi5 exists on device but missing from NetBox. Gi2 documented in NetBox but admin-down on device. Reconciliation report generated.","artifacts":["reconcile-report-r1.json"]}'
```

## Integration with ALL Other Skills

GAIT session tracking is used by every other NetClaw skill for audit compliance:

- **pyats-health-check** -- Record each health check step and overall results
- **pyats-topology** -- Record discovered neighbors and topology changes
- **pyats-security** -- Record audit findings by severity
- **pyats-config-mgmt** -- Record pre-change baseline, change applied, post-change verification
- **pyats-troubleshoot** -- Record each investigation step and root cause
- **pyats-routing** -- Record routing table snapshots and protocol state
- **netbox-reconcile** -- Record drift detection and remediation actions
- **drawio-diagram** -- Record diagram generation with source data reference
- **markmap-viz** -- Record mind map creation with underlying data
- **rfc-lookup** -- Record RFC references used during investigation
- **wikipedia-research** -- Record protocol research context
- **servicenow-incidents** -- Record ticket creation and updates
- **nvd-cve** -- Record vulnerability findings and remediation tracking

## When to Use

Always. Every NetClaw session. No exceptions. This is the audit backbone of the system.
