"""Capability & version negotiation (feature 053, US4).

Federated claws run different OpenClaw builds. Rather than assume a fixed agent
CLI flag or reply shape (which broke silently — --session-key vs --session-id,
payloads vs finalAssistantVisibleText), each claw:
  1. probes its OWN local environment once (cached), and
  2. advertises a capability descriptor in n2n/hello.
The requester adapts to the peer's descriptor; a peer that sends none is treated
as pre-053 (052 baseline) — graceful degrade (FR-016).
"""

import logging
import subprocess

logger = logging.getLogger("n2n.negotiate")

PROTO_VERSION = "053"
FEATURES = ["async_tasks", "endpoint_reannounce", "negotiate"]

_local_descriptor = None  # cached — probe once per process (FR-014, do not re-probe per call)


def _probe_agent_invoke() -> str:
    """Which session flag does the local `openclaw agent` accept? Probe --help
    once. Prefer --session-id (broadest support); fall back to --session-key."""
    try:
        out = subprocess.run(["openclaw", "agent", "--help"],
                             capture_output=True, text=True, timeout=15).stdout
        if "--session-id" in out:
            return "session-id"
        if "--session-key" in out:
            return "session-key"
    except Exception as e:
        logger.debug("agent flag probe failed (%s) — defaulting to session-id", e)
    return "session-id"


def local_descriptor() -> dict:
    """Build (and cache) this claw's capability descriptor."""
    global _local_descriptor
    if _local_descriptor is None:
        _local_descriptor = {
            "proto_version": PROTO_VERSION,
            "features": list(FEATURES),
            "agent_invoke": _probe_agent_invoke(),
            "reply_shapes": ["finalAssistantVisibleText", "payloads"],
        }
        logger.info("Local capability descriptor: %s", _local_descriptor)
    return _local_descriptor


def normalize(descriptor) -> dict:
    """A peer that sent no descriptor is pre-053 → 052 baseline (graceful degrade)."""
    if not descriptor or not isinstance(descriptor, dict):
        return {"proto_version": "052", "features": [], "agent_invoke": "session-key",
                "reply_shapes": ["payloads"]}
    return {
        "proto_version": descriptor.get("proto_version", "052"),
        "features": descriptor.get("features", []),
        "agent_invoke": descriptor.get("agent_invoke", "session-key"),
        "reply_shapes": descriptor.get("reply_shapes", ["payloads"]),
    }


def peer_supports(peer_descriptor, feature: str) -> bool:
    return feature in normalize(peer_descriptor).get("features", [])


# Two-tier admission (reconciled from Josh/TunnelMind's report): a consented peer
# that proved no key is admitted at attestation "self-asserted" (tier-0) —
# federated for presence + inventory ONLY. Every execution / impersonation /
# state-changing surface requires a possession-proven ("possession") session:
# tool + async-skill invocation, endpoint redirection, and chat (which runs the
# local gateway agent under the peer's identity).
TIER0_DENIED = frozenset({
    "tools/call", "tasks/submit", "endpoint_update", "chat/open", "chat/message",
    "knowledge/query",
})


def allows(attestation: str, operation: str) -> bool:
    return attestation == "possession" or operation not in TIER0_DENIED
