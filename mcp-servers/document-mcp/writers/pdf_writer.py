"""PDF forms. Spec 082, US4.

PDF is the one template case in this feature, and deliberately so: a form's fields are
explicitly *named and machine-readable*, so "there is no data for this field" is
unambiguous. Word and PowerPoint placeholder-matching is the guessing version of the
same problem, which is why those formats are built from scratch.

Two limits, both stated rather than worked around:

  * Only named fields are written. Positional text placement onto a PDF with no form
    fields would produce a document that LOOKS filled and carries no field data — the
    exact "visually similar but non-functional" outcome FR-024 prohibits.

  * A filled form cannot carry a Sources section. It is the customer's document and
    adding a page would alter it. For this one format provenance lives in the response
    and the GAIT record, and the skill says so. Pretending otherwise would be worse
    than the limitation.

Measured 2026-08-03: `doc.is_form_pdf` returns an **int** (3) for a form and False for
a plain PDF. Compared truthily below — never `is True`.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from outcomes import Outcome, ValueRefused, parse_tagged
from provenance import SourceLedger

_WIDGET_KINDS = {
    fitz.PDF_WIDGET_TYPE_TEXT: "text",
    fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
    fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "radio",
    fitz.PDF_WIDGET_TYPE_COMBOBOX: "combobox",
    fitz.PDF_WIDGET_TYPE_LISTBOX: "listbox",
    fitz.PDF_WIDGET_TYPE_BUTTON: "button",
    fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
}

PROVENANCE_LIMITATION = (
    "A filled PDF form carries no Sources section: it is the supplied document and "
    "adding a page would alter it. For this format only, provenance lives in this "
    "response and the GAIT record. Every other format carries it inside the file."
)


def _open(path: str) -> tuple[fitz.Document, Path]:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = (Path(__file__).resolve().parents[3] / resolved)
    if not resolved.is_file():
        raise ValueRefused(f"PDF {path!r} does not exist", Outcome.SOURCE_MISSING)
    try:
        return fitz.open(str(resolved)), resolved
    except Exception as exc:  # noqa: BLE001 — surface the library's own reason
        raise ValueRefused(f"could not open {path!r} as a PDF: {exc}", Outcome.SOURCE_MISSING) from exc


def inspect(path: str) -> dict:
    """List the form's named fields so a caller maps data to fields it has actually
    seen, rather than inventing names."""
    doc, resolved = _open(path)
    try:
        fillable = bool(doc.is_form_pdf)  # int (measured: 3) — never `is True`
        fields = []
        for page_index, page in enumerate(doc):
            for widget in page.widgets():
                fields.append(
                    {
                        "name": widget.field_name,
                        "kind": _WIDGET_KINDS.get(widget.field_type, "unknown"),
                        "current_value": widget.field_value,
                        "page": page_index,
                    }
                )
        if not fillable or not fields:
            return {
                "outcome": Outcome.NOT_FILLABLE,
                "data": {"fillable": False, "field_count": 0, "fields": []},
                "message": (
                    f"{resolved.name} has no form fields. NetClaw will not place text "
                    f"positionally onto it — that would produce a document that looks "
                    f"filled but carries no field data (FR-024a)."
                ),
            }
        return {
            "outcome": Outcome.OK,
            "data": {"fillable": True, "field_count": len(fields), "fields": fields},
            "message": None,
        }
    finally:
        doc.close()


def fill(path: str, values: dict, ledger: SourceLedger, dest: Path) -> dict:
    """Fill named fields into a NEW file. The input PDF is never modified."""
    if not isinstance(values, dict) or not values:
        raise ValueRefused("'values' must be a non-empty object", Outcome.REFUSED_UNTYPED)

    # Parse every value through the same typed gate as every other format, so a bare
    # scalar cannot slip a blank into a governance form.
    parsed = {k: parse_tagged(v, f"values[{k}]") for k, v in values.items()}

    doc, resolved = _open(path)
    try:
        if not bool(doc.is_form_pdf):
            return {
                "outcome": Outcome.NOT_FILLABLE,
                "data": None,
                "message": (
                    f"{resolved.name} is not a fillable PDF. Nothing was written — a "
                    f"visually similar file with no field data would be worse than no "
                    f"file (FR-024)."
                ),
            }

        present: set[str] = set()
        filled: list[str] = []
        unfilled: list[str] = []

        for page in doc:
            for widget in page.widgets():
                name = widget.field_name
                present.add(name)
                tv = parsed.get(name)
                if tv is None or tv.is_gap or tv.value in (None, ""):
                    # Left genuinely empty. A form is never completed with a guess.
                    unfilled.append(name)
                    if tv is not None:
                        ledger.record(tv)
                    continue
                widget.field_value = str(tv.value)
                widget.update()
                filled.append(name)
                ledger.record(tv)

        # Supplied keys matching no field. NEVER dropped silently: data that vanished
        # is indistinguishable from data never supplied.
        unmatched = sorted(k for k in parsed if k not in present)
        for k in unmatched:
            ledger.record(parsed[k])

        if not filled and not unmatched:
            # Nothing was written and nothing was wrong — still emit, but say so.
            pass

        doc.save(str(dest), incremental=False, deflate=True)
        return {
            "outcome": Outcome.OK if not unfilled and not unmatched else Outcome.WRITTEN_WITH_GAPS,
            "data": {
                "filled": sorted(filled),
                "unfilled": sorted(unfilled),
                "unmatched": unmatched,
                "input_pdf": str(resolved),
            },
            "message": None,
            "caveats": _caveats(filled, unfilled, unmatched),
        }
    finally:
        doc.close()


def _caveats(filled: list[str], unfilled: list[str], unmatched: list[str]) -> list[str]:
    out = [PROVENANCE_LIMITATION]
    if unfilled:
        out.append(
            f"{len(unfilled)} field(s) were left empty because no data was supplied "
            f"for them: {', '.join(sorted(unfilled))}. They are blank in the form and "
            f"need completing by hand — NetClaw did not guess."
        )
    if unmatched:
        out.append(
            f"{len(unmatched)} supplied value(s) matched no field in this form and were "
            f"NOT written: {', '.join(unmatched)}. Reported rather than dropped, because "
            f"data that vanished is indistinguishable from data never supplied."
        )
    if not filled:
        out.append("No field was filled. The output is a copy of the input form.")
    return out
