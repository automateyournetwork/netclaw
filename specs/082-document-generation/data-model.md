# Data Model — Document Generation (spec 082 / roadmap R18)

**Date**: 2026-08-03 · Derived from spec.md Key Entities + research.md D8

No database. Every entity here is an in-memory shape passed across the MCP boundary or written into a file.
The point of typing them is FR-005c: **the honest representation must be the only expressible one.**

---

## 1. TaggedValue — the load-bearing type

Every populated field in every document is one of exactly three shapes. This is what makes FR-001–FR-004
enforceable rather than aspirational.

```jsonc
// (a) a real value, with where it came from
{ "v": <string|number|bool>, "src": "fgt_list_interfaces", "device": "fgt-01",
  "as_of": "2026-08-03T14:02:00Z" }

// (b) no data — the source was consulted and had nothing, or was never reachable for this field
{ "unavailable": "device did not answer within timeout" }

// (c) the source errored
{ "failed": "FortiGate plane unreachable: connection refused" }
```

| Field | Required | Notes |
|---|---|---|
| `v` | in shape (a) | May be `""` — meaning *the source genuinely returned empty*, which is a **different fact** from `unavailable` and renders differently |
| `src` | **yes, in shape (a)** | Tool or system name. Absent → `ProvenanceError`, refused. Never defaulted. |
| `device` | no | Device, record or account the value came from, when there is one |
| `as_of` | no | The **source's** own as-of time (FR-010). Distinct from the document's generation time. Absent means the source did not provide one — not that it equals generation time. |
| `unavailable` | in shape (b) | Free text reason, rendered verbatim |
| `failed` | in shape (c) | Free text reason, rendered verbatim |

### Validation rules

| Rule | Violation → |
|---|---|
| Exactly one of `v` / `unavailable` / `failed` present | `refused`, message naming the field path |
| `v` present without `src` | `refused` — **FR-007**. An unattributed figure is not renderable. |
| A bare scalar where a TaggedValue is expected | `refused`, message naming the field path and showing the accepted shapes |
| `as_of` not ISO-8601 | `refused` |
| `unavailable` / `failed` with an empty reason | `refused` — "unavailable" with no reason is a blank wearing a label |

### Rendering contract

| Shape | Renders as |
|---|---|
| `{"v": x, ...}` | `x`, with visible attribution (column / inline parenthetical) |
| `{"v": ""}` | `(empty)` — explicit, plus attribution. The source *was* consulted. |
| `{"unavailable": r}` | `NOT AVAILABLE — <r>` |
| `{"failed": r}` | `RETRIEVAL FAILED — <r>` |

`unavailable` and `failed` **never** render as an empty cell, `N/A`, `0`, `-`, or whitespace (FR-001).

---

## 2. SourceRecord — one entry in the Sources section

Accumulated by the chokepoint from every TaggedValue seen, deduplicated by `(src, device)`.

| Field | Type | Notes |
|---|---|---|
| `src` | string | Tool or system name |
| `device` | string? | Device/record scope, if any |
| `as_of` | string? | Latest as-of seen for this source |
| `element_count` | int | How many elements in this document came from it |
| `status` | enum | `ok` \| `partial` \| `failed` — `partial` when this source produced both values and unavailables |

Every generated file carries a **Sources section** built from these (FR-009a): a `Sources` section in
`.docx`, a `Sources` worksheet in `.xlsx`, a `Sources` slide in `.pptx`. Required **in addition to**
per-element attribution, never instead of it.

---

## 3. DocumentStamp — the every-document header/footer

| Field | Type | Source |
|---|---|---|
| `generated_at` | ISO-8601 UTC | Server clock at write time (FR-006) |
| `generated_by` | string | `"NetClaw"` + server version — constant, never caller-supplied |
| `tool` | string | Which tool produced it |
| `truncated` | bool | Whether a bound was applied (FR-027) |
| `bound_applied` | int? | The bound, stated **in the document** when `truncated` |

Rendered in the `.docx` section footer (every page), the `.xlsx` `Sources` sheet header **and** a frozen
banner row on each data sheet, and the `.pptx` title slide plus the Sources slide.

**Not caller-supplied.** A caller cannot set `generated_at` or `generated_by` — they are stamped at the
chokepoint (FR-005b).

---

## 4. Document block types (`docx_write`)

An ordered list. Each block is `{"type": ..., ...}`.

| Type | Payload | Provenance handling |
|---|---|---|
| `heading` | `{"text": str, "level": 1-4}` | none (structural) |
| `paragraph` | `{"text": str}` | none (structural narrative) |
| `figure` | `{"label": str, "value": TaggedValue}` | inline parenthetical after the value (D3) |
| `table` | `{"caption": str?, "columns": [str], "rows": [[TaggedValue]]}` | a `Source` column is **appended by the writer**, not by the caller |
| `keyvalue` | `{"pairs": [{"label": str, "value": TaggedValue}]}` | two-column table + `Source` column |
| `image` | `{"path": str, "caption": str, "src": str}` | `src` names the diagram skill that produced it (FR-014); a path outside the workspace output dir is refused |
| `pagebreak` | `{}` | none |

**`paragraph` carries no TaggedValue by design** — free prose is the one place a model could smuggle an
unattributed figure. Any number a document asserts must be a `figure`, `table` or `keyvalue`, all of which
force attribution. This is stated in the skill and enforced by a lint in the writer: a `paragraph` whose text
matches a bare-number pattern emits a caveat naming the block index.

---

## 5. Worksheet model (`xlsx_write`)

```jsonc
{ "sheets": [ { "name": "Interfaces",
                "columns": ["Device", "Interface", "Admin state", "Oper state", "Address"],
                "rows": [ [TaggedValue, TaggedValue, ...] ],
                "failed_rows": [ {"label": "fgt-02", "failed": "connection refused"} ] } ] }
```

| Rule | Why |
|---|---|
| The writer appends a `Source` column and an `As of` column | FR-009a, per-row visible attribution |
| `failed_rows` are rendered **as rows**, visually marked, counted in the total | FR-003 — a shorter sheet reads as a smaller estate |
| A row-count banner states *attempted / succeeded / failed* | SC-004 |
| Admin and operational state are separate columns; a merged `status` is refused | FR-015 |
| Every string cell is forced `data_type = 's'` after assignment | FR-026 / research D5 — a leading `=` otherwise becomes a live formula |
| A `Sources` sheet is always added | FR-009a |

---

## 6. Slide model (`pptx_write`)

```jsonc
{ "slides": [ { "layout": "title" | "bullets" | "figure" | "image",
                "title": str,
                "bullets": [str]?,
                "figures": [{"label": str, "value": TaggedValue}]?,
                "image": {"path": str, "src": str}?,
                "detail_ref": str? } ] }
```

| Rule | Why |
|---|---|
| Any slide carrying a `figure` gets a **visible** source line along the bottom | FR-008a / research D4 — speaker notes are hidden |
| A `Sources` slide is always appended | FR-009a |
| A summary claim carries `detail_ref` pointing at a detail slide or the Sources slide | FR-005, SC-003 of US3 |
| `image.path` must be inside the workspace output dir and `src` must name the producing skill | FR-014 |
| Speaker notes may repeat the detail — additive only | FR-008a |

---

## 7. PDF form model (`pdf_inspect_form`, `pdf_fill_form`)

**FormField** (read, from `pdf_inspect_form`):

| Field | Type | From |
|---|---|---|
| `name` | string | `widget.field_name` |
| `kind` | enum | `text` \| `checkbox` \| `radio` \| `combobox` \| `listbox` \| `button` \| `signature` |
| `current_value` | string | `widget.field_value` |
| `page` | int | page index |

**FillResult** (from `pdf_fill_form`):

| Field | Type | Meaning |
|---|---|---|
| `filled` | [str] | Field names written |
| `unfilled` | [str] | Named fields left genuinely empty (FR-024b) |
| `unmatched` | [str] | Supplied keys matching no field — **never dropped silently** (FR-024b) |
| `output_path` | str | The new file. The input PDF is never modified. |

A PDF where `doc.is_form_pdf` is falsy → `outcome: not_fillable`, no output file (FR-024). Note
`is_form_pdf` returns an **int** (measured: `3`); compare truthily.

Fill values are `TaggedValue`s. `unavailable` / `failed` leave the field **empty** and are reported in
`unfilled` — a form is never completed with a guess (FR-024b, US4 scenario 2).

---

## 8. Outcome — the response vocabulary

Following spec 080's `Outcome` and spec 081's `outcomes.py` split.

| Value | Means |
|---|---|
| `ok` | Document written |
| `written_with_gaps` | Written, and it contains `unavailable` or `failed` elements — **stated, not hidden** |
| `truncated` | Written, and a bound was applied; the bound is in the document |
| `refused_unattributed` | A `v` arrived without a `src` |
| `refused_untyped` | A bare scalar arrived where a TaggedValue was required |
| `refused_template` | An Office template was supplied (FR-023a) |
| `refused_merged_status` | Admin and operational state were merged into one column (FR-015) |
| `not_fillable` | The PDF has no form fields |
| `output_unwritable` | Directory missing or not writable — **no silent fallback** (FR-020) |
| `source_missing` | An `image.path` does not exist or is outside the output dir |

`ok` and `written_with_gaps` are deliberately distinct: a caller must not be able to read "success" and
assume completeness.

---

## 9. OutputArtifact

| Field | Type | Notes |
|---|---|---|
| `path` | str | `workspace/output/document-mcp/<kind>-<UTC stamp>-<safe-id>.<ext>` |
| `bytes` | int | |
| `created_at` | ISO-8601 UTC | |
| `collision_suffix` | int? | Present when `-2`, `-3`… was needed |

Written with `os.open(..., O_CREAT | O_EXCL | O_WRONLY)`. On `FileExistsError` the suffix increments — an
existing file is **never** opened for writing (FR-018 / research D7). Feature 046's convention relies on
timestamp uniqueness alone, which collides within the same second; this is the one place spec 082 tightens
it.

---

## Entity relationships

```
DocumentRequest
 ├─ blocks / sheets / slides / form-mapping
 │    └─ TaggedValue  ──accumulated by──▶ SourceRecord ──renders──▶ Sources section
 ├─ stamped at chokepoint with ──▶ DocumentStamp
 ├─ written by ──▶ OutputArtifact  (O_EXCL)
 └─ returns ──▶ Envelope { outcome, artifact, sources_consulted, caveats } ──▶ GAIT record
```

Every path passes through the chokepoint. There is no writer entry point that skips `DocumentStamp` or
`SourceRecord` accumulation — that is the structural guarantee SC-018a tests.
