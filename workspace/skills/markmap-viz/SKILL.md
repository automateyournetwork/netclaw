---
name: markmap-viz
description: "Create interactive mind map visualizations from markdown using markmap.js"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["markmap-mcp"] } } }
---

# Markmap Mind Map Visualization

You can create interactive mind maps from markdown content using the markmap-mcp server.

## How to Use

Send JSON-RPC requests to the markmap MCP server via exec:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"create_markmap","arguments":{"markdown":"# Root\n## Branch 1\n### Leaf\n## Branch 2"}}}' | markmap-mcp --oneshot
```

Or create a markdown file and convert it:

```bash
# Write markdown to a file
cat > /tmp/network-map.md << 'EOF'
# Network Topology
## Routers
### R1 - 10.10.20.171
### R2 - 10.10.20.172
## Switches
### SW1 - 10.10.20.173
### SW2 - 10.10.20.174
EOF

# Generate mind map HTML
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"create_markmap","arguments":{"file":"/tmp/network-map.md"}}}' | markmap-mcp --oneshot
```

## When to Use

- Visualizing network topology hierarchies
- Mapping OSPF areas, BGP peers, VLAN structures
- Summarizing audit findings by severity
- Displaying configuration comparisons
- Any hierarchical data that benefits from visual tree representation

## Output

Generates an interactive HTML file that opens in a browser with zoom, collapse/expand, and pan controls.
