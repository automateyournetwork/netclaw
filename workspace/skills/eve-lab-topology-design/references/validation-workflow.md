# Validation workflow

Use this reference before declaring a design complete.

## Decision gate before build

Confirm all of these:
1. Topology domain classified
2. Node list finalized
3. Link list finalized
4. No orphan nodes
5. No isolated networks
6. Redundancy level stated and accepted
7. Forbidden adjacencies identified
8. Image availability confirmed
9. Host resource fit checked
10. Scope confirmed

If any item is unresolved, surface it before build.

## Required final output sections

1. Requirement summary
2. Best-practice recommendations
3. Image and platform recommendations
4. Physical topology
5. Logical / protocol topology
6. Design validation check
7. Build plan
8. Configuration plan (if requested)
9. Risks, open questions, unresolved items

## Validation checklist

### Structural checks
- Every node has at least one link
- Every network segment has at least two endpoints
- Topology graph is connected
- Link list matches connectivity matrix

### Role / adjacency checks
- No host-to-core direct link unless intentional
- No access-to-internet direct link unless intentional and labeled
- In leaf-spine: spines connect only to leaves
- In SP labs: PE nodes connect only to CE/P roles as intended

### Resilience checks
- Redundancy claim matches the link list
- Articulation-point nodes are identified
- Bridge links / partition SPOFs are identified
- Peer redundancy groups have symmetric uplinks when expected

### Protocol checks
- Routing coverage exists for all non-host nodes
- Redistribution points are named
- No obvious routing black holes

State PASS, WARN, or FAIL.
Also state resilience level: FULL / HIGH / MEDIUM / LOW / CRITICAL.

## Build-plan sequence

1. Verify or create the lab
2. Confirm images available
3. Check host capacity
4. Create nodes
5. Verify node creation
6. Map interfaces
7. Create network objects
8. Connect interfaces
9. Verify topology
10. Run UNL validator
11. Start nodes
12. Apply startup configs if in scope
13. Verify connectivity

## Configuration-output rules

- Use node name as hostname
- State image/OS target at the top of each config block
- Use a stated addressing scheme
- Include only requested/selected protocols
- Use `<password>` markers, not fake secrets
