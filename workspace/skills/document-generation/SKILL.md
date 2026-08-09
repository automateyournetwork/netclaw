---
name: document-generation
description: "Generate Word (.docx), Excel (.xlsx) and PowerPoint (.pptx) documents and fill existing PDF forms, from real NetClaw data, with per-element provenance and no fabrication. Use when someone needs a deliverable rather than an answer — a change record to attach to a CR, an audit workbook for a compliance reviewer, a summary deck for a director, or a required PDF form filled from real device and ticket data."
version: 1.0.0
license: Apache-2.0
tags: [documents, docx, xlsx, pptx, pdf, reporting, change-record, audit, deliverables]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["DOCUMENT_MCP_CMD"] } } }
---

# Document Generation

## MCP Server

- **Server**: `document-mcp` (NetClaw-authored, spec 082 / roadmap R18)
- **Command**: `$DOCUMENT_MCP_CMD`
- **Transport**: stdio
- **Credentials**: **none.** This server writes files and touches nothing else
- **Infrastructure**: no device access, no ticket writes — so there is no approval gate here

## The one rule that matters most

> ### A document must never fabricate to fill a blank.

Tool output is ephemeral — read once, in context, by the person who asked. **A document is not.** It gets
emailed, attached to a ticket, filed for audit, and read months later by someone who was not there, and it
carries the authority of its formatting.

A professional-looking change record with a plausible invented number is a far more effective way to launder
a guess into an official record than any amount of terminal output, because **nobody re-derives a figure
that is already in a table in a `.docx`.**

**So: never infer, estimate, interpolate, or carry forward a stale value to complete a document.** If you do
not have a figure, send `{"unavailable": "<why>"}`. The server renders that as visible text. It will not
render a blank, and it will not let you send one.

## Tagged values — the only accepted shape

Every value in a figure, table, keyvalue or form field is one of exactly three shapes:

```jsonc
{"v": "fgt-01", "src": "fgt_system_status", "device": "fgt-01", "as_of": "2026-08-03T13:58:00Z"}
{"unavailable": "device did not answer within timeout"}
{"failed": "FortiGate plane unreachable: connection refused"}
```

| You send | The document shows |
|---|---|
| `{"v": x, "src": ...}` | `x`, with a visible source |
| `{"v": ""}` | `(empty)` — the source *was* consulted and returned nothing |
| `{"unavailable": r}` | `NOT AVAILABLE — r` |
| `{"failed": r}` | `RETRIEVAL FAILED — r` |
| `{"v": x}` with no `src` | **refused** |
| a bare `x` | **refused** |

`unavailable` and `failed` are different facts and render differently: a dead query is not an empty result.
Neither ever renders as `N/A`, `0`, `-`, or an empty cell.

## Tools (6)

| Tool | Does |
|---|---|
| `docx_write` | Word document from ordered blocks: heading, paragraph, figure, table, keyvalue, image, pagebreak |
| `xlsx_write` | Workbook from sheets of tagged rows, plus `failed_rows` |
| `pptx_write` | Deck from slides: bullets, figure, image |
| `pdf_inspect_form` | List a PDF's **real** named fields — call this before filling |
| `pdf_fill_form` | Fill named fields into a new file; reports `unfilled` and `unmatched` |
| `list_documents` | Find something you generated earlier |

## What the server adds that you cannot omit

- A **Source column** on every table and every spreadsheet row — appended by the writer.
- An **As of** column carrying the *source's* own collection time, distinct from the generation time.
- Generation time and NetClaw attribution in the `.docx` footer on every page, the `.xlsx` banner, and the
  `.pptx` title and Sources slides.
- A **Sources section** in every file, listing each tool with its as-of and whether it was `ok`, `partial`
  or `failed`.
- A **GAIT record** for every call, including refusals.

If any figure lacks a source, the whole call is refused. There is no partial path.

## Three limits, stated up front

**No footnotes in Word.** `python-docx` has no footnote API, so attribution is inline — a Source column in
tables, a small parenthetical after prose figures. That is more visible than a footnote, not less. Word
comments and document properties are set additively but **never** count as provenance: they are collapsed by
default, stripped on paste, and absent in print.

**No Office templates.** `.docx`, `.xlsx` and `.pptx` are built from scratch and a supplied template is
**refused**, not ignored — otherwise you would get an unbranded document believing it was branded. A
corporate template's empty field is the strongest fabrication pressure in the feature. PDF forms are the
exception *because* their fields are explicitly named: there is nothing to guess.

**A filled PDF carries no Sources section.** It is the customer's form and adding a page would alter it. For
that one format provenance lives in the tool response and the GAIT record. Say so when you hand the file
over.

## Put figures in the right block

Prose carries no attribution. A `paragraph` asserting a bare number gets a caveat naming the block index —
use `figure`, `table` or `keyvalue` instead, all of which force a source. Dates, ticket numbers, IPs,
versions and "Section 2" are not flagged.

## Other behaviour worth knowing

- **Admin state and operational state must be separate columns.** A merged `status` column is refused. An
  interface can be administratively up with no carrier, and collapsing them tells a reader traffic is
  passing when nothing is.
- **Sources that disagree are both shown**, with their origins and a caveat. NetClaw does not pick a winner.
- **Untrusted text cannot become a formula.** A description beginning with `=` is written as literal text —
  openpyxl would otherwise turn it into a live formula in an auditor's spreadsheet.
- **Files are never overwritten.** Output is timestamped and exclusively created, so a regenerated report
  cannot replace one already attached to a ticket. Path is reported back.
- **`ok` means complete.** A document with any gap comes back as `written_with_gaps`, and you cannot
  override that.

## Boundaries — which skill owns what

| Want to… | Use |
|---|---|
| Draw a diagram | `drawio-diagram`, `markmap-viz`, `uml-diagram`, `threejs-network-viz`. This **embeds** their output and never redraws it — pass the file they produced plus `src` naming them |
| Read a document into the knowledge base | `rag-mcp` (feature 062). It **reads** these formats; this **writes** them. Same libraries, opposite direction |
| Create or update a change record | `servicenow-change-workflow` owns the CR lifecycle. This renders a document **from** one and never writes a ticket |
| Send the document somewhere | `slack-report-delivery`, `webex-report-delivery`. Writing a file is in scope here; sending it is not |
| Compose a NetClaw-shaped report | `network-report-documents` — the four standard compositions |

## Important rules

1. **Never fill a gap with a guess.** Send `unavailable` or `failed` with a real reason.
2. **Never send a value without `src`.** It will be refused, and it should be.
3. **Call `pdf_inspect_form` before `pdf_fill_form`** so you map data to fields that actually exist.
4. **Report what the response says.** If it came back `written_with_gaps`, tell the operator the document is
   incomplete and which parts. Handing over a gapped document as if it were finished undoes the whole point.
5. **Give the operator the path.** They need to find the file.
