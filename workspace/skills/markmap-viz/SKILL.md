---
name: markmap-viz
description: "Create interactive mind map visualizations from markdown - network inventory, OSPF areas, BGP topology, security audit results"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["node"], "env": ["MARKMAP_MCP_SCRIPT"] } } }
---

# Markmap Mind Map Visualization

You can create interactive mind maps from markdown content using the markmap MCP server.

## How to Call the Tools

The Markmap MCP server provides 5 tools. Call them via mcp-call:

### Generate from Markdown (primary tool)

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_generate '{"markdown_content":"# Network Topology\n## Routers\n### R1 - 10.255.255.1\n### R2 - 10.255.255.2\n## Switches\n### SW1\n### SW2"}'
```

### Generate from Outline Structure

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_from_outline '{"outline_items":["Network","  Routers","    R1","    R2","  Switches","    SW1","    SW2"]}'
```

### Extract Structure (no rendering)

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_get_structure '{"markdown_content":"# Root\n## Branch 1\n## Branch 2","include_content":true}'
```

### Render from File

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_render_file '{"file_path":"/tmp/network-map.md","save_output":true,"output_path":"/tmp/network-map.svg"}'
```

### Custom Themed Mindmap

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_customize '{"markdown_content":"# Audit Results\n## Critical\n### Missing AAA\n## High\n### Weak SNMP\n## Medium\n### No NTP auth","theme":"dark","color_scheme":"rainbow"}'
```

## When to Use

- **Network inventory** — Devices organized by site, role, platform
- **OSPF topology** — Areas → routers → interfaces → neighbors
- **BGP topology** — AS numbers → peers → prefixes → communities
- **Security audit results** — Findings by severity (Critical/High/Medium/Low)
- **VLAN structure** — VLANs → ports → trunk/access → STP role
- **Troubleshooting trees** — Symptom → possible causes → verification steps
- **Config comparison** — Before/after with highlighted diffs
- **ACI fabric** — Tenant → VRF → BD → EPG → contract hierarchy
- **ISE policy** — Policy sets → authorization rules → conditions → results

## Example: OSPF Mind Map

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_generate '{"markdown_content":"# OSPF Domain\n## Area 0 - Backbone\n### R1 (ABR)\n- RID: 10.255.255.1\n- Neighbors: R2, R3\n### R2 (ABR)\n- RID: 10.255.255.2\n## Area 1 - Campus\n### R3\n- RID: 10.255.255.3\n- Type: Stub\n## Area 2 - WAN\n### R4\n- RID: 10.255.255.4\n- Type: NSSA"}'
```

## Example: Security Audit Mind Map

```bash
python3 $MCP_CALL "node $MARKMAP_MCP_SCRIPT" markmap_customize '{"markdown_content":"# Security Audit - R1\n## CRITICAL\n### No AAA configured\n### SNMP community: public\n## HIGH\n### No CoPP policy\n### HTTP server enabled\n## MEDIUM\n### NTP without authentication\n### No login banner\n## LOW\n### CDP enabled globally","theme":"dark"}'
```

## Integration with Other Skills

- Use **pyats-health-check** data to generate health overview mind maps
- Use **pyats-security** audit results to create severity-ranked visualizations
- Use **pyats-topology** discovery data to map the network hierarchy
- Use **netbox-reconcile** drift data to visualize discrepancies
- Use alongside **drawio-diagram** — markmap for hierarchical views, Draw.io for topology views

## Output

Returns interactive SVG content that can be saved to a file and opened in a browser with zoom, collapse/expand, and pan controls.
