---
name: drawio-diagram
description: "Generate network diagrams using Draw.io - supports XML, CSV, and Mermaid formats"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"] } } }
---

# Draw.io Network Diagrams

You can generate and open network diagrams in the Draw.io editor using the drawio MCP tool server.

## How to Use

Send JSON-RPC requests to the Draw.io MCP server via exec:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"create_diagram","arguments":{"format":"mermaid","content":"graph TD; R1-->SW1; R1-->SW2; R2-->SW1; R2-->SW2;"}}}' | npx -y @drawio/mcp --oneshot
```

### Supported Formats

1. **Mermaid** - Simple text-based diagrams
2. **XML** - Native Draw.io XML format
3. **CSV** - Tabular data converted to diagrams

## When to Use

- Network topology diagrams from CDP/LLDP neighbor data
- Architecture diagrams showing device interconnections
- Flowcharts for troubleshooting procedures
- Any visual diagram that benefits from the Draw.io editor

## Output

Opens the diagram in the Draw.io browser editor where it can be edited, exported to PNG/SVG/PDF, or saved.
