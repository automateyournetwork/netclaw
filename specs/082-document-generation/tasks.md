# Tasks: Document Generation (docx / pptx / xlsx / pdf)

**Feature**: spec 082 / roadmap R18 · **Branch**: `082-document-generation` · **Date**: 2026-08-03
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/mcp-tools.md](./contracts/mcp-tools.md)

**Tests are included and are not optional here.** The spec requires them explicitly (FR-025, SC-020,
SC-023) and spec 080 shipped a tool returning three nulls past 24 passing tests because those tests asserted
on envelope *shape* and never on payload *content*. This feature's entire output **is** content, so every
verification task below reparses the produced file.

**Total: 145 tasks** (14 added by `/speckit.analyze` remediation). MVP = Phase 1 + 2 + 3 (T001–T059, US1
the change record).

**Traceability**: all 60 FRs and all 33 SCs have at least one task; no task references a requirement that
does not exist. Verified mechanically, not by eye.

---

## Phase 1: Setup

- [X] T001 Create the server directory tree `mcp-servers/document-mcp/` with `writers/` and an empty `writers/__init__.py`
- [X] T002 Create `mcp-servers/document-mcp/requirements.txt` with bounded pins only: `mcp>=1.2.0,<2`, `python-docx>=1.1,<2`, `openpyxl>=3.1,<4`, `python-pptx>=1.0,<2`, `pymupdf>=1.24,<2` — with a comment recording that the `mcp` bound is load-bearing (mcp 2.0 removed `mcp.server.fastmcp`) and that these bounds describe already-installed versions and move nothing (FR-030, FR-032a, FR-032c)
- [X] T003 Verify T002's bounds resolve to exactly the installed versions with no pip action: `python3 -c "import docx,openpyxl,pptx,fitz"` and record docx 1.2.0 / openpyxl 3.1.5 / pptx 1.0.2 / PyMuPDF 1.28.0 (SC-018)
- [X] T004 Create `tests/document/` and `tests/document/run-tests.sh` following `tests/bgp-intel/run-tests.sh` verbatim in structure (bash, `set -uo pipefail`, `REPO_ROOT` resolution, `run()` helper, FAILED counter, per-suite header comment naming FR/SC coverage)

**Checkpoint**: directory exists, dependencies confirmed present, test harness runnable (with zero suites).

---

## Phase 2: Foundational — the chokepoint (BLOCKING)

**Nothing in Phase 3+ can start until this completes.** This is where FR-001–FR-010, FR-026 and FR-034 stop
being prose and become structure.

### The typed vocabulary

- [X] T005 [P] Create `mcp-servers/document-mcp/outcomes.py` with the `Outcome` str-enum: `ok`, `written_with_gaps`, `truncated`, `refused_unattributed`, `refused_untyped`, `refused_template`, `refused_merged_status`, `not_fillable`, `output_unwritable`, `source_missing` (data-model §8). Factor it out of `envelope.py` following spec 081's split, not spec 080's inline enum
- [X] T006 Add `TaggedValue` parsing to `outcomes.py`: a `parse_tagged(raw, field_path)` returning a discriminated result for the three shapes `{"v",...}` / `{"unavailable"}` / `{"failed"}` (data-model §1)
- [X] T007 Add the validation rules to `parse_tagged`: exactly one discriminator present; `v` without `src` → refuse; a bare scalar → refuse with a message naming `field_path` **and showing the accepted shapes**; non-ISO `as_of` → refuse; empty `unavailable`/`failed` reason → refuse ("unavailable with no reason is a blank wearing a label")
- [X] T008 Add `render_tagged(tv)` to `outcomes.py` returning the display string per data-model §1: value as-is; `{"v": ""}` → `(empty)`; unavailable → `NOT AVAILABLE — <reason>`; failed → `RETRIEVAL FAILED — <reason>`. **Assert in the function** that no branch can return `""`, `"N/A"`, `"-"`, `"0"` or whitespace for a non-`v` shape, and that `unavailable` and `failed` render **differently from each other** — a dead query and an empty result are different facts (FR-001, FR-002)

### Provenance accumulation

- [X] T009 [P] Create `mcp-servers/document-mcp/provenance.py` with `SourceRecord` (src, device, as_of, element_count, status ok/partial/failed) and a `SourceLedger` that accumulates from TaggedValues, deduplicating on `(src, device)` and keeping the latest `as_of` (data-model §2)
- [X] T010 Add `SourceLedger.status_for()` returning `partial` when a source produced both values and unavailables — so a source that half-worked is not reported as clean
- [X] T011 Add `DocumentStamp` to `provenance.py` (generated_at UTC, generated_by `"NetClaw document-mcp <version>"`, tool, truncated, bound_applied). **Constructor takes no caller input for `generated_at`/`generated_by`** (data-model §3, FR-005b)

### The output writer

- [X] T012 [P] Create `mcp-servers/document-mcp/output.py` with `OUTPUT_DIR` resolved from `__file__` (repo root = `parents[2]`) to `workspace/output/document-mcp/`, overridable by `DOCUMENT_OUTPUT_DIR`. **Persistent, never a temp directory** (FR-016) — following `workspace/skills/threejs-network-viz/output.py` (research D7)
- [X] T013 Add the timestamped filename builder: `f"{kind}-{UTC %Y%m%dT%H%M%SZ}-{safe_id}.{ext}"` with 046's sanitiser (`c if c.isalnum() or c in "-_" else "_"`). `output_id` is the caller's identifier; `safe_id` is its sanitised form (FR-017)
- [X] T014 Add `exclusive_create(path)` using `os.open(path, O_CREAT | O_EXCL | O_WRONLY, 0o644)`; on `FileExistsError` append `-2`, `-3`, … and record `collision_suffix`. **An existing file is never opened for writing** (FR-018 — this is where spec 082 tightens feature 046, which relies on timestamp uniqueness alone)
- [X] T015 Add the unwritable-directory path: a missing or non-writable output dir raises so the chokepoint can return `output_unwritable`. **No fallback to a temp directory** (FR-020)
- [X] T016 Add `list_outputs(kind, limit)` to `output.py` for the `list_documents` tool

### Untrusted text

- [X] T017 [P] Create `mcp-servers/document-mcp/sanitize.py` with `force_text_cell(cell, value)` that assigns then sets `cell.data_type = "s"` — the measured mitigation for openpyxl writing a leading `=` as `<f>` (research D5, FR-026)
- [X] T018 Add `plain_text(value)` to `sanitize.py` for docx/pptx: strips control characters and guarantees the value is inserted as a text run, never as a field code

### The chokepoint itself

- [X] T019 Create `mcp-servers/document-mcp/envelope.py` with `emit(*, tool, outcome, artifact, ledger, stamp, gaps, caveats, message)` building the response of contracts §"Every response envelope"
- [X] T020 Add `ProvenanceError` to `envelope.py` and raise it from `emit()` when an artifact is present but the ledger is empty — a document with no nameable source is not emittable (FR-007, mirrors spec 081's `emit()` source guard)
- [X] T021 Add `refused(tool, reason, outcome)` to `envelope.py` for the six refusal outcomes; it produces **no artifact** and is still audited
- [X] T022 Add `audit(tool, response)` to `envelope.py` writing one JSON line to `DOCUMENT_AUDIT_LOG` or `~/.openclaw/gait/document-mcp.jsonl`, with the stderr warning on `OSError` — following `bgp-intel-mcp/envelope.py`. **Called from inside `emit()` and `refused()`, never by a caller** (FR-034)
- [X] T023 Add the gap accounting to `emit()`: `gaps: {"unavailable": N, "failed": N}` counted from the ledger, and force `outcome = written_with_gaps` when either is non-zero and the caller passed `ok` — a caller **cannot** report a gapped document as clean
- [X] T024 Verify by reading `envelope.py` and each writer stub that there is **no code path** producing a file without passing through `emit()` — record the audit in a comment at the top of `envelope.py`

### Foundational tests

- [X] T025 [P] Create `tests/document/test_tagged_values.py` following `tests/bgp-intel/test_outcomes.py` conventions (module `FAILURES`, `check(name, condition, detail)`, `main()` → 0/1, `sys.path.insert` to the server dir)
- [X] T026 In `test_tagged_values.py`: assert `{"v": 5}` without `src` is refused, and the message names the field path (FR-007)
- [X] T027 In `test_tagged_values.py`: assert a bare scalar `5` where a TaggedValue is expected is refused with `refused_untyped` (FR-005c)
- [X] T028 In `test_tagged_values.py`: assert `{"v": ""}`, `{"unavailable": "x"}` and `{"failed": "x"}` render to **three different strings**, and assert on the **rendered text** that none is `""`, `"N/A"`, `"-"` or whitespace (spec 081's rendered-text technique — an assertion on wording is the only kind that catches a wording bug)
- [X] T029 In `test_tagged_values.py`: assert `{"unavailable": ""}` (empty reason) is refused
- [X] T030 [P] Create `tests/document/test_output_paths.py`: two writes in the same second produce two distinct files; after the second, the first is **byte-identical** to before (FR-018, SC-012)
- [X] T031 In `test_output_paths.py`: assert the second file carries `collision_suffix` and the reported `artifact.path` is the file that actually exists on disk, so the operator can retrieve it (FR-019, SC-014)
- [X] T032 In `test_output_paths.py`: point `DOCUMENT_OUTPUT_DIR` at a non-writable path and assert `output_unwritable`, **and** assert no file was created anywhere else (FR-020, SC-013)
- [X] T033 [P] Create `tests/document/test_sanitize.py`: write `=1+1` through the xlsx path, reopen, assert `cell.data_type == "s"`, **and unzip the workbook and assert `<f>` does not appear in `xl/worksheets/sheet1.xml`** (FR-026, SC-015 — the raw-XML assertion is what catches research D5)
- [X] T034 In `test_sanitize.py`: assert the round-tripped value is still literally `=1+1` — the mitigation must not corrupt the text with a `'` prefix
- [X] T035 Wire T025/T030/T033 suites into `tests/document/run-tests.sh` and confirm the harness passes

**Checkpoint**: the chokepoint exists, refuses correctly, audits everything, and cannot overwrite. No writer
exists yet.

---

## Phase 3: User Story 1 — Change record `.docx` (Priority: P1) 🎯 MVP

**Goal**: produce a change record from a real CR plus real device state, where every populated field traces
to a named source and every unavailable field says so.

**Independent test**: generate from a real CR number and a real device query; open the `.docx` and confirm
every populated field has a named source and every gap is explicit.

- [X] T036 [P] [US1] Create `mcp-servers/document-mcp/writers/docx_writer.py` — named `docx_writer.py`, **not `docx.py`**, which would shadow the third-party package on the path the server inserts
- [X] T037 [US1] Implement the `heading` and `paragraph` blocks in `docx_writer.py` (contracts §1)
- [X] T038 [US1] Implement the `keyvalue` block: two columns plus a **`Source` column appended by the writer**, so a caller cannot omit attribution — per element, never one collective citation (FR-009, FR-009a)
- [X] T039 [US1] Implement the `table` block with the same writer-appended `Source` column, and an `As of` column when any row carries `as_of` (FR-009, FR-010)
- [X] T040 [US1] Implement the `figure` block: value followed by a visible inline parenthetical `(src · device · as of …)` in a smaller run — **inline, because python-docx 1.2.0 has no footnote API** (research D3, FR-008a)
- [X] T041 [US1] Implement the `image` block: validate the path exists **and** resolves inside the workspace output dir, require `src` naming the producing skill, else `source_missing` (FR-014, FR-035)
- [X] T042 [US1] Implement `pagebreak`
- [X] T043 [US1] Add the section footer carrying generation time and NetClaw attribution on **every page** (FR-006, FR-008)
- [X] T044 [US1] Append the visible `Sources` section built from the `SourceLedger`, with per-source as-of and status (FR-009a)
- [X] T045 [US1] Add the prose lint with a **defined trigger**: a `paragraph` emits a caveat naming the block index if its text contains a digit **that is not** part of an allow-listed pattern — an ISO/RFC date, a time, a ticket identifier matching `[A-Z]{2,6}\d{4,}`, a version like `7.6.7`, an ordinal like "Section 2", or an IP/prefix/ASN literal. Everything else is a bare figure, and prose is the one place an unattributed figure could hide (data-model §4). The vague version of this rule ("contains a bare number") fires on every date and gets tuned into vacuity — the allow-list is what keeps it real
- [X] T046 [US1] Set `core_properties.comments` additively, and add a comment recording that this is **additive only** and must never be the provenance mechanism (FR-008a)
- [X] T047 [US1] Reject any `template`/`template_path` parameter on `docx_write` with `refused_template` and a message saying Office templates are out of scope and why (FR-023a, SC-008b). Put the check in a **shared helper** so `xlsx_write` (T067a) and `pptx_write` (T081a) reuse it rather than each re-deriving it
- [X] T047a [US1] Implement the block bound (`DOCUMENT_MAX_BLOCKS`, default 5,000): on truncation set `outcome = truncated` and **write the bound into the document body** (FR-027a, SC-026)
- [X] T047b [US1] Implement the disagreement rule: two TaggedValues for the same label with different `src` are **both** rendered, each with its own origin, and a caveat names the disagreement. No winner is picked and neither is dropped (FR-027b, SC-027)
- [X] T048 [US1] Create `mcp-servers/document-mcp/server.py` with the FastMCP init, `sys.path.insert`, and stdio `mcp.run()` tail, following `bgp-intel-mcp/server.py`
- [X] T049 [US1] Add the `docx_write` tool to `server.py`, delegating to the writer and returning through `envelope.emit()` (FR-021)
- [X] T050 [P] [US1] Create `tests/document/test_provenance.py`: generate a `.docx`, **reopen it with python-docx**, and assert the footer contains a generation time and "NetClaw" (SC-009 — verified by opening the file, not by inspecting code)
- [X] T051 [US1] In `test_provenance.py`: assert every table in the reopened `.docx` has a `Source` column and that no data row has an empty source cell (SC-010)
- [X] T052 [US1] In `test_provenance.py`: assert a `Sources` section exists and lists each source with its as-of (SC-010a)
- [X] T053 [US1] In `test_provenance.py`: assert a source's own `as_of` is rendered and is **distinguishable** from the document's generation time (SC-011)
- [X] T054 [US1] In `test_provenance.py`: assert a refusal still produced a GAIT record — read `DOCUMENT_AUDIT_LOG` and find the line (SC-019, and the defect `/speckit.analyze` caught in specs 076 and 080)
- [X] T055 [P] [US1] Create `tests/document/test_no_fabrication.py`: a `keyvalue` with one `unavailable` pair renders `NOT AVAILABLE — <reason>` in the reopened document, and the literal strings `N/A`, `TBD` and `Unknown` do **not** appear (SC-002)
- [X] T056 [US1] In `test_no_fabrication.py`: a `failed` value renders `RETRIEVAL FAILED` and is textually distinct from an `unavailable` value in the same document (SC-003)
- [X] T057 [US1] In `test_no_fabrication.py`: `outcome` is `written_with_gaps`, not `ok`, whenever any gap is present — and the caller passing `ok` cannot override it (T023)
- [X] T057a [US1] In `test_no_fabrication.py`: two sources disagreeing on one label produce **both** values in the reopened document, each with its own source, plus a caveat. Assert on rendered text that neither value is absent (FR-027b, SC-027)
- [X] T057b [US1] In `test_no_fabrication.py`: assert `docx_write`, `xlsx_write` and `pptx_write` **all three** return `refused_template` for a supplied template — a single parametrised assertion, so a fourth format cannot be added without it (SC-008b)
- [X] T057c [US1] In `test_no_fabrication.py`: assert an over-bound docx block list and an over-bound pptx slide list each yield `truncated` with the bound present in the reopened file (FR-027a, SC-026)
- [X] T058 [US1] Wire `test_provenance.py` and `test_no_fabrication.py` into `run-tests.sh`
- [X] T059 [US1] **Produce a real change-record `.docx` from a real ServiceNow CR and real FortiGate state, open it, and record what it contains** in a scratch note for `VERIFICATION.md` (FR-011, FR-025, SC-001). If ServiceNow is not configured, use real FortiGate state plus a hand-supplied CR and **record that half as unverified** rather than claiming it

**Checkpoint**: US1 independently deliverable. A real `.docx` exists and has been opened.

---

## Phase 4: User Story 2 — Interface audit `.xlsx` (Priority: P1)

**Goal**: every interface across a set of devices in a spreadsheet, with separate admin/oper columns,
per-row provenance, and failed devices present as failed rows.

**Independent test**: generate from a real device query; row count matches the source; every column has a
stated origin; a failed device appears as a failed row.

- [X] T060 [P] [US2] Create `mcp-servers/document-mcp/writers/xlsx_writer.py` (not `openpyxl.py`)
- [X] T061 [US2] Implement sheet creation from `{name, columns, rows}` with every string cell written through `sanitize.force_text_cell` (FR-026)
- [X] T062 [US2] Append the writer-owned `Source` and `As of` columns to every sheet (FR-009a, FR-010)
- [X] T063 [US2] Render `failed_rows` **as rows**, visually marked, positioned with the data — not in a separate section a reader can miss (FR-003)
- [X] T064 [US2] Add the banner row stating *attempted / succeeded / failed*, frozen at the top of each data sheet (SC-004)
- [X] T065 [US2] Refuse a merged state column with `refused_merged_status` and a message citing the distinction (FR-015). **Defined trigger**: the header, case-folded and stripped of punctuation, is one of `status`, `state`, `updown`, `up/down`, `link status`, `interface status` — **and** the sheet contains no separate column matching `admin` and no separate column matching `oper`. A sheet that already has both may legitimately also carry a derived summary column
- [X] T066 [US2] Add the `Sources` worksheet built from the `SourceLedger`, plus the `DocumentStamp` in its header (FR-009a, FR-006)
- [X] T067 [US2] Implement the row bound from `DOCUMENT_MAX_ROWS` (default 50,000): on truncation set `outcome = truncated` and **write the bound into the sheet itself**, not only into the response (FR-027, SC-016)
- [X] T067a [US2] Reject any `template`/`template_path` parameter on `xlsx_write` with `refused_template` (FR-023a, SC-008b) — the scratch-only decision applies to **all three** Office formats, not only the first one implemented
- [X] T068 [US2] Add the `xlsx_write` tool to `server.py` (FR-022)
- [X] T069 [P] [US2] In `test_provenance.py`: generate a workbook, **reopen with openpyxl**, assert every data sheet has a populated `Source` column on every row (SC-005, SC-010)
- [X] T070 [US2] In `test_no_fabrication.py`: a failed device appears as a row; the sheet's row count equals *attempted*, not *succeeded*; the banner reports the split (SC-004)
- [X] T071 [US2] In `test_no_fabrication.py`: assert admin and operational state occupy **two columns** and that no single column merges them (SC-006)
- [X] T072 [US2] In `test_no_fabrication.py`: assert a truncated workbook states its bound in a cell, found by reopening (SC-016)
- [X] T073 [US2] **Produce a real interface-audit `.xlsx` from a real `fgt_list_interfaces` (or `multivendor-device-query`) result, open it, and confirm the row count matches the source**; record for `VERIFICATION.md` (FR-012, SC-005)

**Checkpoint**: US2 independently deliverable, and it does not depend on US1.

---

## Phase 5: User Story 3 — Executive summary `.pptx` (Priority: P2)

**Goal**: a short deck carrying findings, with sources visible on the slide and an embedded diagram from an
existing diagram skill.

**Independent test**: generate from real findings, open it, confirm the diagram came from an existing skill.

- [X] T074 [P] [US3] Create `mcp-servers/document-mcp/writers/pptx_writer.py` (not `pptx.py`)
- [X] T075 [US3] Implement the `title` and `bullets` layouts
- [X] T076 [US3] Implement the `figure` layout with a **visible on-slide source line** along the bottom — speaker notes are hidden in presentation and print and do not satisfy FR-008a (research D4)
- [X] T077 [US3] Implement the `image` layout: path validated inside the workspace output dir, `src` naming the producing diagram skill, else `source_missing` (FR-014)
- [X] T078 [US3] Write the same detail into `notes_slide` **additively**, with a comment recording that it is additive and never the mechanism
- [X] T079 [US3] Append the `Sources` slide from the `SourceLedger` (FR-009a)
- [X] T080 [US3] Put the `DocumentStamp` on the title slide and the Sources slide (FR-006)
- [X] T081 [US3] Emit a caveat for any `bullets` slide with no `detail_ref` — a summary claim should be traceable to detail (FR-005)
- [X] T081a [US3] Reject any `template`/`template_path` parameter on `pptx_write` with `refused_template` (FR-023a, SC-008b)
- [X] T081b [US3] Implement the slide bound (`DOCUMENT_MAX_SLIDES`, default 200): on truncation set `outcome = truncated` and **write the bound onto a slide** (FR-027a, SC-026)
- [X] T082 [US3] Add the `pptx_write` tool to `server.py` (FR-023)
- [X] T083 [P] [US3] In `test_provenance.py`: generate a deck, **reopen with python-pptx**, and assert the on-slide source text is present in a **shape**, not only in `notes_slide` (SC-007, SC-010b)
- [X] T084 [US3] In `test_provenance.py`: assert a `Sources` slide exists and the title slide carries the stamp
- [X] T085 [US3] **Produce a real `.pptx` embedding a diagram actually generated by `drawio-diagram` or `threejs-network-viz`, open it**, and record which skill produced the diagram (FR-013, SC-007)

---

## Phase 6: User Story 4 — Fill a PDF form (Priority: P3)

**Goal**: fill an existing fillable PDF from real data, leaving unmatched fields genuinely empty and
reporting both directions of mismatch.

**Independent test**: fill a real form with known values, reopen, confirm values landed in the right named
fields and unfilled fields are actually unfilled.

- [X] T086 [P] [US4] Create `mcp-servers/document-mcp/writers/pdf_writer.py` (not `fitz.py`)
- [X] T087 [US4] Implement form detection with `doc.is_form_pdf` — **compare truthily; it returns an int (measured: 3), never `is True`** (research D6)
- [X] T088 [US4] Implement field enumeration from `page.widgets()` returning name, kind (mapped from `PDF_WIDGET_TYPE_*`), current value, page index (data-model §7)
- [X] T089 [US4] Add the `pdf_inspect_form` tool to `server.py`, returning `not_fillable` with a message for a PDF with no form fields, and **no output file** (FR-024)
- [X] T090 [US4] Implement filling by **named field only** — no positional text placement, which would produce a document that looks filled but carries no field data (FR-024a)
- [X] T091 [US4] Leave a field empty for `unavailable`/`failed` values and add it to `unfilled`; never write a guess to complete the form (FR-024b, US4 §2)
- [X] T092 [US4] Compute and return `unmatched` — supplied keys matching no field. **Never dropped silently**: data that vanished is indistinguishable from data never supplied (FR-024b)
- [X] T093 [US4] Write to a **new** file via `output.exclusive_create`; the input PDF is never modified
- [X] T094 [US4] Add the `pdf_fill_form` tool to `server.py`
- [X] T095 [US4] Document the one place FR-008 cannot be met inside the artefact: a customer's form has nowhere for a Sources section without altering it, so provenance for a fill lives in the response and the GAIT record. **State this in the tool docstring and the skill** rather than pretending otherwise
- [X] T096 [P] [US4] Create `tests/document/test_pdf_forms.py`: build a fixture form with `fitz.Widget()` + `page.add_widget()` (research D6 — the suite generates its own form, no customer artefact needed)
- [X] T097 [US4] In `test_pdf_forms.py`: fill a subset, reopen, assert values are in the correct named fields and untouched fields are still empty (SC-008)
- [X] T098 [US4] In `test_pdf_forms.py`: assert `unfilled` and `unmatched` are both reported and neither is silently absorbed (SC-008a)
- [X] T099 [US4] In `test_pdf_forms.py`: assert a non-fillable PDF returns `not_fillable` and **no output file was created** (SC-008)
- [X] T100 [US4] In `test_pdf_forms.py`: assert the input PDF is byte-identical after a fill
- [X] T101 [US4] Wire `test_pdf_forms.py` into `run-tests.sh`

---

## Phase 7: Dependency correction (cross-cutting)

**Sequenced after the writers** so a dependency change cannot be blamed for a writer bug.

- [X] T102 Bound the unpinned declarations in `mcp-servers/rag-mcp/pyproject.toml`: `mcp>=1.2.0,<2`, `fastmcp` (bound to the installed major — **measure it first**), `pymupdf>=1.24,<2`, `python-docx>=1.1,<2`, `openpyxl>=3.1,<4`, `python-pptx>=1.0,<2`, `vsdx` (measure and bound). Add a comment naming spec 082 and stating no installed version moves (FR-032b, FR-032c)
- [X] T103 Confirm T102 moved nothing: re-import all of rag-mcp's document libraries and compare versions to the T003 record (SC-018)
- [X] T104 Extend `scripts/check-dependency-pins.py` to read `pyproject.toml` `[project].dependencies` in addition to `requirements.txt` — **rag-mcp has no `requirements.txt` and has therefore never been scanned** (FR-032, research D2)
- [X] T105 Add a distribution→module alias map to `check-dependency-pins.py` covering at least `pymupdf`→`fitz`, `python-docx`→`docx`, `python-pptx`→`pptx`, `beautifulsoup4`→`bs4`, `pillow`→`PIL` — the checker matches by distribution name, so these renames slip through even a scanned file (FR-032, research D2)
- [X] T106 Run `python3 scripts/check-dependency-pins.py; echo $?` and confirm exit 0 with a **higher** scanned-server count than the 63 baseline. If the extended checker surfaces genuine pre-existing hazards in other servers, **list them in `VERIFICATION.md` as found-not-fixed** rather than silently widening this feature's scope
- [X] T107 Re-exercise rag-mcp ingestion after T102 — ingest a real `.docx`, `.xlsx`, `.pptx` and `.pdf` and confirm it still parses them. Editing another feature's dependency file obliges proving that feature still works (FR-032d, SC-018b)
- [X] T108 Verify no unbounded declaration of the four document libraries remains anywhere in the repo: `grep -rn` across `requirements.txt` and `pyproject.toml` files (SC-018a)

---

## Phase 8: Skills and artifact coherence (Principle XI)

- [X] T109 [P] Create `workspace/skills/document-generation/SKILL.md` — frontmatter copied exactly from `workspace/skills/bgp-registry-intel/SKILL.md` (quoted single-line `description` ending in a "Use when …" clause, `version`, `license: Apache-2.0`, `tags`, `user-invocable: true`, inline-JSON `metadata.openclaw.requires`). Body: the six tools, **the one rule** ("a document must never fabricate to fill a blank"), the TaggedValue shapes, the output convention, and the **three stated limits** (no docx footnotes, no Office templates, no Sources section in a filled PDF)
- [X] T109a Add the agent-facing prohibition to `document-generation/SKILL.md`, stated as strongly as the tool refusals: **never infer, estimate, interpolate, or carry forward a stale value to complete a document** (FR-004). The server structurally cannot fabricate — it only renders TaggedValues — but the agent composing the request can, and this is the only place that half of the discipline can live
- [X] T109b Add all **three** boundary statements to `document-generation/SKILL.md`: diagram skills own diagrams and this embeds them (FR-035); `rag-mcp` **reads** these formats and this **writes** them, same libraries opposite direction (FR-036); `servicenow-change-workflow` owns the CR lifecycle and this renders a document from it (FR-037)
- [X] T110 [P] Create `workspace/skills/network-report-documents/SKILL.md` with the four compositions — change record, interface/config audit workbook, executive summary deck, PDF form fill — each naming the upstream skills that feed it (`servicenow-change-workflow`, `fortigate-ops`/`multivendor-cli`, the diagram skills) and the boundary against them
- [X] T110a Repeat the no-inference prohibition (FR-004) and the three boundaries (FR-035/036/037) in `network-report-documents/SKILL.md` — this is the skill an agent actually reaches for, so the discipline cannot live only in its sibling
- [X] T111 Add the `document` entry to `scripts/lib/catalog.sh` in the `Platform Services` group, **and add `document` to `PROFILE_RECOMMENDED`** — profile membership is the easy-to-miss artifact `docs/ADDING-AN-MCP.md` calls out
- [X] T112 Add `component_install_document()` to `scripts/lib/install-steps.sh` following `component_install_bgp_intel()` verbatim in shape: `netclaw_pip_install -r "$DIR/requirements.txt"`, `log_warn` on failure, `DOCUMENT_MCP_CMD_DETECTED` export. **Never call `pip`/`pip3` directly** (FR-031). Do not copy bgp-intel's stale section comment
- [X] T113 Register `document-mcp` in `config/openclaw.json` with repo-relative paths, `command`/`args` separate, `-u` flag, and `${VAR}` env passthrough only — appended after `bgp-intel-mcp`
- [X] T114 Add **both** HUD entries to `ui/netclaw-visual/server.js`: the `INTEGRATION_CATALOG` node (id `document`, category `Platform Services`, prefixes `['docx_','xlsx_','pptx_','pdf_','list_documents']`, transport `stdio`, toolEstimate 6) **and** the `ENV_MAP` annotation (env vars, `files`, and a `notes` string stating no credentials, files-only, and the no-fabrication discipline). One entry is not enough
- [X] T115 Update `.env.example` with the box-header block for spec 082: `DOCUMENT_MCP_CMD`, `DOCUMENT_OUTPUT_DIR`, `DOCUMENT_MAX_ROWS`, `DOCUMENT_AUDIT_LOG` — names and defaults only, no values (FR-038)
- [X] T116 Update `TOOLS.md` with `## Document Generation (\`document-mcp\`, NetClaw-native)` following the bgp-intel block's shape: spec/roadmap line, format table, `### Environment`, `### Behaviour worth knowing` (including the measured openpyxl formula hazard, the three limits, and the three boundaries FR-035/036/037), and the measured manifest token count
- [X] T117 Update `SOUL.md`: add a `### Document Generation (2)` capability section describing what NetClaw can now deliver and the no-fabrication discipline — **a capability description, not merely an incremented count** (FR-038, SC-022) — and update both count sites (line ~15 `**209 skills** backed by 155 MCP servers`, line ~525 `all 209 skills`)
- [X] T118 Update `README.md`: two new MCP table rows and two new skill rows for this feature; **plus the pre-existing drift found in research D13** — the missing table rows for Fortinet (spec 080) and BGP-intel (spec 081) and the missing `bgp-registry-intel`/`fortigate-ops`/`fortianalyzer-ops` skill rows. Then update all four count sites to 155 / 209

---

## Phase 9: Honest verification and polish

- [X] T119 Create `tests/document/test_manifest_size.py`: measure the tool manifest and assert **≤ 5,000 tokens** (FR-038a, SC-025). Add the read-only surface guard with a **defined predicate** — no tool may accept a parameter that is a device target, a hostname/IP, a credential, or a ticket identifier, and no tool description may claim to change infrastructure state (FR-033). *Not* "no tool name implies a write": four of six tools do write, to files, which is the whole point. Prove the guard non-vacuous by temporarily adding a tool with a `device_host` parameter and confirming it fails
- [X] T119a Wire `test_manifest_size.py` into `tests/document/run-tests.sh` — every other suite has an explicit wiring task and this one would otherwise never run
- [X] T120 Add the structural-guarantee test to `test_provenance.py`: attempt, from a caller's position, to produce a document lacking generation time, attribution, or per-element provenance — and assert it is **impossible**, not merely discouraged (SC-023)
- [X] T121 Add the no-skill-writes assertion: `grep` the two SKILL.md files and confirm neither contains document-writing code, and that every generated file traces to the single server (SC-024, FR-005a, FR-005d)
- [X] T122 Add the forwarding test to `test_provenance.py`: extract a table's text from each generated file (the copy-paste path) and assert attribution survives; assert no provenance is carried solely by a cell comment, tooltip, or document metadata property (SC-010b, FR-008a)
- [X] T122a **Licence verification** (FR-028, FR-029, FR-029a, SC-017): confirm no file in this feature's diff was copied from `anthropics/skills`; `grep` every shipped artifact — installer, skills, server, docs — for any `git clone`, `curl`, `wget`, `pip install` from a URL, or other fetch path targeting it, and confirm there is none; confirm the licence finding is recorded durably in `docs/COVERAGE-ROADMAP.md` **and** `research.md` D1. This is the constraint that redefined R18 and nothing else checks it
- [X] T123 Create `mcp-servers/document-mcp/README.md` — the step-5 artifact: tools, env vars, transport, the output convention, the three limits, the three boundaries (FR-035/036/037), and install
- [X] T124 Create `specs/082-document-generation/VERIFICATION.md` with a per-format table distinguishing **produced-and-opened** from **executed-without-error**, and mark anything uninspected as unverified or cut (FR-042, FR-043, SC-020). Include the T106 found-not-fixed list if any
- [X] T124a In `VERIFICATION.md`, record the **iN2N decision** (FR-039): this capability is Border-only because it holds no credentials and composes across domains, so the five member artifacts plus a mesh restart are **not triggered** — and state that they apply in full if a member is ever given it. A conditional requirement resolved silently reads as an omitted one (research D11)
- [X] T125 Run `bash tests/document/run-tests.sh` and confirm all suites pass
- [X] T126 Run `python3 scripts/reconcile-mcp.py; echo $?` and confirm **exit 0 across all four surfaces** (FR-040) — read the exit code directly, never through a pipe (CLAUDE.md: `cmd | tail` reports `tail`'s status)
- [X] T127 Run `python3 scripts/verify-inventory-counts.py; echo $?` and confirm exit 0 with 209 skills / 155 integrations (FR-041, SC-021)
- [X] T128 Run `python3 scripts/trace-skill.py document-generation` and `... network-report-documents` and confirm both resolve (SC-021)
- [X] T129 Deploy to the live workspace and run an end-to-end generation from Slack, then **open the produced file** — the bug spec 080 shipped surfaced only in a live run, not in 24 passing tests
- [X] T130 Secret-scan the diff before commit; confirm no credential, path or hostname leaked into any artifact
- [X] T131 Record the GAIT session log for this feature (Principle IV, artifact checklist)

---

## Dependencies

```
Phase 1 (Setup)
   └─▶ Phase 2 (Foundational chokepoint)  ── BLOCKING ──┐
                                                        ├─▶ Phase 3 (US1 docx, P1)  🎯 MVP
                                                        ├─▶ Phase 4 (US2 xlsx, P1)
                                                        ├─▶ Phase 5 (US3 pptx, P2)
                                                        └─▶ Phase 6 (US4 pdf,  P3)
                                                                    │
                                             Phase 7 (dependency correction) ◀┘
                                                        │
                                             Phase 8 (skills + artifacts)
                                                        │
                                             Phase 9 (honest verification)
```

**Story independence**: US1, US2, US3 and US4 each depend only on Phase 2. None depends on another. US1
alone is a shippable MVP.

**Sequencing note**: Phase 7 comes after Phase 6 deliberately. Changing dependency declarations while
writers are still being debugged would make a writer bug look like a dependency regression.

---

## Parallel execution opportunities

**Within Phase 2** — T005, T009, T012, T017 touch four different new files:
```
T005 outcomes.py   ┐
T009 provenance.py ├── all [P], no shared files
T012 output.py     │
T017 sanitize.py   ┘
```
Then T019–T024 (`envelope.py`) must be serial — they all edit one file.

**Across user stories** — after Phase 2, the four writers are four separate files:
```
T036 writers/docx_writer.py  (US1)  ┐
T060 writers/xlsx_writer.py  (US2)  ├── all [P]
T074 writers/pptx_writer.py  (US3)  │
T086 writers/pdf_writer.py   (US4)  ┘
```
Their `server.py` tool registrations (T049, T068, T082, T089/T094) must serialise — one file.

**Within Phase 8** — T109 and T110 are two different SKILL.md files and are `[P]`. Everything else in
Phase 8 edits a distinct shared file and should be done one at a time to keep diffs reviewable.

---

## Independent test criteria per story

| Story | Independently testable by |
|---|---|
| **US1** (P1, docx) | Generate from a real CR + real device state; **open the file**; every populated field names a source; every gap is explicit text, not a blank |
| **US2** (P1, xlsx) | Generate from a real device query; **open the workbook**; row count = attempted; admin/oper in separate columns; failed device present as a failed row |
| **US3** (P2, pptx) | Generate from real findings; **open the deck**; source text lives in a slide shape, not only in speaker notes; diagram came from an existing skill |
| **US4** (P3, pdf) | Fill a real form; **reopen it**; values in the right named fields; `unfilled` and `unmatched` both reported; input file unchanged |

---

## Implementation strategy

**MVP** = Phases 1–3 (T001–T059). That is a working change-record generator with the full no-fabrication
discipline already structural, because the discipline lives in Phase 2, not in the writers.

**Then** Phase 4 (US2) for the highest-volume real use, Phase 5, Phase 6 — each independently shippable.

**Then** Phases 7–9, which are cross-cutting and must not be skipped: Phase 7 closes a hazard that predates
this feature, Phase 8 is Principle XI, and Phase 9 is the difference between "the tests pass" and "a human
opened the document and it was right".

**The rule that governs Phase 9**: a file being written is not evidence the document is correct. Spec 080
had 24 passing tests and a tool returning three nulls. Every claim in `VERIFICATION.md` must say whether the
artefact was **opened** or merely **produced**.
