# Quickstart — Document Generation (spec 082 / roadmap R18)

Turn a NetClaw finding into something you can attach to a change record or hand to a director.

---

## Install

```bash
./scripts/install.sh          # select "document" in the component checklist
# or, if NetClaw is already installed:
netclaw_pip_install -r mcp-servers/document-mcp/requirements.txt
```

**No credentials.** The server writes files and touches nothing else.

The four libraries are almost certainly already present — `rag-mcp` (feature 062) installs them to *read*
these formats. Verify:

```bash
python3 -c "import docx, openpyxl, pptx, fitz; print(docx.__version__, openpyxl.__version__, pptx.__version__, fitz.__doc__)"
```

## Environment (all optional)

```bash
DOCUMENT_MCP_CMD=            # command the skills invoke
DOCUMENT_OUTPUT_DIR=         # default: workspace/output/document-mcp/
DOCUMENT_MAX_ROWS=           # default: 50000 data rows per sheet
DOCUMENT_AUDIT_LOG=          # default: ~/.openclaw/gait/document-mcp.jsonl
```

## Where files land

```
workspace/output/document-mcp/changerecord-20260803T140200Z-chg0012345.docx
```

Timestamped UTC, uniquely named, **never overwritten** — a regenerated report cannot silently replace the
one already attached to a ticket. The directory is gitignored (`.gitignore:110`, feature 046's convention).

---

## Four things to try

### 1. A change record an approver will accept

> "Generate a change record document for CHG0012345 with the current state of fgt-01."

NetClaw pulls the CR from `servicenow-change-workflow`, the device state from `fortigate-ops`, and writes a
`.docx` where every field names its source. A device that did not answer says so — it does not appear as a
blank.

### 2. An interface audit workbook

> "Build an interface audit spreadsheet for all my FortiGates."

Every interface, one row each, with **administrative and operational state in separate columns** and a
`Source` column per row. A device that failed appears as a marked failed row — the sheet never gets shorter
because a device was unreachable.

### 3. An executive summary deck

> "Make an exec deck from the posture review, with the topology diagram."

Findings on slides, sources visible on the slide itself (not hidden in speaker notes), the diagram embedded
from `threejs-network-viz` or `drawio-diagram`, and a Sources slide at the end.

### 4. Fill a PDF form

> "What fields does audit-response.pdf have?" → then → "Fill it from the CR and the device state."

`pdf_inspect_form` lists the real field names first, so nothing is mapped to a field that does not exist.
The fill reports which fields it left empty and which of your values matched no field.

---

## The one rule that matters most

> ### A document must never fabricate to fill a blank.

Tool output is ephemeral — read once, in context, by the person who asked. **A document is not.** It gets
emailed, filed, and read months later by someone who was not there, and it carries the authority of its
formatting. A professional-looking change record with a plausible invented number is a far more effective
way to launder a guess into an official record than any amount of terminal output, because nobody
re-derives a figure that is already in a table in a `.docx`.

So the server refuses rather than guesses:

| You send | You get |
|---|---|
| A value with no source | **Refused.** An unattributed figure is not renderable. |
| A bare scalar where a value belongs | **Refused.** It would let missing data render as a blank. |
| `{"unavailable": "device did not answer"}` | `NOT AVAILABLE — device did not answer`, in the document |
| `{"failed": "connection refused"}` | `RETRIEVAL FAILED — connection refused`, in the document |
| `{"v": ""}` | `(empty)` — the source *was* consulted and returned nothing. A different fact. |

`unavailable` and `failed` never render as an empty cell, `N/A`, `0`, or a dash.

---

## Three limits, stated up front

**No footnotes in Word.** python-docx has no footnote API, so per-figure attribution is inline — a `Source`
column in tables, a parenthetical after prose figures. This is more visible, not less; a footnote is easy to
skip.

**No Office templates.** `.docx`, `.xlsx` and `.pptx` are built from scratch. A corporate template's empty
field is the strongest fabrication pressure in the whole feature, and placeholder-matching in Word is the
guessing version of the problem. Supplying one is refused, not silently ignored. PDF forms are the exception
*because* their fields are explicitly named — there is nothing to guess.

**A filled PDF cannot carry a Sources section.** It is the customer's form; adding a page would alter it. For
that one format the provenance lives in the response and the GAIT record. Every other format carries it
inside the file.

---

## Boundaries

| Want to… | Use |
|---|---|
| Draw a diagram | `drawio-diagram`, `markmap-viz`, `uml-diagram`, `threejs-network-viz` — this **embeds** their output |
| Read a document into the knowledge base | `rag-mcp` (feature 062) — same libraries, opposite direction |
| Create or update a change record | `servicenow-change-workflow` — this renders a document *from* one |
| Send the document somewhere | `slack-report-delivery`, `webex-report-delivery` — writing a file is in scope, sending it is not |

---

## Verify

```bash
bash tests/document/run-tests.sh          # no network, no credentials
python3 scripts/reconcile-mcp.py          # must exit 0
```

The tests **open every generated file and assert on what is inside it.** Spec 080 shipped a tool returning
three nulls past 24 passing tests because its suites asserted on envelope shape and never on payload
content. This feature's entire output *is* content, so a write that succeeded proves nothing on its own.
