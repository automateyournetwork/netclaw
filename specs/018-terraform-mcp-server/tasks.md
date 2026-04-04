# Tasks: Terraform MCP Server Integration

**Feature**: 018-terraform-mcp-server | **Date**: 2026-04-04
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

### T1: Register Terraform MCP Server in openclaw.json
**File**: `config/openclaw.json`
**Action**: Add MCP server configuration

```json
{
  "terraform-mcp": {
    "command": "terraform-mcp-server",
    "args": ["--enable-all-toolsets"],
    "env": {
      "TFE_TOKEN": "${TFE_TOKEN}",
      "TFE_ADDRESS": "${TFE_ADDRESS}"
    }
  }
}
```

**Acceptance**: Server appears in `openclaw list` output

### T2: Add Environment Variables to .env.example
**File**: `.env.example`
**Action**: Add Terraform environment variables

```bash
# Terraform MCP Server
TFE_TOKEN=your_hcp_terraform_token
# TFE_ADDRESS=https://tfe.example.com  # For self-hosted TFE
```

**Acceptance**: Variables documented with comments

---

## P1: Skill Creation

### T3: Create terraform-registry Skill
**File**: `workspace/skills/terraform-registry/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: search_providers, get_provider_details, search_modules, get_module_details
- Example queries (provider search, module discovery)
- Prerequisites

**Acceptance**: Skill invocable via `/terraform-registry`

### T4: Create terraform-workspaces Skill
**File**: `workspace/skills/terraform-workspaces/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: list_workspaces, get_workspace, create_workspace, trigger_run, get_run_status
- Example queries (workspace management)
- Prerequisites (TFE_TOKEN required)

**Acceptance**: Skill invocable via `/terraform-workspaces`

### T5: Create terraform-operations Skill
**File**: `workspace/skills/terraform-operations/SKILL.md`
**Action**: Create skill documentation

**Content Requirements**:
- Skill name and description
- Tool list: terraform_init, terraform_validate, terraform_fmt, terraform_plan, terraform_apply, terraform_destroy
- Example queries
- Security notes: apply/destroy require ServiceNow CR
- Prerequisites

**Acceptance**: Skill invocable via `/terraform-operations`

---

## P1: Configuration Updates

### T6: Update install.sh with Terraform Dependencies
**File**: `scripts/install.sh`
**Action**: Add Go/terraform-mcp-server installation

```bash
# Terraform MCP Server
if command -v terraform-mcp-server &> /dev/null; then
    echo "✓ terraform-mcp-server installed"
else
    echo "⚠ Install terraform-mcp-server:"
    echo "  go install github.com/hashicorp/terraform-mcp-server@latest"
fi

# Also check for Terraform CLI
if command -v terraform &> /dev/null; then
    echo "✓ Terraform CLI available"
else
    echo "⚠ Install Terraform CLI for local operations"
fi
```

**Acceptance**: Installation script checks for dependencies

### T7: Update SOUL.md Skill Index
**File**: `SOUL.md`
**Action**: Add Terraform skills to index

```markdown
### Infrastructure as Code
- `/terraform-registry` - Provider and module discovery
- `/terraform-workspaces` - HCP Terraform workspace management
- `/terraform-operations` - Plan, apply, and state operations
```

**Acceptance**: Skills appear in SOUL.md index

---

## P2: Documentation Updates

### T8: Update README.md Architecture Section
**File**: `README.md`
**Action**: Add Terraform to MCP server count and integration list

- Update total MCP server count
- Add Terraform to integrations table
- Update tool count

**Acceptance**: README reflects new integration

### T9: Update README.md Tool Count
**File**: `README.md`
**Action**: Update total tool count (+15 tools)

**Acceptance**: Tool count accurate

### T10: Create Terraform Section in README
**File**: `README.md`
**Action**: Add Terraform integration description

```markdown
### Terraform (15+ tools)
Infrastructure as Code capabilities with Registry, Operations, and HCP Terraform.
- Provider and module discovery from Registry
- HCP Terraform workspace management
- Local Terraform operations (init, plan, apply)
- Apply/destroy gated by ServiceNow CR
```

**Acceptance**: Terraform documented in README

### T11: Update Skill Count in README
**File**: `README.md`
**Action**: Update total skill count (+3 skills)

**Acceptance**: Skill count accurate

---

## P2: UI Integration

### T12: Add Terraform to UI INTEGRATION_CATALOG
**File**: `ui/netclaw-visual/server.js`
**Action**: Add Terraform integration entry

```javascript
{
  id: 'terraform',
  name: 'Terraform',
  category: 'Infrastructure as Code',
  prefixes: ['terraform-'],
  color: '#7b42bc',
  transport: 'stdio',
  toolEstimate: 15,
  skills: ['terraform-registry', 'terraform-workspaces', 'terraform-operations']
}
```

**Also update ENV_MAP**:
```javascript
'terraform': ['TFE_TOKEN', 'TFE_ADDRESS']
```

**Acceptance**: Terraform appears in UI integration catalog

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

- [ ] `terraform-mcp-server --help` works
- [ ] Server appears in `openclaw list`
- [ ] All 3 skills invocable
- [ ] Skills appear in SOUL.md
- [ ] Terraform in README integrations
- [ ] Terraform in UI catalog
- [ ] Tool count updated
- [ ] Skill count updated
