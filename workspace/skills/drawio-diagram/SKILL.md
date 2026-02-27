---
name: drawio-diagram
description: "Generate draw.io network diagrams — native .drawio files with CLI export (PNG/SVG/PDF), plus browser-based Mermaid/XML/CSV via MCP server"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"] } } }
---

# Draw.io Network Diagrams

Generate network diagrams using two complementary approaches:

1. **Native File Mode** — Generate `.drawio` XML files on disk with optional PNG/SVG/PDF export via the draw.io desktop CLI (official jgraph skill-cli)
2. **Browser Mode** — Open diagrams in the Draw.io browser editor via the `@drawio/mcp` MCP server (Mermaid, XML, or CSV input)

---

## Mode 1: Native File Generation (Official Skill-CLI)

Generate native `.drawio` files directly. Optionally export to PNG, SVG, or PDF with the diagram XML embedded (so the exported file remains editable in draw.io).

### How to Create a Diagram

1. **Generate draw.io XML** in mxGraphModel format for the requested diagram
2. **Write the XML** to a `.drawio` file in the current working directory using the Write tool
3. **If the user requested an export format** (png, svg, pdf), export using the draw.io CLI with `--embed-diagram`, then delete the source `.drawio` file
4. **Open the result** — the exported file if exported, or the `.drawio` file otherwise

### Choosing the Output Format

Check the user's request for a format preference:

- `/drawio create a flowchart` → `flowchart.drawio`
- `/drawio png flowchart for login` → `login-flow.drawio.png`
- `/drawio svg: ER diagram` → `er-diagram.drawio.svg`
- `/drawio pdf architecture overview` → `architecture-overview.drawio.pdf`

If no format is mentioned, write the `.drawio` file and open it. The user can ask to export later.

### Supported Export Formats

| Format | Embed XML | Notes |
|--------|-----------|-------|
| `png` | Yes (`-e`) | Viewable everywhere, editable in draw.io |
| `svg` | Yes (`-e`) | Scalable, editable in draw.io |
| `pdf` | Yes (`-e`) | Printable, editable in draw.io |
| `jpg` | No | Lossy, no embedded XML support |

PNG, SVG, and PDF all support `--embed-diagram` — the exported file contains the full diagram XML, so opening it in draw.io recovers the editable diagram.

### draw.io CLI

The draw.io desktop app includes a command-line interface for exporting.

#### Locating the CLI

Try `drawio` first (works if on PATH), then fall back to the platform-specific path:

- **macOS**: `/Applications/draw.io.app/Contents/MacOS/draw.io`
- **Linux**: `drawio` (typically on PATH via snap/apt/flatpak)
- **Windows**: `"C:\Program Files\draw.io\draw.io.exe"`

Use `which drawio` (or `where drawio` on Windows) to check if it's on PATH before falling back.

#### Export Command

```bash
drawio -x -f <format> -e -b 10 -o <output> <input.drawio>
```

Key flags:
- `-x` / `--export`: export mode
- `-f` / `--format`: output format (png, svg, pdf, jpg)
- `-e` / `--embed-diagram`: embed diagram XML in the output (PNG, SVG, PDF only)
- `-o` / `--output`: output file path
- `-b` / `--border`: border width around diagram (default: 0)
- `-t` / `--transparent`: transparent background (PNG only)
- `-s` / `--scale`: scale the diagram size
- `--width` / `--height`: fit into specified dimensions (preserves aspect ratio)
- `-a` / `--all-pages`: export all pages (PDF only)
- `-p` / `--page-index`: select a specific page (1-based)

#### Opening the Result

- **macOS**: `open <file>`
- **Linux**: `xdg-open <file>`
- **Windows**: `start <file>`

### File Naming

- Use a descriptive filename based on the diagram content (e.g., `login-flow`, `database-schema`)
- Use lowercase with hyphens for multi-word names
- For export, use double extensions: `name.drawio.png`, `name.drawio.svg`, `name.drawio.pdf` — this signals the file contains embedded diagram XML
- After a successful export, delete the intermediate `.drawio` file — the exported file contains the full diagram

---

## Mode 2: Browser Editor via MCP Server

Open diagrams directly in the Draw.io browser editor using the `@drawio/mcp` MCP server. Supports three input formats.

### Mermaid Diagrams (best for quick topology graphs)

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD\n  A --> B"}'
```

### XML Diagrams (best for detailed, styled diagrams with precise positioning)

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_xml '{"content":"<mxGraphModel>...</mxGraphModel>"}'
```

### CSV Diagrams (best for device inventories)

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_csv '{"content":"## label: %name%\nname,refs\nA,B\nB,C"}'
```

All three tools accept optional `"lightbox": true` for read-only view and `"dark": "auto"|"true"|"false"` for dark mode.

The tool returns a Draw.io URL. Share it directly — the diagram opens in the browser editor where it can be edited, exported, or saved.

---

## XML Format Reference

A `.drawio` file is native mxGraphModel XML. Always generate XML directly — Mermaid and CSV formats require server-side conversion and cannot be saved as native files.

### Basic Structure

Every diagram must have this structure:

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- Diagram cells go here with parent="1" -->
  </root>
</mxGraphModel>
```

- Cell `id="0"` is the root layer
- Cell `id="1"` is the default parent layer
- All diagram elements use `parent="1"` unless using multiple layers

### Common Styles

**Rounded rectangle:**
```xml
<mxCell id="2" value="Label" style="rounded=1;whiteSpace=wrap;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
</mxCell>
```

**Diamond (decision):**
```xml
<mxCell id="3" value="Condition?" style="rhombus;whiteSpace=wrap;" vertex="1" parent="1">
  <mxGeometry x="100" y="200" width="120" height="80" as="geometry"/>
</mxCell>
```

**Arrow (edge):**
```xml
<mxCell id="4" value="" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="2" target="3" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

**Labeled arrow:**
```xml
<mxCell id="5" value="Yes" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="3" target="6" parent="1">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### Useful Style Properties

| Property | Values | Use for |
|----------|--------|---------|
| `rounded=1` | 0 or 1 | Rounded corners |
| `whiteSpace=wrap` | wrap | Text wrapping |
| `fillColor=#dae8fc` | Hex color | Background color |
| `strokeColor=#6c8ebf` | Hex color | Border color |
| `fontColor=#333333` | Hex color | Text color |
| `shape=cylinder3` | shape name | Database cylinders |
| `shape=mxgraph.flowchart.document` | shape name | Document shapes |
| `ellipse` | style keyword | Circles/ovals |
| `rhombus` | style keyword | Diamonds |
| `edgeStyle=orthogonalEdgeStyle` | style keyword | Right-angle connectors |
| `edgeStyle=elbowEdgeStyle` | style keyword | Elbow connectors |
| `dashed=1` | 0 or 1 | Dashed lines |
| `swimlane` | style keyword | Swimlane containers |

---

## Diagram Types for Network Engineering

### 1. Physical Topology Diagram

Shows devices, physical links, interface names, IP addresses, and link speeds.

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD\n  R1[\"R1\\nCore Router\\n10.255.255.1\"]\n  R2[\"R2\\nCore Router\\n10.255.255.2\"]\n  SW1[\"SW1\\nDist Switch\\n10.255.255.3\"]\n  R1 -->|\"Gi0/0 -- Gi0/0\\n10.1.1.0/30\"| R2\n  R1 -->|\"Gi0/1 -- Gi0/1\\n10.1.2.0/30\"| SW1\n  R2 -->|\"Gi0/1 -- Gi0/1\\n10.1.3.0/30\"| SW1"}'
```

### 2. Logical Topology Diagram

Shows routing protocol relationships, areas, AS numbers, VRFs.

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph TD\n  subgraph \"OSPF Area 0\"\n    R1[\"R1 ABR\"]\n    R2[\"R2 ABR\"]\n  end\n  subgraph \"OSPF Area 1\"\n    R3[\"R3\"]\n  end\n  R1 --- R2\n  R1 --- R3"}'
```

### 3. Security Zones Diagram

Shows firewalls, DMZs, trust boundaries, ACL enforcement points.

```bash
python3 $MCP_CALL "npx -y @drawio/mcp" open_drawio_mermaid '{"content":"graph LR\n  subgraph \"Untrusted\"\n    INET((Internet))\n  end\n  subgraph \"DMZ\"\n    WEB[\"Web Server\"]\n  end\n  subgraph \"Trusted\"\n    CORE[\"Core Switch\"]\n  end\n  INET --> FW[\"Firewall\"]\n  FW --> WEB\n  FW --> CORE"}'
```

---

## CRITICAL: XML Well-Formedness

- **NEVER use double hyphens (`--`) inside XML comments.** `--` is illegal inside `<!-- -->` per the XML spec and causes parse errors. Use single hyphens or rephrase.
- Escape special characters in attribute values: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- Always use unique `id` values for each `mxCell`

---

## When to Use Each Mode

| Scenario | Mode | Why |
|----------|------|-----|
| Generate `.drawio` file for version control | Native File | Produces actual file on disk |
| Export PNG/SVG/PDF for documentation | Native File | CLI export with embedded XML |
| Quick topology preview from discovery data | Browser | Instant visual in browser |
| CSV-based inventory diagram | Browser | CSV format only available via MCP |
| Mermaid syntax diagram | Browser | Mermaid conversion only via MCP |
| Offline/air-gapped environment | Native File | No network needed |
| Sharing a link to the diagram | Browser | Returns shareable URL |

## Integration with Other Skills

- Use **pyats-topology** to discover the network, then generate diagrams from the data
- Use **netbox-reconcile** to color-code links by reconciliation status (documented/undocumented/missing)
- Use **markmap-viz** for hierarchical views alongside Draw.io for topology views
- Use **aci-fabric-audit** data to generate ACI fabric topology diagrams
- Use **gait-session-tracking** to record diagram generation with source data references
