# document-mcp

**Spec 082 / roadmap R18.** NetClaw-authored. FastMCP, stdio, 6 tools, **no credentials**.

Turns a NetClaw finding into a deliverable: a change-record `.docx`, an interface-audit `.xlsx`, an
executive `.pptx`, or an existing PDF form filled from real data.

This server writes files. It touches no device and no ticket, so there is no approval gate here.

## The one rule

> **A document must never fabricate to fill a blank.**

Tool output is ephemeral — read once, in context, by the person who asked. A document is emailed, attached
to a ticket, filed for audit, and read months later by someone who was not there, and it carries the
authority of its formatting. A professional-looking change record with a plausible invented number is a far
more effective way to launder a guess into an official record than any amount of terminal output, because
nobody re-derives a figure that is already in a table in a `.docx`.

So every populated field is a **tagged value** — exactly one of:

```jsonc
{"v": "fgt-01", "src": "fgt_system_status", "device": "fgt-01", "as_of": "2026-08-03T13:58:00Z"}
{"unavailable": "device did not answer within timeout"}
{"failed": "FortiGate plane unreachable: connection refused"}
```

A value with no `src` is refused. A bare scalar is refused. `{"v": ""}` is legal and means *the source was
consulted and genuinely returned empty* — a different fact from `unavailable`, rendered differently.
Nothing ever renders as `N/A`, `0`, `-`, or an empty cell.

## Tools

| Tool | Purpose |
|---|---|
| `docx_write` | Word document from ordered blocks (heading, paragraph, figure, table, keyvalue, image, pagebreak) |
| `xlsx_write` | Workbook from sheets of tagged rows plus `failed_rows` |
| `pptx_write` | Deck from slides (bullets, figure, image) |
| `pdf_inspect_form` | List a PDF's real named fields — call before filling |
| `pdf_fill_form` | Fill named fields into a new file; reports `unfilled` and `unmatched` |
| `list_documents` | Find something generated earlier |

Manifest measured at **1,232 / 5,000 tokens**.

## Install

```bash
./scripts/install.sh                      # select "document"
# or
netclaw_pip_install -r mcp-servers/document-mcp/requirements.txt
```

The four libraries are almost certainly already installed — `rag-mcp` (feature 062) brings them in to
**read** these formats. This server **writes** them. Bounds are identical in both declarations so one shared
install satisfies both; nothing here moves an installed version.

## Environment (all optional)

| Variable | Default |
|---|---|
| `DOCUMENT_MCP_CMD` | command the skills invoke |
| `DOCUMENT_OUTPUT_DIR` | `workspace/output/document-mcp/` |
| `DOCUMENT_MAX_ROWS` | 50000 data rows per worksheet |
| `DOCUMENT_MAX_BLOCKS` | 5000 blocks per Word document |
| `DOCUMENT_MAX_SLIDES` | 200 slides per deck |
| `DOCUMENT_AUDIT_LOG` | `~/.openclaw/gait/document-mcp.jsonl` |

No API keys. Nothing to rotate.

## Layout

```
server.py            FastMCP entrypoint, 6 tools
envelope.py          THE CHOKEPOINT — emit/refused + GAIT. Every response passes through it
outcomes.py          Outcome enum + the tagged-value vocabulary and its rendering
provenance.py        SourceLedger accumulation, DocumentStamp, the Sources model
output.py            O_EXCL timestamped writer — an existing file is never opened for writing
sanitize.py          untrusted text; the openpyxl forced-string mitigation
guards.py            shared refusals: templates, merged status, embedded-image paths, bounds
writers/
  docx_writer.py     inline Source column, per-page footer, Sources section
  xlsx_writer.py     per-row Source column, failed rows, banner, Sources sheet
  pptx_writer.py     visible on-slide source box, Sources slide
  pdf_writer.py      named-field fill, unfilled/unmatched reporting
```

The writer filenames carry a `_writer` suffix for readability and to stay safe if `writers/` is ever
flattened into this directory. They do **not** shadow the third-party packages at this layout — that was
measured (research D14) after an earlier draft claimed otherwise.

## Behaviour worth knowing

- **Provenance is visible, never hidden.** Source column per table row, per-figure parenthetical in prose, a
  visible source box on every slide, a Sources section in every file. Word comments, document metadata and
  speaker notes are written *additively* but never count — they are collapsed by default, stripped on paste,
  and absent in print.
- **`python-docx` has no footnote API** (measured), so `.docx` attribution is inline.
- **openpyxl writes a leading `=` as a live formula.** Measured: `ws["A1"] = "=1+1"` produces
  `<c r="A1"><f>1+1</f>…`. Every string cell is forced to `inlineStr` at one helper, so a device description
  cannot put executing content into an auditor's spreadsheet.
- **Admin and operational state must be separate columns** — a merged `status` column is refused.
- **Failed devices are rows, not omissions.** A banner reports attempted / returned / failed.
- **Sources that disagree are both rendered**, with a caveat. No winner is picked.
- **Office templates are refused, not ignored.** PDF forms are supported precisely because their fields are
  explicitly named and machine-readable.
- **A filled PDF carries no Sources section** — it is the customer's document. Provenance for that one
  format lives in the response and the GAIT record.
- **Files are never overwritten** (`O_EXCL` + collision suffix). An unwritable output directory is a
  reported failure with no temp-directory fallback.
- **`ok` means complete.** Any gap forces `written_with_gaps`, and a caller cannot override it.
- Every call, **including refusals**, is GAIT-audited at the chokepoint.

## Boundaries

| Concern | Owner |
|---|---|
| Drawing diagrams | `drawio-diagram`, `markmap-viz`, `uml-diagram`, `threejs-network-viz` — this **embeds** their output |
| Reading documents | `rag-mcp` (feature 062) — same libraries, opposite direction |
| Change-record lifecycle | `servicenow-change-workflow` — this renders a document from one |
| Sending documents | `slack-report-delivery`, `webex-report-delivery` |

## Tests

```bash
bash tests/document/run-tests.sh    # no network, no credentials
```

240 assertions across seven suites. **They reopen every generated file and assert on what is inside it** —
spec 080 shipped a tool returning three nulls past 24 passing tests because its suites asserted on envelope
shape and never on payload content, and this feature's entire output is content. One suite asserts against
raw worksheet XML, which is the only thing that catches the openpyxl formula conversion.
