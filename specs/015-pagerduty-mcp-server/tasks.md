# Tasks: PagerDuty MCP Server Integration

**Feature**: 015-pagerduty-mcp-server | **Date**: 2026-04-04
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

## Task Overview

| Category | Tasks | Priority |
|----------|-------|----------|
| MCP Registration | 2 | P0 |
| Skills | 4 | P1 |
| Configuration | 2 | P1 |
| Documentation | 4 | P2 |
| UI Integration | 1 | P2 |

---

## P0: MCP Server Registration

### T1: Register PagerDuty MCP Server in openclaw.json
**File**: `config/openclaw.json`
**Action**: Add MCP server configuration

```json
{
  "pagerduty-mcp": {
    "command": "uvx",
    "args": ["pagerduty-mcp", "--enable-write-tools"],
    "env": {
      "PAGERDUTY_USER_API_KEY": "${PAGERDUTY_USER_API_KEY}"
    }
  }
}
```

**Acceptance**: Server appears in `openclaw list` output

### T2: Add Environment Variables to .env.example
**File**: `.env.example`
**Action**: Add PagerDuty environment variables

```bash
# PagerDuty MCP Server
PAGERDUTY_USER_API_KEY=your_pagerduty_api_token
# PAGERDUTY_API_HOST=https://api.eu.pagerduty.com  # For EU customers
```

**Acceptance**: Variables documented with comments

---

## P1: Skill Creation

### T3: Create pagerduty-incidents Skill
**File**: `workspace/skills/pagerduty-incidents/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: list_incidents, get_incident, get_alert_from_incident, list_alerts_from_incident, list_incident_notes, get_outlier_incident, get_past_incidents, get_related_incidents, create_incident, manage_incidents, add_note_to_incident, add_responders
- Example queries
- Prerequisites

**Acceptance**: Skill invocable via `/pagerduty-incidents`

### T4: Create pagerduty-oncall Skill
**File**: `workspace/skills/pagerduty-oncall/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: list_oncalls, get_schedule, list_schedules, list_schedule_users, get_escalation_policy, list_escalation_policies, create_schedule, update_schedule, create_schedule_override
- Example queries
- Prerequisites

**Acceptance**: Skill invocable via `/pagerduty-oncall`

### T5: Create pagerduty-services Skill
**File**: `workspace/skills/pagerduty-services/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: get_service, list_services, create_service, update_service
- Example queries
- Prerequisites

**Acceptance**: Skill invocable via `/pagerduty-services`

### T6: Create pagerduty-orchestration Skill
**File**: `workspace/skills/pagerduty-orchestration/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: get_event_orchestration, get_event_orchestration_global, get_event_orchestration_router, get_event_orchestration_service, list_event_orchestrations, update_event_orchestration_router, append_event_orchestration_router_rule
- Example queries
- Prerequisites

**Acceptance**: Skill invocable via `/pagerduty-orchestration`

---

## P1: Configuration Updates

### T7: Update install.sh with PagerDuty Dependencies
**File**: `scripts/install.sh`
**Action**: Add uvx/pagerduty-mcp installation check

```bash
# PagerDuty MCP Server
if command -v uvx &> /dev/null; then
    echo "✓ uvx available for PagerDuty MCP"
else
    echo "⚠ Install uvx for PagerDuty MCP: pip install uvx"
fi
```

**Acceptance**: Installation script checks for uvx

### T8: Update SOUL.md Skill Index
**File**: `SOUL.md`
**Action**: Add PagerDuty skills to index

```markdown
### Incident Management
- `/pagerduty-incidents` - Incident visibility and management
- `/pagerduty-oncall` - On-call schedules and escalation
- `/pagerduty-services` - Service catalog and health
- `/pagerduty-orchestration` - Event routing configuration
```

**Acceptance**: Skills appear in SOUL.md index

---

## P2: Documentation Updates

### T9: Update README.md Architecture Section
**File**: `README.md`
**Action**: Add PagerDuty to MCP server count and integration list

- Update total MCP server count
- Add PagerDuty to integrations table
- Update tool count

**Acceptance**: README reflects new integration

### T10: Update README.md Tool Count
**File**: `README.md`
**Action**: Update total tool count (+70 tools)

**Acceptance**: Tool count accurate

### T11: Create PagerDuty Section in README
**File**: `README.md`
**Action**: Add PagerDuty integration description

```markdown
### PagerDuty (70 tools)
Incident management, on-call visibility, and event orchestration.
- Incident queries and management
- On-call schedule visibility
- Service catalog access
- Event routing configuration
```

**Acceptance**: PagerDuty documented in README

### T12: Update Skill Count in README
**File**: `README.md`
**Action**: Update total skill count (+4 skills)

**Acceptance**: Skill count accurate

---

## P2: UI Integration

### T13: Add PagerDuty to UI INTEGRATION_CATALOG
**File**: `ui/netclaw-visual/server.js`
**Action**: Add PagerDuty integration entry

```javascript
{
  id: 'pagerduty',
  name: 'PagerDuty',
  category: 'Incident Management',
  prefixes: ['pagerduty-'],
  color: '#06ac38',
  transport: 'stdio',
  toolEstimate: 70,
  skills: ['pagerduty-incidents', 'pagerduty-oncall', 'pagerduty-services', 'pagerduty-orchestration']
}
```

**Also update ENV_MAP**:
```javascript
'pagerduty': ['PAGERDUTY_USER_API_KEY']
```

**Acceptance**: PagerDuty appears in UI integration catalog

---

## Dependency Graph

```
T1 (MCP registration) ──┬──> T3, T4, T5, T6 (Skills)
T2 (env variables)     │
                       └──> T7 (install.sh)
                            │
T3, T4, T5, T6 ────────────> T8 (SOUL.md)
                            │
T8 ────────────────────────> T9, T10, T11, T12 (README)
                            │
T9 ────────────────────────> T13 (UI)
```

## Verification Checklist

- [ ] `uvx pagerduty-mcp --help` works
- [ ] Server appears in `openclaw list`
- [ ] All 4 skills invocable
- [ ] Skills appear in SOUL.md
- [ ] PagerDuty in README integrations
- [ ] PagerDuty in UI catalog
- [ ] Tool count updated
- [ ] Skill count updated
