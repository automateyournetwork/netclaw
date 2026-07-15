---
name: gns3-packet-capture
description: "Capture network traffic on GNS3 links - start/stop captures, retrieve PCAP data"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["GNS3_URL", "GNS3_USER", "GNS3_PASSWORD"]
---

# GNS3 Packet Capture

Start and stop packet captures on links in GNS3 projects. Capture network traffic for analysis and troubleshooting.

## When to Use

- Troubleshooting network connectivity issues in a lab
- Capturing traffic for analysis with Wireshark
- Verifying routing protocol exchanges (OSPF, BGP, etc.)
- Debugging application traffic
- Learning about network protocols
- Validating QoS or security policies

## MCP Server

- **Command**: `python3 -u mcp-servers/gns3-mcp-server/gns3_mcp_server.py` (stdio transport)
- **Requires**: `GNS3_URL`, `GNS3_USER`, `GNS3_PASSWORD` environment variables

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `gns3_start_capture` | project_id, link_id, capture_file_name? | Start packet capture on a link |
| `gns3_stop_capture` | project_id, link_id | Stop packet capture and finalize PCAP file |
| `gns3_get_capture` | project_id, link_id | Get capture file path and stream URL |

## Workflow Examples

### Capture Traffic for Analysis

```bash
# First, identify the link to capture
"List all links in routing-test"

# Start capture on the link between router1 and router2
"Start capturing traffic on link abc123 in routing-test"

# Generate some traffic (ping, routing updates, etc.)
# ...

# Stop capture when done
"Stop the capture on link abc123 in routing-test"

# Get the PCAP file location
"Get capture info for link abc123 in routing-test"
```

### Custom Capture Filename

```bash
# Start capture with custom filename
"Start capturing on link abc123 in routing-test as ospf_adjacency.pcap"
```

### Live Streaming

```bash
# Get stream URL for live capture viewing
"Get capture info for link abc123 in routing-test"
# Returns stream_url for live PCAP streaming
```

## Integration with Other Skills

- **gns3-link-management**: List links to find the one to capture
- **gns3-node-operations**: Ensure nodes are running before capturing
- **packet-analysis**: Hand off PCAP data for deep inspection

## Capture Output

- **PCAP Format**: Standard libpcap format compatible with Wireshark
- **File Location**: Stored on GNS3 server, path returned in response
- **Stream URL**: Available for live capture viewing when capture is active

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| GNS3_NOT_FOUND | Link doesn't exist | Use gns3_list_links to find valid link IDs |
| GNS3_CONFLICT | Capture already running | Stop existing capture first |

## Tips

1. **Find the right link**: Use `gns3_list_links` to see all connections and their IDs
2. **Start before traffic**: Begin capture before generating the traffic you want to analyze
3. **Stop cleanly**: Always stop capture to finalize the PCAP file
4. **Use custom names**: Descriptive filenames help organize multiple captures

## Notes

- Captures are stored on the GNS3 server
- Link IDs are UUIDs from `gns3_list_links`
- Only one capture per link at a time
- Stop capture to ensure PCAP file is complete
- All operations logged to GAIT audit trail
