# Tasks: Splunk MCP Server Integration

**Feature**: 017-splunk-mcp-server | **Date**: 2026-04-04
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

## Task Overview

| Category | Tasks | Priority |
|----------|-------|----------|
| MCP Registration | 2 | P0 |
| Skills | 3 | P1 |
| Configuration | 2 | P1 |
| Documentation | 4 | P2 |
| UI Integration | 1 | P2 |

---

## P0: MCP Server Registration

### T1: Register Splunk MCP Server in openclaw.json
**File**: `config/openclaw.json`
**Action**: Add MCP server configuration

```json
{
  "splunk-mcp": {
    "command": "npx",
    "args": ["@splunk/mcp-server2", "--transport", "stdio"],
    "env": {
      "SPLUNK_HOST": "${SPLUNK_HOST}",
      "SPLUNK_PORT": "${SPLUNK_PORT}",
      "SPLUNK_USERNAME": "${SPLUNK_USERNAME}",
      "SPLUNK_PASSWORD": "${SPLUNK_PASSWORD}",
      "SPLUNK_VERIFY_SSL": "${SPLUNK_VERIFY_SSL}"
    }
  }
}
```

**Acceptance**: Server appears in `openclaw list` output

### T2: Add Environment Variables to .env.example
**File**: `.env.example`
**Action**: Add Splunk environment variables

```bash
# Splunk MCP Server
SPLUNK_HOST=splunk.example.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=netclaw
SPLUNK_PASSWORD=your_password_here
# SPLUNK_VERIFY_SSL=false  # For self-signed certs
```

**Acceptance**: Variables documented with comments

---

## P1: Skill Creation

### T3: Create splunk-search Skill
**File**: `workspace/skills/splunk-search/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: validate_spl, search_oneshot, search_export
- Example queries (SPL syntax, time ranges)
- Output format: Markdown tables (per clarification)
- Prerequisites

**Acceptance**: Skill invocable via `/splunk-search`

### T4: Create splunk-indexes Skill
**File**: `workspace/skills/splunk-indexes/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: get_indexes, get_config
- Example queries (index discovery)
- Prerequisites

**Acceptance**: Skill invocable via `/splunk-indexes`

### T5: Create splunk-saved Skill
**File**: `workspace/skills/splunk-saved/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: get_saved_searches, run_saved_search
- Example queries
- Prerequisites

**Acceptance**: Skill invocable via `/splunk-saved`

---

## P1: Configuration Updates

### T6: Update install.sh with Splunk Dependencies
**File**: `scripts/install.sh`
**Action**: Add npm/npx installation check

```bash
# Splunk MCP Server
if command -v npx &> /dev/null; then
    echo "✓ npx available for Splunk MCP"
else
    echo "⚠ Install Node.js/npm for Splunk MCP"
fi
```

**Acceptance**: Installation script checks for npx

### T7: Update SOUL.md Skill Index
**File**: `SOUL.md`
**Action**: Add Splunk skills to index

```markdown
### Log Management
- `/splunk-search` - SPL query execution and validation
- `/splunk-indexes` - Index discovery and metadata
- `/splunk-saved` - Saved search management
```

**Acceptance**: Skills appear in SOUL.md index

---

## P2: Documentation Updates

### T8: Update README.md Architecture Section
**File**: `README.md`
**Action**: Add Splunk to MCP server count and integration list

- Update total MCP server count
- Add Splunk to integrations table
- Update tool count

**Acceptance**: README reflects new integration

### T9: Update README.md Tool Count
**File**: `README.md`
**Action**: Update total tool count (+7 tools)

**Acceptance**: Tool count accurate

### T10: Create Splunk Section in README
**File**: `README.md`
**Action**: Add Splunk integration description

```markdown
### Splunk (7 tools)
Log aggregation and SPL query capabilities with built-in validation.
- SPL query validation and execution
- Index discovery and metadata
- Saved search management
- Output sanitization for sensitive data
```

**Acceptance**: Splunk documented in README

### T11: Update Skill Count in README
**File**: `README.md`
**Action**: Update total skill count (+3 skills)

**Acceptance**: Skill count accurate

---

## P2: UI Integration

### T12: Add Splunk to UI INTEGRATION_CATALOG
**File**: `ui/netclaw-visual/server.js`
**Action**: Add Splunk integration entry

```javascript
{
  id: 'splunk',
  name: 'Splunk',
  category: 'Log Management',
  prefixes: ['splunk-'],
  color: '#65a637',
  transport: 'stdio',
  toolEstimate: 7,
  skills: ['splunk-search', 'splunk-indexes', 'splunk-saved']
}
```

**Also update ENV_MAP**:
```javascript
'splunk': ['SPLUNK_HOST', 'SPLUNK_PORT', 'SPLUNK_USERNAME', 'SPLUNK_PASSWORD', 'SPLUNK_VERIFY_SSL']
```

**Acceptance**: Splunk appears in UI integration catalog

---

## Dependency Graph

```
T1 (MCP registration) ──┬──> T3, T4, T5 (Skills)
T2 (env variables)     │
                       └──> T6 (install.sh)
                            │
T3, T4, T5 ────────────────> T7 (SOUL.md)
                            │
T7 ────────────────────────> T8, T9, T10, T11 (README)
                            │
T8 ────────────────────────> T12 (UI)
```

## Verification Checklist

- [ ] `npx @splunk/mcp-server2 --help` works
- [ ] Server appears in `openclaw list`
- [ ] All 3 skills invocable
- [ ] Skills appear in SOUL.md
- [ ] Splunk in README integrations
- [ ] Splunk in UI catalog
- [ ] Tool count updated
- [ ] Skill count updated
