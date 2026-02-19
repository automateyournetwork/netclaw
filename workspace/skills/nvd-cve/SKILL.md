---
name: nvd-cve
description: "Search the National Vulnerability Database for CVEs - find vulnerabilities by keyword, get CVE details with CVSS scores"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"] } } }
---

# NVD CVE Vulnerability Search

You can search the National Vulnerability Database for CVE vulnerabilities using the NVD CVE MCP server.

## How to Use

Send JSON-RPC requests to the NVD CVE MCP server via exec:

### Search for CVEs by keyword

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_cves","arguments":{"keyword":"IOS-XE 17.3"}}}' | npx -y nvd-cve-mcp-server --oneshot
```

### Get details for a specific CVE

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_cve_details","arguments":{"cve_id":"CVE-2023-20198"}}}' | npx -y nvd-cve-mcp-server --oneshot
```

## Available Tools

1. **search_cves** - Search NVD by keyword
   - `keyword`: Search term (e.g., "Cisco IOS-XE", "NX-OS 10.2")
   - Returns: List of CVEs with IDs, descriptions, and severity

2. **get_cve_details** - Get full CVE details
   - `cve_id`: CVE identifier (e.g., "CVE-2023-20198")
   - Returns: Full details including CVSS score, affected products, remediation

## When to Use

- Auditing network devices for known vulnerabilities
- Checking if a specific software version has CVEs
- Getting CVSS scores to prioritize remediation
- Cross-referencing with device show version output
- Security compliance reporting

## Workflow

1. Run `show version` on a device to get the software version
2. Search NVD for that version (e.g., "IOS-XE 17.3.4")
3. Get details for each CVE found
4. Classify by CVSS severity (Critical > 9.0, High > 7.0, Medium > 4.0, Low)
5. Recommend remediation (upgrade paths, workarounds)
