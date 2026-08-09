"""Response envelope — the structural guarantee this feature exists to provide.

Spec 080, FR-005/FR-006/FR-007/FR-009/FR-023.

Fortinet is three planes and they are not substitutes for one another:

    manager   FortiManager   what policy is *intended* across the estate
    device    FortiGate      what a box is *actually* doing right now
    analyzer  FortiAnalyzer  what traffic *actually hit* the policy

A rule present on a FortiGate but absent from its FortiManager policy package is
an out-of-band change. FortiManager's database is intent; the device's running
config is state; they legitimately diverge between installs. Reporting one as the
other is the failure mode this module prevents.

WHY THIS IS A CHOKEPOINT AND NOT A HELPER
-----------------------------------------
The clarification that produced FR-005 asked where attribution is enforced. Prose
in a SKILL.md is a *request to the model*; a field every response must carry is a
*guarantee*. A helper that tools may call is a convention someone eventually
forgets. `emit()` is the only way to produce a response, so omission is not
possible rather than merely discouraged.

The same argument applies to the GAIT audit record (Principle IV, NON-NEGOTIABLE:
"No operation MAY execute silently"). /speckit.analyze found FR-023 with a
verification task and no implementation — the identical defect it caught in spec
076, where Principle III was recorded as "inherited" with nothing behind it.
Verification of an unimplemented guarantee passes only by accident. So auditing
happens here, in the one place every response passes through.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Plane(str, Enum):
    """Which appliance produced an answer. Never a caller-supplied parameter."""

    MANAGER = "manager"
    DEVICE = "device"
    ANALYZER = "analyzer"


class Outcome(str, Enum):
    """Distinguishable results.

    Collapsing any two of these is the error class this feature is built around,
    and the one spec 078 ("no advisories != not vulnerable") and spec 079
    ("no probes != outage") each fought in their own domain.
    """

    OK = "ok"

    # Queried successfully, nothing matched. NOT an error, and critically NOT
    # evidence that a rule is unused — a retention window is not all of history.
    NO_LOGS_IN_WINDOW = "no_logs_in_window"
    EMPTY_RESULT = "empty_result"

    # The appliance did not answer. MUST NOT be filled in from another plane.
    PLANE_UNREACHABLE = "plane_unreachable"

    # An expired session reported as "no policies exist" would be a silent,
    # plausible, wrong answer. It is an authentication condition.
    AUTH_EXPIRED = "auth_expired"
    AUTH_MISSING = "auth_missing"

    # Write refusals. These are THREE distinct values on purpose. A single
    # "not authorised" would reproduce exactly the conflation /speckit.analyze
    # caught in spec 076: human approval and an approved change record are
    # different gates, and neither substitutes for the other.
    REFUSED_READ_ONLY = "refused_read_only"
    REFUSED_NO_APPROVAL = "refused_no_approval"
    REFUSED_NO_CHANGE_RECORD = "refused_no_change_record"

    # Scope could not be established. An error, never an unqualified result.
    SCOPE_INDETERMINATE = "scope_indeterminate"


#: Scope keys each plane must supply. A manager result without its ADOM is
#: ambiguous (package names are unique only within an ADOM); a device figure
#: without its VDOM is ambiguous; a log result without its window is meaningless.
REQUIRED_SCOPE: dict[Plane, tuple[str, ...]] = {
    Plane.MANAGER: ("adom",),
    Plane.DEVICE: ("device", "vdom"),
    Plane.ANALYZER: ("window_start", "window_end"),
}


class ScopeError(ValueError):
    """Raised when a response cannot name the scope that makes it unambiguous."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_scope(plane: Plane, scope: dict[str, Any] | None) -> dict[str, Any]:
    """Return a validated scope or raise. FR-009.

    Missing scope is an error rather than an omission, because an unqualified
    result reads as authoritative while being ambiguous — the more dangerous of
    the two failures.
    """
    scope = dict(scope or {})
    missing = [k for k in REQUIRED_SCOPE[plane] if not scope.get(k)]
    if missing:
        raise ScopeError(
            f"{plane.value}-plane response is missing required scope "
            f"{', '.join(missing)}; an unqualified result is not reportable"
        )
    return scope


def emit(
    plane: Plane,
    *,
    source: str,
    scope: dict[str, Any] | None = None,
    data: Any = None,
    outcome: Outcome = Outcome.OK,
    message: str | None = None,
    notes: list[str] | None = None,
    tool: str = "",
) -> dict[str, Any]:
    """Build the one response shape every tool returns, and audit it.

    `plane` is passed by the calling module, never accepted from a caller —
    a manager tool cannot claim to speak for the device (FR-006).
    """
    notes = list(notes or [])

    if outcome in (Outcome.AUTH_MISSING, Outcome.PLANE_UNREACHABLE, Outcome.AUTH_EXPIRED):
        # These fail before a query runs, so there is no scope to report and
        # demanding one would turn a clear diagnosis into a confusing one.
        validated: dict[str, Any] = dict(scope or {})
    else:
        try:
            validated = _validate_scope(plane, scope)
        except ScopeError as exc:
            outcome = Outcome.SCOPE_INDETERMINATE
            message = str(exc)
            validated = dict(scope or {})
            data = None

    response: dict[str, Any] = {
        "plane": plane.value,
        "scope": validated,
        "source": source,
        "retrieved_at": _utc_now(),
        "outcome": outcome.value,
        "data": data,
        "notes": notes,
    }
    if message:
        response["message"] = message

    audit(tool=tool, response=response)
    return response


def unreachable(plane: Plane, source: str, reason: str, *, tool: str = "") -> dict[str, Any]:
    """A plane did not answer. FR-007.

    The caller MUST NOT substitute another plane's data. A device that did not
    respond is not described by the manager's intended configuration for it.
    """
    return emit(
        plane,
        source=source,
        outcome=Outcome.PLANE_UNREACHABLE,
        message=f"The {plane.value} plane did not respond: {reason}",
        notes=[f"No data was returned for the {plane.value} plane; it was not consulted successfully."],
        tool=tool,
    )


# --------------------------------------------------------------------------
# Audit trail — Principle IV (NON-NEGOTIABLE), FR-023
# --------------------------------------------------------------------------

#: Substrings whose values never appear in an audit record. The audit trail is a
#: disclosure surface too, and error strings are where credentials usually leak.
_SECRET_HINTS = ("token", "key", "password", "secret", "session", "cookie", "apikey")


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
    """Record one operation. Every response, including refusals.

    Writes JSON Lines to `FORTINET_AUDIT_LOG` (default: the GAIT trail directory).
    Records the shape of the operation, never its payload — a policy package can
    be large and an audit trail is not a data store.

    A write failure is surfaced on stderr rather than swallowed: an unaudited
    operation violates Principle IV whether or not the tool call itself worked.
    """
    record = {
        "ts": response.get("retrieved_at") or _utc_now(),
        "component": "fortinet-mcp",
        "tool": tool or "<unnamed>",
        "plane": response.get("plane"),
        "scope": _redact(response.get("scope")),
        "source": response.get("source"),
        "outcome": response.get("outcome"),
    }
    if response.get("message"):
        record["message"] = response["message"]

    path = os.environ.get("FORTINET_AUDIT_LOG") or os.path.expanduser(
        "~/.openclaw/gait/fortinet-mcp.jsonl"
    )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError as exc:
        # Deliberately loud. Silence here would mean operations executing with no
        # audit record, which Principle IV forbids outright.
        print(
            f"[fortinet-mcp] AUDIT WRITE FAILED ({exc}) for tool={record['tool']} "
            f"plane={record['plane']} outcome={record['outcome']}",
            file=sys.stderr,
            flush=True,
        )
