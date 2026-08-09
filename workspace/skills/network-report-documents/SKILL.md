---
name: network-report-documents
description: "The four standard NetClaw document compositions — a change-record Word document from a real ServiceNow CR plus device state, an interface/config audit workbook from real device queries, an executive summary deck with an embedded topology diagram, and a required PDF form filled from real data. Use when an operator asks for a deliverable to attach to a change record, hand to an auditor, or put in front of a director."
version: 1.0.0
license: Apache-2.0
tags: [documents, reporting, change-record, audit, executive-summary, pdf-forms, deliverables]
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["DOCUMENT_MCP_CMD"] } } }
---

# Network Report Documents

Four compositions built on `document-mcp`. This skill owns **what goes in the document**; the server owns
**writing it**. Read [document-generation](../document-generation/SKILL.md) for the tool surface, the tagged
value shapes, and the stated limits.

## The rule that governs all four

> ### A document must never fabricate to fill a blank.

**Never infer, estimate, interpolate, or carry forward a stale value to complete a document.** The server
structurally cannot fabricate — it only renders tagged values — but *you* can, by inventing a plausible
figure while assembling the request. That half of the discipline lives here and nowhere else.

If a device did not answer, send `{"unavailable": "device did not answer"}`. A change record that says
"NOT AVAILABLE — device did not answer" is useful. One with a confident wrong number is worse than none,
because a change advisory board will act on it and nobody will re-derive it.

## 1 · Change record (`.docx`)

> *"Generate a change record for CHG0012345 with the current state of fgt-01."*

**Feed it from**: `servicenow-change-workflow` for the CR (read-only — this composition never creates or
updates a ticket), plus `fortigate-ops` / `multivendor-cli` / `pyats` for device state.

**Shape**:

| Section | Block | Notes |
|---|---|---|
| Change details | `keyvalue` | CR number, state, requester, window, risk — each tagged with `src: servicenow_get_change` |
| Pre-change state | `keyvalue` + `table` | Real device output, tagged per device |
| Topology | `image` | Only if a diagram skill already produced one |
| Rollback | `paragraph` | Narrative — put no figures here |

**If the CR does not exist or is not approved, say so and stop.** Do not produce a document with an invented
CR — the document would outlive the conversation that knew it was a placeholder.

**If ServiceNow is not configured**, you may still produce the device half, but state in the response that
the CR half was hand-supplied and unverified.

## 2 · Interface / config audit workbook (`.xlsx`)

> *"Build an interface audit spreadsheet for all my FortiGates."*

**Feed it from**: `fgt_list_interfaces`, `multivendor-device-query`, `pyats` — whatever actually reached the
devices.

**Non-negotiables**:

- **Administrative and operational state go in separate columns.** A merged `status` column is refused by
  the server. An interface can be admin-up with no carrier; collapsing them tells the auditor traffic is
  passing when nothing is. This is the distinction spec 080's completion established after NetClaw itself
  reported the conflation on a real FortiGate.
- **A device that failed goes in `failed_rows`, never omitted.** A shorter spreadsheet reads as a smaller
  estate, which is a false statement about the network. The server renders failures as marked rows and
  reports attempted / returned / failed in a banner.
- Device descriptions are untrusted text; the server writes them as literal text so a leading `=` cannot
  become a live formula. You do not need to sanitise anything.

## 3 · Executive summary deck (`.pptx`)

> *"Make an exec deck from the posture review, with the topology diagram."*

**Feed it from**: findings other NetClaw skills produced, and a diagram file an existing diagram skill
already generated.

**Shape**: a `bullets` slide for what was found, `figure` slides for the numbers behind it, an `image` slide
for the diagram, and the auto-appended Sources slide.

- **Give every summary slide a `detail_ref`** pointing at the detail slide or the Sources slide. A bare
  summary claim gets a caveat, and rightly — an executive reading "everything is fine" deserves to know
  where that came from.
- **Do not draw the diagram.** Run `drawio-diagram`, `markmap-viz`, `uml-diagram` or `threejs-network-viz`
  first, then pass its output path and `src`. A path outside the workspace output directory is refused.
- Sources appear in a **visible box on the slide**, not in speaker notes — notes are invisible in
  presentation and print.

## 4 · Fill a required PDF form

> *"What fields does audit-response.pdf have?"* → *"Fill it from the CR and the device state."*

1. **Always `pdf_inspect_form` first.** It returns the real field names. Never guess them.
2. Map tagged values onto those exact names.
3. Read back `unfilled` and `unmatched` and **tell the operator both**: which fields they must complete by
   hand, and which of their values matched nothing.

A field with no data is left genuinely empty. Never fill one to make the form look complete — an audit
response form is precisely where an invented answer does the most damage.

**Tell the operator the one limitation**: a filled form carries no Sources section, because it is their
document and adding a page would alter it. Provenance for a fill lives in the tool response and the GAIT
record.

## Boundaries

| Want to… | Use |
|---|---|
| Draw a diagram | `drawio-diagram`, `markmap-viz`, `uml-diagram`, `threejs-network-viz` — embedded here, never redrawn |
| Read a document into the knowledge base | `rag-mcp` (feature 062) — it **reads** these formats, this **writes** them |
| Create, update or close a change record | `servicenow-change-workflow` — this renders a document from one and writes no ticket |
| Send the document | `slack-report-delivery`, `webex-report-delivery` — writing the file is in scope, sending it is a separate, outward-facing action |
| Understand the tool surface | `document-generation` |

## Before you hand anything over

- **Read the `outcome`.** `written_with_gaps` means the document is incomplete — say which parts, do not
  present it as finished.
- **Give the path.** The operator has to find the file.
- **Say what is unverified.** If half the data was hand-supplied because a system was unconfigured, that
  belongs in your reply, not just in your head.
