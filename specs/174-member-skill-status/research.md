# Research

- Routing: `RiskRouter.candidates()` keeps routable members whose `scope` covers the
  capability; `specialty_capabilities()` and the peer card's risk aggregate
  (`InventoryBuilder`, `risk_aggregate`) read the same `scope` column. None consult the
  member's runtime.
- The member already sends `n2n/inventory` to the Border right after connecting
  (`service.py`, `local_inventory()`), stored in `member.health.inventory`. Two tests pin
  that the connection's calls end with that one inventory message.
- A member knows its scope as names (`N2N_MEMBER_SCOPE`, `FederationService.member_scope`).
  Every scope name except the base floor (`n2n-member-runtime`, `self-status`, served by
  the member daemon) is a workspace skill name: `in2n-profiles.py` matches skill
  directories by prefix or exact name.
- `openclaw skills check --agent <id> --json` (OpenClaw 2026.10.9) returns `workspaceDir`,
  `eligible`, `missingRequirements` (`{name, missing: {bins, anyBins, env, config, os}}`),
  `disabled`, `blocked`, `agentFiltered` and `notInjected`. It takes about 2.5 s.
- `openclaw skills check` calls the gateway's `skills.status` first. It falls back to a
  local evaluation only when the gateway is unavailable or wants credentials
  (`canFallbackToImplicitLocalGateway`). Run with a member's environment it reached the
  Border's gateway on 18789 and failed with "gateway token mismatch"; had the token
  matched, it would have reported the Border process's environment. With
  `OPENCLAW_GATEWAY_PORT` set to an unused port it evaluated the member's own workspace
  and environment.
- `--agent` is required when the home configures several agents;
  `gateway._member_agent_args()` already makes that choice for agent turns.
- A skill folder present in the workspace but in none of the lists was not loaded:
  OpenClaw's defaults are `maxSkillsLoadedPerSource` 200, `maxCandidatesPerRoot` 300,
  `maxSkillsInPrompt` 150, `maxSkillsPromptChars` 18000. The operator's Border workspace
  held 252 skills; OpenClaw listed the first 200 alphabetically.
- Operator Risk, per member, from the check run in each member's environment:
  viz `blender-3d-viz`, `ue5-network-viz`, `uml-diagram`, `threejs-network-viz`;
  pyats 17 `pyats-*` skills (`PYATS_MCP_SCRIPT`); cml `gait-session-tracking`,
  `humanrail-escalation` (disabled); guardian-claw five skills absent from its own
  workspace; `humanrail-escalation` missing its key on four members.
