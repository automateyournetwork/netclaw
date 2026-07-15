---
name: nmap-network-scan
description: "Host discovery and port scanning using nmap — ICMP/ARP host discovery, SYN/TCP/UDP port scanning with scope enforcement and audit logging. Use when discovering live hosts on a subnet, scanning for open ports, verifying firewall rules, or doing pre/post-change port scans"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "nmap"], "env": ["NMAP_MCP_SCRIPT"] } } }
---

# Network Scanning with nmap

## How to Call the nmap MCP Tools

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" TOOL_NAME '{"param":"value"}'
```

## When to Use

- Discover what hosts are alive on a subnet before deeper analysis
- Find open ports on network devices, servers, or lab infrastructure
- Verify firewall rules by checking which ports are reachable
- Pre-change/post-change port scans to confirm expected service exposure
- Asset discovery on RFC1918 or lab networks

## Available Tools

| Tool | Purpose | Privileges |
|------|---------|-----------|
| `nmap_ping_scan` | ICMP+TCP host discovery (no port scan) | none |
| `nmap_arp_discovery` | ARP host discovery (LAN only) | cap_net_raw |
| `nmap_top_ports` | Fast scan of N most common ports | none |
| `nmap_syn_scan` | SYN half-open port scan (fast, stealthy) | cap_net_raw |
| `nmap_tcp_scan` | Full TCP connect scan (no root needed) | none |
| `nmap_udp_scan` | UDP port scan (DNS, SNMP, NTP, etc.) | cap_net_raw |

## Workflow: Subnet Discovery

When asked "what's on this network?" or "scan this subnet":

### Step 1: Host Discovery

Find live hosts first — avoids wasting time port-scanning dead IPs.

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_ping_scan '{"target":"192.168.1.0/24"}'
```

On directly-connected LANs, ARP discovery is more reliable:

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_arp_discovery '{"target":"192.168.1.0/24"}'
```

### Step 2: Quick Port Scan

Scan the top 100 common ports on discovered hosts:

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_top_ports '{"target":"192.168.1.1","count":100}'
```

### Step 3: Targeted Port Scan

For deeper scanning, use SYN scan (faster) or TCP connect scan:

```bash
# SYN scan — faster, requires cap_net_raw
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_syn_scan '{"target":"192.168.1.1","ports":"1-65535"}'

# TCP connect — works without special privileges
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_tcp_scan '{"target":"192.168.1.1","ports":"22,80,443,8080"}'
```

### Step 4: UDP Services

Check for UDP services (DNS, SNMP, TFTP, NTP, syslog):

```bash
python3 $MCP_CALL "python3 -u $NMAP_MCP_SCRIPT" nmap_udp_scan '{"target":"192.168.1.1","ports":"53,67,68,69,123,161,162,500,514,1900"}'
```

## Tool Parameters

### nmap_ping_scan
- `target` (required): IP, hostname, or CIDR range

### nmap_arp_discovery
- `target` (required): CIDR range or IP (LAN segment only)

### nmap_top_ports
- `target` (required): IP, hostname, or CIDR range
- `count` (optional): Number of top ports to scan (default 100, max 65535)

### nmap_syn_scan
- `target` (required): IP, hostname, or CIDR range
- `ports` (optional): Port range (default "1-1024", use "common" for top 1000)

### nmap_tcp_scan
- `target` (required): IP, hostname, or CIDR range
- `ports` (optional): Port range (default "1-1024")

### nmap_udp_scan
- `target` (required): IP, hostname, or CIDR range
- `ports` (optional): Port list or range (default: common UDP service ports)

## Scope Enforcement

All targets are validated against the CIDR allowlist in `config.yaml`. Targets outside the allowed ranges are hard-rejected before nmap runs. Default allowed ranges:

- `127.0.0.0/8` (loopback)
- `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC1918)
- `fd00::/8` (IPv6 ULA)

## Output Format

All tools return structured JSON with:
- `scan_id` — unique identifier for retrieving results later
- `target` — what was scanned
- `hosts_up` / `per_host` — discovered hosts with open ports
- `count` / `total_open` — summary counts

## Important Rules

- Always start with host discovery before port scanning large ranges
- SYN scan is faster but requires cap_net_raw on the nmap binary
- UDP scans are inherently slow — keep port lists targeted
- Every scan is logged in the audit log for compliance
- Scan results are persisted and retrievable via `nmap_list_scans` / `nmap_get_scan`
