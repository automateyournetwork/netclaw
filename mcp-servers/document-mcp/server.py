"""document-mcp — turn a NetClaw finding into a document a human will act on.

Spec 082 / roadmap R18. FastMCP, stdio, no credentials, no device access, no ticket
writes. Six tools. This server writes files and does nothing else.

THE ONE RULE: a document must never fabricate to fill a blank.

Tool output is ephemeral — read once, in context, by the person who asked. A document
is emailed, filed, and read months later by someone who was not there, and it carries
the authority of its formatting. A professional-looking change record with a plausible
invented number is a far more effective way to launder a guess into an official record
than any amount of terminal output, because nobody re-derives a figure that is already
in a table in a .docx.

So every populated field is a TAGGED VALUE — one of:

    {"v": <value>, "src": "<tool or system>", "device": "...", "as_of": "..."}
    {"unavailable": "<reason>"}
    {"failed": "<reason>"}

A value without `src` is refused. A bare scalar is refused. There is no way to express
"missing" as a blank.

Composition lives in the skills (document-generation, network-report-documents), not
here. This server holds no vendor knowledge — it renders tagged values.
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP  # noqa: E402

import envelope  # noqa: E402
import output  # noqa: E402
from outcomes import Outcome, ValueRefused  # noqa: E402
from provenance import DocumentStamp, SourceLedger  # noqa: E402
from writers import docx_writer, pdf_writer, pptx_writer, xlsx_writer  # noqa: E402

mcp = FastMCP("document-mcp")


def _write(kind: str, tool: str, payload: dict[str, Any], builder) -> dict:
    """The single path from a tool to a file. Every writer goes through here, and here
    goes through envelope.emit(), which is what makes the stamp, the provenance and the
    GAIT record impossible to omit."""
    stamp = DocumentStamp(tool=tool)
    ledger = SourceLedger()
    try:
        data, caveats = builder(payload, stamp, ledger)
    except ValueRefused as exc:
        return envelope.refused(tool=tool, reason=str(exc), outcome=exc.outcome)
    except output.OutputUnwritable as exc:
        return envelope.refused(tool=tool, reason=str(exc), outcome=Outcome.OUTPUT_UNWRITABLE)

    try:
        path, suffix = output.reserve(kind, payload.get("output_id", kind))
        path.write_bytes(data)
        artifact = output.finalize(path, suffix)
    except output.OutputUnwritable as exc:
        return envelope.refused(tool=tool, reason=str(exc), outcome=Outcome.OUTPUT_UNWRITABLE)

    return envelope.emit(
        tool=tool,
        outcome=Outcome.OK,
        artifact=artifact.as_dict(),
        ledger=ledger,
        stamp=stamp,
        caveats=caveats,
    )


@mcp.tool()
async def docx_write(
    title: str,
    blocks: list[dict],
    output_id: str = "document",
    template: str = "",
) -> dict:
    """Write a Word document (.docx) from an ordered list of typed blocks.

    Block types: heading, paragraph, figure, table, keyvalue, image, pagebreak.
    Every value in a figure/table/keyvalue must be a TAGGED VALUE (see server docstring)
    — the writer appends a Source column you cannot omit, footers every page with the
    generation stamp, and appends a Sources section.

    Prose paragraphs carry no attribution, so a paragraph asserting a bare number gets a
    caveat: put figures in a figure/table/keyvalue block instead.

    Office templates are NOT supported and `template` is refused rather than ignored.
    """
    return _write(
        "docx",
        "docx_write",
        {"title": title, "blocks": blocks, "output_id": output_id, "template": template},
        docx_writer.build,
    )


@mcp.tool()
async def xlsx_write(sheets: list[dict], output_id: str = "workbook", template: str = "") -> dict:
    """Write a spreadsheet (.xlsx) from typed sheets.

    Each sheet: {name, columns[], rows[[TaggedValue]], failed_rows[{label, failed}]}.
    The writer appends Source and As-of columns, adds a banner stating
    attempted/returned/failed, renders failed_rows AS ROWS (a shorter sheet would read
    as a smaller estate), and adds a Sources sheet.

    Administrative and operational state must be separate columns — a merged `status`
    column is refused. Untrusted text is written as literal text, so a value beginning
    with `=` cannot become a live formula.

    Office templates are NOT supported and `template` is refused rather than ignored.
    """
    return _write(
        "xlsx",
        "xlsx_write",
        {"sheets": sheets, "output_id": output_id, "template": template},
        xlsx_writer.build,
    )


@mcp.tool()
async def pptx_write(
    title: str, slides: list[dict], output_id: str = "deck", template: str = ""
) -> dict:
    """Write a presentation (.pptx) from typed slides.

    Each slide: {layout: bullets|figure|image, title, bullets[], figures[{label,value}],
    image{path,src}, detail_ref}. Sources appear in a VISIBLE box on the slide, not in
    speaker notes (which are invisible in presentation and print). A Sources slide is
    appended.

    Diagrams are embedded, never drawn here: image.path must be an artefact already
    produced by drawio-diagram, markmap-viz, uml-diagram or threejs-network-viz, and
    `src` must name it.

    Office templates are NOT supported and `template` is refused rather than ignored.
    """
    return _write(
        "pptx",
        "pptx_write",
        {"title": title, "slides": slides, "output_id": output_id, "template": template},
        pptx_writer.build,
    )


@mcp.tool()
async def pdf_inspect_form(path: str) -> dict:
    """List the named fields of a fillable PDF, so data is mapped to fields that exist.

    Call this BEFORE pdf_fill_form. A PDF with no form fields is reported as not
    fillable — NetClaw will not place text positionally, which would produce a document
    that looks filled and carries no field data.
    """
    tool = "pdf_inspect_form"
    try:
        result = pdf_writer.inspect(path)
    except ValueRefused as exc:
        return envelope.refused(tool=tool, reason=str(exc), outcome=exc.outcome, query={"path": path})
    if result["outcome"] is Outcome.NOT_FILLABLE:
        return envelope.refused(
            tool=tool, reason=result["message"], outcome=Outcome.NOT_FILLABLE, query={"path": path}
        )
    ledger = SourceLedger()
    ledger.attribute_gap_to("(inspection only — no document written)")
    return envelope.emit(
        tool=tool,
        outcome=Outcome.OK,
        data=result["data"],
        ledger=ledger,
        stamp=DocumentStamp(tool=tool),
    )


@mcp.tool()
async def pdf_fill_form(path: str, values: dict, output_id: str = "form") -> dict:
    """Fill a fillable PDF's named fields from tagged values, into a NEW file.

    The input PDF is never modified. Values that are `unavailable` or `failed` leave the
    field genuinely empty and are reported in `unfilled` — a form is never completed
    with a guess. Supplied keys matching no field are reported in `unmatched`, never
    dropped silently.

    Note the one provenance limitation in this feature: a filled form carries no Sources
    section, because it is the supplied document and adding a page would alter it. For
    this format only, provenance lives in this response and the GAIT record.
    """
    tool = "pdf_fill_form"
    ledger = SourceLedger()
    stamp = DocumentStamp(tool=tool)
    try:
        dest, suffix = output.reserve("pdfform", output_id)
    except output.OutputUnwritable as exc:
        return envelope.refused(tool=tool, reason=str(exc), outcome=Outcome.OUTPUT_UNWRITABLE)

    try:
        result = pdf_writer.fill(path, values, ledger, dest)
    except ValueRefused as exc:
        dest.unlink(missing_ok=True)
        return envelope.refused(tool=tool, reason=str(exc), outcome=exc.outcome, query={"path": path})

    if result["outcome"] is Outcome.NOT_FILLABLE:
        dest.unlink(missing_ok=True)  # no output file for a non-fillable PDF
        return envelope.refused(
            tool=tool, reason=result["message"], outcome=Outcome.NOT_FILLABLE, query={"path": path}
        )

    artifact = output.finalize(dest, suffix)
    return envelope.emit(
        tool=tool,
        outcome=result["outcome"],
        artifact=artifact.as_dict(),
        data=result["data"],
        ledger=ledger,
        stamp=stamp,
        caveats=result.get("caveats", []),
    )


@mcp.tool()
async def list_documents(kind: str = "", limit: int = 50) -> dict:
    """List documents this server has generated, newest first, so you can find a file.

    `kind` filters to docx | xlsx | pptx | pdfform. Read-only.
    """
    tool = "list_documents"
    entries = output.list_outputs(kind or None, limit)
    ledger = SourceLedger()
    ledger.attribute_gap_to("(local filesystem listing — no document written)")
    return envelope.emit(
        tool=tool,
        outcome=Outcome.OK,
        data={"directory": str(output.output_dir()), "count": len(entries), "documents": entries},
        ledger=ledger,
        stamp=DocumentStamp(tool=tool),
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
