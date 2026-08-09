"""The chokepoint. Spec 082, FR-005a/005b, FR-006..FR-010, FR-034.

EVERY response this server produces passes through emit() or refused(). There is no
other exit. That is what makes provenance and GAIT structural rather than a convention
a writer is asked to follow — the pattern specs 080 and 081 used, applied to a format
that outlives the session.

Audited by inspection 2026-08-03 (task T024): the four writers construct bytes and hand
them back; only server.py calls emit()/refused(); output.reserve() is the sole path that
creates a file, and every caller of it returns through emit(). No writer imports
`audit` directly.

Two things a caller CANNOT do, by construction:

  1. Set generated_at or generated_by. They are stamped here (FR-005b), so a document
     cannot claim to have been produced at a time of the caller's choosing.
  2. Report a gapped document as clean. emit() recounts the gaps from the ledger and
     forces WRITTEN_WITH_GAPS, so "ok" always means complete.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from outcomes import Outcome
from provenance import DocumentStamp, SourceLedger, utc_now

COMPONENT = "document-mcp"


class ProvenanceError(RuntimeError):
    """A document was about to be emitted with nothing to attribute it to. Raised, not
    logged — an unattributed artefact is not shippable."""


def emit(
    *,
    tool: str,
    outcome: Outcome = Outcome.OK,
    artifact: dict[str, Any] | None = None,
    ledger: SourceLedger | None = None,
    stamp: DocumentStamp | None = None,
    data: Any = None,
    caveats: list[str] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    caveats = list(caveats or [])

    # FR-007, mirroring spec 081's source guard. An artefact with an empty ledger has
    # no nameable origin, which is the exact failure this feature exists to prevent.
    if artifact is not None and (ledger is None or ledger.is_empty):
        raise ProvenanceError(
            f"tool {tool!r} produced a document with no nameable source. An "
            f"unattributed document is not emittable — it looks authoritative and "
            f"cannot be checked (FR-007)"
        )

    gaps = ledger.gaps if ledger else {"unavailable": 0, "failed": 0}

    # A caller cannot report a gapped document as clean.
    if artifact is not None and outcome is Outcome.OK and any(gaps.values()):
        outcome = Outcome.WRITTEN_WITH_GAPS

    if stamp is not None and stamp.truncated and outcome in (Outcome.OK, Outcome.WRITTEN_WITH_GAPS):
        outcome = Outcome.TRUNCATED
        caveats.append(stamp.truncation_text())

    if any(gaps.values()):
        caveats.append(
            f"{gaps['unavailable']} field(s) had no data and {gaps['failed']} "
            f"retrieval(s) failed. Both are stated explicitly in the document — this "
            f"document is incomplete and says so"
        )

    response: dict[str, Any] = {
        "source": COMPONENT,
        "tool": tool,
        "generated_at": stamp.generated_at if stamp else utc_now(),
        "generated_by": stamp.generated_by if stamp else None,
        "outcome": outcome.value,
        "artifact": artifact,
        "sources_consulted": (
            [
                {
                    "src": r.src,
                    "device": r.device or None,
                    "as_of": r.as_of or None,
                    "element_count": r.element_count,
                    "status": r.status,
                }
                for r in ledger.records
            ]
            if ledger
            else []
        ),
        "gaps": gaps,
        "caveats": caveats,
    }
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message

    audit(tool=tool, response=response)
    return response


def refused(
    *,
    tool: str,
    reason: str,
    outcome: Outcome,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A refusal. Produces NO artifact and is audited exactly like a success —
    the GAIT trail must show what NetClaw declined as well as what it did."""
    response = {
        "source": COMPONENT,
        "tool": tool,
        "generated_at": utc_now(),
        "outcome": outcome.value,
        "artifact": None,
        "sources_consulted": [],
        "gaps": {"unavailable": 0, "failed": 0},
        "caveats": [],
        "message": reason,
    }
    if query:
        response["query"] = query
    audit(tool=tool, response=response)
    return response


_SECRET_HINTS = ("token", "key", "password", "secret", "session", "cookie", "apikey", "auth")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("<redacted>" if any(h in k.lower() for h in _SECRET_HINTS) else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def audit(*, tool: str, response: dict[str, Any]) -> None:
    """One JSON line per call, success or refusal. FR-034.

    Called from inside emit() and refused(), never by a caller — the defect
    /speckit.analyze caught in specs 076 and 080 was GAIT having verification but no
    implementation, and a chokepoint is the only way that cannot recur.
    """
    record = {
        "ts": response.get("generated_at") or utc_now(),
        "component": COMPONENT,
        "tool": tool or "<unnamed>",
        "outcome": response.get("outcome"),
        "artifact_path": (response.get("artifact") or {}).get("path")
        if isinstance(response.get("artifact"), dict)
        else None,
        "sources": [s.get("src") for s in response.get("sources_consulted", [])],
        "gaps": response.get("gaps"),
    }
    if response.get("message"):
        record["message"] = response["message"]
    if response.get("query"):
        record["query"] = _redact(response["query"])

    path = os.environ.get("DOCUMENT_AUDIT_LOG") or os.path.expanduser(
        "~/.openclaw/gait/document-mcp.jsonl"
    )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError as exc:
        print(
            f"[document-mcp] AUDIT WRITE FAILED ({exc}) for tool={record['tool']} "
            f"outcome={record['outcome']}",
            file=sys.stderr,
            flush=True,
        )
