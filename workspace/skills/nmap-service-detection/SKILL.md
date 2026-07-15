---
name: nmap-service-detection
description: "Service fingerprinting, OS detection, NSE script execution, and vulnerability scanning using nmap MCP. Use when identifying services on open ports, fingerprinting OS versions, running NSE scripts for SSL or SMB checks, or scanning for known CVEs and vulnerabilities"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "nmap"], "env": ["NMAP_MCP_SCRIPT"] } } }
---

# Service Detection & Vulnerability Scanning with nmap

## How to Call the nmap MCP Tools

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## When to Use

- Identify what software/version is running on an open port
- Fingerprint the OS of a network device or server
- Run targeted NSE scripts (SSL cert check, banner grab, protocol probe)
- Scan for known CVEs and common misconfigurations
- Full reconnaissance sweep of a single host or small range

## Available Tools

| Tool | Purpose | Privileges |
|------|---------|-----------|
| `nmap_service_detection` | Service name + version on open ports (-sV) | none |
| `nmap_os_detection` | OS fingerprinting (-O) | cap_net_raw |
| `nmap_script_scan` | Run specific NSE scripts | none |
| `nmap_vuln_scan` | Run the "vuln" NSE script category | none |
| `nmap_full_recon` | SYN + service + OS + default scripts all-in-one | cap_net_raw |

## Workflow: Service Identification

When asked "what's running on this host?" or "identify the services":

### Step 1: Service Version Detection

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_service_detection '{"target":"192.168.1.1","ports":"common","intensity":7}'
```

Returns per-port: service name, product, version, CPE identifier.

### Step 2: OS Fingerprinting

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_os_detection '{"target":"192.168.1.1"}'
```

Works best when the target has at least one open and one closed port.

## Workflow: Security Assessment

When asked "check this host for vulnerabilities" or "security scan":

### Step 1: Full Recon

Run the all-in-one audit sweep:

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_full_recon '{"target":"192.168.1.1","ports":"common"}'
```

This combines SYN scan + service detection + OS fingerprinting + default NSE scripts.

### Step 2: Vulnerability Scan

Run the vuln NSE category for known CVEs:

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_vuln_scan '{"target":"192.168.1.1","ports":"common"}'
```

This is slow — use on specific targets, not wide ranges.

### Step 3: Targeted Script Scans

Run specific NSE scripts for focused checks:

```bash
# SSL certificate inspection
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_script_scan '{"target":"192.168.1.1","scripts":"ssl-cert,ssl-enum-ciphers","ports":"443"}'

# HTTP title + headers
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_script_scan '{"target":"192.168.1.1","scripts":"http-title,http-headers","ports":"80,443,8080"}'

# Banner grabbing
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_script_scan '{"target":"192.168.1.1","scripts":"banner","ports":"1-1024"}'

# SMB enumeration
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_script_scan '{"target":"192.168.1.1","scripts":"smb-enum-shares,smb-os-discovery","ports":"445"}'
```

## Tool Parameters

### nmap_service_detection
- `target` (required): IP, hostname, or CIDR range
- `ports` (optional): Port range or "common" for top 1000 (default: "common")
- `intensity` (optional): Version detection aggressiveness 0-9 (default: 7)

### nmap_os_detection
- `target` (required): Single IP or hostname (ranges don't work well)

### nmap_script_scan
- `target` (required): IP, hostname, or CIDR range
- `scripts` (required): NSE script name(s), e.g. "ssl-cert", "http-title,http-headers", "banner"
- `ports` (optional): Port range or "common" (default: "common")

### nmap_vuln_scan
- `target` (required): IP or hostname (keep scope tight)
- `ports` (optional): Port range or "common" (default: "common")

### nmap_full_recon
- `target` (required): IP, hostname, or small CIDR range (/28 or smaller)
- `ports` (optional): Port range or "common" (default: "common")

## Common NSE Script Names

| Script | Purpose |
|--------|---------|
| `ssl-cert` | Display SSL certificate details |
| `ssl-enum-ciphers` | List supported SSL/TLS ciphers |
| `http-title` | Grab HTML page title |
| `http-headers` | Dump HTTP response headers |
| `http-methods` | Check supported HTTP methods |
| `banner` | Grab service banners |
| `smb-enum-shares` | Enumerate SMB shares |
| `smb-os-discovery` | Discover OS via SMB |
| `ssh-hostkey` | Show SSH host keys |
| `dns-brute` | DNS subdomain brute force |
| `ftp-anon` | Check for anonymous FTP |

## Output Format

All tools return structured JSON:
- `scan_id` — for retrieving results later
- `per_host` — per-host breakdown with open ports, services, versions
- `os_detection` — OS match name, accuracy, device type
- `results` / `vulnerability_findings` — script output organized by port

## Important Rules

- OS detection requires at least one open and one closed port to fingerprint accurately
- Vuln scans are slow — target specific hosts, not wide ranges
- Full recon combines multiple scan types — takes longer but gives comprehensive results
- All scans respect the CIDR allowlist and are audit-logged
- Scan results persist and can be retrieved with `nmap_list_scans` / `nmap_get_scan`
