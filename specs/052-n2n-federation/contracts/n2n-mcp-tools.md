# Contract: n2n-mcp Operator Tools

**Feature**: 052-n2n-federation | **Server**: `mcp-servers/n2n-mcp/server.py`
(FastMCP, stdio) | **Pattern**: thin proxy over daemon `/n2n/*` (like
protocol-mcp → 8179, commit d6e2cb2). Registered in `config/openclaw.json` as
`n2n-mcp`.

The gateway agent uses these tools to answer operator asks like
"does Nicholas's claw have CML?", "ask Byrn's claw about its OSPF flap",
"let Nicholas run my cml list tool".

## Tools

| Tool | Args | Behavior |
|---|---|---|
| `n2n_status` | — | Federation overview: identity, peers, states, staleness |
| `n2n_consent` | `peer, display_name?` | Consent to federate (FR-001). Reminds the operator to confirm the peer's AS/router-id out-of-band before calling |
| `n2n_kill` | `peer` | Kill switch (FR-004). Destructive → requires explicit operator confirmation in conversation before the agent calls it |
| `n2n_peer_capabilities` | `peer, query?` | Peer inventory (optionally filtered); always includes staleness (FR-009) |
| `n2n_compare_capabilities` | `peer` | Diff: what they advertise that we lack, and vice versa |
| `n2n_set_visibility` | `item_type, item_name, visibility, peers?` | Control what we advertise (FR-006) |
| `n2n_grant` | `peer, target_type, target_name, requires_approval?` | Allowlist a tool/skill for a peer (FR-012/FR-013) |
| `n2n_revoke_grant` | `grant_id` | Remove a grant |
| `n2n_list_grants` | `peer?` | Current allowlist |
| `n2n_invoke` | `peer, target_type, target_name, arguments?, input_text?` | Invoke a remote tool (`target_type=tool`, `arguments`) or delegate a skill (`target_type=skill`, `input_text`). Blocks up to timeout, returns result or explicit refusal code. Results are presented as untrusted remote data (FR-016) |
| `n2n_chat` | `peer, message, session_id?` | Send one claw-to-claw message; returns the streamed reply text and `session_id` for continuation (FR-019) |
| `n2n_approvals` | — | List pending inbound approval requests |
| `n2n_approve` / `n2n_deny` | `approval_id` | Resolve an approval from any connected channel (research R6) |
| `n2n_audit` | `peer?, limit?` | Recent invocation/chat audit records (FR-015/FR-022) |
| `n2n_config` | `peer, chat_enabled?, budgets…` | Per-peer chat toggle, budget and rate overrides |

## Response conventions

- All responses serialize via the repo's GCF serializer (`_gcf_dumps`) like
  protocol-mcp — token-optimized, JSON fallback.
- Refusals surface the wire error code verbatim (`not_allowlisted`,
  `budget_exhausted`, …) so the agent can explain precisely why.
- Every result from a remote peer is wrapped with
  `{"source": "<peer identity>", "trust": "remote-untrusted", ...}` so the
  agent's context always shows provenance (FR-016).

## SKILL.md

`workspace/skills/n2n-federation/SKILL.md` documents the operator workflows
(federate, browse, grant, invoke, chat, sever) over these tools, per
Constitution VII/XII.
