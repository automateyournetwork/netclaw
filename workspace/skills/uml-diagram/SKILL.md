---
name: uml-diagram
description: "UML and diagram generation via Kroki — class, sequence, activity, state, component, deployment, network, ER, C4, Mermaid, D2, Graphviz, BPMN, 27+ types"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": [] } } }
---

# UML & Diagram Generation via Kroki

Generate 27+ diagram types using the UML MCP server backed by [Kroki](https://kroki.io) multi-engine rendering. Supports PlantUML, Mermaid, D2, Graphviz, BPMN, ERD, C4, network diagrams, rack diagrams, packet diagrams, and more — output as SVG, PNG, PDF, or JPEG.

## MCP Server

| Property | Value |
|----------|-------|
| **Source** | [antoinebou12/uml-mcp](https://github.com/antoinebou12/uml-mcp) |
| **Transport** | stdio (default) or HTTP |
| **Tools** | 2 (`generate_uml`, `generate_diagram_url`) |
| **Resources** | 8 (diagram types, templates, examples, formats, server info) |
| **Prompts** | 11 (class, sequence, activity, usecase, Mermaid, BPMN, etc.) |
| **Rendering** | Kroki (primary) with PlantUML and Mermaid.ink fallback |

## Tools

### `generate_uml`

Generate a diagram and optionally save to disk.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `diagram_type` | string | required | Diagram type (class, sequence, mermaid, d2, graphviz, etc.) |
| `code` | string | required | Diagram source code |
| `output_dir` | string | null | Directory to save file (null = no file write) |
| `output_format` | string | "svg" | Output format: svg, png, pdf, jpeg, txt, base64 |
| `theme` | string | null | PlantUML theme directive |
| `scale` | float | 1.0 | SVG scaling factor (min 0.1) |

**Returns:** `{ code, url, playground, local_path, content_base64, error }`

### `generate_diagram_url`

Get the Kroki rendering URL and optional base64 content without saving to disk.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `diagram_type` | string | required | Diagram type |
| `code` | string | required | Diagram source code |
| `output_format` | string | "svg" | Output format |
| `theme` | string | null | PlantUML theme |
| `scale` | float | 1.0 | SVG scaling factor |

**Returns:** `{ code, url, playground, content_base64, error }`

---

## Supported Diagram Types (27+)

### PlantUML-based

| Type | Description | Use Case |
|------|-------------|----------|
| `class` | Class diagrams | Object relationships, inheritance, interfaces |
| `sequence` | Sequence diagrams | Message flows between components |
| `activity` | Activity diagrams | Workflow and process flows |
| `usecase` | Use case diagrams | Actor-system interactions |
| `state` | State machine diagrams | FSM, protocol states |
| `component` | Component diagrams | System architecture |
| `deployment` | Deployment diagrams | Infrastructure layout |
| `object` | Object diagrams | Instance-level relationships |
| `c4plantuml` | C4 architecture | System context, container, component views |
| `plantuml` | Generic PlantUML | Any PlantUML syntax |

### Network & Infrastructure

| Type | Description | Use Case |
|------|-------------|----------|
| `nwdiag` | Network diagrams | Network topology, IP addressing, VLANs |
| `rackdiag` | Rack diagrams | Data center rack layouts |
| `packetdiag` | Packet diagrams | Protocol header formats (Ethernet, IP, TCP) |
| `blockdiag` | Block diagrams | System block diagrams |
| `actdiag` | Activity diagrams | Activity flow (blockdiag family) |
| `seqdiag` | Sequence diagrams | Sequence flow (blockdiag family) |

### Other Backends

| Type | Description | Use Case |
|------|-------------|----------|
| `mermaid` | Mermaid diagrams | Flowcharts, Gantt, sequence, pie, journey |
| `d2` | D2 declarative | Modern declarative diagrams |
| `graphviz` | Graphviz DOT | Graph layouts, dependency trees |
| `erd` | Entity-Relationship | Database schema diagrams |
| `dbml` | Database Markup | Database schema (DBML syntax) |
| `bpmn` | BPMN 2.0 | Business process modeling |
| `structurizr` | Structurizr DSL | C4 model architecture |
| `ditaa` | ASCII art to diagram | Convert ASCII art to polished diagrams |
| `wavedrom` | Digital timing | Protocol timing diagrams, signal waveforms |
| `wireviz` | Wire/cable harness | Cable and connector documentation |
| `bytefield` | Byte field | Binary format documentation |

---

## Network Engineering Examples

### Network Topology (nwdiag)

```
generate_uml(
  diagram_type="nwdiag",
  code="""
nwdiag {
  network dmz {
    address = "210.x.x.x/24"
    web01 [address = "210.x.x.1"];
    web02 [address = "210.x.x.2"];
  }
  network internal {
    address = "172.x.x.x/24"
    web01 [address = "172.x.x.1"];
    web02 [address = "172.x.x.2"];
    db01;
  }
}
""",
  output_format="svg"
)
```

### Rack Diagram (rackdiag)

```
generate_uml(
  diagram_type="rackdiag",
  code="""
rackdiag {
  16U;
  1: UPS;
  2: UPS;
  3: Patch Panel;
  4: Catalyst 9300;
  5: Catalyst 9300;
  6: Nexus 9000;
  7: Nexus 9000;
  8: ASR 1001-X;
  9: ASR 1001-X;
  10: BIG-IP i5800;
  11: BIG-IP i5800;
  12: UCS C220;
  13: UCS C220;
  14: UCS C220;
  15: UCS C220;
  16: Cable Management;
}
""",
  output_format="png"
)
```

### Packet Header (packetdiag)

```
generate_uml(
  diagram_type="packetdiag",
  code="""
packetdiag {
  colwidth = 32
  node_height = 72
  0-3: Version
  4-7: IHL
  8-15: DSCP / ECN
  16-31: Total Length
  32-47: Identification
  48-50: Flags
  51-63: Fragment Offset
  64-71: TTL
  72-79: Protocol
  80-95: Header Checksum
  96-127: Source Address
  128-159: Destination Address
}
""",
  output_format="svg"
)
```

### BGP State Machine (state)

```
generate_uml(
  diagram_type="state",
  code="""
@startuml
[*] --> Idle
Idle --> Connect : Start
Connect --> OpenSent : TCP established
Connect --> Active : TCP failed
Active --> OpenSent : TCP established
Active --> Connect : ConnectRetry timer
OpenSent --> OpenConfirm : OPEN received (valid)
OpenSent --> Idle : OPEN received (error)
OpenConfirm --> Established : KEEPALIVE received
OpenConfirm --> Idle : Hold timer expired
Established --> Idle : NOTIFICATION / Hold expired
Established : Process UPDATE messages
@enduml
""",
  output_format="svg"
)
```

### OSPF Area Design (class)

```
generate_uml(
  diagram_type="class",
  code="""
@startuml
package "Area 0 - Backbone" {
  class "Core-1" as C1 { router-id: 1.1.1.1 }
  class "Core-2" as C2 { router-id: 2.2.2.2 }
  C1 -- C2 : 10G P2P
}
package "Area 1 - Campus" {
  class "Dist-1" as D1 { router-id: 3.3.3.3 }
  class "Dist-2" as D2 { router-id: 4.4.4.4 }
}
package "Area 2 - DC" {
  class "Spine-1" as S1 { router-id: 5.5.5.5 }
  class "Spine-2" as S2 { router-id: 6.6.6.6 }
}
C1 -- D1 : ABR
C2 -- D2 : ABR
C1 -- S1 : ABR
C2 -- S2 : ABR
@enduml
""",
  output_format="svg"
)
```

### Sequence: Change Request Flow

```
generate_uml(
  diagram_type="sequence",
  code="""
@startuml
actor Engineer
participant NetClaw
participant ServiceNow
participant Device
participant GAIT

Engineer -> NetClaw : "Add Loopback99"
NetClaw -> ServiceNow : Create Change Request
ServiceNow --> NetClaw : CR-12345 (New)
NetClaw -> ServiceNow : Wait for approval
ServiceNow --> NetClaw : CR-12345 (Implement)
NetClaw -> Device : Capture baseline
Device --> NetClaw : Running config
NetClaw -> Device : Apply config
Device --> NetClaw : Config applied
NetClaw -> Device : Verify change
Device --> NetClaw : Loopback99 up/up
NetClaw -> ServiceNow : Close CR-12345
NetClaw -> GAIT : Record full audit trail
NetClaw --> Engineer : Done. Verified.
@enduml
""",
  output_format="svg"
)
```

### C4 Architecture (structurizr)

```
generate_uml(
  diagram_type="structurizr",
  code="""
workspace {
  model {
    engineer = person "Network Engineer"
    netclaw = softwareSystem "NetClaw" {
      openclaw = container "OpenClaw Agent"
      pyats = container "pyATS MCP"
      gait = container "GAIT MCP"
    }
    network = softwareSystem "Network Devices"
    servicenow = softwareSystem "ServiceNow"

    engineer -> openclaw "Chat"
    openclaw -> pyats "MCP (stdio)"
    openclaw -> gait "MCP (stdio)"
    pyats -> network "SSH/NETCONF"
    openclaw -> servicenow "REST API"
  }
  views {
    container netclaw {
      include *
      autoLayout
    }
  }
}
""",
  output_format="svg"
)
```

---

## Workflows

### 1. Network Topology Documentation
```
pyats-topology → CDP/LLDP discovery data
→ generate_uml(type="nwdiag") → network topology diagram
→ msgraph-files → upload to SharePoint
→ GAIT
```

### 2. Protocol State Machine Reference
```
generate_uml(type="state") → BGP/OSPF/STP state machine
→ Share in Slack/Teams for team reference
→ GAIT
```

### 3. Change Request Visualization
```
servicenow-change-workflow → CR details
→ generate_uml(type="sequence") → change flow diagram
→ Attach to ServiceNow CR or GAIT log
→ GAIT
```

### 4. Data Center Rack Documentation
```
generate_uml(type="rackdiag") → rack layout
→ generate_uml(type="nwdiag") → network connections
→ Cross-reference with NetBox rack/device data
→ msgraph-files → upload to SharePoint
→ GAIT
```

### 5. Packet Format Reference
```
generate_uml(type="packetdiag") → protocol header diagram
→ rfc-lookup → verify against RFC
→ Share as reference material
→ GAIT
```

### 6. Architecture Documentation
```
generate_uml(type="structurizr" or "c4plantuml") → C4 architecture views
→ generate_uml(type="deployment") → deployment diagram
→ generate_uml(type="component") → component breakdown
→ msgraph-files → upload to SharePoint
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-topology** | Feed CDP/LLDP discovery data into nwdiag for topology diagrams |
| **drawio-diagram** | UML MCP for standards-based UML; Draw.io for freeform network diagrams |
| **markmap-viz** | Markmap for hierarchical mind maps; UML for structured diagrams |
| **netbox-reconcile** | Generate nwdiag diagrams color-coded by reconciliation status |
| **rfc-lookup** | Pair packetdiag with RFC references for protocol documentation |
| **servicenow-change-workflow** | Sequence diagrams documenting change request flows |
| **msgraph-files** | Upload generated diagrams to SharePoint |
| **msgraph-teams** | Share diagram URLs in Teams channels |
| **gait-session-tracking** | Record all diagram generation in GAIT |

---

## Comparison: UML MCP vs Draw.io vs Markmap

| Feature | UML MCP | Draw.io | Markmap |
|---------|---------|---------|---------|
| **Best for** | Structured UML, protocol diagrams, architecture | Freeform network topology | Hierarchical mind maps |
| **Diagram types** | 27+ (class, sequence, nwdiag, rack, packet, etc.) | Network topology, flowcharts | Mind maps from markdown |
| **Rendering** | Kroki (server-side) | Browser or CLI | Browser |
| **Output** | SVG, PNG, PDF, JPEG | .drawio, PNG, SVG, PDF | HTML |
| **Code-based** | Yes (PlantUML, Mermaid, D2, DOT, etc.) | XML/Mermaid/CSV | Markdown |
| **Network-specific** | nwdiag, rackdiag, packetdiag | Full topology editor | OSPF/BGP hierarchies |

**When to use UML MCP:**
- Protocol state machines (BGP FSM, OSPF states, STP states)
- Network topology diagrams from code (nwdiag)
- Rack layouts (rackdiag)
- Packet header documentation (packetdiag)
- Sequence diagrams (change workflows, protocol exchanges)
- Architecture documentation (C4, component, deployment)
- Database schema diagrams (ERD, DBML)
- Any diagram type supported by Kroki

**When to use Draw.io:**
- Interactive topology editing
- Native .drawio files for team collaboration
- Color-coded reconciliation status overlays

**When to use Markmap:**
- Hierarchical data (OSPF areas, BGP peers, config structure)
- Quick visual summaries from markdown

---

## Guardrails

- **All operations are read-only** — generates diagrams, never modifies network state
- **Public Kroki by default** — diagram source code is sent to kroki.io for rendering; use a local Kroki instance (`KROKI_SERVER`) for sensitive topology data
- **No secrets in diagrams** — never include IP credentials, passwords, or SNMP communities in diagram source code
- **Record in GAIT** — every diagram generation must be logged
