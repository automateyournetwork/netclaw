---
name: gns3-project-lifecycle
description: "Manage GNS3 network lab projects - create, open, close, delete, clone, export/import"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["GNS3_URL", "GNS3_USER", "GNS3_PASSWORD"]
---

# GNS3 Project Lifecycle

Manage GNS3 network lab projects through natural language commands. Create new labs, open/close existing projects, clone for experimentation, and export/import for sharing.

## When to Use

- Creating a new GNS3 lab environment for testing or training
- Opening or closing existing projects to manage resources
- Cloning projects before making experimental changes
- Exporting projects to share with colleagues
- Importing projects from archives
- Listing all available labs on the GNS3 server
- Deleting projects that are no longer needed

## MCP Server

- **Command**: `python3 -u mcp-servers/gns3-mcp-server/gns3_mcp_server.py` (stdio transport)
- **Requires**: `GNS3_URL`, `GNS3_USER`, `GNS3_PASSWORD` environment variables

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `gns3_list_projects` | None | List all GNS3 projects with name, status, and path |
| `gns3_create_project` | name, auto_open?, auto_close?, auto_start? | Create a new project |
| `gns3_get_project` | project_id | Get detailed project information |
| `gns3_open_project` | project_id | Open a closed project |
| `gns3_close_project` | project_id | Close an opened project and release resources |
| `gns3_delete_project` | project_id | Delete a project and all its resources |
| `gns3_clone_project` | project_id, new_name, reset_mac_addresses? | Clone an existing project |
| `gns3_export_project` | project_id, include_snapshots?, include_images?, compression? | Export project as archive |
| `gns3_import_project` | file_path, name? | Import project from archive |

## Workflow Examples

### Create and Manage a Lab

```bash
# List existing projects
"List all my GNS3 labs"

# Create a new project
"Create a new GNS3 lab called routing-test"

# Open a project
"Open the routing-test project"

# Close when done
"Close the routing-test project"
```

### Clone Before Experimentation

```bash
# Clone a project before making risky changes
"Clone routing-test as routing-test-experiment"

# Work on the clone, then delete if not needed
"Delete routing-test-experiment"
```

### Export and Import

```bash
# Export for sharing
"Export the routing-test project with snapshots"

# Import a shared project
"Import the project from /tmp/routing-test.gns3project"
```

## Integration with Other Skills

- **gns3-node-operations**: After creating a project, add nodes
- **gns3-link-management**: Connect nodes in the project
- **gns3-snapshot-ops**: Save project state before changes

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| GNS3_NOT_FOUND | Project doesn't exist | Check project name/ID |
| GNS3_CONFLICT | Project is locked or name exists | Wait for unlock or use different name |
| GNS3_AUTH_FAILED | Authentication failed | Verify GNS3_USER and GNS3_PASSWORD |

## Notes

- Projects can be referenced by name or UUID
- Close projects to release compute resources
- Lab-only operations - no ServiceNow CR gating required
- All operations logged to GAIT audit trail
