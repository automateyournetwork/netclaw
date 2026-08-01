"""Platform-first routing: which server should answer for a given device.

Spec 076 FR-009 through FR-012. Ratified in spec.md "The layering decision".

The rule, and the one exception that makes it non-trivial:

    Cisco IOS/XE/NXOS/XR ......... pyats       (owns it)
    Juniper Junos ................ junos-mcp   (owns it)
    Everything else .............. this server (owns it)

    EXCEPTION: cross-vendor NORMALIZED READS are permitted here even on
    platforms another server owns — because NAPALM returns one shape across
    vendors and no other server can answer "compare BGP neighbours across
    Cisco AND Arista AND Nokia" at all.

Why the exception needs writing down: NAPALM also supports IOS and Junos. So
"use the dedicated server for Cisco" is an incomplete rule — it leaves
cross-vendor questions unassigned, and two servers answering the same question
in different shapes is worse than a gap.

**Writes stay single-pathed.** Reads may overlap; writes may not. That asymmetry
is not tidiness — Principle I requires device state be verified rather than
assumed, and Principle VIII requires post-change verification. Both become
unenforceable the moment "verified by which tool?" has two answers for one
platform. So this module refuses writes it is technically capable of performing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SERVER_ID = "multivendor-cli"

# Platforms owned by a dedicated server, and which one. Reads are permitted here
# for these (normalized only); writes are not.
OWNED_ELSEWHERE: dict[str, str] = {
    "cisco_ios": "pyats",
    "cisco_xe": "pyats",
    "cisco_iosxe": "pyats",
    "cisco_nxos": "pyats",
    "cisco_xr": "pyats",
    "cisco_iosxr": "pyats",
    "juniper_junos": "junos-mcp",
    "juniper": "junos-mcp",
}

# Why each owning server is richer for its own platform — surfaced in refusals so
# the message teaches rather than merely blocks.
OWNER_RATIONALE: dict[str, str] = {
    "pyats": "pyATS/Genie has ~2000 parsers and state snapshot/diff for Cisco platforms",
    "junos-mcp": "junos-mcp uses PyEZ/NETCONF natively for Junos",
}


class Operation(str, Enum):
    NORMALIZED_READ = "normalized_read"   # NAPALM getter — allowed everywhere
    RAW_READ = "raw_read"                 # raw CLI — only for unowned platforms
    WRITE = "write"                       # config change — only for unowned platforms


@dataclass(frozen=True)
class Decision:
    permitted: bool
    owning_server: str          # who owns this platform
    reason: str | None = None   # populated when refused

    @property
    def refused(self) -> bool:
        return not self.permitted


def owner_of(platform: str | None) -> str:
    """Which server owns this platform. This server owns anything unclaimed."""
    return OWNED_ELSEWHERE.get((platform or "").lower(), SERVER_ID)


def route(platform: str | None, operation: Operation) -> Decision:
    """Decide whether this server may perform `operation` on `platform`."""
    owner = owner_of(platform)

    if owner == SERVER_ID:
        return Decision(True, SERVER_ID)

    # Platform belongs to a dedicated server.
    if operation is Operation.NORMALIZED_READ:
        # The deliberate exception (FR-008): cross-vendor normalized reads are
        # this server's unique capability, so they are permitted read-only even
        # on someone else's platform.
        return Decision(True, owner)

    rationale = OWNER_RATIONALE.get(owner, "")
    if operation is Operation.WRITE:
        reason = (
            f"platform {platform!r} is owned by the {owner!r} server; this server is "
            f"read-only for it so that every platform has exactly one write path"
            + (f" ({rationale})" if rationale else "")
        )
    else:
        reason = (
            f"platform {platform!r} is owned by the {owner!r} server; use it for "
            f"single-device work"
            + (f" ({rationale})" if rationale else "")
            + ". This server answers cross-vendor normalized reads for this platform."
        )
    return Decision(False, owner, reason)


def refusal_payload(device: str, platform: str | None, decision: Decision) -> dict:
    """Refusal shaped per contracts/mcp-tools.md.

    A refusal is a SUCCESSFUL call carrying a refusal result — never a protocol
    error — so the agent can read why and route elsewhere instead of retrying
    blindly (FR-045 / contract "Refusal semantics").
    """
    return {
        "device": device,
        "platform": platform,
        "server": SERVER_ID,
        "status": "refused",
        "refused_reason": decision.reason,
        "owning_server": decision.owning_server,
    }
