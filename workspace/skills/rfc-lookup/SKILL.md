---
name: rfc-lookup
description: "Search and retrieve IETF RFC documents - lookup by number, search by keyword, extract sections. Use when looking up an RFC, checking protocol specifications, verifying standards compliance, or researching how a protocol should behave per the spec."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"] } } }
---

# IETF RFC Lookup

## How to Use

Send requests to the RFC MCP server via mcp-call:

### Get an RFC by number

```bash
python3 $MCP_CALL "npx -y @mjpitz/mcp-rfc" get_rfc '{"number":"4271"}'
```

### Search RFCs by keyword

```bash
python3 $MCP_CALL "npx -y @mjpitz/mcp-rfc" search_rfcs '{"query":"BGP security"}'
```

### Get a specific section

```bash
python3 $MCP_CALL "npx -y @mjpitz/mcp-rfc" get_rfc_section '{"number":"4271","section":"Security Considerations"}'
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
