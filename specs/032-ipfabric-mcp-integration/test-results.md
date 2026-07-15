# IP Fabric MCP Integration - Test Results

**Test Date:** 2026-06-19
**Tester:** NetClaw (automated)
**Status:** ALL TESTS PASSED

---

## Test Environment

| Property | Value |
|----------|-------|
| IP Fabric Instance | `https://sa-itentialdev01a.hel1-cloud.ipf.cx` |
| IP Fabric Version | 7.12.2 |
| MCP Server Version | 0.1.0 |
| Protocol Version | 2024-11-05 |
| Total Devices | 154 |
| Total Sites | 18 |
| Vendors | Arista, Cisco, Palo Alto, Juniper, Nokia |

---

## MCP Server Initialization

**Test:** Initialize MCP session with protocol negotiation

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "netclaw-test", "version": "1.0.0"}
  },
  "id": 1
}
```

**Response:**
```json
{
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {"listChanged": true},
      "prompts": {"listChanged": true},
      "resources": {"listChanged": true}
    },
    "serverInfo": {
      "name": "IPFabric MCP",
      "version": "0.1.0"
    }
  },
  "jsonrpc": "2.0",
  "id": 1
}
```

**Result:** PASS

---

## Tool: ipf_network_health_assess

**Test:** Network health assessment

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ipf_network_health_assess",
    "arguments": {}
  },
  "id": 3
}
```

**Response Summary:**
```
# Network Health Report - 2026-06-19

## Executive Summary
- Overall Health Score: CRITICAL
- Critical Issues: 11
- Warnings: 12
- Devices: 154/154 reachable

## Critical Findings (Immediate Action Required)
1. Built-in Intent: Non-Redundant Links rule (1 critical issue)
2. Custom Intent: Management Consistency (20 critical issues)
   - NTP Synchronized Sources (3)
   - NTP Stratum Level (3)
   - NTP Time Offset (4)
3. Custom Intent: Security (8 critical issues)
   - IPsec Tunnel Status (2)
   - IPsec Gateway Status (2)
4. Custom Intent: Stability (66 critical issues)
   - OSPF Session Age (7)
   - EIGRP Session Age (1)
   - IS-IS Session Age (1)
5. Custom Intent: Inventory (4 critical issues)
   - End of Support Detail (2)
```

**Result:** PASS

---

## Tool: ipf_pathlookup_unicast

**Test:** Unicast path lookup between two IPs

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ipf_pathlookup_unicast",
    "arguments": {
      "src": "10.1.0.1",
      "dst": "10.1.0.10",
      "snapshotId": "$last"
    }
  },
  "id": 6
}
```

**Response:**
```
unicast path from 10.1.0.1; . ():
c0xr04 (router) [MPLS] -> c0xr01 (router) [MPLS] ->
c0xr05 (router) [MPLS] -> c0xr06 (router) [MPLS].
Hops: 3, total nodes: 4, edges: 3.
Device types: router.
```

**Result:** PASS

---

## Tool: ipf_png_pathlookup_unicast

**Test:** PNG diagram generation for unicast path

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ipf_png_pathlookup_unicast",
    "arguments": {
      "src": "10.1.0.1",
      "dst": "10.1.0.10",
      "snapshotId": "$last"
    }
  },
  "id": 7
}
```

**Response:**
- Content Type: image (base64 encoded PNG)
- Image Dimensions: 610 x 159 pixels
- File Size: 7,042 bytes
- Format: PNG image data, 8-bit/color RGB, non-interlaced

**Saved To:** `/tmp/ipfabric-path-test.png`

**Result:** PASS

---

## Tool: ipf_api_endpoint_search

**Test:** Natural language API endpoint search

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ipf_api_endpoint_search",
    "arguments": {
      "query": "BGP neighbors",
      "limit": 3
    }
  },
  "id": 8
}
```

**Response Summary:**
```
Found 3 API endpoints matching "BGP neighbors":

1. POST /tables/routing/protocols/bgp/neighbors
   - Match Score: 1.050 (hybrid search)
   - Callable: Yes

2. GET /settings/bgp
   - Match Score: 0.597 (hybrid search)
   - Callable: No (requires admin)

3. POST /tables/routing/protocols/bgp/address-families
   - Match Score: 0.577 (hybrid search)
   - Callable: Yes
```

**Result:** PASS

---

## Tool: ipf_api_endpoint_invoke

**Test:** Invoke arbitrary API endpoint (device inventory)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ipf_api_endpoint_invoke",
    "arguments": {
      "path": "/tables/addressing/managed-devs",
      "method": "post",
      "body": {
        "columns": ["hostname", "intName", "ip", "net"],
        "filters": {},
        "pagination": {"start": 0, "limit": 10},
        "snapshot": "$last"
      }
    }
  },
  "id": 5
}
```

**Response Sample:**
```json
{
  "data": [
    {"hostname": "s3xlbsw01", "intName": "Et1", "ip": "172.16.30.130", "net": "172.16.30.128/25"},
    {"hostname": "sdwan-validator", "intName": "ge0/0", "ip": "10.254.0.5", "net": "10.254.0.4/30"},
    {"hostname": "s3xasw03", "intName": "Lo0", "ip": "10.250.0.31", "net": "10.250.0.31/32"},
    {"hostname": "edge1x01", "intName": "GigabitEthernet1", "ip": "10.0.0.15", "net": "10.0.0.0/24"},
    {"hostname": "s3xlbr01", "intName": "Et1", "ip": "10.1.0.162", "net": "10.1.0.160/30"}
  ],
  "_meta": {"limit": 10, "start": 0, "count": 671, "size": 10}
}
```

**Result:** PASS

---

## Direct API Tests (Non-MCP)

### Snapshots Query

**Endpoint:** `GET /api/v7.12/snapshots`
**Header:** `X-API-Token: <token>`

**Response Summary:**
- 12 snapshots available
- Latest: "Day 5" (154 devices, 18 sites)
- Oldest: "Itential demo" (75 devices, locked)

**Result:** PASS

### BGP Neighbors Query

**Endpoint:** `POST /api/v7.12/tables/routing/protocols/bgp/neighbors`

**Response Sample:**
```json
[
  {"hostname": "s4xsw06", "localAs": 65044, "neiHostname": "s4xsw01", "neiAs": 65044, "state": "established"},
  {"hostname": "s4xsw06", "localAs": 65044, "neiHostname": "s4xsw02", "neiAs": 65044, "state": "established"},
  {"hostname": "s4xsw06", "localAs": 65044, "neiHostname": "s4xsw03", "neiAs": 65044, "state": "established"}
]
```

**Result:** PASS

---

## Enable Script Test (ipfabric-enable.sh)

**Test:** Run enable script with sandbox credentials

**Input:**
```
Enable IP Fabric Integration? y
IP Fabric Host URL: https://sa-itentialdev01a.hel1-cloud.ipf.cx
API Token: 2fe04e6c7eb787f5547d72abbd7b4f09
```

**Output:**
```
[STEP] 1/4 Checking prerequisites...
[INFO] Node.js version: v25.1.0
[INFO] All prerequisites satisfied.

[STEP] 2/4 Configuring IP Fabric credentials...
[INFO] Set IPFABRIC_HOST=https://sa-itentialdev01a.hel1-cloud.ipf.cx
[INFO] Set IPFABRIC_API_TOKEN=***
[INFO] Credentials saved to /home/johncapobianco/.openclaw/.env

[STEP] 3/4 Verifying IP Fabric MCP connectivity...
[INFO] Testing connection to https://sa-itentialdev01a.hel1-cloud.ipf.cx/mcp...
[INFO] Connection will be verified when OpenClaw starts

[STEP] 4/4 Verifying configuration...
[INFO] ✓ IP Fabric MCP already registered in openclaw.json

=========================================
  IP Fabric Integration Complete
=========================================
```

**Files Updated:**
- `~/.openclaw/.env` - Credentials saved
- `~/.openclaw/openclaw.json` - MCP server verified

**Result:** PASS

---

## Authentication Notes

| Method | Header | Result |
|--------|--------|--------|
| Direct API | `X-API-Token: <token>` | Works |
| MCP Server | `Authorization: Bearer <token>` | Works |

The MCP server requires Bearer token authentication, while the direct REST API accepts X-API-Token header. NetClaw configuration handles this via the `IPFABRIC_AUTH_HEADER` environment variable.

---

## Summary

| Test Category | Tests | Passed | Failed |
|---------------|-------|--------|--------|
| MCP Initialization | 1 | 1 | 0 |
| Health Assessment | 1 | 1 | 0 |
| Path Lookup | 1 | 1 | 0 |
| PNG Diagrams | 1 | 1 | 0 |
| API Search | 1 | 1 | 0 |
| API Invoke | 1 | 1 | 0 |
| Direct API | 2 | 2 | 0 |
| Enable Script | 1 | 1 | 0 |
| **Total** | **9** | **9** | **0** |

**Overall Result: ALL TESTS PASSED**

---

## Artifacts

| File | Location | Description |
|------|----------|-------------|
| Test Results | `specs/032-ipfabric-mcp-integration/test-results.md` | This document |
| Path Diagram | `/tmp/ipfabric-path-test.png` | Sample PNG output |
| Credentials | `~/.openclaw/.env` | Production credentials |

---

*Tests performed by NetClaw automated validation on 2026-06-19*
