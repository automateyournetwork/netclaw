# Phase 0 Research — Document Generation (spec 082 / roadmap R18)

**Date**: 2026-08-03 · **Branch**: `082-document-generation`

Everything below was **measured on this machine**, not inferred from documentation. Where a finding
contradicts an assumption in the spec or the roadmap, the contradiction is stated rather than smoothed over.

---

## D1 — The licence finding (confirms the clarification, changes the roadmap)

**Decision**: Build NetClaw's own capability. No vendored copy, no installer, no runtime fetch.

**Rationale**: The four `anthropics/skills` document skills (`skills/docx`, `skills/pptx`, `skills/xlsx`,
`skills/pdf`) are **source-available and "provided for demonstration and educational purposes only"** — not
Apache-2.0. The repository's *example* skills carry Apache-2.0; the document skills specifically do not.
NetClaw ships Apache-2.0 skills, so vendoring is not licence-compatible.

**Consequence for the roadmap**: R18's checklist item *"Vendor the four official skills"* cannot be
satisfied as written. `docs/COVERAGE-ROADMAP.md` has been corrected in this branch with the finding and the
struck item, so the next reader does not re-litigate it. This makes R18 **build-rather-than-adopt for a
licensing reason** — distinct from R1/R3/R9, where the community options were technically inadequate.

**Alternatives considered**: an opt-in runtime installer that fetches upstream into the operator's own
workspace (keeps demo-only code out of the repo but adds a second code surface and leaves the discipline
unenforceable); seeking relicensing (blocks the feature on an external party). Both rejected in
clarification.

---

## D2 — Dependencies: all four already installed, and the checker cannot see rag-mcp at all

**Measured** on the system interpreter, 2026-08-03:

| Distribution | Import name | Version | Result |
|---|---|---|---|
| `python-docx` | `docx` | **1.2.0** | import OK |
| `openpyxl` | `openpyxl` | **3.1.5** | import OK |
| `python-pptx` | `pptx` | **1.0.2** | import OK |
| `PyMuPDF` | **`fitz`** | **1.28.0** | import OK |

**Decision**: declare upper-bounded pins in `mcp-servers/document-mcp/requirements.txt`, and correct
`mcp-servers/rag-mcp/pyproject.toml` to match. Bounds describe the already-resolved majors; **no installed
version moves**.

### The finding that is worse than the spec assumed

`scripts/check-dependency-pins.py` **reads `requirements.txt` only** (line 57-58,
`_requirements(server_dir)` → `os.path.join(server_dir, "requirements.txt")`). `rag-mcp` has **no
`requirements.txt`** — it declares dependencies in `pyproject.toml`. Measured: `ls requirements.txt` →
*No such file or directory*.

**So rag-mcp has never been scanned by the spec-077 checker.** `python3 scripts/check-dependency-pins.py`
reports `Servers scanned: 63 · PASS`, and rag-mcp is not among the 63 in any meaningful way. The baseline
`reconcile-mcp.py` exits 0 across all four surfaces — a clean bill of health that is clean because the file
is invisible, not because it is correct.

What is actually in there (`pyproject.toml:6-20`), and what each one imports:

| Declared | Bounded? | Code imports | Hazard |
|---|---|---|---|
| `"mcp"` | ❌ none | — | mcp 2.0 exists and removes `mcp.server.fastmcp` |
| `"fastmcp"` | ❌ none | `from fastmcp import FastMCP` (`rag_mcp_server.py:53`) | attribute import, unbounded major |
| `"pymupdf"` | ❌ none | `import fitz` (`ingestion/parsers.py:107`) | **name mismatch** — dist `pymupdf`, module `fitz` |
| `"python-docx"` | ❌ none | `import docx` (`parsers.py:342`) | dist/module mismatch |
| `"openpyxl"` | ❌ none | `import openpyxl` (`parsers.py:382`) | unbounded major |
| `"python-pptx"` | ❌ none | `from pptx import Presentation` (`parsers.py:405`) | dist/module mismatch + attribute import |
| `"vsdx"` | ❌ none | `from vsdx import VisioFile` (`parsers.py:440`) | attribute import |

Two independent gaps, both real:

1. **The checker does not read `pyproject.toml`.** Any server declaring deps that way is unchecked.
2. **The checker matches by distribution name.** `pymupdf`→`fitz`, `python-docx`→`docx`,
   `python-pptx`→`pptx` are all dist/module renames, so even a scanned `pyproject.toml` would not connect
   `"pymupdf"` to `import fitz`.

**Decision**: fix the declaration (FR-032b, in scope) **and** extend the checker to read `pyproject.toml`
with a dist→module alias map (in scope — a correction that closes the hazard permanently rather than
patching one instance of it). `"mcp"` and `"fastmcp"` are bounded at the same time: leaving them unbounded
while bounding the document libraries in the same file would be arbitrary, and `mcp<2` is the bound spec 081
already calls load-bearing.

**Constraint**: FR-032c/SC-018 — the bounds must not move an installed version. Verified targets:
`pymupdf>=1.24,<2` (have 1.28.0), `python-docx>=1.1,<2` (have 1.2.0), `openpyxl>=3.1,<4` (have 3.1.5),
`python-pptx>=1.0,<2` (have 1.0.2), `mcp>=1.2.0,<2`, `fastmcp>=2.0,<3` (bound to what is installed —
confirm at implementation), `vsdx>=0.5,<1` (confirm installed version at implementation).

---

## D3 — python-docx has **no footnote API** (this changes FR-009a's implementation)

**Measured**:

```
docx Paragraph footnote attrs: []
docx Run attrs w/ foot:        []
docx Document attrs: [..., 'add_comment', 'add_heading', 'add_page_break', 'add_paragraph',
                      'add_picture', 'add_section', 'add_table', 'comments', 'core_properties', ...]
```

python-docx 1.2.0 exposes **no** `add_footnote`. It does expose `add_comment` — which is precisely the
hidden mechanism **FR-008a prohibits as the means of satisfying provenance** (comments are collapsed by
default, stripped on paste, absent in print).

**Decision**: in `.docx`, per-element provenance is **inline and visible**:
- **Tables** carry a literal `Source` column — the same shape as the spreadsheet.
- **Prose figures** carry an inline parenthetical immediately after the figure, in a smaller run:
  `12 interfaces (fgt_list_interfaces · fgt-01 · as of 2026-08-03T14:02Z)`.
- Every document ends with a visible **Sources** section.
- The section **footer** carries generation time and NetClaw attribution on every page (measured available:
  `sections[0].footer` exists and is writable).
- `core_properties.comments` and `add_comment` may be set **additively** but never counted as the mechanism.

**Alternative rejected**: hand-building `w:footnote` XML through `python-docx`'s `element` escape hatch.
Real footnotes would be nicer typographically, but hand-rolled OOXML is a corruption risk in an artefact
whose whole purpose is to be opened by someone else, and inline attribution is *more* visible, not less.

---

## D4 — pptx speaker notes are hidden too

**Measured**: `slide.notes_slide.notes_text_frame` works and `has_notes_slide` is True. But speaker notes
are not visible in presentation mode and not in a default print or PDF export — the same class of mechanism
as a cell comment.

**Decision**: decks carry a **visible source line on the slide itself** (a small text box along the bottom)
for any slide asserting a figure, plus a final **Sources slide**. Notes may additionally carry the detail.
This satisfies FR-008a and SC-010b's forwarding test.

---

## D5 — openpyxl writes a leading `=` as a **live formula** (FR-026 is not theoretical)

**Measured**, writing the string `=1+1` into cells and reading back `xl/worksheets/sheet1.xml`:

| Cell | How written | `data_type` on read | Raw XML |
|---|---|---|---|
| A1 | `ws["A1"] = "=1+1"` | `'f'` | `<c r="A1"><f>1+1</f><v></v></c>` |
| A2 | assign, then `cell.data_type = 's'` | `'s'` | `<c r="A2" t="inlineStr"><is><t>=1+1</t></is></c>` |

**A naive write turns untrusted text into an executing formula.** A FortiGate interface description, a
ServiceNow short-description, or a hostname beginning with `=` is enough. This is the concrete form of the
threat FR-026 names.

Also measured: `@SUM(1,1)`, `+1+1` and `-1+1` are **not** converted by openpyxl — they stay `inlineStr`. The
leading `=` is the only conversion openpyxl performs.

**Decision**: every untrusted string written to a worksheet is forced to `data_type = 's'` **after
assignment**, at the single write helper. Not a per-caller responsibility, not a prefix hack (prefixing with
`'` would visibly corrupt the value in a document whose whole point is fidelity). Applied uniformly rather
than only to `=`, because "which prefixes Excel treats as formulas" varies by locale and by paste path,
whereas `t="inlineStr"` is unambiguous in the file itself.

---

## D6 — PDF form filling works end to end (US4 is viable)

**Measured** with PyMuPDF 1.28.0, building a three-field form and filling one field:

```
is_form_pdf: 3                     # truthy int for a form
discovered fields: [('change_number','Text',"''"), ('device_hostname','Text',"''"), ('approver','Text',"''")]
filled: ['change_number']  unfilled: ['device_hostname','approver']  unmatched: ['nonexistent_field']
readback: [('change_number',"'CHG0012345'"), ('device_hostname',"''"), ('approver',"''")]
plain.pdf is_form_pdf: False  widgets: []
```

Every requirement of US4 is demonstrably supported:

| Requirement | Mechanism | Measured |
|---|---|---|
| FR-024 non-fillable detected | `doc.is_form_pdf` | `False` + zero widgets on a plain PDF ✅ |
| FR-024a named fields only | `widget.field_name` from `page.widgets()` | ✅ |
| FR-024b unfilled reported | field names with no data | ✅ |
| FR-024b unmatched reported | data keys ∉ discovered field names | ✅ |
| Round-trip fidelity | reopen and read `field_value` | ✅ |

Note `is_form_pdf` returns an **int** (3), not a bool — compare truthily, never with `is True`.

Fixture generation is also solved: `fitz.Widget()` + `page.add_widget()` builds a fillable PDF, so the test
suite can create its own form rather than depending on a customer artefact.

---

## D7 — Output convention: follow feature 046, and fix its one weakness

**Feature 046's implementation** (`workspace/skills/threejs-network-viz/output.py`, the whole convention in
33 lines):

```python
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "threejs-network-viz"
timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in snapshot_id)
path = OUTPUT_DIR / f"topology-{timestamp}-{safe_id}.html"
path.write_text(html, encoding="utf-8")
```

`.gitignore:108-110` ignores `workspace/output/` wholesale, so a new subdirectory needs **no .gitignore
change**.

**Decision**: same directory shape (`workspace/output/document-mcp/`), same UTC `%Y%m%dT%H%M%SZ` stamp, same
sanitiser — **plus an exclusive create**. FR-018 says a file MUST NEVER be overwritten; 046 relies on
timestamp uniqueness alone, which collides for two documents generated in the same second. The writer uses
`os.open(path, O_CREAT | O_EXCL | O_WRONLY)` and, on `FileExistsError`, appends `-2`, `-3`, … rather than
replacing. Small, and it is the difference between "unlikely to overwrite" and "cannot".

**Path resolution**: 046 resolves relative to `__file__`, which works from any cwd. `document-mcp` lives in
`mcp-servers/document-mcp/`, not `workspace/skills/`, so the repo root is `parents[2]` from the server
directory — computed the same way, with `DOCUMENT_OUTPUT_DIR` as an override for operators who want
documents elsewhere.

---

## D8 — The typed-value contract (how FR-005c becomes enforceable)

The chokepoint only works if a caller **cannot express a missing value as an empty string**. Over MCP
everything is JSON, so the enforcement has to be in the accepted shape.

**Decision**: every populated field is a **tagged value**, exactly one of three shapes:

```jsonc
{"v": <any>, "src": "fgt_list_interfaces", "device": "fgt-01", "as_of": "2026-08-03T14:02Z"}
{"unavailable": "device did not answer within timeout"}
{"failed": "FortiGate plane unreachable: connection refused"}
```

- `v` **without** `src` → `ProvenanceError`, refused. Not defaulted, not silently stamped.
- A bare scalar where a tagged value is expected → refused with a message naming the field.
- `{"v": ""}` is legal and means *the source genuinely returned empty* — which is a different fact from
  `unavailable`, and renders differently.
- `unavailable` and `failed` are separate tags, because FR-002 says a dead query and an empty result are
  different facts.

This is the mechanism for FR-001 through FR-005c: the shape makes the honest thing the only expressible
thing. It follows spec 080's `Outcome` enum and spec 081's `RpkiState`/`WIRE_TO_STATE` precedent — typed
vocabulary at the boundary, not prose in a skill.

**Alternative rejected**: accepting plain values and letting the server infer missing-ness from `null`. That
puts the distinction in the caller's hands, which is what FR-005d exists to prevent.

---

## D9 — Server shape and tool surface

**Decision**: one server, `mcp-servers/document-mcp/`, modelled on `bgp-intel-mcp` (spec 081 — newest, and
the one that factored `Outcome` out of `envelope.py`, which is the better split).

```
mcp-servers/document-mcp/
  server.py          FastMCP entrypoint, stdio, the tool defs
  envelope.py        the chokepoint: emit/refused, GAIT audit  (FR-005b, FR-034)
  outcomes.py        typed Outcome + the tagged-value vocabulary (FR-005c, D8)
  provenance.py      source records, as-of handling, the Sources section model (FR-006..FR-010)
  output.py          exclusive-create timestamped writer               (FR-016..FR-020, D7)
  sanitize.py        untrusted-text handling, incl. the openpyxl forced-string (FR-026, D5)
  writers/docx_writer.py  inline source column + footer + Sources section  (D3)
  writers/xlsx_writer.py  per-row source column + Sources sheet            (D5)
  writers/pptx_writer.py  visible per-slide source line + Sources slide    (D4)
  writers/pdf_writer.py   named-field fill, unfilled/unmatched reporting   (D6)
  requirements.txt   bounded pins
  README.md          step-5 artifact
```

**Six tools**, keeping the surface small so the 5,000-token ceiling (FR-038a) is comfortable and so
composition stays in the skills (FR-005d):

| Tool | Purpose |
|---|---|
| `docx_write` | Build a Word document from a typed block list |
| `xlsx_write` | Build a workbook from typed sheets and rows |
| `pptx_write` | Build a deck from typed slides |
| `pdf_inspect_form` | List a PDF's named fields; report whether it is fillable at all |
| `pdf_fill_form` | Fill named fields; report unfilled fields and unmatched data |
| `list_documents` | List what has been generated, so the operator can find a file |

`pdf_inspect_form` is separate from `pdf_fill_form` deliberately: an operator (or a model) that must
enumerate real field names before mapping data cannot invent them.

**Alternative rejected**: one tool per user story (`generate_change_record`, …). That would put composition
in the server and make the tool schemas carry NetClaw domain knowledge that belongs in skills, violating
FR-005d in the other direction.

---

## D10 — Skills: two, not four

**Decision**:

| Skill | Owns |
|---|---|
| `document-generation` | The tool surface, the no-fabrication discipline, the output convention, per-format capabilities **and limits** (no footnotes, no Office templates) |
| `network-report-documents` | The four NetClaw compositions — change record, interface/config audit workbook, executive summary deck, PDF form fill — each naming the upstream skills that feed it |

**Rationale**: the roadmap asked for wrapper skills per document type; four skills would each be thin and
would repeat the same discipline four times, which is how a discipline gets diluted. Splitting
*capability* from *composition* mirrors the server/skill split FR-005d already requires, and matches spec
081's precedent (one skill, 10 tools, workflows as sections) rather than spec 080's (three skills for three
genuinely separate credentialed planes — not the situation here).

**Counts**: skills 207 → **209**; MCP integrations 154 → **155**.

**Frontmatter**: copy `workspace/skills/bgp-registry-intel/SKILL.md` exactly — `name`, quoted single-line
`description` ending in a "Use when …" clause, `version`, `license: Apache-2.0`, `tags`,
`user-invocable: true`, and the inline-JSON `metadata.openclaw.requires` block. Do **not** copy
`threejs-network-viz/SKILL.md`, which predates the schema and has no frontmatter.

---

## D11 — iN2N: Border-only, and why

**Decision**: this capability is **not** given to an iN2N member. FR-039's five-artifact obligation is
therefore not triggered.

**Rationale**: members are credentialed specialists (`fortimanager`, `fortigate`, …) whose value is holding
one domain's credentials. Document generation holds no credentials and composes across domains — that is
Border work by construction. Giving it to a member would mean the member composing data it cannot reach.

**Recorded so it is a decision and not an omission**: a member producing a workbook scoped to its *own*
domain is a coherent follow-on, and if it is ever done, `docs/ADDING-AN-MCP.md`'s five artifacts plus
`systemctl --user restart netclaw-mesh.service` apply in full.

---

## D12 — Testing convention

**Decision**: `tests/document/` with `run-tests.sh`, following `tests/bgp-intel/` — plain Python, stdlib
only, no pytest, `sys.path.insert` to reach the server modules, module-level `FAILURES`, a
`check(name, condition, detail)` helper, `main()` returning 0/1, `raise SystemExit(main())`.

**And the lesson from spec 080, applied structurally**: that feature shipped `fgt_system_status` returning
three nulls past **24 passing tests**, because the tests asserted on envelope *shape* and never on payload
*content*. This feature's whole output is content.

So the suites here **open the generated file and assert on what is inside it** — not that a write succeeded:

| Suite | Asserts |
|---|---|
| `test_tagged_values.py` | `v` without `src` is refused; `unavailable` ≠ `failed` ≠ `{"v":""}` |
| `test_provenance.py` | Every writer's output, **reparsed**, contains generation time, attribution, per-element source, Sources section |
| `test_no_fabrication.py` | A missing field renders as explicit text; a failed row is present and marked; row counts reflect attempts |
| `test_sanitize.py` | `=1+1` written to xlsx reads back `data_type == 's'` and the raw XML has **no `<f>`** |
| `test_pdf_forms.py` | Round-trip fill; non-fillable rejected; unfilled and unmatched both reported |
| `test_output_paths.py` | Two writes in the same second produce two files; the first is byte-identical afterwards |
| `test_manifest_size.py` | ≤ 5,000 tokens, plus a read-only surface guard |

Raw-XML assertion is the technique that catches D5, exactly as spec 081 used a rendered-text assertion to
catch "the word 'invalid' must not appear in a not-found result".

---

## D13 — Pre-existing README drift found while surveying (adjacent, in scope to fix)

`README.md` was **never updated for specs 080 or 081**. The numbered MCP table ends at row 118 (Globalping,
line 630); there is no row for Fortinet or BGP-intel, and `grep` finds no `bgp-registry-intel`,
`fortigate-ops` or `fortianalyzer-ops` skill rows. SOUL.md and TOOLS.md *were* updated.

`verify-inventory-counts.py` does not catch this: it checks headline arithmetic at six claim sites, not
table membership. The counts pass because the count of `workspace/skills/*/SKILL.md` directories is what it
compares against.

**Decision**: fix it in this branch. It is two table rows and three skill rows, it is Principle XI, and this
feature has to edit those exact tables anyway. Doing it here costs minutes; leaving it means the next
feature inherits a README two specs behind.

---

## Summary of measured facts that changed the design

| # | Finding | Design consequence |
|---|---|---|
| D2 | `check-dependency-pins.py` reads only `requirements.txt`; rag-mcp has none | rag-mcp never scanned — fix the declaration **and** the checker |
| D2 | Checker matches dist names; `pymupdf`→`fitz` etc. are renames | checker needs a dist→module alias map |
| D3 | python-docx 1.2.0 has **no footnote API** | provenance in docx is inline + Sources section, never `add_comment` |
| D4 | pptx speaker notes are not visible in presentation or print | visible on-slide source line + Sources slide |
| D5 | openpyxl writes leading `=` as `<f>` — a live formula | force `data_type='s'` at the single write helper |
| D6 | PyMuPDF form fill round-trips; `is_form_pdf` returns int | US4 viable; compare truthily, never `is True` |
| D7 | Feature 046 relies on timestamp uniqueness alone | add `O_EXCL` create so FR-018 is guaranteed, not likely |
| D13 | README is two specs behind on table membership | fix in this branch |
| D14 | `writers/pptx.py` would **not** actually shadow `pptx` (measured) | keep `_writer` names for clarity, not for a shadowing reason that does not exist |

---

## D14 — The `_writer` suffix, and a claim that had to be withdrawn

`/speckit.analyze` challenged the naming rationale, so it was measured rather than argued.

**Claim under test**: that `writers/pptx.py` would shadow the third-party `pptx` package on the import path
`server.py` inserts.

**Measured**: it does not. With `sys.path.insert(0, <server dir>)` and a module at `writers/pptx.py`,
`from pptx import Presentation` inside it resolves to the **third-party package** and works — Python 3's
absolute-import default means a submodule does not shadow a top-level package of the same name.

```
--- case A: writers/pptx.py inside a package ---
  writers/pptx.py imported Presentation OK: <function Presentation at 0x...>
--- case B: pptx.py at the top level of the inserted dir ---
  ImportError: cannot import name 'Presentation' from 'pptx'
  (consider renaming '.../pptx.py' if it has the same name as a library you intended to import)
```

Shadowing is real **only** for a module at the top level of the inserted directory (case B).

**Decision unchanged, rationale corrected**: keep `docx_writer.py` / `xlsx_writer.py` / `pptx_writer.py` /
`pdf_writer.py`. They are clearer at a call site (`xlsx_writer.build(...)` reads better than
`xlsx.build(...)`), and they stay safe if anyone later flattens `writers/` into the server directory, which
*would* trigger case B. But the plan originally justified them with a hazard that does not exist at this
layout, and shipping a false technical claim in a design document is worse than the naming question it was
defending.
