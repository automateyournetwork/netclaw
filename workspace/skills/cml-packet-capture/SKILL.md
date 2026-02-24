---
name: cml-packet-capture
description: CML packet capture — start, stop, download pcaps from CML lab links, integrate with Packet Buddy for analysis
version: 1.0.0
tags: [cml, pcap, capture, troubleshooting, wireshark]
---

# CML Packet Capture

Capture packets on CML lab links and analyze them. Start captures on any link in a running lab, stop them, download the pcap file, and hand off to the Packet Buddy skill for deep tshark-powered analysis.

## MCP Server

- **Command**: `cml-mcp` (pip-installed, stdio transport)
- **Requires**: `CML_URL`, `CML_USERNAME`, `CML_PASSWORD` environment variables

## Available Tools

### Packet Capture Operations

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `start_capture` | `lab_id`/`lab_title`, `link_id`, `max_packets?`, `pcap_filter?` | Start capturing packets on a link |
| `stop_capture` | `lab_id`/`lab_title`, `link_id` | Stop an active capture |
| `get_capture_status` | `lab_id`/`lab_title`, `link_id` | Check capture status (running, packet count) |
| `download_capture` | `lab_id`/`lab_title`, `link_id`, `file_path?` | Download the captured pcap file |
| `list_captures` | `lab_id`/`lab_title` | List all active and completed captures in a lab |

## Workflow: Capture and Analyze (Full Pipeline)

When a user says "capture traffic between R1 and R2 and analyze it":

1. **Find the link**: Use `get_links` (from cml-topology-builder) to find the link ID between R1 and R2
2. **Start capture**: `start_capture` with optional filter (e.g., "icmp", "tcp port 179")
3. **Generate traffic**: Tell the user to generate traffic (or use `execute_command` to ping)
4. **Stop capture**: `stop_capture` after sufficient traffic is collected
5. **Download pcap**: `download_capture` to save the pcap file locally
6. **Analyze with Packet Buddy**: Hand off to the packet-analysis skill:
   - `pcap_summary` — overview
   - `pcap_protocol_hierarchy` — protocol breakdown
   - `pcap_conversations` — who talked to whom
   - `pcap_expert_info` — errors, retransmissions
   - `pcap_filter` — drill into specific traffic
7. **Report findings**: Summarize the analysis in plain English

## Workflow: Targeted Protocol Capture

When troubleshooting a specific protocol:

### BGP Troubleshooting
```
1. start_capture with pcap_filter="tcp port 179"
2. Wait for BGP events (or trigger with clear ip bgp)
3. stop_capture
4. download_capture
5. Analyze: Look for OPEN, KEEPALIVE, UPDATE, NOTIFICATION messages
6. Check for: hold timer expiry, capability mismatch, prefix limit exceeded
```

### OSPF Troubleshooting
```
1. start_capture with pcap_filter="ospf"
2. Wait for OSPF events (or trigger with clear ip ospf process)
3. stop_capture
4. download_capture
5. Analyze: Look for Hello, DBD, LSR, LSU, LSAck packets
6. Check for: area mismatch, auth failure, MTU mismatch, dead timer expiry
```

### ICMP / Connectivity
```
1. start_capture (no filter, or pcap_filter="icmp")
2. execute_command on source node: "ping {destination}"
3. stop_capture
4. download_capture
5. Analyze: Look for echo request/reply, unreachable, TTL exceeded
6. Check for: asymmetric routing, ACL drops, MTU issues
```

### Spanning Tree
```
1. start_capture with pcap_filter="stp"
2. Wait for STP convergence or trigger topology change
3. stop_capture
4. download_capture
5. Analyze: BPDUs, topology change notifications, root bridge elections
```

## Capture Filters

CML uses BPF (Berkeley Packet Filter) syntax for capture filters:

| Filter | Captures |
|--------|----------|
| `icmp` | ICMP (ping) traffic |
| `tcp port 179` | BGP traffic |
| `ospf` | OSPF traffic |
| `tcp port 22` | SSH traffic |
| `udp port 53` | DNS traffic |
| `arp` | ARP requests/replies |
| `stp` | Spanning Tree BPDUs |
| `tcp port 80 or tcp port 443` | HTTP/HTTPS traffic |
| `host 10.0.0.1` | Traffic to/from specific host |
| `net 10.0.0.0/24` | Traffic to/from specific subnet |
| `vlan 100` | Traffic on VLAN 100 |

## Workflow: Compare Before/After

When verifying a configuration change:

1. **Capture before**: Start capture, collect baseline traffic
2. **Stop and download**: Save as `before.pcap`
3. **Make the change**: Apply configuration via cml-node-operations
4. **Capture after**: Start new capture, collect post-change traffic
5. **Stop and download**: Save as `after.pcap`
6. **Compare**: Analyze both pcaps with Packet Buddy
7. **Report**: Document the differences (e.g., "BGP converged in 3s after route-map change")

## Integration with Packet Buddy

After downloading a pcap from CML, use these Packet Buddy tools for analysis:

| Step | Packet Buddy Tool | Purpose |
|------|-------------------|---------|
| 1 | `pcap_summary` | Big picture: packet count, duration, size |
| 2 | `pcap_protocol_hierarchy` | What protocols are present |
| 3 | `pcap_conversations` | Who is talking to whom |
| 4 | `pcap_expert_info` | Errors, warnings, retransmissions |
| 5 | `pcap_filter` | Focus on specific traffic |
| 6 | `pcap_packet_detail` | Deep dive into a single packet |
| 7 | `pcap_dns_queries` | DNS resolution analysis |
| 8 | `pcap_http_requests` | HTTP traffic analysis |

## Important Rules

- **Lab must be running** — captures only work on links in a started lab
- **One capture per link** — stop an existing capture before starting a new one
- **Use filters for busy links** — unfiltered captures on high-traffic links can be large
- **Set max_packets** — prevent runaway captures; 10000 packets is usually enough
- **Download before stopping** — some CML versions clear the capture buffer on link state change
- **File naming**: Save pcaps with descriptive names like `r1-r2-bgp-capture.pcap`
- **Record in GAIT** — log captures and findings for audit trail
