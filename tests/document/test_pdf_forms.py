"""PDF form filling. Spec 082, US4, FR-024/024a/024b, SC-008/008a.

The suite builds its own fixture form with fitz.Widget() + page.add_widget(), so it
needs no customer artefact and no network. Measured 2026-08-03: doc.is_form_pdf returns
an int (3) for a form and False for a plain PDF — compared truthily throughout.
"""

from __future__ import annotations

import hashlib
import os

import fitz

from _harness import FAILURES, check, cleanup, run, sandbox  # noqa: F401

import output  # noqa: E402
from outcomes import Outcome, ValueRefused  # noqa: E402
from provenance import SourceLedger  # noqa: E402
from writers import pdf_writer  # noqa: E402

FIELDS = ["change_number", "device_hostname", "approver", "risk_level"]


def _fixture_form(directory: str) -> str:
    path = os.path.join(directory, "audit-response.pdf")
    doc = fitz.open()
    page = doc.new_page()
    for i, name in enumerate(FIELDS):
        w = fitz.Widget()
        w.field_name = name
        w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.rect = fitz.Rect(50, 50 + i * 40, 400, 80 + i * 40)
        w.field_value = ""
        page.add_widget(w)
    doc.save(path)
    doc.close()
    return path


def _plain_pdf(directory: str) -> str:
    path = os.path.join(directory, "plain.pdf")
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "this is not a form")
    doc.save(path)
    doc.close()
    return path


def _sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_inspect_lists_real_field_names():
    d = sandbox()
    try:
        result = pdf_writer.inspect(_fixture_form(d))
        check("a form is reported fillable", result["outcome"] is Outcome.OK, str(result["outcome"]))
        names = [f["name"] for f in result["data"]["fields"]]
        check("every field is discovered", sorted(names) == sorted(FIELDS), str(names))
        check("the field count matches", result["data"]["field_count"] == len(FIELDS))
        check("field kinds are mapped", all(f["kind"] == "text" for f in result["data"]["fields"]),
              str(result["data"]["fields"]))
    finally:
        cleanup(d)


def test_non_fillable_is_reported_not_faked():
    d = sandbox()
    try:
        result = pdf_writer.inspect(_plain_pdf(d))
        check("a plain PDF is reported not fillable",
              result["outcome"] is Outcome.NOT_FILLABLE, str(result["outcome"]))
        check("the message explains why nothing was written",
              "positionally" in result["message"], result["message"][:120])

        dest = os.path.join(d, "should-not-exist.pdf")
        fill = pdf_writer.fill(_plain_pdf(d), {"a": {"v": "1", "src": "x"}},
                               SourceLedger(), dest)
        check("filling a non-fillable PDF is refused",
              fill["outcome"] is Outcome.NOT_FILLABLE, str(fill["outcome"]))
        check("NO output file was produced", not os.path.exists(dest),
              "a visually-similar file with no field data is worse than no file")
    finally:
        cleanup(d)


def test_values_land_in_the_right_named_fields():
    d = sandbox()
    try:
        form = _fixture_form(d)
        dest_path, _s = output.reserve("pdfform", "chg")
        result = pdf_writer.fill(
            form,
            {"change_number": {"v": "CHG0012345", "src": "servicenow_get_change"},
             "risk_level": {"v": "Low", "src": "servicenow_get_change"}},
            SourceLedger(),
            dest_path,
        )
        check("the fill succeeded", result["outcome"] in (Outcome.OK, Outcome.WRITTEN_WITH_GAPS))

        doc = fitz.open(str(dest_path))
        values = {w.field_name: w.field_value for p in doc for w in p.widgets()}
        doc.close()
        check("change_number landed in its own field",
              values["change_number"] == "CHG0012345", str(values))
        check("risk_level landed in its own field", values["risk_level"] == "Low", str(values))
        check("untouched fields are genuinely empty",
              values["approver"] == "" and values["device_hostname"] == "", str(values))
    finally:
        cleanup(d)


def test_unfilled_and_unmatched_are_both_reported():
    """SC-008a. Neither direction of mismatch is silently absorbed."""
    d = sandbox()
    try:
        form = _fixture_form(d)
        dest_path, _s = output.reserve("pdfform", "gaps")
        result = pdf_writer.fill(
            form,
            {"change_number": {"v": "CHG0012345", "src": "servicenow_get_change"},
             "approver": {"unavailable": "no approver recorded on the CR"},
             "ghost_field": {"v": "x", "src": "somewhere"}},
            SourceLedger(),
            dest_path,
        )
        data = result["data"]
        check("filled lists only what was written", data["filled"] == ["change_number"], str(data))
        check("an unavailable value leaves the field unfilled",
              "approver" in data["unfilled"], str(data))
        check("a field with no data at all is unfilled",
              "device_hostname" in data["unfilled"], str(data))
        check("a supplied key matching no field is reported",
              data["unmatched"] == ["ghost_field"], str(data))

        doc = fitz.open(str(dest_path))
        values = {w.field_name: w.field_value for p in doc for w in p.widgets()}
        doc.close()
        check("the unavailable field is EMPTY, not filled with the reason",
              values["approver"] == "", repr(values["approver"]))
        check("no guess was written to complete the form",
              all(v == "" for k, v in values.items() if k != "change_number"), str(values))

        caveats = " ".join(result["caveats"])
        check("a caveat names the unfilled fields", "approver" in caveats, caveats[:150])
        check("a caveat names the unmatched value", "ghost_field" in caveats, caveats[:200])
        check("the provenance limitation is stated",
              "no Sources section" in caveats, caveats[:200])
    finally:
        cleanup(d)


def test_the_input_pdf_is_never_modified():
    d = sandbox()
    try:
        form = _fixture_form(d)
        before = _sha(form)
        dest_path, _s = output.reserve("pdfform", "immutable")
        pdf_writer.fill(form, {"change_number": {"v": "X", "src": "t"}},
                        SourceLedger(), dest_path)
        check("the input PDF is byte-identical afterwards", _sha(form) == before,
              "the supplied form was modified in place")
        check("a new file was produced", os.path.exists(dest_path))
        check("the new file differs from the input", _sha(str(dest_path)) != before)
    finally:
        cleanup(d)


def test_fill_values_go_through_the_same_typed_gate():
    d = sandbox()
    try:
        form = _fixture_form(d)
        dest_path, _s = output.reserve("pdfform", "typed")
        raised = None
        try:
            pdf_writer.fill(form, {"change_number": "CHG0012345"}, SourceLedger(), dest_path)
        except ValueRefused as exc:
            raised = exc
        check("a bare scalar is refused even for a PDF form", raised is not None,
              "a governance form must not be fillable from untyped values")
        if raised:
            check("the refusal is typed", raised.outcome is Outcome.REFUSED_UNTYPED, str(raised.outcome))

        raised2 = None
        try:
            pdf_writer.fill(form, {"change_number": {"v": "X"}}, SourceLedger(), dest_path)
        except ValueRefused as exc:
            raised2 = exc
        check("a value without src is refused", raised2 is not None)
    finally:
        cleanup(d)


def test_missing_pdf_is_reported():
    d = sandbox()
    try:
        raised = None
        try:
            pdf_writer.inspect(os.path.join(d, "nope.pdf"))
        except ValueRefused as exc:
            raised = exc
        check("a nonexistent PDF is refused", raised is not None)
        if raised:
            check("typed as source_missing", raised.outcome is Outcome.SOURCE_MISSING, str(raised.outcome))
    finally:
        cleanup(d)


TESTS = [
    test_inspect_lists_real_field_names,
    test_non_fillable_is_reported_not_faked,
    test_values_land_in_the_right_named_fields,
    test_unfilled_and_unmatched_are_both_reported,
    test_the_input_pdf_is_never_modified,
    test_fill_values_go_through_the_same_typed_gate,
    test_missing_pdf_is_reported,
]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "PDF form"))
