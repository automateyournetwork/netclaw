"""Write gating: read-only default, human approval, ServiceNow CR. FR-019..FR-024.

PORTED FROM `mcp-servers/multivendor-cli-mcp/tools/change.py` (spec 076), whose
module docstring records why it exists:

    "The distinction that took a /speckit.analyze finding to surface: **human
    approval** and a ServiceNow Change Request are distinct gates ... 'inherited
    from the existing approval path' — an assertion with no implementation."

Copied rather than imported: the two servers are separate processes with separate
dependency sets, and 076's version is bound to its own `inventory.Device` type. A
shared package across MCP servers is real future work; inventing one mid-feature
is not.

THE INVARIANT
-------------
Three checks, each with its OWN outcome value:

    FORTINET_ALLOW_WRITES unset  -> refused_read_only
    approved_by missing          -> refused_no_approval
    change_request missing/bad   -> refused_no_change_record

Neither gate can satisfy the other. A single "not authorised" would reproduce
exactly the conflation that /speckit.analyze caught in spec 076, and a caller
that cannot tell *which* gate blocked it cannot fix the right thing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from credentials import writes_allowed
from envelope import Outcome

#: ServiceNow states that count as approved for execution. Matches spec 076.
APPROVED_CR_STATES = {"implement", "scheduled", "-1", "-2"}


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    outcome: Outcome
    message: str


def _sn_env() -> tuple[str | None, str | None, str | None]:
    return (
        os.environ.get("SERVICENOW_INSTANCE_URL"),
        os.environ.get("SERVICENOW_USERNAME"),
        os.environ.get("SERVICENOW_PASSWORD"),
    )


async def check_change_request(cr_number: str | None) -> GateResult:
    """Gate 2: is there a genuinely approved ServiceNow change record?

    An unconfigured ServiceNow reports **unconfigured** and fails closed. Treating
    "I could not check" as "approved" is how an ITSM gate becomes decorative.
    """
    if not cr_number:
        return GateResult(False, Outcome.REFUSED_NO_CHANGE_RECORD,
                          "No ServiceNow change record supplied.")

    url, user, password = _sn_env()
    if not (url and user and password):
        return GateResult(
            False, Outcome.REFUSED_NO_CHANGE_RECORD,
            "ServiceNow is not configured (SERVICENOW_INSTANCE_URL / "
            "SERVICENOW_USERNAME / SERVICENOW_PASSWORD), so the change record "
            f"{cr_number} could not be verified. Unverified is not approved.",
        )

    endpoint = url.rstrip("/") + "/api/now/table/change_request"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                endpoint,
                params={"sysparm_query": f"number={cr_number}",
                        "sysparm_fields": "number,state,short_description,approval"},
                auth=(user, password),
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        records = response.json().get("result") or []
    except httpx.HTTPError as exc:
        return GateResult(
            False, Outcome.REFUSED_NO_CHANGE_RECORD,
            f"Could not reach ServiceNow to verify {cr_number} "
            f"({type(exc).__name__}). Failing closed.",
        )

    if not records:
        return GateResult(False, Outcome.REFUSED_NO_CHANGE_RECORD,
                          f"Change record {cr_number} was not found in ServiceNow.")

    cr = records[0]
    approval = str(cr.get("approval", "")).strip().lower()
    state = str(cr.get("state", "")).strip().lower()
    if approval == "approved" or state in APPROVED_CR_STATES:
        return GateResult(True, Outcome.OK,
                          f"Change record {cr_number} is approved (state={state!r}).")
    return GateResult(
        False, Outcome.REFUSED_NO_CHANGE_RECORD,
        f"Change record {cr_number} exists but is NOT approved "
        f"(state={state!r}, approval={approval!r}).",
    )


async def evaluate(
    *, approved_by: str | None, change_request: str | None, is_lab: bool = False
) -> GateResult:
    """Run all three checks in order. FR-019/FR-020/FR-020a/FR-024.

    `is_lab` exempts ONLY the change-record gate, never the approval gate. And a
    device that cannot be classified is treated as **production** — inherited
    from spec 076, on the reasoning that misclassifying production as lab permits
    an unauthorised change, while the reverse costs one change record.
    """
    if not writes_allowed():
        return GateResult(
            False, Outcome.REFUSED_READ_ONLY,
            "Writes are disabled. This server is read-only by default; set "
            "FORTINET_ALLOW_WRITES=true to enable the write path. Note that "
            "enabling it does not authorise a write — it only makes the two "
            "gates reachable.",
        )

    if not approved_by:
        return GateResult(
            False, Outcome.REFUSED_NO_APPROVAL,
            "Missing gate 1 of 2: no human approval. Supply `approved_by` with "
            "the name of the person authorising this change. A change record "
            "does NOT substitute for human approval.",
        )

    if is_lab:
        return GateResult(
            True, Outcome.OK,
            f"Approved by {approved_by}. Lab device: the change-record gate is "
            "waived, but the operation is still audited (Principle III).",
        )

    cr = await check_change_request(change_request)
    if not cr.allowed:
        return GateResult(
            False, cr.outcome,
            f"Missing gate 2 of 2: {cr.message} Human approval from "
            f"{approved_by} is present but does NOT substitute for an approved "
            "change record.",
        )

    return GateResult(True, Outcome.OK,
                      f"Both gates satisfied: approved by {approved_by}; {cr.message}")


def describe() -> dict[str, Any]:
    """Current posture, for skills and operators to report without attempting a write."""
    url, user, password = _sn_env()
    return {
        "writes_enabled": writes_allowed(),
        "servicenow_configured": bool(url and user and password),
        "gates": [
            {"gate": 1, "name": "human approval", "parameter": "approved_by",
             "waived_for_lab": False},
            {"gate": 2, "name": "approved ServiceNow change record",
             "parameter": "change_request", "waived_for_lab": True},
        ],
        "note": "Both gates are required independently. Neither satisfies the other.",
    }
