---
name: topolograph-igp-analysis
description: "Reason over the OSPF/IS-IS link-state topology as a whole — shortest and backup paths, per-area LSDB, edge and node failure simulation, MPLS-TE/CSPF feasibility, and a timeline of topology change events. Use when the question is about what the IGP believes the topology is, or what it would do if a link or node failed, rather than what one live device's routing table currently shows. Read-only."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "env": ["TOPOLOGRAPH_API_TOKEN"] } } }
---

# Topolograph IGP Topology Analysis

Every device-facing routing skill NetClaw has — `pyats-routing`,
`pyats-junos-routing`, `multivendor-device-query` — reads **one live device's**
RIB and LSDB. This one reasons over the **whole area's link-state database**
at once, from a graph Topolograph already built, and can simulate a change
without touching anything.

It answers "what does the IGP think the topology is, and what would it do if
X failed?" — not "what is on this router right now."

## Remote, read-only

`topolograph-mcp` is a remote HTTP MCP registered in `config/openclaw.json`.
There is no local server. It fronts **your own** Topolograph instance
(`TOPOLOGRAPH_MCP_URL`, default `https://topolograph.com/mcp`), bearer
`TOPOLOGRAPH_API_TOKEN`.

The server runs with `TOPOLOGRAPH_MCP_READ_ONLY=true`: mutation tools
(`upload_graph`, `add_lsp`, `update_lsp`, `delete_lsp`) are absent from
`tools/list` and cannot be called. Do not try to reach them — a topology
change belongs in the device-write path, gated, not here.

## Client-side allowlist

The tool filter is enforced with the DefenseClaw CLI, not a config block:

```bash
defenseclaw tool allow topolograph-mcp get_all_graphs
defenseclaw tool allow topolograph-mcp get_graph_by_time
defenseclaw tool allow topolograph-mcp get_network_by_graph_time
defenseclaw tool allow topolograph-mcp get_graph_status
defenseclaw tool allow topolograph-mcp get_network_events
defenseclaw tool allow topolograph-mcp get_adjacency_events
defenseclaw tool allow topolograph-mcp get_events_timeline
defenseclaw tool allow topolograph-mcp get_nodes
defenseclaw tool allow topolograph-mcp get_edges
defenseclaw tool allow topolograph-mcp get_lsps
defenseclaw tool allow topolograph-mcp get_shortest_path
defenseclaw tool allow topolograph-mcp get_cspf_path
defenseclaw tool allow topolograph-mcp get_edge_failure_reaction
defenseclaw tool block topolograph-mcp upload_graph
defenseclaw tool block topolograph-mcp add_lsp
defenseclaw tool block topolograph-mcp update_lsp
defenseclaw tool block topolograph-mcp delete_lsp
```

The `block` lines are belt-and-braces: the server already hides those, but a
misconfigured (`TOPOLOGRAPH_MCP_READ_ONLY=false`) instance must not widen
NetClaw's surface.

## Tools

| Tool | Answers |
|---|---|
| `get_all_graphs` | Which stored topology snapshots exist (filter by protocol, area, date). Start here to get a `graph_time`. |
| `get_graph_by_time` | The full graph for one snapshot. |
| `get_graph_status` | Health of a snapshot — is it complete and consistent. |
| `get_network_by_graph_time` | Which prefixes/networks are in the graph, by mask/area. |
| `get_nodes` | Routers in the area, filterable by role flag (ABR/ASBR, IS-IS overload/attached). |
| `get_edges` | Adjacencies, with `include=["lsps","is_te_link","lsp_left_bw","edge_key"]` for MPLS-TE fields. |
| `get_lsps` | MPLS-TE LSP tunnels, filter by `status`, `via_node`, `via_edge`. |
| `get_shortest_path` | SPF path between two nodes; `with_lsps=true` accounts for autoroute tunnels. |
| `get_cspf_path` | Constrained-SPF feasibility between two nodes — never mutates the graph. |
| `get_edge_failure_reaction` | Whole-network impact if one or more links fail: stays connected? rerouting pattern? Simulation only. |
| `get_network_events` / `get_adjacency_events` | Raw topology-change events in a time range. |
| `get_events_timeline` | The same events grouped into waves for incident narration. |

## Boundary — when to use something else

| Question | Skill |
|---|---|
| "What does the IGP topology look like / what if this link fails?" | **this skill** |
| "What is in *this router's* routing table / LSDB right now?" | `pyats-routing`, `pyats-junos-routing`, `multivendor-device-query` |
| "Is this adjacency actually up on the device?" | the platform routing skill |
| "Push a metric / cost change" | device-write path, gated — never here |

Topolograph reasons over a **stored** snapshot. If the question is "is this
true on the wire this second", confirm on the device after.

## Never

- Never present a simulation result (`get_edge_failure_reaction`,
  `get_cspf_path`) as something that happened. It is a prediction over a
  snapshot.
- Never report a stale `graph_time` as current — check `get_all_graphs` for
  the latest snapshot, and say how old it is.
