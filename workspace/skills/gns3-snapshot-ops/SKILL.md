---
name: gns3-snapshot-ops
description: "Manage GNS3 project snapshots - create, restore, delete for safe experimentation"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["GNS3_URL", "GNS3_USER", "GNS3_PASSWORD"]
---

# GNS3 Snapshot Operations

Create and manage snapshots of GNS3 project state. Save checkpoints before risky changes and restore to known-good states.

## When to Use

- Saving project state before making experimental changes
- Creating checkpoints at key milestones (baseline, after config, etc.)
- Restoring to a previous state after a failed experiment
- Rolling back configuration mistakes
- Comparing different configurations by restoring snapshots
- Training scenarios with repeatable starting points

## MCP Server

- **Command**: `python3 -u mcp-servers/gns3-mcp-server/gns3_mcp_server.py` (stdio transport)
- **Requires**: `GNS3_URL`, `GNS3_USER`, `GNS3_PASSWORD` environment variables

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `gns3_list_snapshots` | project_id | List all snapshots for a project |
| `gns3_create_snapshot` | project_id, name | Create a snapshot of current state |
| `gns3_restore_snapshot` | project_id, snapshot_id | Restore project to snapshot state |
| `gns3_delete_snapshot` | project_id, snapshot_id | Delete a snapshot |

## Workflow Examples

### Safe Experimentation

```bash
# Create baseline before changes
"Create a snapshot called baseline for routing-test"

# Make some changes...
# (configure OSPF, add new links, etc.)

# Something went wrong? Restore to baseline
"Restore routing-test to baseline snapshot"
```

### Milestone Checkpoints

```bash
# Save after initial topology setup
"Create a snapshot called topology-complete for routing-test"

# Save after basic configuration
"Create a snapshot called basic-config for routing-test"

# Save after full configuration
"Create a snapshot called full-config for routing-test"

# List all checkpoints
"List snapshots for routing-test"
```

### Training Scenarios

```bash
# Create starting point for students
"Create a snapshot called student-starting-point for training-lab"

# After each session, restore to starting point
"Restore training-lab to student-starting-point"
```

### Clean Up Old Snapshots

```bash
# Remove snapshots no longer needed
"Delete the old-test snapshot from routing-test"
```

## Integration with Other Skills

- **gns3-project-lifecycle**: Create project before snapshots
- **gns3-node-operations**: Stop nodes before snapshot for cleaner state
- **gns3-link-management**: Topology is preserved in snapshots

## What Snapshots Include

- All node configurations and state
- All links and topology
- Node positions on canvas
- Project settings

## Best Practices

1. **Descriptive names**: Use names like `before-ospf-config` not `snap1`
2. **Create before changes**: Always snapshot before risky operations
3. **Stop nodes first**: Cleaner snapshots when nodes are stopped
4. **Clean up regularly**: Delete old snapshots to save disk space

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| GNS3_NOT_FOUND | Project or snapshot doesn't exist | Check names/IDs |
| GNS3_CONFLICT | Snapshot name already exists | Use unique names |

## Notes

- Snapshots can be referenced by name or UUID
- Restore stops running nodes automatically
- Snapshots are stored within the project directory
- Snapshot names must be unique within a project
- All operations logged to GAIT audit trail
