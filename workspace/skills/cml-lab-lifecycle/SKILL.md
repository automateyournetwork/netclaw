---
name: cml-lab-lifecycle
description: Cisco CML lab lifecycle management — create, start, stop, wipe, delete, clone, import/export labs
version: 1.0.0
tags: [cml, labs, simulation, lifecycle]
---

# CML Lab Lifecycle Management

You have access to Cisco Modeling Labs (CML) via the CML MCP server. This skill covers full lab lifecycle operations — everything from creating a brand-new lab to cleaning up finished ones.

## MCP Server

- **Command**: `cml-mcp` (pip-installed, stdio transport)
- **Requires**: `CML_URL`, `CML_USERNAME`, `CML_PASSWORD` environment variables
- **Optional**: `CML_VERIFY_SSL` (default: true)

## Available Tools

### Lab CRUD Operations

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `create_lab` | `title` | Create a new empty lab with a title |
| `get_lab` | `lab_id` or `lab_title` | Get lab details (state, node count, link count) |
| `get_labs` | none | List all labs on the CML server |
| `start_lab` | `lab_id` or `lab_title` | Start all nodes in a lab (boot the topology) |
| `stop_lab` | `lab_id` or `lab_title` | Stop all nodes in a lab (graceful shutdown) |
| `wipe_lab` | `lab_id` or `lab_title` | Wipe lab node configurations (reset to factory) |
| `delete_lab` | `lab_id` or `lab_title` | Delete a lab permanently |

### Lab Import/Export

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `import_lab` | `topology` (YAML string) | Import a lab from CML topology YAML |
| `export_lab` | `lab_id` or `lab_title` | Export a lab as CML topology YAML |
| `clone_lab` | `lab_id` or `lab_title` | Clone an existing lab (deep copy) |
| `download_lab_configs` | `lab_id` or `lab_title` | Download all node configs from a running lab |

## Workflow: Create a Lab from Scratch (Slack)

When a user says something like "build me a 3-router OSPF lab" in Slack:

1. **Create the lab**: Use `create_lab` with a descriptive title
2. **Add nodes**: (See cml-topology-builder skill) Add routers, switches, servers
3. **Wire the topology**: (See cml-topology-builder skill) Create interfaces and links
4. **Apply configs**: (See cml-node-operations skill) Set startup configs
5. **Start the lab**: Use `start_lab` to boot everything
6. **Verify convergence**: (See cml-node-operations skill) Execute show commands to verify routing
7. **Report back**: Tell the user the lab is ready with node names and management IPs

### Example Slack Conversations

**"Build me a 3-router OSPF lab"**
→ create_lab "OSPF Lab - 3 Routers"
→ create_node x3 (IOSv: R1, R2, R3)
→ create_interface + create_link (R1-R2, R2-R3, R1-R3 full mesh)
→ set_node_config for each (OSPF area 0, loopbacks, point-to-point links)
→ start_lab
→ execute_command: "show ip ospf neighbor" on each router
→ Report: "Lab ready! R1, R2, R3 all have FULL OSPF adjacencies."

**"Add a 4th router to the OSPF lab"**
→ stop_lab (topology changes require stopped state)
→ create_node R4 (IOSv)
→ create_interface + create_link (R4 to R2 and R3)
→ set_node_config for R4 (OSPF area 0)
→ Update R2 and R3 configs if needed
→ start_lab
→ Verify all 4 routers have adjacencies

**"Create a lab from this YAML topology"**
→ import_lab with the provided YAML
→ start_lab
→ Report node count, link count, state

**"Clone the OSPF lab and add BGP peering"**
→ clone_lab "OSPF Lab - 3 Routers" → "OSPF+BGP Lab"
→ Modify configs to add BGP router stanzas
→ start_lab
→ Verify both OSPF and BGP adjacencies

## Workflow: Lab Cleanup

When a user is done with a lab:

1. **Stop the lab**: `stop_lab` — graceful shutdown of all nodes
2. **Optional export**: Ask if they want to save the topology (`export_lab`)
3. **Wipe configs**: `wipe_lab` to reset node configs (if reusing later)
4. **Delete the lab**: `delete_lab` to free CML resources

## Workflow: Clone and Modify

When a user wants to experiment with a variant of an existing lab:

1. **Clone the lab**: `clone_lab` creates a deep copy
2. **Modify the clone**: Add/remove nodes, change links, update configs
3. **Start the clone**: `start_lab` on the new copy
4. Keep the original untouched for comparison

## Workflow: Export for Sharing

When a user wants to share a lab topology:

1. **Export**: `export_lab` returns CML YAML topology
2. **Optionally commit to GitHub**: Use github-ops skill to commit the YAML to a repo
3. **Share via Slack**: Post the YAML or share the GitHub link

## Lab States

Labs go through these states:

| State | Meaning |
|-------|---------|
| `DEFINED_ON_CORE` | Lab exists but no nodes are running |
| `STARTED` | All (or some) nodes are booting/running |
| `STOPPED` | All nodes have been shut down |
| `BOOTED` | All nodes have finished booting |

## Common Lab Patterns

### CCIE Routing Lab
```
"Create a CCIE routing lab with:
- 4 x IOSv routers (R1-R4)
- 2 x IOSv L2 switches (SW1-SW2)
- Full mesh between R1-R4
- SW1 connecting R1 and R2, SW2 connecting R3 and R4"
```

### Data Center Lab
```
"Build a DC lab:
- 2 x NX-OS spines
- 4 x NX-OS leaves
- 1 x external router (IOSv)
- Spine-leaf full mesh, external router to both spines"
```

### Service Provider Lab
```
"Create an SP lab:
- 4 x IOS-XR routers (PE1, PE2, P1, P2)
- 2 x IOSv CE routers
- PE-P full mesh, CE1 to PE1, CE2 to PE2"
```

## Important Rules

- **Always check lab state** before operations — don't try to start an already-running lab
- **Use `get_labs`** first to see what already exists — avoid duplicate lab names
- **Export before delete** — ask the user if they want to save the topology before destroying it
- **Lab titles can be used** instead of lab IDs — the CML MCP resolves titles to IDs
- **Wipe requires stop** — a lab must be stopped before configs can be wiped
- **Record in GAIT** — log lab creation/deletion for audit trail

## Environment Variables

- `CML_URL` — CML server URL (e.g., https://cml.example.com)
- `CML_USERNAME` — CML username
- `CML_PASSWORD` — CML password
- `CML_VERIFY_SSL` — Verify SSL certificate (true/false)
