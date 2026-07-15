---
name: gtrace-ip-enrichment
description: "IP address enrichment — ASN ownership lookup, geolocation (city/region/country/coordinates), and reverse DNS resolution. Use when identifying who owns an IP address, locating an IP geographically, resolving reverse DNS for a traceroute hop, or enriching unknown IPs from logs or flow data."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "gtrace"], "env": ["GTRACE_MCP_BIN"] } } }
---

# IP Address Enrichment with gtrace

## How to Call the gtrace MCP Tools

```bash
python3 $MCP_CALL "gtrace mcp" TOOL_NAME '{"param":"value"}'
```

## When to Use

- Identify who owns an IP address (ASN, organization name, network range)
- Determine the geographic location of an IP (city, region, country, coordinates)
- Resolve an IP address to its PTR/reverse DNS hostname
- Enrich traceroute hop data with ASN and geo context
- Investigate unknown IPs appearing in logs, flow data, or routing tables
- Map network paths to physical geography for latency analysis

## Available Tools

| Tool | Purpose |
|------|---------|
| `asn_lookup` | Look up ASN, organization, and network range for an IP |
| `geo_lookup` | Get geographic location (city, region, country, lat/lon) for an IP |
| `reverse_dns` | Resolve an IP to its PTR record (reverse DNS hostname) |

## Workflow: IP Investigation

When asked "who owns this IP?" or "where is this IP?":

### Step 1: ASN Lookup

Identify the Autonomous System and organization that owns the IP.

```bash
python3 $MCP_CALL "gtrace mcp" asn_lookup '{"ip":"8.8.8.8"}'
```

Returns: ASN number, organization name, network CIDR, registry (ARIN, RIPE, APNIC, etc.)

### Step 2: Geolocation

Determine the physical location of the IP.

```bash
python3 $MCP_CALL "gtrace mcp" geo_lookup '{"ip":"8.8.8.8"}'
```

Returns: City, region/state, country, latitude/longitude, timezone

### Step 3: Reverse DNS

Resolve the IP to its PTR record for hostname identification.

```bash
python3 $MCP_CALL "gtrace mcp" reverse_dns '{"ip":"8.8.8.8"}'
```

Returns: PTR hostname (e.g., `dns.google`)

## Workflow: Traceroute Hop Enrichment

After running a traceroute (via gtrace-path-analysis skill), enrich each hop with ASN and geo data:

1. Run `traceroute` to get the path with hop IPs
2. For each hop IP, run `asn_lookup` to identify the network owner
3. For key hops (transit boundaries, high-latency hops), run `geo_lookup` to map physical location
4. Use `reverse_dns` on hops to identify router naming conventions (often reveals ISP, POP location, interface type)

```bash
# Example: enrich a traceroute hop
python3 $MCP_CALL "gtrace mcp" asn_lookup '{"ip":"72.14.215.85"}'
python3 $MCP_CALL "gtrace mcp" geo_lookup '{"ip":"72.14.215.85"}'
python3 $MCP_CALL "gtrace mcp" reverse_dns '{"ip":"72.14.215.85"}'
```

## Workflow: BGP Peer Identification

When investigating BGP peers or routes:

1. Get the peer IP from `bgp_get_peers` (protocol-participation skill)
2. Run `asn_lookup` to verify the peer's ASN matches what BGP reports
3. Run `geo_lookup` to confirm the peer's physical location
4. Run `reverse_dns` to identify the peer's hostname and operator

## Tool Parameters

### asn_lookup
- `ip` (required): IPv4 or IPv6 address to look up

### geo_lookup
- `ip` (required): IPv4 or IPv6 address to geolocate

### reverse_dns
- `ip` (required): IPv4 or IPv6 address to resolve

## Output Format

- **asn_lookup** — ASN number, organization name, network CIDR prefix, RIR (ARIN/RIPE/APNIC/LACNIC/AFRINIC)
- **geo_lookup** — city, region/state, country, country code, latitude, longitude, timezone
- **reverse_dns** — PTR hostname, or indication that no PTR record exists

## Important Rules

- These tools require internet access for IP intelligence lookups
- Geolocation accuracy varies — typically city-level for broadband, region-level for mobile/cloud
- ASN lookup is the most reliable enrichment — it uses RIR delegation data
- Reverse DNS depends on the IP owner having configured PTR records
- Use all three tools together for comprehensive IP enrichment
- Cross-reference ASN data with BGP RIB entries for routing consistency verification
- Record all IP enrichment in GAIT
