# Feature Specification: Document Generation (docx / pptx / xlsx / pdf)

**Feature Branch**: `082-document-generation`
**Created**: 2026-08-03
**Status**: Draft
**Roadmap**: R18 — *"Best effort-to-value ratio on the roadmap"*

## Overview

NetClaw can render Three.js topologies, drawio diagrams, markmap mind maps, UML via Kroki, Blender scenes
and UE5 walkthroughs. It cannot produce a change-record `.docx`, an executive `.pptx`, an interface-audit
`.xlsx`, or fill a PDF form.

**Its output lands in front of enterprise humans** — change advisory boards, auditors, directors. Those
people work in Office documents. Every other NetClaw capability produces *findings*; this is what turns a
finding into something you can attach to a change record or hand to someone who will never open a terminal.

That is the deliverable gap, and it is why the roadmap rates this the best effort-to-value item on the list.

## The distinction this feature exists to protect

### A document must never fabricate to fill a blank

This is the largest risk in the feature by a wide margin, and it is a *new* risk rather than a variation of
the previous four.

Specs 078, 079, 080 and 081 each protected a distinction in **tool output** — "no advisories ≠ not
vulnerable", "no probes ≠ outage", "no logs ≠ rule unused", "not-found ≠ invalid". Tool output is ephemeral:
it is read once, in context, by someone who just asked the question.

**A document is none of those things.** It gets emailed, attached to a ticket, filed for audit, and read
months later by someone who was not there. It carries the authority of its formatting. A professional-looking
change record with a plausible-but-invented device count is a far more effective way to launder a guess into
an official record than any amount of terminal output — because nobody re-derives a number that is already
in a table in a `.docx`.

Three consequences:

1. **An empty field renders as explicitly empty or absent — never as a plausible placeholder.** If a device
   did not answer, the document says the device did not answer. Not `N/A`, not a sensible-looking default,
   not silence.
2. **Every figure carries where it came from.** A number in a spreadsheet cell with no provenance is *worse*
   than no spreadsheet: it looks authoritative and cannot be checked. This is the provenance discipline of
   spec 081 applied to a format that outlives the session.
3. **A document states when it was generated and by what.** Read six months later, "as of" is the
   difference between a record and a misleading artefact.

### Generation is not the engineering; composition is

`python-docx` writes Word files. That is a solved problem and not what this feature is for.

The value is that a change record is populated from **an actual ServiceNow CR plus real device state**, and
an interface audit from **an actual `fgt_list_interfaces` or `multivendor-device-query` result** — not typed
by hand. The composition with NetClaw's existing 200-plus skills is the feature; the library
call is an implementation detail.

## The licence constraint — this changes the roadmap's plan

The roadmap says: *"Vendor the four official skills; note their license terms explicitly."*

**Noting the terms explicitly is the finding.** Measured 2026-08-03: the four document skills in
`anthropics/skills` (`skills/docx`, `skills/pptx`, `skills/xlsx`, `skills/pdf`) are **source-available, not
open source**, and are described as *"provided for demonstration and educational purposes only."* The
repository's *example* skills are Apache-2.0; the document skills specifically are not.

NetClaw ships Apache-2.0 skills. **Vendoring demonstration-only source into it is not licence-compatible**,
so the roadmap's checklist item cannot be satisfied as literally written.

This makes R18 a build-rather-than-adopt feature — but for a **licensing** reason, not a quality one, which
is a different situation from R1, R3 and R9 where the community options were technically inadequate. The
official skills remain valuable as **reference for what capabilities matter** (the `docx` skill's tracked
changes and find-and-replace, `pdf`'s form filling and merge/split, `pptx`'s template-vs-scratch modes), and
reading them to decide *what* to build is entirely legitimate.

## The dependencies are already here

Measured on the system interpreter, 2026-08-03:

| Library | Installed | Needed for |
|---|---|---|
| `python-docx` | **1.2.0** ✅ | `.docx` |
| `openpyxl` | **3.1.5** ✅ | `.xlsx` |
| `python-pptx` | **1.0.2** ✅ | `.pptx` |
| `PyMuPDF` (`fitz`) | **1.28.0** ✅ | `.pdf` |

All four arrive with **feature 062's `rag-mcp`**, which *reads* these formats for ingestion. This feature
*writes* them — same libraries, opposite direction.

**But rag-mcp declares them unpinned** (`"pymupdf"`, `"python-docx"`, `"openpyxl"`, `"python-pptx"` in its
`pyproject.toml`). That is a latent spec-077 hazard in existing code: a fresh installer resolves whatever
major is current, and PyMuPDF is imported as `fitz` — exactly the submodule case spec 077 requires bounding.

Decided in clarification: **this feature declares upper-bounded pins and corrects rag-mcp's declaration to
match**, bounded to the majors already installed. No installed version moves; the bounds describe what is
already resolved. Leaving two servers with conflicting requirements for one shared install is not an
acceptable end state, and this feature is the first to notice the hazard.

## Clarifications

### Session 2026-08-03

- Q: Given the upstream document skills are source-available/demonstration-only rather than Apache-2.0, what licence approach should this feature take? → A: Build NetClaw's own document skills outright. Upstream is cited as reference for capability selection only — never vendored, and no install machinery for it. One code surface, Apache-2.0 clean.
- Q: What shape should the capability ship as — skills, one MCP server, or four? → A: One MCP server plus skills on top. The server owns file writing and stamps generation time, attribution and per-element provenance at a single chokepoint, with unavailable/failed as typed states it cannot skip; skills own the four compositions.
- Q: How must provenance actually render, given a spreadsheet cell has no room for a citation? → A: Visible per-element attribution plus a sources section. Spreadsheets get a source column per row; documents and decks get an inline or footnoted source per figure; every file also carries a sources section with as-of times. Hidden mechanisms (cell comments, document metadata) do not satisfy the requirement.
- Q: Are templates supported, given a template's empty field is the strongest fabrication pressure in the feature? → A: Scratch-only for docx/xlsx/pptx. PDF form filling stays, because a PDF form's fields are explicitly named and machine-readable — the safe form of template population. Corporate-template support for Word/PowerPoint is deferred to a follow-on feature with its own fabrication analysis.
- Q: How should the four document libraries be pinned, given rag-mcp declares them unpinned? → A: Declare upper-bounded pins here **and** fix rag-mcp's declaration to match, pinned to the currently-installed majors. No installed version moves. This closes a pre-existing spec-077 hazard rather than leaving two servers declaring conflicting requirements for one shared install.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A change record an approver will actually accept (Priority: P1)

An operator has an approved ServiceNow CR and real pre-change device state. They need a `.docx` to attach to
the change record and put in front of a change advisory board.

**Why this priority**: It is the single most requested enterprise artefact, it exercises the composition that
justifies the feature, and it is where fabrication would do the most damage — a change record is a governance
document.

**Independent Test**: generate a change record from a real CR number and a real device query; open the
resulting file and confirm every populated field traces to a named source and every unavailable field is
explicitly marked unavailable.

**Acceptance Scenarios**:

1. **Given** an approved CR and reachable devices, **When** a change record is generated, **Then** the
   document contains the CR details, the pre-change state, and **a named source for each**.
2. **Given** a device that did not answer, **When** the document is generated, **Then** the affected section
   says the device did not answer — and MUST NOT show a blank cell, a zero, or a plausible default that
   reads as real data.
3. **Given** any generated document, **When** it is opened, **Then** it states when it was generated and
   that NetClaw generated it.
4. **Given** a CR that does not exist or is not approved, **When** generation is requested, **Then** NetClaw
   reports that rather than producing a document with an invented CR.
5. **Given** a document is generated twice, **When** the second run completes, **Then** the first file still
   exists unmodified.

---

### User Story 2 — An interface audit in a spreadsheet (Priority: P1)

An auditor wants every interface across a set of devices in `.xlsx`: name, addressing, administrative state,
operational state, role, errors.

**Why this priority**: The highest-volume real use, and independently valuable with nothing else built.
Spreadsheets are also where unprovenanced numbers do the most quiet damage, because a cell has no room for
a caveat unless the design makes room.

**Independent Test**: generate an audit from a real device query; confirm row count matches the source, every
column has a stated origin, and a device that failed appears as a failed row rather than being omitted.

**Acceptance Scenarios**:

1. **Given** a real device query, **When** an audit is generated, **Then** every interface appears with its
   fields, and the sheet records which tool and which device produced each row.
2. **Given** a device that failed, **When** the audit is generated, **Then** it appears as an explicitly
   failed entry. **Silently omitting it is prohibited** — a shorter spreadsheet reads as a smaller estate.
3. **Given** administrative and operational state differ, **When** rendered, **Then** they occupy **separate
   columns** and are not merged into one "status".
4. **Given** a generated workbook, **When** opened, **Then** it carries generation time and source
   attribution somewhere durable, not only in a filename.

---

### User Story 3 — An executive summary deck (Priority: P2)

A director wants a short `.pptx`: what was found, what it means, what happens next — with a topology diagram.

**Why this priority**: Real demand and the natural composition with the existing diagram skills, but the
audience tolerates less detail and the fabrication risk is lower because slides are read as summary.

**Independent Test**: generate a deck from real findings, confirm it opens, and confirm any embedded diagram
came from an existing diagram skill rather than being redrawn here.

**Acceptance Scenarios**:

1. **Given** findings from a NetClaw investigation, **When** a deck is generated, **Then** slides carry the
   findings with sources on the detail slides.
2. **Given** a diagram is wanted, **When** the deck is built, **Then** it embeds output from an existing
   diagram skill and does **not** reimplement diagram rendering.
3. **Given** a summary claim on a slide, **When** it is rendered, **Then** it is traceable to a detail slide
   or an appendix rather than asserted bare.

---

### User Story 4 — Fill an existing PDF form (Priority: P3)

Some organisations require a specific PDF form for a change or an audit response. The operator wants it
filled from real data rather than by hand.

**Why this priority**: Genuinely useful and clearly bounded, but the least common and the most dependent on a
specific customer artefact. Most likely of the four to be cut if PDF form handling proves unreliable.

**Independent Test**: fill a real PDF form with known values, open it, and confirm the values landed in the
right fields and unfilled fields were left genuinely unfilled.

**Acceptance Scenarios**:

1. **Given** a fillable PDF and real data, **When** it is filled, **Then** the values appear in the correct
   named fields.
2. **Given** a field with no corresponding data, **When** the form is filled, **Then** it is left empty —
   **never** populated with a guess to make the form look complete.
3. **Given** a PDF that is not fillable, **When** filling is attempted, **Then** NetClaw says so rather than
   producing a visually-similar but non-functional file.

---

### Edge Cases

- **The source data is partially missing.** The document renders what exists and states what does not.
  Partial data with the gaps marked is useful; partial data silently presented as complete is dangerous.
- **A source disagrees with another.** Both are shown with their origins rather than reconciled silently.
- **The output directory does not exist or is not writable.** Reported as a failure; no silent fallback to a
  temp directory the operator will never find.
- **A filename would collide.** The existing file is never overwritten — a regenerated report must not
  silently replace one already attached to a ticket.
- **A very large dataset** — thousands of interfaces. Bounded with the bound stated in the document itself,
  not just in tool output the reader never sees.
- **Untrusted content in source data.** Device banners, ticket descriptions and hostnames can contain
  formula-like or markup-like text; it must not be interpreted as a spreadsheet formula or document markup.
- **A `.docx`/`.pptx`/`.xlsx` template is supplied.** Rejected with a clear reason — out of scope by
  clarification, not silently ignored and not partially honoured.
- **A PDF form has fields the data does not cover.** Those fields are left genuinely empty; the response
  states which named fields went unfilled so the operator knows what to complete by hand.
- **A PDF form has data with no matching field.** Reported as unmatched rather than dropped silently — data
  that vanished is indistinguishable from data that was never supplied.

## Requirements *(mandatory)*

### Functional Requirements

#### Never fabricate — the core

- **FR-001**: A field with no source data MUST render as **explicitly unavailable or absent**. Plausible
  placeholders, invented defaults, and silent blanks are all prohibited.
- **FR-002**: A source that failed MUST be represented **in the document** as having failed, distinct from
  having returned nothing. A dead query and an empty result are different facts.
- **FR-003**: A record that failed to retrieve MUST NOT be silently omitted from a list, table or sheet. A
  shorter table reads as a smaller estate, which is a false statement about the network.
- **FR-004**: NetClaw MUST NOT infer, estimate, or interpolate a value to complete a document. If a figure
  is unknown, the document says it is unknown.
- **FR-005**: Where a document summarises (an executive slide, a total row), the summary MUST be traceable to
  the underlying detail within the same document.

#### One chokepoint, so omission is structurally impossible

- **FR-005a**: A **single MCP server** MUST own all document writing. No skill, script, or other server may
  write a document by any other path.
- **FR-005b**: That server MUST stamp generation time, NetClaw attribution, and per-element provenance at
  **one chokepoint** every document passes through — the envelope pattern specs 080 and 081 used to make
  attribution impossible to omit. Provenance MUST NOT be a per-call caller responsibility.
- **FR-005c**: "Unavailable" and "failed" MUST be **typed states in the server's own vocabulary**, distinct
  from each other and from a present value. A caller MUST NOT be able to express a missing value as a plain
  empty string that renders as a blank cell.
- **FR-005d**: Skills MUST own the compositions (change record, audit, deck, form fill) and MUST NOT contain
  document-writing logic of their own. Prose guidance in a skill is not an acceptable enforcement mechanism
  for FR-001 through FR-004.

#### Provenance that outlives the session

- **FR-006**: Every generated document MUST state, in the document itself, **when it was generated** and
  **that NetClaw generated it**.
- **FR-007**: Every figure, table and populated field MUST carry the **source** that produced it — the tool
  or system, and the device or record where applicable.
- **FR-008**: Provenance MUST be durable in the document body, not only in the filename or the tool response.
  A file that is renamed, forwarded or printed must still carry it.
- **FR-008a**: Provenance MUST be **visible without interaction**. Cell comments, tooltips, document metadata
  properties, and any other hidden mechanism MUST NOT be the means of satisfying FR-007 or FR-008 — they are
  hidden by default, stripped on copy-paste, and absent in print, which are the exact scenarios these
  requirements exist for. Such mechanisms MAY be added *in addition*, never *instead*.
- **FR-009**: Where a document mixes sources, **per-element** attribution is required. One collective
  citation for a mixed table is not attribution.
- **FR-009a**: Concretely: a spreadsheet MUST carry a **visible source column per row**; a document or deck
  MUST carry a **visible source per figure** — inline, since python-docx exposes no footnote API (research
  D3), so "footnoted" is not an available option for `.docx`; and **every** generated file MUST carry a
  **sources section** listing each tool and system consulted with its as-of time. The sources section is
  required in addition to per-element attribution, never as a substitute for it.
- **FR-010**: Source data as-of times MUST be preserved where the source provides one, distinct from the
  document's own generation time. Data collected on Monday and rendered on Friday is a Monday fact.

#### Composition with real NetClaw data

- **FR-011**: A change record MUST be populatable from a real change-management record plus real device
  state, without hand-typed content.
- **FR-012**: An interface or configuration audit MUST be populatable from real device-query output.
- **FR-013**: An executive summary MUST be populatable from findings produced by other NetClaw skills.
- **FR-014**: Where a document should contain a diagram, it MUST embed output from an existing NetClaw
  diagram capability and MUST NOT reimplement diagram rendering.
- **FR-015**: Administrative and operational state, where both exist, MUST occupy separate columns or fields
  and MUST NOT be merged into a single "status" — the distinction spec 080's completion established.

#### Output convention

- **FR-016**: Documents MUST be written to a **persistent** workspace output directory the operator can find
  — never a temporary directory.
- **FR-017**: Filenames MUST be timestamped and uniquely named.
- **FR-018**: An existing file MUST NEVER be overwritten. A regenerated report must not replace one already
  attached to a ticket.
- **FR-019**: The path of the written file MUST be reported back so the operator can retrieve it.
- **FR-020**: A directory that is missing or unwritable MUST be reported as a failure, with no silent
  fallback.

#### Format support

- **FR-021**: `.docx` generation MUST be supported.
- **FR-022**: `.xlsx` generation MUST be supported.
- **FR-023**: `.pptx` generation MUST be supported.
- **FR-023a**: `.docx`, `.xlsx` and `.pptx` MUST be built **from scratch**. Template population for these
  three formats is out of scope; a supplied Office template MUST be **rejected with a clear reason**, never
  silently ignored and never partially honoured.
- **FR-024**: PDF form filling MUST be supported, and a non-fillable PDF MUST be reported as such rather
  than producing a visually-similar non-functional file.
- **FR-024a**: PDF filling MUST operate on **explicitly named form fields**. Positional or visual placement
  of text onto a PDF that has no named fields MUST NOT be used as a substitute — it produces a document that
  looks filled but carries no field data.
- **FR-024b**: After filling, the response MUST state **which named fields were left unfilled** and **which
  supplied data matched no field**. Unmatched data MUST NOT be dropped silently: data that vanished is
  indistinguishable from data never supplied.
- **FR-025**: Every format claimed as supported MUST have a **real file produced and opened** during
  verification. A code path that ran without error is not evidence the document is correct.

#### Content safety

- **FR-026**: Text drawn from device output, ticket fields or hostnames MUST NOT be interpreted as a
  spreadsheet formula, document field code, or markup. Untrusted content is rendered as text.
- **FR-027**: Large datasets MUST be bounded, with the bound **stated in the document**, not only in the
  tool response the eventual reader never sees.
- **FR-027a**: The bound applies to **every format, not only spreadsheets**: worksheet rows, `.docx` blocks
  and `.pptx` slides each have a defined ceiling. An unbounded document request is a memory and
  readability hazard in exactly the same way an unbounded worksheet is.
- **FR-027b**: Where two sources report different values for the same thing, **both MUST be rendered with
  their own origins**. Silent reconciliation, picking a winner, or dropping one is prohibited — a document
  that hides a disagreement asserts a certainty the data does not support.

#### Licensing

- **FR-028**: The licence terms of any referenced upstream skill MUST be recorded explicitly. Measured: the
  four `anthropics/skills` document skills are **source-available, demonstration-only** — not Apache-2.0 —
  and therefore MUST NOT be vendored into NetClaw.
- **FR-029**: Any capability inspired by those skills MUST be independently implemented. Reading them to
  decide *what* to build is legitimate; copying them is not.
- **FR-029a**: NetClaw MUST author its own document-generation capability. It MUST NOT ship, fetch, or
  install the upstream skills — **no install path, no runtime download, no vendored copy**. There is exactly
  one code surface for this feature and it is Apache-2.0.

#### Dependencies

- **FR-030**: The four document libraries are **already installed** via feature 062's `rag-mcp`
  (`python-docx` 1.2.0, `openpyxl` 3.1.5, `python-pptx` 1.0.2, `PyMuPDF` 1.28.0). This feature MUST NOT move
  a version another feature depends on (spec 076's `cryptography` lesson).
- **FR-031**: Installation MUST use `netclaw_pip_install`, never a bare `pip`/`pip3` (spec 077).
- **FR-032**: Any pin on a package whose submodule is imported MUST be upper-bounded (spec 077). PyMuPDF is
  imported as `fitz` and is precisely that case.
- **FR-032a**: This feature MUST declare **upper-bounded pins** for all four libraries, bounded to the
  currently-installed majors.
- **FR-032b**: `rag-mcp`'s `pyproject.toml` MUST be corrected in this feature to declare the same
  upper-bounded pins, replacing its current unpinned `"pymupdf"` / `"python-docx"` / `"openpyxl"` /
  `"python-pptx"`. Leaving two servers declaring conflicting requirements for one shared install is not an
  acceptable end state, and the unbounded declaration is a pre-existing spec-077 hazard this feature is the
  first to notice.
- **FR-032c**: The correction MUST NOT move any installed version. `python-docx` 1.2.0, `openpyxl` 3.1.5,
  `python-pptx` 1.0.2 and PyMuPDF 1.28.0 MUST remain exactly as installed — the bounds describe what is
  already resolved, they do not request a change (FR-030, spec 076's `cryptography` lesson).
- **FR-032d**: `rag-mcp`'s own ingestion behaviour MUST be confirmed unaffected after the declaration change.
  Editing another feature's dependency file obliges verifying that feature still works.

#### Read-only with respect to infrastructure

- **FR-033**: This feature MUST NOT touch a device, and MUST NOT create or update a ticket. It writes files.
  There is therefore no approval or change-record gate to design.
- **FR-034**: Every generation MUST produce a GAIT record (Principle IV), including failures.

#### Composition boundaries

- **FR-035**: The boundary against the existing diagram skills (`drawio-rfc`, `markmap`, `uml`,
  `threejs-network-viz`) MUST be stated: those produce **diagrams**; this produces **documents** that may
  embed them.
- **FR-036**: The boundary against `rag-mcp` MUST be stated: rag-mcp **reads** these formats for ingestion,
  this **writes** them. Same libraries, opposite direction.
- **FR-037**: The boundary against `servicenow-change-workflow` MUST be stated: that manages the CR
  lifecycle, this renders a document from it.

#### Artifact coherence (Principle XI)

- **FR-038**: All of the following MUST be updated, none assumed: registration or an `EXTERNAL_INTEGRATIONS`
  entry with a stated reason; `scripts/lib/catalog.sh` entry **and curated profile membership**;
  `scripts/lib/install-steps.sh` install function; **both** HUD entries in `ui/netclaw-visual/server.js`;
  `README.md` and `SOUL.md` including counts **and** a SOUL capability section; `SKILL.md`; `.env.example`;
  `TOOLS.md`; a server `README.md`.
- **FR-038a**: The server's tool manifest MUST measure **≤ 5,000 tokens**, the ceiling specs 080 and 081
  held, and the measured figure MUST be recorded.
- **FR-039**: If an iN2N member should generate documents, the **five member artifacts plus a mesh restart**
  from `docs/ADDING-AN-MCP.md` MUST be completed — the section spec 080's completion added.
- **FR-040**: `python3 scripts/reconcile-mcp.py` MUST exit 0 across all four surfaces.
- **FR-041**: `python3 scripts/verify-inventory-counts.py` MUST exit 0 with counts updated from the current
  207 skills / 154 integrations.

#### Honest verification

- **FR-042**: On completion, the feature MUST state per format what was **actually produced and opened**
  versus what merely executed without error.
- **FR-043**: Any format that could not be produced and inspected MUST be marked unverified or cut.

### Key Entities

- **Document request** — a format, a layout choice, and the data sources to populate from. For PDF, an
  existing fillable form plus a field-to-data mapping.
- **Source attribution** — the tool, system, device or record that produced a value, plus its as-of time
  where available. Carried per element, **visibly**, and never by a hidden mechanism alone.
- **Sources section** — a visible section in every generated file listing each tool and system consulted with
  its as-of time. Required alongside per-element attribution, never instead of it.
- **Unavailable field** — a field with no data. A **typed state in the server's vocabulary**, rendered
  explicitly, never expressible as a plain blank.
- **Failed source** — a source that errored. A typed state, distinct from a source that returned nothing.
- **Output artefact** — a written file with a timestamped unique path, never overwritten.
- **PDF form field** — an explicitly named, machine-readable field in an existing fillable PDF. The only
  template-population surface in scope, chosen because a named field makes "no data for this field"
  unambiguous.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `.docx` change record is generated from a real change record and real device state, opened,
  and every populated field traces to a named source.
- **SC-002**: A field with no data renders as explicitly unavailable — and the document contains no invented
  value, no misleading blank, and no plausible default in its place.
- **SC-003**: A failed source appears in the document as failed, distinguishable from a source that returned
  nothing.
- **SC-004**: A record that failed to retrieve appears as a failed entry rather than being omitted; the row
  count reflects what was attempted, not only what succeeded.
- **SC-005**: An `.xlsx` interface audit is generated from a real device query, opened, and its row count
  matches the source.
- **SC-006**: Administrative and operational state occupy separate columns in the audit.
- **SC-007**: A `.pptx` is generated, opened, and any embedded diagram demonstrably came from an existing
  diagram skill.
- **SC-008**: A fillable PDF is filled, opened, and values appear in the correct named fields; a
  non-fillable PDF is reported as such.
- **SC-008a**: A fill with incomplete data reports the named fields left unfilled; a fill with extra data
  reports the values that matched no field. Neither is silently absorbed.
- **SC-008b**: Supplying an Office template is rejected with a stated reason by **all three** of
  `docx_write`, `xlsx_write` and `pptx_write` — not only the first format implemented — and is neither
  ignored nor partially applied.
- **SC-009**: **Every** generated document states its generation time and that NetClaw produced it, in the
  document body — verified by opening the file, not by inspecting code.
- **SC-010**: A mixed-source table carries per-element attribution rather than one collective citation — a
  visible source column per row in a spreadsheet, a visible per-figure source in a document or deck.
- **SC-010a**: Every generated file carries a sources section listing each tool and system with its as-of
  time, **in addition to** per-element attribution.
- **SC-010b**: Provenance survives the forwarding test: after copying a table out of the file and after
  rendering it to print/PDF, the attribution is still present. No provenance is carried solely by a cell
  comment, tooltip, or document metadata property.
- **SC-011**: A source's own as-of time is preserved where provided and is distinguishable from the
  document's generation time.
- **SC-012**: Generating the same report twice leaves the first file unmodified and produces a second,
  differently-named file.
- **SC-013**: A missing or unwritable output directory is reported as a failure with no silent fallback.
- **SC-014**: The written file path is reported back and the file exists at that path.
- **SC-015**: Formula-like or markup-like text from a source renders as literal text, not as a formula or
  field code.
- **SC-016**: A bounded large dataset states its bound inside the document — for worksheet rows, `.docx`
  blocks and `.pptx` slides alike.
- **SC-017**: Upstream licence terms are recorded durably; no demonstration-only source is present in the
  repository, and no install, fetch, clone or download path for it exists in any shipped artifact —
  verified by inspecting the diff and grepping the installer, skills, server and docs.
- **SC-018**: No shared dependency version is moved. `python-docx` 1.2.0, `openpyxl` 3.1.5, `python-pptx`
  1.0.2 and PyMuPDF 1.28.0 are the same versions after this feature as before it.
- **SC-018a**: Both this feature and `rag-mcp` declare identical upper-bounded pins for the four libraries;
  no unbounded declaration of any of them remains in the repository.
- **SC-018b**: `rag-mcp` ingestion is exercised after the declaration change and still works.
- **SC-019**: Every generation, including failures, produces a GAIT record.
- **SC-020**: A per-format verification table exists distinguishing **produced-and-opened** from
  **executed-without-error**, with anything uninspected marked unverified or cut.
- **SC-021**: `reconcile-mcp.py` exits 0 across all four surfaces; `verify-inventory-counts.py` exits 0 with
  updated counts; `trace-skill.py` resolves for every skill added.
- **SC-022**: `SOUL.md` gains a capability section describing what NetClaw can now deliver and the
  no-fabrication discipline — not merely an incremented count.
- **SC-023**: A test proves a caller **cannot** produce a document lacking generation time, attribution, or
  per-element provenance — the guarantee is structural, not a convention the caller follows.
- **SC-024**: No skill contains document-writing logic; every generated file traces to the single server.
- **SC-025**: The tool manifest measures ≤ 5,000 tokens, with the figure recorded, and the read-only surface
  guard is proven non-vacuous.
- **SC-026**: `.docx` block count and `.pptx` slide count are bounded, and an applied bound is stated inside
  the produced document, exactly as the worksheet row bound is.
- **SC-027**: Two sources reporting different values for the same thing are both rendered with their own
  origins; neither is dropped and no silent reconciliation occurs.

## Assumptions

- **The four libraries are present and their installed versions must not move.** Verified installed via
  rag-mcp (feature 062). Decided in clarification: both this feature and rag-mcp declare **upper-bounded
  pins** to the already-installed majors, which closes rag-mcp's pre-existing unbounded declaration without
  changing a single resolved version.
- **The upstream document skills cannot be vendored, and no install path for them will be built.** Their
  terms are source-available, demonstration-only. Decided in clarification: NetClaw authors its own
  capability outright, citing upstream as **reference for capability selection** only. This makes R18
  build-rather-than-adopt for a licensing reason rather than a quality one.
- **Output goes to a persistent workspace output directory**, matching feature 046's convention for generated
  topology visualisations (timestamped, never overwritten, gitignored).
- **Diagram generation is out of scope and delegated.** Existing skills own it; this embeds their output.
- **No credentials are introduced.** Data arrives from existing skills that already hold their own
  credentials; this feature holds none.
- **`.docx`, `.xlsx` and `.pptx` are built from scratch.** Decided in clarification: no template population
  for the Office formats. A template's empty field is the strongest fabrication pressure in the feature, and
  Word/PowerPoint placeholder-matching is the fuzzy version of it. Corporate-branded-template support is a
  follow-on feature that needs its own fabrication analysis.
- **PDF is the one template case, and deliberately so.** A PDF form's fields are explicitly named and
  machine-readable, so "this field has no data" is unambiguous rather than guessed.
- **PDF support is form filling and assembly, not authoring.** Generating a rich PDF from scratch is a
  different and larger problem than populating an existing one.

## Out of Scope

- **Diagram and visualisation rendering** — owned by `drawio-rfc`, `markmap`, `uml`, `threejs-network-viz`
  (FR-035). This embeds, never redraws.
- **Reading or ingesting documents** — that is `rag-mcp` (feature 062). Same libraries, opposite direction.
- **Creating or updating tickets** — `servicenow-change-workflow` owns the CR lifecycle (FR-037).
- **Sending documents anywhere.** Writing a file is in scope; emailing it, attaching it to a ticket, or
  posting it to Slack is a separate, externally-visible action and belongs to the skills that already own
  those channels under Principle XIV.
- **A general report-templating platform.** Deliberately bounded to four formats and the compositions
  NetClaw actually needs.
- **Populating corporate-branded `.docx`/`.pptx`/`.xlsx` templates** — excluded by clarification (FR-023a).
  This is real enterprise demand and a legitimate follow-on feature, but placeholder-matching in an Office
  template is the fabrication surface this feature most needs to avoid, and it deserves its own analysis
  rather than being smuggled in as a convenience.
- **Authoring rich PDFs from scratch**, and **OCR of scanned documents** — both materially larger problems
  than the deliverable gap this feature closes.
- **Editing documents in place** — every generation produces a new artefact (FR-018).
- **Any installer, fetcher or vendored copy of the upstream `anthropics/skills` document skills** — excluded
  on licence grounds by clarification (FR-029a).
