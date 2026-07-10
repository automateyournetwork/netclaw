"""NetClaw N2N Federation (feature 052).

Elevates the NetClaw Mesh from route exchange to agent federation: consenting
peers exchange capability inventories, invoke allowlisted tools/skills, and chat
claw-to-claw over the NCFED channel multiplexed on the existing mesh port.

Modules:
  manager       consent state machine, SQLite persistence, peer registry
  channel       NCFED framing, handshake, JSON-RPC 2.0 dispatcher
  inventory     build/filter/advertise capability inventories
  authorization grants, budgets, rate limits, approvals (US2)
  invocation    inbound tool/skill execution (US2)
  chat          claw-to-claw chat sessions (US3)
  audit         dual-side audit records
"""

from .manager import FederationManager, PeerState

__all__ = ["FederationManager", "PeerState"]
