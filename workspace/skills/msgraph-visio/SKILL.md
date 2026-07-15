---
name: msgraph-visio
description: "Generate and manage Visio network diagrams on SharePoint via Microsoft Graph API - create topology diagrams from CDP/LLDP discovery, update existing diagrams, export to PDF. Use when creating Visio topology diagrams, uploading network diagrams to SharePoint, or generating physical/logical topology views from discovery data"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"], "env": ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"] } } }
---

# Microsoft Graph — Visio Diagram Generation

## How to Call the Tools

The Microsoft Graph MCP server is invoked via npx with Azure AD credentials:

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" <tool-name> '<arguments-json>'
```

## Visio Generation Workflow

### Step 1: Discover the Network Topology

Use **pyats-topology** to collect CDP/LLDP neighbor data from all devices:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show cdp neighbors detail"}'
```

Collect from all devices via pCall for a complete topology view.

### Step 2: Build the Visio Diagram Content

From discovery data, construct the topology as a Visio-compatible format. Use the OOXML structure that Visio .vsdx files use (ZIP archive containing XML).

For simpler workflows, generate the topology as **Mermaid** first, then use **Draw.io** for the editable diagram, and export the final version as .vsdx via the Draw.io editor.

### Step 3: Upload to SharePoint

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_upload_file '{"driveId":"<drive-id>","parentId":"<topology-folder-id>","fileName":"campus-topology-2026-02-22.vsdx","content":"<base64-vsdx-content>"}'
```

### Step 4: Share the Diagram

Create a sharing link for the team:

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_create_sharing_link '{"driveId":"<drive-id>","itemId":"<file-id>","type":"view","scope":"organization"}'
```

## Diagram Types

### 1. Physical Topology Diagram

Generated from CDP/LLDP neighbor data. Shows:
- Device icons (router, switch, firewall, AP)
- Physical connections with interface labels
- IP addressing on each link
- Link speeds and media types

Data sources:
- `show cdp neighbors detail` — device names, platforms, interfaces, IPs
- `show lldp neighbors detail` — same for LLDP-enabled devices
- `show interfaces` — link speeds, media types, error counters

### 2. Logical Topology Diagram

Generated from routing protocol data. Shows:
- OSPF areas with area boundaries
- BGP AS topology with eBGP/iBGP peerings
- VRF boundaries and route leaking points
- VXLAN overlay vs underlay

Data sources:
- `show ip ospf neighbor` + `show ip ospf database` — OSPF topology
- `show bgp summary` — BGP peering topology
- `show vrf` — VRF membership

### 3. Reconciliation Status Diagram

Color-coded by NetBox reconciliation status:
- **Green** — Documented in NetBox, matches live state
- **Yellow** — Documented but mismatched (IP drift, MTU mismatch)
- **Red** — Undocumented link (exists on device, not in NetBox)
- **Gray** — Missing link (in NetBox, not seen on device)

Data source: **netbox-reconcile** skill output

### 4. Data Center Fabric Diagram

ACI-specific topology showing:
- Spine/leaf fabric with APIC controllers
- Tenant/VRF/BD/EPG hierarchy
- Contract relationships
- External connectivity (L3Out)

Data source: **aci-fabric-audit** skill output

## Integration with Other Skills

- **pyats-topology** — Primary data source for physical/logical topology discovery
- **netbox-reconcile** — Provides reconciliation status for color-coded diagrams
- **aci-fabric-audit** — ACI fabric topology data for data center diagrams
- **drawio-diagram** — Use Draw.io for quick interactive editing, then export to .vsdx format
- **msgraph-files** — Organize Visio files in SharePoint folder structure
- **msgraph-teams** — Post diagram links to Teams channels for team visibility
- **gait-session-tracking** — Record diagram generation in audit trail

## Naming Convention

```
<site>-<diagram-type>-<date>.vsdx

Examples:
  campus-physical-topology-2026-02-22.vsdx
  dc-aci-fabric-2026-02-22.vsdx
  wan-bgp-logical-2026-02-22.vsdx
  site-a-reconciliation-2026-02-22.vsdx
```

## SharePoint Organization

```
SharePoint: Network Engineering/
  └── Topology/
      ├── Physical/
      │   ├── campus-physical-topology-2026-02-22.vsdx
      │   └── dc-physical-topology-2026-02-22.vsdx
      ├── Logical/
      │   ├── wan-bgp-logical-2026-02-22.vsdx
      │   └── campus-ospf-logical-2026-02-22.vsdx
      ├── Reconciliation/
      │   └── site-a-reconciliation-2026-02-22.vsdx
      └── ACI/
          └── dc-aci-fabric-2026-02-22.vsdx
```

## GAIT Audit Trail

Record diagram generation in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Generated campus physical topology diagram from CDP/LLDP discovery (4 devices, 6 links). Uploaded to SharePoint Network Engineering/Topology/Physical/campus-physical-topology-2026-02-22.vsdx. Sharing link created for Network Engineering team.","artifacts":[]}}'
```
