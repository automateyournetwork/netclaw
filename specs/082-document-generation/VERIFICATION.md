# Verification Report — Document Generation (spec 082 / R18)

**Date**: 2026-08-03 · **FR-025, FR-042, FR-043, SC-020**

FR-043 requires that anything not exercised is recorded as **unverified** rather than claimed. This is spec
078's precedent (four of five Cisco API families dropped after returning 403) and spec 080's lesson: that
feature had **24 passing appliance-free tests while shipping a tool that returned three nulls**, because its
suites asserted on envelope *shape* and never on payload *content*.

This feature's entire output **is** content. So the column that matters below is not "did it run" but
**"was the file opened and read"**.

## Per-format status

| Format | Produced | **Opened & inspected** | Real data | Evidence |
|---|---|---|---|---|
| `.docx` | ✅ | ✅ | ✅ **live FortiGate** | Change record from `fgt_system_status` + `fgt_list_interfaces` on FGVMEVS9GWUAOMBD, reopened with python-docx; footer, 4 tables, Sources section, per-row attribution all read back |
| `.xlsx` | ✅ | ✅ | ✅ **live FortiGate** | Interface audit reopened with openpyxl; banner `4 attempted · 2 returned data · 2 failed`, Source + As-of columns populated, two failed planes present as marked rows |
| `.pptx` | ✅ | ✅ | ✅ **live FortiGate** | 5-slide deck reopened with python-pptx; source text found in a **shape** on every slide, 1 embedded picture, gap rendered on-slide |
| `.pdf` (form fill) | ✅ | ✅ | ✅ **live FortiGate** | Serial/firmware/HA filled from real device state, reopened with PyMuPDF; `reviewer_signature` left genuinely empty, `site_code` reported unmatched, input byte-identical |

**All four formats were produced from real device data and opened.** None is claimed on the strength of a
code path that merely ran.

## The lab

| | |
|---|---|
| Device | FortiGate-VM64-HV, Hyper-V, `192.168.2.130` |
| Serial | `FGVMEVS9GWUAOMBD` · FortiOS **7.6.7** build 3704 |
| Data source | `fortinet-mcp` device plane, read-only `netclawapi` token |
| Source as-of | `2026-08-03T18:19:57Z` — **distinct from** the documents' generation time `18:20:58Z` / `18:22:18Z`, which is what makes FR-010 testable rather than trivially true |
| Diagram | Real PNG from **Kroki** (`uml-diagram`'s backend), written to `workspace/output/uml-diagram/` and embedded with `src: uml-diagram` |
| ServiceNow | ❌ not configured — see below |

## Per-capability status

### The chokepoint — VERIFIED

| Guarantee | Status |
|---|---|
| Every response passes `emit()`/`refused()` | ✅ asserted by source inspection in `test_manifest_size.py` |
| No writer imports `envelope` | ✅ asserted for all four writers |
| Artefact with an empty ledger raises `ProvenanceError` | ✅ tested |
| A caller cannot set `generated_at`/`generated_by` | ✅ tested |
| A caller cannot report a gapped document as `ok` | ✅ tested — `ok` was passed, `written_with_gaps` came back |
| GAIT record on success **and refusal** | ✅ log read back, both outcomes present |

### No fabrication — VERIFIED

| Guarantee | Status | Evidence |
|---|---|---|
| Value without `src` refused | ✅ | `refused_unattributed` |
| Bare scalar refused | ✅ | `refused_untyped`, all of int/str/bool/None/list |
| `unavailable` ≠ `failed` ≠ `{"v":""}` | ✅ | three distinct rendered strings, asserted on text |
| Gap never renders as `N/A`/`0`/`-`/blank | ✅ | runtime guard in `render_tagged` **plus** a text assertion on the opened file |
| Gap with no reason refused | ✅ | "a blank wearing a label" |
| Failed devices are rows, not omissions | ✅ | live: fortimanager + fortianalyzer present as marked rows |
| Row count = attempted, not succeeded | ✅ | live banner reads `4 attempted` |
| Admin vs operational state separate | ✅ | merged `status`/`state`/`up-down` refused; live audit has both columns |
| Sources that disagree both rendered | ✅ | both values + caveat, no winner picked |
| Prose asserting a bare figure flagged | ✅ | fires on "We observed 12 interfaces"; does **not** fire on dates, CR numbers, IPs, versions, "Section 2" |

### Provenance — VERIFIED (by opening files)

| Guarantee | Status |
|---|---|
| Generation time + NetClaw in `.docx` footer | ✅ read back from the section footer |
| Source column on every table, no empty source cell | ✅ asserted per row |
| Source's own as-of preserved and distinct from generation time | ✅ 18:19:57Z vs 18:20:58Z in the live document |
| Sources section in every file | ✅ `.docx` section, `.xlsx` sheet, `.pptx` slide |
| `.pptx` source in a **shape**, not only notes | ✅ asserted against shape text |
| Survives copy-paste and print | ✅ table text extracted; `word/comments.xml` absent |

### Content safety — VERIFIED

Measured: `ws["A1"] = "=1+1"` produces `<c r="A1"><f>1+1</f>…` — a live formula. Mitigated and asserted
against **raw worksheet XML**: no `<f>` element for any of six hostile inputs, values round-trip exactly
(no apostrophe corruption), numbers stay numeric.

### Output convention — VERIFIED

Same-second writes produce two files with the first byte-identical afterwards; collision suffix recorded;
unwritable directory raises with nothing written anywhere else; reported path is the real one.

## Unverified, and stated as such

| Item | Why | What would close it |
|---|---|---|
| **ServiceNow CR half of US1** | ServiceNow is not configured on this deployment. The live change record was produced from **real device state** with the CR field explicitly rendered as `NOT AVAILABLE — ServiceNow is not configured … hand-supplied and unverified`. The composition against a real CR has **not** run. | A configured ServiceNow instance |
| **`.pptx` embed from `drawio-diagram` / `threejs-network-viz`** | Verified with a real PNG from **Kroki**, which is `uml-diagram`'s backend — so FR-014 is exercised against a genuine diagram-skill artefact. The other three diagram skills produce HTML or need a display and were not exercised. | Running those skills to a raster artefact |
| **Checkbox / radio / combobox PDF fields** | Only `text` widgets were exercised. The kind mapping for the other six `PDF_WIDGET_TYPE_*` values is coded from the PyMuPDF constants and **not observed**. | A form with non-text fields |
| **50,000-row worksheet at full scale** | Truncation logic verified at a bound of 2. The 50,000 default was never reached — no data source here produces that many rows. | A large real inventory |
| **iN2N member usage** | **Not applicable by decision, not by omission.** This capability holds no credentials and composes across domains, so it is Border work by construction; a member would be composing data it cannot reach. FR-039's five member artifacts plus `systemctl --user restart netclaw-mesh.service` are therefore **not triggered** — and apply in full if a member is ever given it. | A decision to change that |

## Found and not fixed — pre-existing, surfaced by this feature

Teaching `check-dependency-pins.py` to read `pyproject.toml` and to map distribution names to module names
surfaced **14 real hazards across 10 servers** that had never been visible. The baseline `reconcile-mcp.py`
exited 0 because those files were never read, not because they were correct.

**Fixed here** (tracked, NetClaw-maintained):

| Server | Was | Now |
|---|---|---|
| `rag-mcp` | 13 dependencies, **all unbounded**, in a `pyproject.toml` the checker never read | all bounded to installed majors |
| `memory-mcp` | `mcp` unpinned, `chromadb>=0.4.0` | `mcp>=1.2.0,<2`, `chromadb>=0.4.0,<2` |
| `azure-network-mcp` | `azure-identity>=1.15.0` while importing `azure.identity` | `<2` added |

**Recorded as exceptions, not fixed** — 11 findings across 8 servers
(`AAP-Enterprise-MCP-Server`, `gait_mcp`, `infrahub-mcp`, `junos-mcp-server`, `mcp-nautobot`, `mcp-nvd`,
`meraki-magic-mcp-community`, `servicenow-mcp`):

Every one is a real hazard of exactly the class the checker exists to catch — mostly unbounded `mcp` while
importing `mcp.server.fastmcp`, the breakage spec 077 calls no longer hypothetical. They are **untracked
upstream clones**: `git ls-files` returns nothing for those directories, so a local pin is not committable,
evaporates on the next re-clone, and would leave a fixed-looking check guarding nothing. Each carries a
named reason in `PIN_EXCEPTIONS` saying exactly that, and the comment there says to delete the line the
moment any of them is vendored into the repo.

**Closing them needs an upstream pin or a change to the vendoring policy, not a local edit.** Recorded here
so the next reader inherits the finding rather than rediscovering it.

## Backwards compatibility (Principle XV)

`rag-mcp`'s dependency file was edited by this feature, which obliges proving rag-mcp still works (FR-032d).
It was re-exercised **on the four documents document-mcp had just generated**: `parse_file` returned
`ParsedDocument` for all four — 4 parsed, 0 failed. No installed version moved (SC-018): python-docx 1.2.0,
openpyxl 3.1.5, python-pptx 1.0.2, PyMuPDF 1.28.0, before and after.

## Licence (FR-028/029/029a, SC-017)

Verified by inspection and grep across the installer, both skills, the server and the docs:

- No file copied from `anthropics/skills`; no reference to it in any shipped artifact.
- **No `git clone`, `curl`, `wget`, or URL-based `pip install`** anywhere in this feature's code or its
  install function.
- The finding — those skills are source-available, *"provided for demonstration and educational purposes
  only"*, not Apache-2.0 — is recorded durably in `docs/COVERAGE-ROADMAP.md` (with the roadmap's
  "vendor the four official skills" item struck and the reason given) and in `research.md` D1.

## Checks

| Check | Result |
|---|---|
| `bash tests/document/run-tests.sh` | ✅ **240 assertions, 7 suites, exit 0** |
| `python3 scripts/reconcile-mcp.py` | ✅ exit 0 — all four surfaces |
| `python3 scripts/verify-inventory-counts.py` | ✅ exit 0 — **209 skills / 155 integrations** |
| `python3 scripts/trace-skill.py document-generation` | ✅ exit 0 |
| `python3 scripts/trace-skill.py network-report-documents` | ✅ exit 0 |
| Manifest size | ✅ **1,232 / 5,000 tokens** |
| `node --check ui/netclaw-visual/server.js` | ✅ |
| `bash -n scripts/lib/{catalog,install-steps}.sh` | ✅ |

## Findings worth keeping

- **`check-dependency-pins.py` read `requirements.txt` only.** rag-mcp has none. A server declaring
  dependencies in `pyproject.toml` was invisible to the spec-077 checker entirely, and its clean bill of
  health was an artefact of that invisibility. Fixed permanently, not per-instance.
- **The checker also matched by *distribution* name.** `pymupdf`→`fitz`, `python-docx`→`docx`,
  `beautifulsoup4`→`bs4` never met their imports, so even a scanned file would have passed. An alias map now
  covers the renames actually present in this repo.
- **openpyxl turns a leading `=` into a live formula.** Not theoretical: the strings this server writes come
  from device descriptions and ticket fields. Only the raw-XML assertion catches it — `data_type == "s"` is
  an openpyxl-level claim, `<f>` absent from `sheet1.xml` is a claim about the file an auditor opens.
- **`python-docx` 1.2.0 has no footnote API.** It has `add_comment`, which is the tempting answer and the
  wrong one: comments are collapsed by default, stripped on paste, and invisible in print. Inline
  attribution is more visible, not less.
- **`doc.is_form_pdf` returns an `int`** (measured: 3), not a bool. Compare truthily; `is True` fails.
- **Feature 046's output convention relies on timestamp uniqueness alone.** Two documents in the same second
  collide, and `write_text` would silently replace the first. `O_EXCL` is the difference between "unlikely to
  overwrite" and "cannot".
- **A plan can ship a false technical claim.** This one justified the `_writer` filename suffix as avoiding
  package shadowing. Measured after `/speckit.analyze` challenged it: inside the `writers/` package, absolute
  imports resolve to the real third-party package and there is no shadowing. The names were kept for real
  reasons; the wrong reason was withdrawn (research D14).
- **README was two specs behind.** No MCP table rows for Fortinet (080) or BGP-intel (081), and no
  `fortigate-ops` / `fortianalyzer-ops` / `bgp-registry-intel` skill rows, even though SOUL.md and TOOLS.md
  had been updated. `verify-inventory-counts.py` misses this because it checks headline arithmetic, not table
  membership. Fixed here; the checker's blind spot remains.
