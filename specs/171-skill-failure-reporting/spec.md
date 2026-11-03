# Spec 171: Delegated skills report tool failures

Created 2026-11-03; branch `171-skill-failure-reporting`, on 1.18.3; status:
implementation and verification. Found on an operator Risk whose visualization member
answered three mind-map requests with files it had written by hand.

## Problem

A delegated skill request (Border to member, and federated peer to this claw) asks the
agent to "execute the skill … and return only the result". It says nothing about what to
do when a tool the skill depends on is missing or fails. On the operator Risk the
`markmap-viz` skill's server failed on every call. The member then searched the host for
it for up to 1 h 43 min, installed a package globally, and twice returned the path of a
placeholder SVG it had written itself. The Border recorded each task as `completed` and the
audit log as `in_scope/success`. A requester sees only the reply, so a stand-in made after
a failure is indistinguishable from the skill's result.

## User scenarios and acceptance

1. P1: Every delegated skill request, member and peer, tells the agent that if a tool or
   command the skill needs is missing or fails, it replies with that error and stops, and
   does not substitute output produced another way, such as a file it wrote itself.
2. P1: The instruction comes before the request text, so text in the request cannot pose
   as part of it.
3. P2: Requests are otherwise unchanged: skill name, request text, session, time budget,
   approval handling and trust marking.

## Boundaries

This is an instruction to the model, not enforcement; NetClaw cannot verify that an
answer came from the skill's tools. The failing markmap server is a separate repository
(`automateyournetwork/markmap_mcp`, which the installer clones). Its fix is submitted there
separately.

Found and not changed:

- The installer's readiness discovery lists a component's tools without calling them.
  `markmap` reported ready while every rendering tool failed.
- Member profiles keep only their declared MCP servers natively (`viz`: `blender-mcp`,
  `sketchfab-mcp`). `markmap-viz` and `drawio-diagram` therefore reach their servers
  through `MCP_CALL` and the env slice. That works on current installs, whose runtime
  `.env` holds the generated paths; it fails on an older Border `.env` without them, as on
  the operator Risk.
