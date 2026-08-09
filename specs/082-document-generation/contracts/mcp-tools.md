# Tool Contract — `document-mcp` (spec 082 / roadmap R18)

**Server**: `mcp-servers/document-mcp/server.py` · **Transport**: stdio · **Credentials**: none
**Manifest budget**: ≤ 5,000 tokens (FR-038a) · **Writes**: files only, never a device or a ticket (FR-033)

Six tools. Composition lives in skills, not here (FR-005d).

---

## Shared types

### `TaggedValue` — required wherever a document asserts a value

Exactly one of:

```jsonc
{"v": <scalar>, "src": "<tool or system>", "device": "<optional>", "as_of": "<optional ISO-8601>"}
{"unavailable": "<reason>"}
{"failed": "<reason>"}
```

`v` without `src` → **refused**. A bare scalar → **refused**. `{"v": ""}` is legal and means the source
genuinely returned empty — a different fact from `unavailable`.

### Every response envelope

```jsonc
{
  "source": "document-mcp",
  "generated_at": "2026-08-03T14:02:00Z",
  "outcome": "ok" | "written_with_gaps" | "truncated" | "refused_unattributed" |
             "refused_untyped" | "refused_template" | "refused_merged_status" |
             "not_fillable" | "output_unwritable" | "source_missing",
  "tool": "<tool name>",
  "artifact": {"path": "...", "bytes": 12345, "created_at": "...", "collision_suffix": null} | null,
  "sources_consulted": [{"src": "...", "device": "...", "as_of": "...", "element_count": 12,
                         "status": "ok" | "partial" | "failed"}],
  "gaps": {"unavailable": 3, "failed": 1},
  "caveats": ["..."],
  "message": "<present on any non-ok outcome>"
}
```

`generated_at`, `source` and the in-document stamp are set at the chokepoint. **No tool accepts them as
parameters.** Every response, including refusals, is GAIT-audited (FR-034).

---

## 1. `docx_write`

Build a Word document from an ordered block list.

```jsonc
{
  "title": "Change Record CHG0012345",
  "blocks": [
    {"type": "heading", "text": "Pre-change state", "level": 1},
    {"type": "paragraph", "text": "State captured before the window opened."},
    {"type": "keyvalue", "pairs": [
       {"label": "Hostname", "value": {"v": "fgt-01", "src": "fgt_system_status",
                                       "as_of": "2026-08-03T13:58:00Z"}},
       {"label": "Serial",   "value": {"unavailable": "device did not answer"}}]},
    {"type": "table", "caption": "Interfaces",
     "columns": ["Interface", "Admin state", "Oper state"],
     "rows": [[{"v":"port1","src":"fgt_list_interfaces","device":"fgt-01"},
               {"v":"up","src":"fgt_list_interfaces","device":"fgt-01"},
               {"v":"down","src":"fgt_list_interfaces","device":"fgt-01"}]]},
    {"type": "image", "path": "workspace/output/drawio-diagram/topo-....png",
     "caption": "Topology", "src": "drawio-diagram"}
  ],
  "output_id": "chg0012345"
}
```

**Block types**: `heading`, `paragraph`, `figure`, `table`, `keyvalue`, `image`, `pagebreak`.

**Guarantees**
- A `Source` column is **appended by the writer** to every `table` and `keyvalue` — the caller cannot omit it.
- Every page footer carries generation time and NetClaw attribution.
- A visible `Sources` section is appended.
- `paragraph` accepts no TaggedValue; prose containing a bare number emits a caveat naming the block index
  (see the note in data-model.md §4 — prose is where an unattributed figure would hide).
- `image.path` must exist and be inside the workspace output dir, and `src` must name the producing skill
  (FR-014) → else `source_missing`.
- No footnotes: python-docx 1.2.0 has no footnote API (research D3), so attribution is inline.
- Any `template` / `template_path` parameter → **`refused_template`** (FR-023a).

---

## 2. `xlsx_write`

```jsonc
{
  "sheets": [
    {"name": "Interfaces",
     "columns": ["Device", "Interface", "Admin state", "Oper state", "Address"],
     "rows": [[{"v":"fgt-01","src":"fgt_list_interfaces"}, ...]],
     "failed_rows": [{"label": "fgt-02", "failed": "connection refused"}]}
  ],
  "output_id": "interface-audit"
}
```

**Guarantees**
- A `Source` and an `As of` column are appended to every sheet.
- `failed_rows` render **as rows**, visually marked, and are counted (FR-003).
- A banner row states *attempted / succeeded / failed* (SC-004).
- A `Sources` sheet is always added.
- **Every string cell is forced to `data_type = 's'`** so a leading `=` cannot become a live formula
  (FR-026 / research D5, measured).
- A column named `status` combining admin and operational state → **`refused_merged_status`** (FR-015).
- Row bound: default 50,000 data rows per sheet. On truncation → `truncated`, and the bound is written
  **into the sheet** (FR-027), not only into this response.

---

## 3. `pptx_write`

```jsonc
{
  "title": "Fortinet posture review",
  "slides": [
    {"layout": "bullets", "title": "What we found",
     "bullets": ["Two interfaces admin-up with no carrier"], "detail_ref": "Interface detail"},
    {"layout": "figure", "title": "Scope",
     "figures": [{"label": "Interfaces reviewed",
                  "value": {"v": 2, "src": "fgt_list_interfaces", "device": "fgt-01"}}]},
    {"layout": "image", "title": "Topology",
     "image": {"path": "workspace/output/threejs-network-viz/....png", "src": "threejs-network-viz"}}
  ],
  "output_id": "posture-review"
}
```

**Guarantees**
- Any slide with a `figure` gets a **visible** on-slide source line — speaker notes are hidden and do not
  count (FR-008a / research D4).
- A `Sources` slide is always appended.
- A slide with `bullets` and no `detail_ref` emits a caveat: a summary claim should be traceable (FR-005).
- Diagrams are embedded, never drawn here (FR-014).

---

## 4. `pdf_inspect_form`

```jsonc
{"path": "/abs/or/repo-relative/form.pdf"}
```

Returns the PDF's named fields so a caller can map data to fields it has actually seen, rather than
inventing names.

```jsonc
{"outcome": "ok",
 "data": {"fillable": true, "field_count": 3,
          "fields": [{"name": "change_number", "kind": "text", "current_value": "", "page": 0}]}}
```

Not a form → `not_fillable` with a message. (`doc.is_form_pdf` returns an **int**, measured `3`; compared
truthily.)

---

## 5. `pdf_fill_form`

```jsonc
{"path": "form.pdf",
 "values": {"change_number": {"v": "CHG0012345", "src": "servicenow_get_change"},
            "approver":      {"unavailable": "no approver recorded on the CR"}},
 "output_id": "chg0012345-form"}
```

```jsonc
{"outcome": "written_with_gaps",
 "artifact": {"path": "workspace/output/document-mcp/pdfform-20260803T140200Z-chg0012345-form.pdf"},
 "data": {"filled": ["change_number"],
          "unfilled": ["approver", "device_hostname"],
          "unmatched": []}}
```

**Guarantees**
- The **input PDF is never modified** — a new file is always written.
- `unavailable` / `failed` leave the field genuinely empty and appear in `unfilled` (FR-024b, US4 §2).
- Supplied keys matching no field appear in `unmatched` and are **never dropped silently** (FR-024b).
- Only named fields are written; no positional text placement (FR-024a).
- Non-fillable → `not_fillable`, **no output file** (FR-024).
- Because a filled PDF has nowhere to put a Sources section without altering the customer's form, the
  provenance for a fill lives in the **GAIT record and the response**, and this is stated as an explicit
  limitation in the skill. It is the one format where FR-008 cannot be met inside the artefact, and saying so
  is required rather than pretending otherwise.

---

## 6. `list_documents`

```jsonc
{"kind": "docx" | "xlsx" | "pptx" | "pdf" | null, "limit": 50}
```

Lists what has been generated, newest first, so an operator can find a file. Read-only; touches nothing.

---

## Refusals — the disclosure controls

| Condition | Outcome | Why it is a refusal and not a warning |
|---|---|---|
| `v` without `src` | `refused_unattributed` | An unattributed figure in a durable artefact is the failure mode this feature exists to prevent (FR-007) |
| Bare scalar for a TaggedValue | `refused_untyped` | Accepting it would let a caller express missing data as a blank (FR-005c) |
| Office template supplied | `refused_template` | Out of scope by clarification; silently ignoring it would produce an unbranded document the operator believes is branded (FR-023a) |
| Merged admin/oper `status` column | `refused_merged_status` | The distinction spec 080's completion established (FR-015) |
| Output dir missing/unwritable | `output_unwritable` | No silent fallback to a temp dir the operator will never find (FR-020) |
| `image.path` missing or outside the output dir | `source_missing` | An embedded diagram must be a real artefact from a real skill (FR-014) |

Every refusal is GAIT-audited exactly like a success (FR-034).

---

## What this server will not do

- **Send anything.** Writing a file is in scope; emailing, posting to Slack, or attaching to a ticket is
  Principle XIV territory and belongs to `slack-report-delivery` / `webex-report-delivery`.
- **Create or update a ticket.** `servicenow-change-workflow` owns the CR lifecycle (FR-037).
- **Draw a diagram.** `drawio-diagram`, `markmap-viz`, `uml-diagram`, `threejs-network-viz` own that; this
  embeds their output (FR-014, FR-035).
- **Read documents.** `rag-mcp` ingests these formats; this writes them (FR-036).
- **Touch a device.** No device access, so no approval or change-record gate exists here (FR-033).
