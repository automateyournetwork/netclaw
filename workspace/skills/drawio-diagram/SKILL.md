---
name: drawio-diagram
description: "Generate network diagrams using Draw.io - supports XML, CSV, and Mermaid formats"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"] } } }
---

# Draw.io Network Diagrams

You can generate and open network diagrams in the Draw.io editor using the drawio MCP tool server.

## How to Call the Tools

The Draw.io MCP server provides three tools, one per format. Call them via mcp-call:

### Mermaid Diagrams (best for quick topology graphs)

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD\n  A --> B"}'
```

### XML Diagrams (best for detailed, styled diagrams with precise positioning)

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_xml '{"content":"<mxGraphModel>...</mxGraphModel>"}'
```

### CSV Diagrams (best for device inventories)

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_csv '{"content":"## label: %name%\nname,refs\nA,B\nB,C"}'
```

All three tools accept an optional `"lightbox": true` for read-only view and `"dark": "auto"|"true"|"false"` for dark mode.

## Diagram Types for Network Engineering

### 1. Physical Topology Diagram

Shows devices, physical links, interface names, IP addresses, and link speeds.

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD\n  R1[\"R1\\nCore Router\\n10.255.255.1\"]\n  R2[\"R2\\nCore Router\\n10.255.255.2\"]\n  SW1[\"SW1\\nDist Switch\\n10.255.255.3\"]\n  R1 -->|\"Gi0/0 -- Gi0/0\\n10.1.1.0/30\"| R2\n  R1 -->|\"Gi0/1 -- Gi0/1\\n10.1.2.0/30\"| SW1\n  R2 -->|\"Gi0/1 -- Gi0/1\\n10.1.3.0/30\"| SW1"}'
```

### 2. Logical Topology Diagram

Shows routing protocol relationships, areas, AS numbers, VRFs.

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD\n  subgraph \"OSPF Area 0\"\n    R1[\"R1 ABR\"]\n    R2[\"R2 ABR\"]\n  end\n  subgraph \"OSPF Area 1\"\n    R3[\"R3\"]\n  end\n  R1 --- R2\n  R1 --- R3"}'
```

### 3. Security Zones Diagram

Shows firewalls, DMZs, trust boundaries, ACL enforcement points.

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph LR\n  subgraph \"Untrusted\"\n    INET((Internet))\n  end\n  subgraph \"DMZ\"\n    WEB[\"Web Server\"]\n  end\n  subgraph \"Trusted\"\n    CORE[\"Core Switch\"]\n  end\n  INET --> FW[\"Firewall\"]\n  FW --> WEB\n  FW --> CORE"}'
```

## When to Use

- Network topology diagrams from CDP/LLDP neighbor data
- Architecture diagrams showing device interconnections
- Flowcharts for troubleshooting procedures
- ACI fabric topology (tenants, VRFs, BDs, EPGs)
- Security zone maps with ACL/firewall placement
- Any visual diagram that benefits from the Draw.io editor

## Integration with Other Skills

- Use **pyats-topology** to discover the network, then generate diagrams from the data
- Use **netbox-reconcile** to color-code links by reconciliation status (documented/undocumented/missing)
- Use **markmap-viz** for hierarchical views alongside Draw.io for topology views

## Output

The tool returns a Draw.io URL. Share it directly — the diagram opens in the browser editor where it can be edited, exported to PNG/SVG/PDF, or saved as .drawio file.
