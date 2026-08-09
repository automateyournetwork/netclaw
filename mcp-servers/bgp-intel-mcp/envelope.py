"""Provenance envelope and GAIT audit — one chokepoint. Spec 081, FR-019/020/021/022.

Every response passes through `emit()`. There is no other way to produce one.

WHY A CHOKEPOINT AND NOT A HELPER
---------------------------------
FR-019 requires every result carry the source that produced it. FR-022 requires
every operation produce a GAIT record. Both are only *guarantees* if omission is
structurally impossible — a helper that tools may call is a convention someone
eventually forgets.

Spec 080 proved the pattern works, and its `/speckit.analyze` pass proved the
alternative fails: the audit requirement had a *verification* task and no
*implementation* task, and passed review by accident. Verifying an unimplemented
guarantee always passes. So auditing happens here, beside provenance, in the one
place every response must go through.

WHY PROVENANCE IS THE CORE PROPERTY HERE
----------------------------------------
This feature merges five independent public sources of varying freshness and
reliability. "The registry says" is not attributable — RIRs differ, PeeringDB is
self-reported, RIPEstat sees only its own collectors. A result that cannot name
its source is not a weaker answer; it is an unusable one.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from outcomes import Outcome


class ProvenanceError(ValueError):
    """Raised when a response cannot name the source that produced it."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(
    *,
    source: str,
    tool: str,
    query: dict[str, Any] | None = None,
    data: Any = None,
    outcome: Outcome = Outcome.OK,
    message: str | None = None,
    caveats: list[str] | None = None,
    cached: bool = False,
    cache_age_seconds: float | None = None,
) -> dict[str, Any]:
    """Build the one response shape every tool returns, and audit it.

    `source` is the **specific service** that answered — `rpki-validator.ripe.net`,
    `rdap.db.ripe.net` — never a category like "registry". FR-019.
    """
    if not source or not str(source).strip():
        raise ProvenanceError(
            f"tool {tool!r} produced a response with no nameable source; an "
            "unattributed result is not reportable (FR-019)"
        )

    response: dict[str, Any] = {
        "source": source,
        "retrieved_at": _utc_now(),
        "outcome": outcome.value,
        "cached": cached,
        "cache_age_seconds": round(cache_age_seconds, 1) if cache_age_seconds else None,
        "query": dict(query or {}),
        "data": data,
        # Structured, not prose decoration: these statements must survive a model
        # summarising the payload (FR-009/013/016).
        "caveats": list(caveats or []),
    }
    if message:
        response["message"] = message

    audit(tool=tool, response=response)
    return response


def merged(
    *,
    tool: str,
    sections: dict[str, dict[str, Any]],
    query: dict[str, Any] | None = None,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    """Compose a multi-source answer with **per-element provenance**. FR-021.

    Each section keeps the envelope it was created with, so every element carries
    its own source. One collective citation across a merged answer is not
    attribution — a reader cannot tell which part came from where, which is
    exactly the situation this feature exists to prevent.
    """
    response: dict[str, Any] = {
        # The composite itself is attributed to this server; the DATA is
        # attributed per section, below.
        "source": "bgp-intel-mcp (composite)",
        "retrieved_at": _utc_now(),
        "outcome": Outcome.OK.value,
        "query": dict(query or {}),
        "sections": sections,
        "sources_consulted": sorted(
            {s.get("source", "?") for s in sections.values() if isinstance(s, dict)}
        ),
        "caveats": list(caveats or []),
    }
    failed = [
        name
        for name, sec in sections.items()
        if isinstance(sec, dict)
        and sec.get("outcome")
        in (
            Outcome.SOURCE_UNAVAILABLE.value,
            Outcome.SOURCE_REFUSED.value,
            Outcome.VALIDATION_UNAVAILABLE.value,
        )
    ]
    if failed:
        # A failed section is reported WITHIN the report; the report does not fail
        # wholesale, and the failure is never presented as an empty result.
        response["caveats"].append(
            "These sections could not be retrieved and are reported as failures, "
            f"not as absence of data: {', '.join(sorted(failed))}."
        )
    audit(tool=tool, response={**response, "data": None})
    return response


def refused(*, tool: str, query: dict[str, Any], reason: str) -> dict[str, Any]:
    """Locally refused input. FR-028.

    `source` is this server because **nothing left the machine** — that is the
    point of refusing rather than forwarding. Sending a private address to a
    public registry is a disclosure even if the query then fails.
    """
    return emit(
        source="bgp-intel-mcp (local)",
        tool=tool,
        query=query,
        outcome=Outcome.INPUT_REFUSED,
        message=reason,
        caveats=["No request was made to any external service."],
    )


def unavailable(
    *, source: str, tool: str, query: dict[str, Any], reason: str,
    outcome: Outcome = Outcome.SOURCE_UNAVAILABLE,
) -> dict[str, Any]:
    """A source did not answer. FR-011.

    Named, and never rendered as "no record" — a dead API must not look like an
    empty registry.
    """
    return emit(
        source=source,
        tool=tool,
        query=query,
        outcome=outcome,
        message=f"{source} did not answer: {reason}",
        caveats=[
            f"This is a failure of {source}, NOT evidence that no record exists. "
            "The two are different findings."
        ],
    )


# --------------------------------------------------------------------------
# Audit trail — Principle IV (NON-NEGOTIABLE), FR-022
# --------------------------------------------------------------------------

def audit(*, tool: str, response: dict[str, Any]) -> None:
    """Record one operation. Every response, including refusals and failures.

    JSON Lines to `BGP_INTEL_AUDIT_LOG` (default: the GAIT trail directory).
    Records the *shape* of the operation, not its payload — a registry response
    can be large and an audit trail is not a data store.

    Unlike specs 078 and 080 there are no credentials in this feature, so there is
    no redaction concern. The `cached` field is recorded because it answers a
    question the trail otherwise could not: did a request actually leave the
    machine, or was this served locally?

    A write failure is surfaced on stderr rather than swallowed: an unaudited
    operation violates Principle IV whether or not the tool call itself worked.
    """
    record = {
        "ts": response.get("retrieved_at") or _utc_now(),
        "component": "bgp-intel-mcp",
        "tool": tool or "<unnamed>",
        "source": response.get("source"),
        "outcome": response.get("outcome"),
        "query": response.get("query"),
        "cached": response.get("cached", False),
    }
    if response.get("message"):
        record["message"] = response["message"]

    path = os.environ.get("BGP_INTEL_AUDIT_LOG") or os.path.expanduser(
        "~/.openclaw/gait/bgp-intel-mcp.jsonl"
    )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError as exc:
        print(
            f"[bgp-intel-mcp] AUDIT WRITE FAILED ({exc}) for tool={record['tool']} "
            f"source={record['source']} outcome={record['outcome']}",
            file=sys.stderr,
            flush=True,
        )
