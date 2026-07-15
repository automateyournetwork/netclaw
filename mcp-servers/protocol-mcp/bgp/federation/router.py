"""iN2N Border routing: capability match → deterministic member selection.

The Border turns an operator request into work on the right Member. Selection
is deterministic (FR-012/FR-011; research R5): among active members whose scope
covers the requested capability, pick the most-specific specialist (fewest
SPECIALTY capabilities — base floor excluded per FR-021b), tie-broken by
lexicographic member_id. Reuses the member registry from RiskManager. The
actual delegation is done by the Invoker over the internal channel.
"""

import logging

from .risk import (
    RiskManager, STATE_ACTIVE, STATE_ENROLLED, STATE_UNREACHABLE, STATE_PROVISIONED,
)

logger = logging.getLogger("n2n.router")

# Members eligible for routing. active/enrolled = trusted+ready; unreachable =
# was live, invoker re-dials; PROVISIONED = a registered cold/on-demand member
# the Border will cold-start on first route (ensure_member_up). quarantined/
# removed are never routable.
_ROUTABLE_STATES = (STATE_ACTIVE, STATE_ENROLLED, STATE_UNREACHABLE, STATE_PROVISIONED)


class NoCapableMember(Exception):
    """Raised when no member in the risk covers the requested capability (FR-011)."""


class RiskRouter:
    def __init__(self, risk_manager: RiskManager):
        self.rm = risk_manager

    def candidates(self, capability: str) -> list:
        """Routable members whose scope covers `capability`."""
        return [
            m for m in self.rm.list_members()
            if m["state"] in _ROUTABLE_STATES and self.rm.covers(m, capability)
        ]

    def select_member(self, capability: str) -> dict:
        """Deterministically select the member to handle `capability`.

        Raises NoCapableMember if none match (the Border reports plainly and does
        NOT attempt the work itself, FR-011).
        """
        cands = self.candidates(capability)
        if not cands:
            risk = self.rm.get_risk().get("risk_name") or "this risk"
            raise NoCapableMember(
                f"No member in risk '{risk}' can perform '{capability}'.")
        # Deterministic tie-break (FR-012):
        #   1) most-specific: fewest SPECIALTY capabilities (base floor excluded, FR-021b)
        #   2) lexicographically smallest member_id
        cands.sort(key=lambda m: (self.rm.specialty_count(m["scope"]), m["member_id"]))
        chosen = cands[0]
        logger.info("Routed capability '%s' → member %s (of %d candidates)",
                    capability, chosen["member_id"], len(cands))
        return chosen

    def route(self, capability: str) -> dict:
        """Convenience wrapper returning a structured result for the daemon."""
        try:
            m = self.select_member(capability)
            return {"member_id": m["member_id"], "profile": m.get("profile"),
                    "state": m["state"]}
        except NoCapableMember as e:
            return {"error": "IN2N_ERR_NO_CAPABLE_MEMBER", "message": str(e)}
