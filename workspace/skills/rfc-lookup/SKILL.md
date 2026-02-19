---
name: rfc-lookup
description: "Search and retrieve IETF RFC documents - lookup by number, search by keyword, extract sections"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"] } } }
---

# IETF RFC Lookup

You can search and retrieve RFC documents using the RFC MCP server.

## How to Use

Send JSON-RPC requests to the RFC MCP server via exec:

### Get an RFC by number

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_rfc","arguments":{"number":"4271"}}}' | npx -y @mjpitz/mcp-rfc --oneshot
```

### Search RFCs by keyword

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_rfcs","arguments":{"query":"BGP security"}}}' | npx -y @mjpitz/mcp-rfc --oneshot
```

### Get a specific section

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_rfc_section","arguments":{"number":"4271","section":"Security Considerations"}}}' | npx -y @mjpitz/mcp-rfc --oneshot
```

## Available Tools

1. **get_rfc** - Fetch full RFC by number
   - `number`: RFC number (e.g., "4271", "5905")

2. **search_rfcs** - Search by keyword
   - `query`: Search term (e.g., "OSPF", "BGP security")

3. **get_rfc_section** - Extract specific section
   - `number`: RFC number
   - `section`: Section title or number

## Common Networking RFCs

- RFC 4271 - BGP-4
- RFC 2328 - OSPF Version 2
- RFC 5905 - NTPv4
- RFC 7454 - BGP Operations and Security
- RFC 8200 - IPv6
- RFC 791 - IPv4
- RFC 2903 - AAA Authorization Framework

## When to Use

- Verifying protocol implementations against standards
- Looking up best practices for configuration
- Cross-referencing CVE remediation with protocol specifications
- Learning about networking protocols
