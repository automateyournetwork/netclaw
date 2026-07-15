---
name: nmap-scan-management
description: "Custom nmap scans with arbitrary flags, plus scan history retrieval and management. Use when running nmap with custom flags, reviewing past scan results, comparing before/after scans, or retrieving a previous scan by ID"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "nmap"], "env": ["NMAP_MCP_SCRIPT"] } } }
---

# nmap Scan Management

## How to Call the nmap MCP Tools

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## When to Use

- Run nmap with flags not covered by the purpose-built tools
- Review past scan results without re-scanning
- Compare before/after scans (pre-change vs post-change)
- Retrieve a specific scan result by ID

## Available Tools

| Tool | Purpose |
|------|---------|
| `nmap_custom_scan` | Run nmap with arbitrary flags (scope-enforced + audit-logged) |
| `nmap_list_scans` | List recent saved scans with IDs, timestamps, targets |
| `nmap_get_scan` | Retrieve full results of a previous scan by ID |

## Custom Scans

For power users who need flags not covered by the dedicated tools:

```bash
# Aggressive scan with version detection
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_custom_scan '{"target":"192.168.1.1","flags":"-A -T4"}'

# Scan specific ports with timing template
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_custom_scan '{"target":"10.0.0.0/24","flags":"-sS -p 22,80,443 -T3 --open"}'

# Idle scan using a zombie host
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_custom_scan '{"target":"192.168.1.1","flags":"-sI 192.168.1.254"}'

# IPv6 scan
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_custom_scan '{"target":"fd00:cc:1:2::1","flags":"-6 -sT -p 179,22,80"}'
```

**Safety:** The following are blocked in custom scans:
- Shell metacharacters (`;`, `&`, `|`, `` ` ``, `$`, etc.)
- Output-writing flags (`-oN`, `-oX`, `-oG`, `-oA`)
- Path-based flags (`--datadir`, `--servicedb`, `--script` with path)

Use the dedicated `nmap_script_scan` or `nmap_vuln_scan` tools for NSE scripts.

## Scan History

### List Recent Scans

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_list_scans '{"limit":20}'
```

Returns newest-first list with scan_id, timestamp, tool used, and target.

### Retrieve a Specific Scan

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_get_scan '{"scan_id":"20250307_143022_a1b2c3"}'
```

Returns the full scan result as originally captured.

## Workflow: Before/After Comparison

When validating a change:

1. **Before change:** Run a baseline scan and note the scan_id
2. **Make the change** (firewall rule, service deploy, etc.)
3. **After change:** Run the same scan again
4. **Compare:** Retrieve both scans and diff the open ports / services

```bash
# Baseline
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_top_ports '{"target":"192.168.1.1","count":1000}'
# Note: scan_id from output, e.g. "20250307_140000_abc123"

# ... make changes ...

# Post-change
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_top_ports '{"target":"192.168.1.1","count":1000}'

# Retrieve both for comparison
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_get_scan '{"scan_id":"20250307_140000_abc123"}'
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_get_scan '{"scan_id":"20250307_141500_def456"}'
```

## Tool Parameters

### nmap_custom_scan
- `target` (required): IP, hostname, or CIDR range
- `flags` (required): Raw nmap flags (do NOT include the target in flags)

### nmap_list_scans
- `limit` (optional): Max number of scans to return (default: 20, newest first)

### nmap_get_scan
- `scan_id` (required): The scan_id returned by any scan tool or nmap_list_scans

## Important Rules

- Custom scans still enforce the CIDR allowlist — out-of-scope targets are rejected
- Every scan (including custom) is recorded in the audit log
- All scan results are saved to disk and retrievable by scan_id
- Do NOT put the target in the `flags` parameter — it's added automatically
- Shell injection is blocked — forbidden characters are rejected
