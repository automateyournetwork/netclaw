# Validation checklists

## Structural checks
- Every node has at least one link
- Every network segment has at least two endpoints
- Topology graph is connected
- Link list matches connectivity matrix

## Role / adjacency checks
- No host-to-core direct link unless intentional
- No access-to-internet direct link unless intentional and labeled
- Spine nodes connect only to leaf nodes in leaf-spine designs
- PE nodes connect only to intended CE/P roles in SP designs

## Resilience checks
- Redundancy declaration matches the link list
- Articulation-point nodes are identified
- Partition-causing links are identified
- Peer redundancy groups are symmetric when expected

## Protocol checks
- Routing coverage exists for all non-host nodes
- Redistribution points are named
- No obvious routing black holes

State PASS / WARN / FAIL and overall resilience: FULL / HIGH / MEDIUM / LOW / CRITICAL.
