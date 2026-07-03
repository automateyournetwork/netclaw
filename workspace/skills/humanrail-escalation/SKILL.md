---
name: humanrail-escalation
description: "Human-in-the-loop escalation via HumanRail — route low-confidence agent decisions, pre-destructive operation approvals, and ambiguous incident tickets to real human engineers. Human answers are verified and returned as structured output. Workers are paid via Lightning Network. Use when the agent is uncertain, when a destructive change needs explicit human sign-off beyond a ServiceNow CR, or when an ambiguous ticket requires human triage before automated handling."
license: Apache-2.0
user-invokable: true
metadata:
  { "openclaw": { "requires": { "env": ["HUMANRAIL_API_KEY", "HUMANRAIL_MCP_URL"] } } }
---

# HumanRail Escalation

## Safety — Non-Negotiable Rules

**NEVER route tasks that expose internal tooling or infrastructure details to workers.** HumanRail workers are external humans. Task descriptions must be neutral: describe the decision needed without referencing agent names, internal hostnames, file paths, or credentials. Frame the task as a domain question a knowledgeable engineer would answer — not as "an AI agent needs help."

**NEVER use HumanRail as a substitute for ServiceNow Change Management.** A HumanRail approval is an engineering judgment call, not a formal ITSM change record. Pre-destructive approvals via HumanRail are a second safety layer — the ServiceNow CR must still exist and be in `Implement` state before any config push.

**NEVER expose PII, device credentials, or configuration secrets in task payloads.** Sanitize payloads: use device roles ("core router") not hostnames, use interface descriptions not IP addresses where possible.

**ALWAYS wait for `verified` status before acting.** A task with status `submitted` has been answered by a worker but not yet verified. Only act on the output when `status == "verified"`.

## When to Use

| Situation | Use HumanRail | Use ServiceNow CR | Use Slack Escalation |
|-----------|:-------------:|:-----------------:|:--------------------:|
| Agent confidence low — multiple valid interpretations | ✓ | — | — |
| Pre-destructive op beyond normal ITSM gating | ✓ | Required (both) | — |
| Ambiguous incident ticket needs triage | ✓ | — | Notify after |
| P1/P2 in-flight, need immediate human judgment | ✓ | — | ✓ (both) |
| Standard config change with approved CR | — | ✓ | — |
| Routine maintenance window | — | ✓ | — |
| Auto-quarantine endpoint (ISE) | — | — | ✓ (ise-incident-response) |

## MCP Server

| Property | Value |
|----------|-------|
| **Source** | [prime001/humanrail-mcp-server](https://github.com/prime001/humanrail-mcp-server) |
| **Transport** | Streamable HTTP (FastMCP, default port 8100) |
| **Language** | Python 3.10+ |
| **Tools** | 7 (create_task, get_task, wait_for_task, cancel_task, list_tasks, get_usage, health_check) |
| **Auth** | `HUMANRAIL_API_KEY` (Bearer token — `ek_live_...` or `ek_test_...`) |
| **Public endpoint** | `https://humanrail.dev/mcp` (no local install required) |

## How to Run (Local)

```bash
# Install dependencies
pip3 install "mcp[cli]>=1.0.0" httpx

# Start the MCP server (runs on http://127.0.0.1:8100/mcp)
HUMANRAIL_API_KEY=ek_live_your_key python3 $HUMANRAIL_MCP_SCRIPT

# Or use the public endpoint directly (no local install needed):
# Set HUMANRAIL_MCP_URL=https://humanrail.dev/mcp in ~/.openclaw/.env
```

Get your free API key at [humanrail.dev](https://humanrail.dev).

## Available Tools

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `create_task` | `task_type`, `payload`, `output_schema`, `risk_tier?`, `sla_seconds?`, `payout_currency?`, `payout_max_amount?`, `callback_url?`, `metadata?` | Post a task to the human worker pool and return a task ID |
| `get_task` | `task_id` | Get current status and output of a task |
| `wait_for_task` | `task_id`, `poll_interval_seconds?`, `timeout_seconds?` | Block until task reaches terminal state (`verified`, `failed`, `cancelled`, `expired`) |
| `cancel_task` | `task_id` | Cancel a non-terminal task |
| `list_tasks` | `status?`, `task_type?`, `limit?`, `created_after?`, `created_before?` | List tasks with optional filters |
| `get_usage` | — | Org-level usage stats and billing summary |
| `health_check` | — | Verify the HumanRail API is reachable |

---

## Workflow 1: Low-Confidence Decision Escalation

When the agent reaches a decision point where two or more interpretations are equally valid and the wrong choice has significant consequences:

### Phase 1: Assess Uncertainty

Identify what the agent cannot determine autonomously:
- Does the context admit multiple valid network design choices?
- Would an experienced engineer need site-specific knowledge the agent doesn't have?
- Is the downstream impact large enough that getting it wrong matters?

If confidence is high enough to proceed, do so — don't over-escalate. HumanRail has an SLA cost.

### Phase 2: Frame the Decision Neutrally

Write the task payload without referencing agent internals. The worker is an engineer; give them the facts they need.

```
task_type: "technical_decision"
payload:
  title:       "BGP policy clarification needed"
  description: |
    A network change is in progress on a dual-homed edge router.
    The router has two upstream transit providers. Policy options:
      A) Prefer Provider-A for all prefixes (lower latency, higher cost)
      B) Prefer Provider-B for all prefixes (higher latency, lower cost)
      C) Split: prefer Provider-A for /24s and shorter, Provider-B for longer prefixes
    Current traffic: ~8 Gbps mixed. No documented preference in the change ticket.
    What is the recommended policy and why?
  context:     "Standard dual-homed BGP edge, no MPLS, IXP peering not in scope."
output_schema:
  type: object
  required: [recommendation, rationale]
  properties:
    recommendation: {type: string, enum: [A, B, C]}
    rationale:      {type: string, minLength: 20}
risk_tier:     "medium"
sla_seconds:   900
payout_currency: "USD"
payout_max_amount: 1.00
```

### Phase 3: Create and Wait

```
task = create_task(...)
result = wait_for_task(task_id=task["id"], timeout_seconds=900)
```

### Phase 4: Act on Verified Output

Only proceed when `result["status"] == "verified"`. The `result["output"]` field contains the worker's structured response matching your `output_schema`.

---

### *** HUMAN DECISION IN FLIGHT ***

While `wait_for_task` polls, **do not proceed with the ambiguous action**. Post a Slack status update:

> "⏳ Waiting for human engineer input on [topic]. Task ID: [id]. ETA: [sla_seconds]s."

If the task expires or fails, fall back to the conservative option and create a ServiceNow incident for manual follow-up.

---

## Workflow 2: Pre-Destructive Operation Approval

For operations the agent is authorized to perform but that are irreversible or high-blast-radius — beyond the standard ServiceNow CR gate:

**Examples:** device reload, `write erase`, BGP peer teardown affecting production traffic, ISE policy purge.

### Phase 1: Baseline and Summarize

Before asking for approval, gather the current state so the human reviewer has complete context.

```bash
# Capture pre-change state first
python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" get_interface_brief '{"device":"core-rtr-01"}'
python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" get_bgp_summary '{"device":"core-rtr-01"}'
```

### Phase 2: Build Approval Request

```
task_type: "change_approval"
payload:
  title:       "Production reload approval — core edge router"
  description: |
    A device reload is requested to apply a software upgrade from IOS-XE 17.9 to 17.12.
    Pre-change state:
      - BGP peers: 4 active (2 transit, 2 iBGP) — all ESTABLISHED
      - Active sessions: 847 flows
      - Estimated downtime: 3-5 minutes
      - Rollback: IOS-XE 17.9 image retained in flash
    ServiceNow CR: [CR number] — in Implement state.
    Should this reload proceed NOW or be deferred to the next maintenance window?
  urgency:     "high"
output_schema:
  type: object
  required: [decision, notes]
  properties:
    decision: {type: string, enum: [proceed, defer]}
    notes:    {type: string}
risk_tier:     "high"
sla_seconds:   300
payout_currency: "USD"
payout_max_amount: 2.00
```

### Phase 3: Gate on Response

```
result = wait_for_task(task_id=task["id"], timeout_seconds=300)
if result["output"]["decision"] == "proceed":
    # Execute the destructive operation
else:
    # Defer — log in GAIT, update ServiceNow CR
```

---

### *** HUMAN APPROVAL GATE ***

**STOP.** The destructive operation MUST NOT execute until `result["status"] == "verified"` AND `result["output"]["decision"] == "proceed"`.

If `wait_for_task` times out: default to DEFER. Update the ServiceNow CR with status "awaiting human authorization" and notify the Slack incident channel.

---

## Workflow 3: Ambiguous Incident Ticket Triage

When an inbound ServiceNow incident has insufficient information to determine severity, affected CIs, or the correct response team:

### Phase 1: Extract What's Known

Pull the raw incident from ServiceNow and identify the gaps:
- Missing: affected device? Affected service? Symptom details?
- Conflicting: multiple possible root causes with different response paths?
- Stale: ticket opened hours ago with no updates — still valid?

### Phase 2: Route to Human Triage

```
task_type: "incident_triage"
payload:
  title:       "Triage: ambiguous network incident ticket"
  description: |
    An incident ticket has insufficient detail for automated handling.
    Ticket summary: [short_description from ServiceNow]
    Known facts:
      - Reported by: [caller_id role/team, no PII]
      - Opened: [timestamp]
      - Impact field: [value]
      - Description: [full description, sanitized]
    Missing or conflicting:
      - [list gaps]
    Please determine: severity (P1/P2/P3/P4), affected CI(s) if identifiable,
    and recommended response team (NOC/NetEng/Security/Application).
output_schema:
  type: object
  required: [severity, team, notes]
  properties:
    severity: {type: string, enum: [P1, P2, P3, P4]}
    team:     {type: string, enum: [NOC, NetEng, Security, Application, Unknown]}
    notes:    {type: string, minLength: 10}
risk_tier:     "medium"
sla_seconds:   600
payout_currency: "USD"
payout_max_amount: 0.50
```

### Phase 3: Apply Triage Output

Use the verified output to:
1. Update the ServiceNow incident severity and assignment group
2. Post a Slack alert at the appropriate level (`#netclaw-alerts` for P1/P2)
3. Trigger the relevant response workflow

---

## Escalation Summary Report Template

Use this when closing a HumanRail-escalated session:

```
HUMANRAIL ESCALATION SUMMARY
==============================
Task ID:       [task_id]
Task Type:     [task_type]
Opened:        [ISO 8601 timestamp]
Resolved:      [ISO 8601 timestamp]
Worker SLA:    [sla_seconds]s / actual: [elapsed]s

Question Summary:
  [One-paragraph neutral description of what was asked]

Human Decision:
  [Paste result["output"] here]

Action Taken:
  [What the agent did based on the decision]

Outcome:
  [ ] Operation completed successfully
  [ ] Operation deferred — scheduled for [date/window]
  [ ] Escalated to [team] — ServiceNow [INC/CHG number]
```

---

## Checklist

Use before closing any HumanRail-escalated action:

- [ ] Task created with neutral, non-internal-leaking payload
- [ ] `status == "verified"` confirmed before acting (not just "submitted")
- [ ] Human decision applied exactly — no agent interpretation of ambiguous output
- [ ] Slack status posted during wait period
- [ ] ServiceNow CR updated with escalation record (if change-related)
- [ ] GAIT audit trail records the task ID, human decision, and action taken
- [ ] If task expired/failed: conservative fallback applied and INC created

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **servicenow-change-workflow** | HumanRail approval is a second-layer gate — ServiceNow CR must still be in `Implement` state; HumanRail output is added as a work note |
| **ise-incident-response** | Use HumanRail for low-confidence risk assessments before the `*** HUMAN DECISION POINT ***` gate when the on-call engineer is not immediately available |
| **slack-incident-workflow** | Post a Slack update when a HumanRail task is created; post result when resolved |
| **gait-session-tracking** | Always record HumanRail task IDs, decisions, and resulting actions in the GAIT audit trail |
| **pyats-config-mgmt** | Use pre-destructive approval workflow before executing high-risk config pushes |

---

## Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `HUMANRAIL_API_KEY` | Yes | `ek_live_abc123...` | API key from [humanrail.dev](https://humanrail.dev) |
| `HUMANRAIL_MCP_URL` | Yes | `http://127.0.0.1:8100/mcp` | MCP endpoint (local server or `https://humanrail.dev/mcp`) |
| `HUMANRAIL_MCP_SCRIPT` | No | `/path/to/server.py` | Path to local server.py (set by install.sh; not needed if using public endpoint) |
| `HUMANRAIL_BASE_URL` | No | `https://api.humanrail.dev/v1` | REST API base URL (default: `https://api.humanrail.dev/v1`) |
