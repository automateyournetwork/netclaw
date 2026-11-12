# Spec 192: Guardrails for three high-impact skill actions

Created 2026-11-12; branch `192-skill-guardrails`, on 1.22.0; status: implementation
and verification. The three rules have run in an operator Border's workspace copies of
these skills since October 2026.

## Problem

Three skills name an action with a large effect but leave the agent to decide when it
applies:

- `n2n-federation` says to confirm `n2n_kill` with the operator, but not when to
  propose it. It severs federation with a peer (revokes consent, drops the channel,
  purges the cached inventory). Proposing it for a dead endpoint or a slow peer
  offers a destructive fix where `n2n_forget_endpoint` is the right one.
- `protocol-participation` says lab mode (`NETCLAW_LAB_MODE=true`) relaxes the CR
  requirement and must not be set in production, but not who sets it. An agent that
  sets or suggests it to get past the CR gate removes the gate it is meant to respect.
- `pyats-config-mgmt` lets an emergency change bypass the CR approval gate but gives
  no test for what counts as an emergency.

## Requirements

- FR-001: `n2n-federation` lists when to propose `n2n_kill` (malicious or corrupted
  data the agent can see, an operator request, a revoked peer that keeps connecting)
  and when not to (connectivity or a dead endpoint, pointing to `n2n_forget_endpoint`;
  a slow peer; a general question). A proposal names the peer and the evidence and
  says restoring needs a new `n2n_consent`.
- FR-002: `protocol-participation` says only the operator sets lab mode, in `.env`;
  the agent never sets or exports it, treats route mutations as production unless it
  is already `true`, and does not suggest enabling it unless asked about lab mode.
- FR-003: `pyats-config-mgmt` qualifies an emergency only when all three hold: the
  outage, incident or exploited vulnerability is affecting production now; the operator
  has confirmed the urgency in the conversation; the fix is a single change that can be
  rolled back. Otherwise the standard CR workflow applies. A qualifying emergency
  records in GAIT which conditions held and the evidence.
- FR-004: Skill descriptions are unchanged, so routing and skill-limit budgets do not
  move; the catalog's skill digests are regenerated.

## Out of scope

Enforcing these rules in code (the MCP servers already gate on CRs and lab mode at
their own level); the `servicenow-change-workflow` emergency process, which stays as is;
other skills.
