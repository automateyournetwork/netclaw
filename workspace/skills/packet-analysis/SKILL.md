---
name: packet-analysis
description: Analyze network packet captures (.pcap/.pcapng) using Packet Buddy MCP
version: 1.0.0
tags: [packets, pcap, wireshark, tshark, troubleshooting]
---

# Packet Analysis Skill

You have access to Packet Buddy MCP — a set of tools for analyzing network packet captures using tshark (Wireshark's CLI).

## MCP Server
- **Script**: `$PACKET_BUDDY_MCP_SCRIPT`
- **Invocation**: `python3 $MCP_CALL "python3 -u $PACKET_BUDDY_MCP_SCRIPT" <tool_name> '<json_args>'`

## Available Tools

### Discovery
- **list_pcaps** — List all pcap files available for analysis
- **pcap_summary** — High-level stats: packet count, duration, capture size

### Traffic Analysis
- **pcap_protocol_hierarchy** — Protocol breakdown (what % is TCP, UDP, DNS, etc.)
- **pcap_conversations** — Who talked to whom (IP, TCP, UDP, or Ethernet layer)
- **pcap_endpoints** — Top talkers by traffic volume

### Filtering & Inspection
- **pcap_filter** — Apply Wireshark display filters (e.g. `tcp.port==80`, `icmp`, `bgp`)
- **pcap_packet_detail** — Full decode of a specific packet by number
- **pcap_to_json** — Export packets as JSON for detailed analysis
- **pcap_expert_info** — Warnings, errors, retransmissions, anomalies

### Protocol-Specific
- **pcap_dns_queries** — Extract all DNS queries and responses
- **pcap_http_requests** — Extract HTTP methods, URIs, and hosts

### File Management
- **save_pcap_from_base64** — Save a base64-encoded pcap (e.g. from Slack file upload)

## Workflow: Slack pcap Upload

When a user uploads a .pcap or .pcapng file in Slack:
1. The file arrives as a Slack file attachment
2. Download the file content and save it using **save_pcap_from_base64**
3. Run **pcap_summary** to give an overview
4. Ask the user what they want to investigate
5. Use appropriate tools to drill down

## Workflow: Troubleshooting

When investigating a network issue with a pcap:
1. Start with **pcap_summary** for the big picture
2. Check **pcap_protocol_hierarchy** — any unexpected protocols?
3. Look at **pcap_conversations** — who's talking to whom?
4. Use **pcap_expert_info** for retransmissions, resets, errors
5. Apply **pcap_filter** to focus on specific traffic
6. Use **pcap_packet_detail** for deep inspection of suspect packets

## Common Display Filters

| Filter | Purpose |
|--------|---------|
| `tcp.analysis.retransmission` | TCP retransmissions |
| `tcp.flags.reset==1` | TCP RST packets |
| `dns` | All DNS traffic |
| `icmp` | Ping and ICMP errors |
| `bgp` | BGP routing protocol |
| `ospf` | OSPF routing protocol |
| `tcp.port==22` | SSH traffic |
| `http` | HTTP requests/responses |
| `tls.handshake` | TLS handshakes |
| `arp` | ARP requests/replies |
| `stp` | Spanning Tree Protocol |
| `ip.addr==10.0.0.1` | Traffic to/from specific host |

## Environment Variables
- `PACKET_BUDDY_MCP_SCRIPT` — Path to packet-buddy-mcp/server.py
- `PCAP_UPLOAD_DIR` — Directory for pcap files (default: /tmp/netclaw-pcaps)

## Important Rules
- Large pcaps can be slow — use filters to narrow down
- When showing results, summarize key findings rather than dumping raw output
- Always check **pcap_expert_info** first — tshark already flags the problems
- For Slack uploads, confirm the file was saved before attempting analysis
