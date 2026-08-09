"""The typed vocabulary this feature exists to protect. Spec 082, FR-001..FR-005c.

Specs 078, 079, 080 and 081 each protected a distinction in *tool output*, which is
ephemeral — read once, in context, by the person who just asked. A document is none of
those things. It gets emailed, attached to a ticket, filed for audit, and read months
later by someone who was not there, and it carries the authority of its formatting.

So the honest representation has to be the ONLY EXPRESSIBLE one. A caller cannot hand
this server a missing value as an empty string and have it render as a blank cell,
because a bare scalar is not an accepted shape at all.

Three shapes, exactly one of which every populated field must be:

    {"v": <scalar>, "src": "...", "device": "...", "as_of": "..."}
    {"unavailable": "<reason>"}
    {"failed": "<reason>"}

`{"v": ""}` is legal and means *the source was consulted and genuinely returned empty*.
That is a different fact from `unavailable`, and it renders differently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Outcome(str, Enum):
    """Response vocabulary. Following spec 081's split — the enum lives here, not in
    envelope.py, because the distinctions are the domain and the envelope is plumbing."""

    OK = "ok"
    # Written, and it contains unavailable or failed elements. DELIBERATELY DISTINCT
    # from OK: a caller must not be able to read "success" and assume completeness.
    WRITTEN_WITH_GAPS = "written_with_gaps"
    # Written, and a bound was applied. The bound is stated IN the document (FR-027).
    TRUNCATED = "truncated"

    # ── refusals: these are disclosure controls, not validation niceties ──
    REFUSED_UNATTRIBUTED = "refused_unattributed"
    REFUSED_UNTYPED = "refused_untyped"
    REFUSED_TEMPLATE = "refused_template"
    REFUSED_MERGED_STATUS = "refused_merged_status"

    NOT_FILLABLE = "not_fillable"
    OUTPUT_UNWRITABLE = "output_unwritable"
    SOURCE_MISSING = "source_missing"


class ValueRefused(ValueError):
    """A value could not be accepted. Carries the outcome so the caller's refusal is
    typed rather than a generic error string."""

    def __init__(self, message: str, outcome: Outcome = Outcome.REFUSED_UNTYPED) -> None:
        super().__init__(message)
        self.outcome = outcome


# ── the three shapes ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TaggedValue:
    """Exactly one of `value` / `unavailable` / `failed` is meaningful, discriminated
    by `kind`."""

    kind: str  # "value" | "unavailable" | "failed"
    value: Any = None
    src: str = ""
    device: str = ""
    as_of: str = ""
    reason: str = ""

    @property
    def is_gap(self) -> bool:
        return self.kind in ("unavailable", "failed")


_ACCEPTED_SHAPES = (
    'accepted shapes are '
    '{"v": <value>, "src": "<tool or system>", "device": "<optional>", "as_of": "<optional ISO-8601>"} '
    'or {"unavailable": "<reason>"} '
    'or {"failed": "<reason>"}'
)

# Deliberately permissive on offset/precision, strict on shape. A date with no time is
# a legitimate as-of; "yesterday" is not.
_ISO = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)


def parse_tagged(raw: Any, field_path: str) -> TaggedValue:
    """Parse one field. Refuses anything that would let missing data look present.

    FR-005c: the caller MUST NOT be able to express a missing value as a plain empty
    string that renders as a blank cell.
    """
    if not isinstance(raw, dict):
        raise ValueRefused(
            f"{field_path}: expected a tagged value, got a bare "
            f"{type(raw).__name__} ({raw!r}). A bare scalar is refused because it "
            f"cannot distinguish 'the source returned this' from 'there was no "
            f"source' — {_ACCEPTED_SHAPES}",
            Outcome.REFUSED_UNTYPED,
        )

    present = [k for k in ("v", "unavailable", "failed") if k in raw]
    if len(present) != 1:
        got = ", ".join(present) if present else "none"
        raise ValueRefused(
            f"{field_path}: exactly one of 'v', 'unavailable' or 'failed' must be "
            f"present, found {got}. {_ACCEPTED_SHAPES}",
            Outcome.REFUSED_UNTYPED,
        )

    tag = present[0]

    if tag in ("unavailable", "failed"):
        reason = raw[tag]
        if not isinstance(reason, str) or not reason.strip():
            raise ValueRefused(
                f"{field_path}: '{tag}' requires a reason. An unavailable with no "
                f"reason is a blank wearing a label — it tells the eventual reader "
                f"nothing they could not have guessed from an empty cell",
                Outcome.REFUSED_UNTYPED,
            )
        return TaggedValue(kind=tag, reason=reason.strip())

    # tag == "v"
    src = raw.get("src")
    if not isinstance(src, str) or not src.strip():
        raise ValueRefused(
            f"{field_path}: a value requires 'src' naming the tool or system it came "
            f"from. An unattributed figure in a durable artefact is not renderable — "
            f"it looks authoritative and cannot be checked (FR-007)",
            Outcome.REFUSED_UNATTRIBUTED,
        )

    as_of = raw.get("as_of", "") or ""
    if as_of and not _ISO.match(str(as_of)):
        raise ValueRefused(
            f"{field_path}: 'as_of' must be ISO-8601, got {as_of!r}. An unparseable "
            f"as-of is worse than none: it looks like a date and is not one",
            Outcome.REFUSED_UNTYPED,
        )

    return TaggedValue(
        kind="value",
        value=raw["v"],
        src=src.strip(),
        device=str(raw.get("device", "") or "").strip(),
        as_of=str(as_of).strip(),
    )


# ── rendering ───────────────────────────────────────────────────────────────

EMPTY_MARKER = "(empty)"
UNAVAILABLE_PREFIX = "NOT AVAILABLE"
FAILED_PREFIX = "RETRIEVAL FAILED"

# Every string a gap must never render as. This list IS the requirement (FR-001) and
# is asserted at runtime rather than only in a test, because a document that ships a
# plausible blank has already done the damage by the time a test would catch it.
_FORBIDDEN_GAP_RENDERINGS = {"", "-", "--", "n/a", "na", "none", "null", "0", "tbd", "unknown"}


def render_tagged(tv: TaggedValue) -> str:
    """The display string. FR-001: a gap never renders as a plausible blank."""
    if tv.kind == "value":
        if tv.value is None:
            # A caller sent {"v": null, "src": ...}. That is a source reporting a null,
            # not a missing field — say so rather than printing "None".
            return "(null)"
        if isinstance(tv.value, str) and tv.value == "":
            return EMPTY_MARKER
        if isinstance(tv.value, bool):
            return "true" if tv.value else "false"
        return str(tv.value)

    if tv.kind == "unavailable":
        out = f"{UNAVAILABLE_PREFIX} — {tv.reason}"
    else:
        out = f"{FAILED_PREFIX} — {tv.reason}"

    # Runtime guard, not decoration. If a future edit lets a gap collapse to something
    # that reads as data, this raises at generation time instead of shipping.
    if out.strip().lower() in _FORBIDDEN_GAP_RENDERINGS:
        raise ValueRefused(
            f"internal: a {tv.kind} value rendered as {out!r}, which reads as data "
            f"rather than as an absence (FR-001)",
            Outcome.REFUSED_UNTYPED,
        )
    return out


def render_source(tv: TaggedValue) -> str:
    """The visible attribution string. Never hidden — FR-008a rules out cell comments,
    tooltips and document properties as the mechanism, because they are collapsed by
    default, stripped on paste, and absent in print."""
    if tv.kind == "unavailable":
        return "— (no data)"
    if tv.kind == "failed":
        return "— (retrieval failed)"
    parts = [tv.src]
    if tv.device:
        parts.append(tv.device)
    return " · ".join(parts)


def render_as_of(tv: TaggedValue) -> str:
    """The SOURCE's own as-of, kept distinct from the document's generation time
    (FR-010). Data collected on Monday and rendered on Friday is a Monday fact."""
    if tv.kind != "value":
        return ""
    return tv.as_of or "(not stated by source)"


# ── disagreement (FR-027b) ──────────────────────────────────────────────────

@dataclass
class Disagreement:
    """Two sources reporting different values for the same label. Both are rendered
    with their own origins; neither is dropped and no winner is picked."""

    label: str
    values: list[TaggedValue] = field(default_factory=list)

    def caveat(self) -> str:
        srcs = ", ".join(sorted({v.src for v in self.values if v.src}))
        return (
            f"{self.label}: sources disagree ({srcs}). Both values are shown with "
            f"their origins; NetClaw has not reconciled them"
        )


def find_disagreements(labelled: list[tuple[str, TaggedValue]]) -> list[Disagreement]:
    """Group by label and report any label where two attributed values differ.

    A document that hides a disagreement asserts a certainty the data does not support,
    which is the same failure as fabricating — just quieter.
    """
    by_label: dict[str, list[TaggedValue]] = {}
    for label, tv in labelled:
        if tv.kind == "value":
            by_label.setdefault(label, []).append(tv)

    out: list[Disagreement] = []
    for label, values in by_label.items():
        distinct = {str(v.value) for v in values}
        distinct_srcs = {v.src for v in values}
        if len(distinct) > 1 and len(distinct_srcs) > 1:
            out.append(Disagreement(label=label, values=values))
    return out
