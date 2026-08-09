"""Per-plane credentials from the environment. Spec 080, FR-028/FR-029/FR-030.

Principle XIII: secrets live in the environment, never in source or config.

The rule that matters most here is FR-029 — a missing variable is reported **by
name, never by value**, and that includes exception text. Error strings are where
credentials usually leak, because the code that formats them is written in a hurry
and never reviewed as a disclosure surface.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from envelope import Plane

#: Environment variable names per plane. Nine variables total; one server backs
#: all three skills, so there is one command variable, not one per skill.
PLANE_ENV: dict[Plane, tuple[str, str]] = {
    Plane.MANAGER: ("FORTIMANAGER_HOST", "FORTIMANAGER_API_TOKEN"),
    Plane.DEVICE: ("FORTIGATE_HOST", "FORTIGATE_API_TOKEN"),
    Plane.ANALYZER: ("FORTIANALYZER_HOST", "FORTIANALYZER_API_TOKEN"),
}

VERIFY_SSL_ENV = "FORTINET_VERIFY_SSL"
ALLOW_WRITES_ENV = "FORTINET_ALLOW_WRITES"


class MissingCredential(RuntimeError):
    """A required variable is unset.

    The message names variables and nothing else. Never interpolate a value into
    this exception — it is rendered into tool output and the audit trail.
    """

    def __init__(self, plane: Plane, names: list[str]) -> None:
        self.plane = plane
        self.names = names
        super().__init__(
            f"The {plane.value} plane is not configured: set "
            f"{' and '.join(names)}. No value is shown here by design."
        )


@dataclass(frozen=True)
class PlaneCredentials:
    plane: Plane
    host: str
    token: str
    verify_ssl: bool

    def __repr__(self) -> str:  # pragma: no cover - defensive
        # A dataclass would otherwise print the token in tracebacks and REPLs.
        return f"PlaneCredentials(plane={self.plane.value!r}, host={self.host!r}, token='<redacted>')"

    __str__ = __repr__


def verify_ssl() -> bool:
    """TLS verification, on unless explicitly disabled. FR-030.

    Fortinet appliances ship self-signed certificates, so this path is exercised
    rather than theoretical. Disabling verification exposes the API token to
    interception, which is why it must be a deliberate per-deployment choice and
    never a silent default — the posture both community servers also take.
    """
    raw = os.environ.get(VERIFY_SSL_ENV, "true").strip().lower()
    return raw not in ("false", "0", "no", "off")


def writes_allowed() -> bool:
    """Read-only unless explicitly opted out of. FR-019.

    Note this is only the *first* of three checks on the write path. Enabling it
    does not authorise a write — human approval and an approved change record are
    separate, independently required gates (FR-020).
    """
    raw = os.environ.get(ALLOW_WRITES_ENV, "false").strip().lower()
    return raw in ("true", "1", "yes", "on")


def load(plane: Plane) -> PlaneCredentials:
    """Read one plane's credentials, or raise naming what is missing."""
    host_var, token_var = PLANE_ENV[plane]
    host = (os.environ.get(host_var) or "").strip()
    token = (os.environ.get(token_var) or "").strip()

    missing = [name for name, val in ((host_var, host), (token_var, token)) if not val]
    if missing:
        raise MissingCredential(plane, missing)

    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"

    return PlaneCredentials(
        plane=plane,
        host=host.rstrip("/"),
        token=token,
        verify_ssl=verify_ssl(),
    )


def configured_planes() -> list[Plane]:
    """Planes with both variables set.

    An estate may legitimately run FortiGates with no FortiManager, or no
    FortiAnalyzer at all. An absent plane is a deployment fact, not a failure —
    what matters is that NetClaw says which planes it could not consult (FR-007)
    rather than answering as though it had.
    """
    found = []
    for plane, (host_var, token_var) in PLANE_ENV.items():
        if os.environ.get(host_var) and os.environ.get(token_var):
            found.append(plane)
    return found
