"""Untrusted text. Spec 082, FR-026.

This is not a theoretical hardening exercise. Measured 2026-08-03:

    ws["A1"] = "=1+1"       →  <c r="A1"><f>1+1</f><v></v></c>     A LIVE FORMULA

openpyxl converts a leading `=` into a formula element. The strings this server writes
come from FortiGate interface descriptions, ServiceNow short-descriptions, device
banners and hostnames — none of which NetClaw controls. A description beginning with
`=` is enough to put executing content into an auditor's spreadsheet.

The mitigation, also measured:

    cell.value = "=1+1"; cell.data_type = "s"
        →  <c r="A2" t="inlineStr"><is><t>=1+1</t></is></c>        LITERAL TEXT

Applied uniformly to every string cell rather than only to values starting with `=`,
because which prefixes a spreadsheet application treats as formulas varies by locale
and by paste path, whereas `t="inlineStr"` is unambiguous in the file itself.

Deliberately NOT done: prefixing with an apostrophe. That is the common advice and it
visibly corrupts the value, in a document whose entire purpose is fidelity.
"""

from __future__ import annotations

# Everything below 0x20 except tab/newline/carriage-return is illegal in OOXML text and
# will produce a file Word or Excel refuses to open.
_CONTROL = {c: None for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)}
_CONTROL[0x7F] = None


def plain_text(value: object) -> str:
    """A string safe to insert as a text run in docx/pptx.

    Strips control characters that would make the OOXML unopenable. Does NOT escape
    anything else — python-docx and python-pptx insert runs as text nodes, so markup in
    the value is already inert; escaping it again would visibly corrupt it.
    """
    if value is None:
        return ""
    return str(value).translate(_CONTROL)


def force_text_cell(cell, value: object) -> None:
    """Write a value into an openpyxl cell as literal text, never as a formula.

    Order matters: the assignment is what triggers openpyxl's formula detection, so the
    data_type override must come after it.
    """
    cell.value = plain_text(value)
    cell.data_type = "s"


def write_cell(cell, value: object) -> None:
    """Write any value. Numbers and booleans stay typed so a spreadsheet can sum them;
    strings go through the forced-text path."""
    if isinstance(value, bool):
        cell.value = value
    elif isinstance(value, (int, float)):
        cell.value = value
    else:
        force_text_cell(cell, value)
