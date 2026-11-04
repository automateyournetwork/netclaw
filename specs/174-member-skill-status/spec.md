# Spec 174: The Border stops routing skills a member cannot load

Created 2026-11-04; branch `174-member-skill-status`, on 1.18.4; status: implementation
and verification. Found on an operator Risk while checking why a member's scoped skills
failed.

## Problem

The Border routes a request, and advertises a capability to peers, from the member's
**scope**: the skill names recorded when the member was provisioned. Whether the member's
own OpenClaw will load that skill is never checked. OpenClaw withholds a skill whose
declared requirements are missing ("Skill … is not available to this agent"), one its
config disables, and one past its per-source load limit. The Border still routes it there.

On the operator Risk, the pyats member was scoped for 18 skills and could load one: its
`.env` lacked `PYATS_MCP_SCRIPT`. Across the running members, OpenClaw refused scoped skills
for four reasons: missing settings, `skills.entries` disabling them, a skill folder
absent from the member's workspace, and skills on disk that were never loaded because the
workspace held more than OpenClaw's default 200 skills per source. Every one was routable.
A request routed there either fails inside the member after a model turn or, before spec
171, could come back with a substitute answer.

## User scenarios and acceptance

1. P1: After connecting to the Border, a member asks its own OpenClaw which of its scoped
   skills it will not load, and reports them with the reason and the names of any missing
   requirements. The check runs against the member's own workspace and environment, not
   the Border's.
2. P1: The Border does not route a skill to a member that reported it cannot load it. If
   another member can, that member is chosen. If none can, the request is refused at once
   with "It is in scope, but no member's runtime can load it."
3. P1: The risk's advertised skills (the peer capability card) and the list of routable
   capabilities leave out a skill that no member can load.
4. P2: The Border logs each reported skill with the member, reason and missing
   requirement names, so the operator can fix it.
5. P2: Nothing changes when a member does not report: an older member, a Hermes member, or
   a check that fails or times out. Routing stays scope-based.

## Boundaries

- Routing only. Authorization (`covers`, `in_scope`) stays scope-based; a member can only
  remove itself from candidates, never add a skill.
- Reports carry names only: skill names, reason codes, and requirement names (environment
  keys, binaries, config paths). Never values. Peers never see member ids or requirement
  names; refusals to them say only that the skill is in scope but unloadable.
- The member reports once per connection. Its environment and config only change across a
  restart, which reconnects. For the few seconds before the report arrives, routing is as
  before.
- A member runs no gateway, and `openclaw skills check` asks the configured gateway first,
  which on a member is the Border's. The member points the check at an unused local port so
  OpenClaw evaluates locally. This relies on OpenClaw's documented local fallback.

Found and not changed:

- NetClaw ships 239 workspace skills; OpenClaw loads at most 200 per source by default
  (`skills.limits.maxSkillsLoadedPerSource`), and at most 150 in the prompt. On every
  install the alphabetically last ~39 skills are never loaded on the Border. Raising the
  limit interacts with the prompt limits, so it is left for a separate decision.
- OpenClaw's tool search sometimes leads a smaller model to call a `tool_call` wrapper
  instead of the tool it needs (see verification).
