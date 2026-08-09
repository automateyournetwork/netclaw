"""Shared refusals. Spec 082, FR-023a, FR-014, FR-015, FR-027a.

These live in one place so all three Office writers reuse them. `/speckit.analyze`
caught the alternative: template rejection had been implemented for `.docx` only, which
is how a decision taken in clarification quietly applies to one format out of three.
"""

from __future__ import annotations

import re
from pathlib import Path

from outcomes import Outcome, ValueRefused

_REPO_ROOT = Path(__file__).resolve().parents[2]

TEMPLATE_KEYS = ("template", "template_path", "template_file", "base_document", "starting_document")

_TEMPLATE_REFUSAL = (
    "Office templates are out of scope for this feature (FR-023a). `.docx`, `.xlsx` "
    "and `.pptx` are built from scratch, because a corporate template's empty field is "
    "the strongest fabrication pressure in the whole feature — placeholder-matching in "
    "Word is the guessing version of the problem. PDF forms ARE supported, precisely "
    "because their fields are explicitly named and machine-readable, so 'no data for "
    "this field' is unambiguous rather than inferred. Corporate-template support is a "
    "follow-on feature with its own fabrication analysis. Refusing here rather than "
    "ignoring the parameter, so you do not receive an unbranded document believing it "
    "is branded."
)


def reject_template(payload: dict) -> None:
    """FR-023a. Refuse rather than silently ignore."""
    supplied = [k for k in TEMPLATE_KEYS if payload.get(k)]
    if supplied:
        raise ValueRefused(
            f"template parameter(s) supplied: {', '.join(supplied)}. {_TEMPLATE_REFUSAL}",
            Outcome.REFUSED_TEMPLATE,
        )


# ── merged admin/operational state (FR-015) ─────────────────────────────────

_MERGED_HEADERS = {"status", "state", "updown", "up/down", "linkstatus", "interfacestatus", "portstatus"}


def _norm(header: str) -> str:
    return re.sub(r"[^a-z/]", "", str(header).lower())


def reject_merged_status(columns: list[str], sheet_name: str = "") -> None:
    """FR-015. Admin state (what the config says) and operational state (what the wire
    says) are different facts — spec 080's completion established this after NetClaw
    itself reported the conflation on a real FortiGate.

    A sheet that ALREADY carries both separately may legitimately also carry a derived
    summary column, so the refusal only fires when the merged column is the only one.
    """
    normed = [_norm(c) for c in columns]
    has_admin = any("admin" in n for n in normed)
    has_oper = any(("oper" in n or "link" in n and "status" not in n) for n in normed)
    if has_admin and has_oper:
        return
    for original, n in zip(columns, normed):
        if n in _MERGED_HEADERS:
            where = f" on sheet {sheet_name!r}" if sheet_name else ""
            raise ValueRefused(
                f"column {original!r}{where} merges administrative and operational "
                f"state into one value. They are different facts: an interface can be "
                f"administratively up with no carrier, and a document that collapses "
                f"them tells the reader an interface is 'up' when nothing is passing. "
                f"Provide separate columns (e.g. 'Admin state' and 'Oper state'), or "
                f"keep this one alongside them.",
                Outcome.REFUSED_MERGED_STATUS,
            )


# ── embedded images must come from a real diagram skill (FR-014) ────────────

def resolve_embedded_image(path: str, src: str, label: str) -> Path:
    """FR-014/FR-035: this server embeds diagrams, it never draws them. The path must
    be a real file inside the workspace output tree — i.e. something a diagram skill
    actually produced — and `src` must name the skill that produced it."""
    if not src or not str(src).strip():
        raise ValueRefused(
            f"{label}: an embedded image requires 'src' naming the skill that produced "
            f"it (drawio-diagram, markmap-viz, uml-diagram, threejs-network-viz). This "
            f"server embeds diagrams and never draws them (FR-014)",
            Outcome.SOURCE_MISSING,
        )

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = _REPO_ROOT / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise ValueRefused(
            f"{label}: image {path!r} does not exist. A document must not claim to "
            f"show a diagram that was never generated",
            Outcome.SOURCE_MISSING,
        ) from None

    allowed = (_REPO_ROOT / "workspace" / "output").resolve()
    if not str(resolved).startswith(str(allowed) + "/"):
        raise ValueRefused(
            f"{label}: image {path!r} is outside {allowed}. Embedded diagrams must be "
            f"artefacts produced by a NetClaw diagram skill, not arbitrary files",
            Outcome.SOURCE_MISSING,
        )
    return resolved


# ── bounds (FR-027a) ────────────────────────────────────────────────────────

import os  # noqa: E402  (kept local to the bounds section for readability)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def max_rows() -> int:
    return _env_int("DOCUMENT_MAX_ROWS", 50_000)


def max_blocks() -> int:
    return _env_int("DOCUMENT_MAX_BLOCKS", 5_000)


def max_slides() -> int:
    return _env_int("DOCUMENT_MAX_SLIDES", 200)


def apply_bound(items: list, bound: int) -> tuple[list, bool]:
    """Returns (kept, truncated). The bound itself is written INTO the document by the
    caller — stating it only in the tool response would hide it from the one person who
    matters, the eventual reader."""
    if len(items) <= bound:
        return items, False
    return items[:bound], True
