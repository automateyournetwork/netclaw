---
name: wikipedia-research
description: "Research networking protocols, standards history, and technology context via Wikipedia - OSPF, BGP, MPLS, 802.1X, VXLAN, and more"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["WIKIPEDIA_MCP_SCRIPT"] } } }
---

# Wikipedia Research

Look up networking protocols, standards history, and technology context on Wikipedia. Use this skill to educate team members, build protocol reference material, understand the evolution of standards, and provide background context alongside hands-on network operations.

## How to Call the Tools

The Wikipedia MCP server uses FastMCP with typed input objects. All arguments must use the `{"input": {...}}` format. Call them via mcp-call:

### Search for Wikipedia Pages

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" search_pages '{"input": {"query": "OSPF routing protocol"}}'
```

Search Wikipedia for pages matching a keyword or phrase. Returns a list of matching page titles.

### Get a Page Summary

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Open Shortest Path First"}}'
```

Returns a concise summary of the page -- useful for quick context without reading the full article.

### Get Full Page Content

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_content '{"input": {"page": "Open Shortest Path First"}}'
```

Returns the complete page content. Use this when you need detailed technical information, history, or implementation specifics.

### Get External References

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_references '{"input": {"page": "Open Shortest Path First"}}'
```

Returns external links and references cited on the page. Useful for finding RFCs, vendor documentation, and academic papers.

### Get Page Categories

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_categories '{"input": {"page": "Open Shortest Path First"}}'
```

Returns the Wikipedia categories the page belongs to. Helpful for discovering related topics and protocols.

### Check if a Page Exists

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" check_page_exists '{"input": {"page": "Open Shortest Path First"}}'
```

Verify that a page exists before attempting to retrieve its content. Use this when unsure of the exact page title.

## Use Cases for Network Engineering

### 1. Protocol History and Evolution

Understand where a protocol came from and why it was designed a certain way.

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_content '{"input": {"page": "Border Gateway Protocol"}}'
```

Extract the history section to learn about BGP's evolution from EGP, the introduction of CIDR support, and the progression through BGP-1 through BGP-4.

### 2. Standards Evolution and Context

Research how standards have evolved over time -- critical for understanding why certain configurations exist.

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_content '{"input": {"page": "IEEE 802.1X"}}'
```

Learn about the 802.1X standard's development, its role in network access control, and its relationship to RADIUS and EAP.

### 3. Technology Context for Team Education

Build reference material for team training and knowledge sharing.

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Multiprotocol Label Switching"}}'
```

Get a concise MPLS overview suitable for a team briefing or documentation preamble.

### 4. Vendor-Neutral Protocol Understanding

Wikipedia provides vendor-neutral explanations that complement vendor-specific documentation.

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_content '{"input": {"page": "Virtual Extensible LAN"}}'
```

Understand VXLAN fundamentals before diving into vendor-specific implementations (Cisco ACI, Arista CVX, etc.).

### 5. Security Protocol Research

Research security mechanisms and their theoretical foundations.

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" search_pages '{"input": {"query": "MACsec IEEE 802.1AE encryption"}}'
```

Find pages related to MACsec for understanding Layer 2 encryption before implementing it.

## Common Networking Topics

### Routing Protocols

```bash
# OSPF
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Open Shortest Path First"}}'

# BGP
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Border Gateway Protocol"}}'

# IS-IS
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "IS-IS"}}'

# EIGRP
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Enhanced Interior Gateway Routing Protocol"}}'
```

### Overlay and Fabric Technologies

```bash
# VXLAN
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Virtual Extensible LAN"}}'

# MPLS
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Multiprotocol Label Switching"}}'

# SD-WAN
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" search_pages '{"input": {"query": "SD-WAN software defined wide area network"}}'

# EVPN
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" search_pages '{"input": {"query": "Ethernet VPN EVPN BGP"}}'
```

### Security Technologies

```bash
# 802.1X
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "IEEE 802.1X"}}'

# RADIUS
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "RADIUS"}}'

# IPsec
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "IPsec"}}'

# MACsec
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "IEEE 802.1AE"}}'
```

### Infrastructure Protocols

```bash
# Spanning Tree Protocol
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Spanning Tree Protocol"}}'

# DHCP
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Dynamic Host Configuration Protocol"}}'

# DNS
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Domain Name System"}}'

# NTP
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Network Time Protocol"}}'
```

## Research Workflow

For thorough protocol research, follow this sequence:

### Step 1: Search and Discover

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" search_pages '{"input": {"query": "OSPF link state routing"}}'
```

### Step 2: Verify the Page Exists

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" check_page_exists '{"input": {"page": "Open Shortest Path First"}}'
```

### Step 3: Get a Quick Summary

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_summary '{"input": {"page": "Open Shortest Path First"}}'
```

### Step 4: Dive into Full Content (if needed)

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_content '{"input": {"page": "Open Shortest Path First"}}'
```

### Step 5: Gather References for Further Reading

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_references '{"input": {"page": "Open Shortest Path First"}}'
```

### Step 6: Explore Related Topics via Categories

```bash
python3 $MCP_CALL "python3 -u $WIKIPEDIA_MCP_SCRIPT" get_categories '{"input": {"page": "Open Shortest Path First"}}'
```

## Integration with Other Skills

- **rfc-lookup** -- Cite Wikipedia for high-level context alongside RFCs for authoritative protocol specifications. Wikipedia explains the "what" and "why"; RFCs define the "how" precisely. Use both together for comprehensive protocol education.
- **pyats-routing** -- Research a routing protocol on Wikipedia before inspecting its live state on devices
- **pyats-security** -- Look up security standards (802.1X, MACsec, IPsec) before running security audits
- **pyats-troubleshoot** -- Understand protocol mechanics from Wikipedia to guide root cause analysis
- **gait-session-tracking** -- Record Wikipedia research findings as GAIT turns for audit trail
- **markmap-viz** -- Generate mind maps from protocol knowledge (e.g., BGP attribute hierarchy, OSPF LSA types)
- **drawio-diagram** -- Create protocol operation diagrams informed by Wikipedia research (e.g., OSPF DR election flow)

## Output

Wikipedia tools return text content -- summaries, full articles, reference lists, and category lists. Use this content to:
- Enrich reports with protocol background
- Build training documentation for network engineering teams
- Provide context in change management tickets
- Support root cause analysis with standards knowledge
