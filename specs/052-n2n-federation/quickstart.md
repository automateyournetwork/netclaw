# Quickstart: N2N Federation

**Feature**: 052-n2n-federation
**Cast**: John (AS 65001, 4.4.4.4) federating with Nicholas (AS 65007, 7.7.7.7),
both already mesh-peered (BGP Established — the live state as of 2026-07-10).

## 0. Prerequisites (both sides)

- NetClaw mesh peering up (`curl -s 127.0.0.1:8179/status` shows the peer
  Established) — see `~/.openclaw/restore-peering.sh`.
- `N2N_ENABLED=true` in `~/.openclaw/.env`, daemon restarted.

## 1. Federate (mutual consent — FR-001)

Confirm identities out-of-band first (Slack: "you're AS 65007 / 7.7.7.7?").

John, in his NetClaw session:
> "Federate with Nicholas — AS 65007, router-id 7.7.7.7"
(agent calls `n2n_consent(peer="as65007-7.7.7.7", display_name="Nicholas")`)

Nicholas, on his side:
> "Federate with John — AS 65001, 4.4.4.4"

The instant both consents exist, the lower-AS side (John) opens the NCFED
channel on the existing mesh endpoint, `n2n/hello` exchanges, and inventories
flow. HUD claw nodes flip from *not federated* to *federated*.

## 2. Browse capabilities (FR-005/FR-009)

> "What can Nicholas's claw do?" / "Does Nicholas have CML?"
(`n2n_peer_capabilities`) — answers locally, with inventory age shown.

> "What skills does Nicholas have that I don't?"
(`n2n_compare_capabilities`)

## 3. Grant and invoke (FR-012/FR-013)

Nicholas allowlists one tool for John:
> "Let John's claw run my CML lab list"
(`n2n_grant(peer="as65001-4.4.4.4", target_type="tool", target_name="cml-mcp/list_labs")`)

John invokes it:
> "List the labs on Nicholas's CML server"
(`n2n_invoke(...)` → runs on Nicholas's claw with his credentials, result
returns attributed and marked remote-untrusted)

Approval-gated variant: Nicholas adds `requires_approval=true`; John's request
pings Nicholas on Slack; Nicholas replies "approve it" (`n2n_approve`); result
flows. Unanswered → expires denied after 15 min.

## 4. Claw-to-claw chat (FR-018/FR-019)

Both enable chat (`n2n_config(peer=…, chat_enabled=true)`), then:
> John: "Ask Nicholas's claw why its OSPF area 0 is flapping"
(`n2n_chat` → Nicholas's gateway agent answers with its own tools/policies;
reply streams back attributed to `as65007-7.7.7.7`)

## 5. HUD (FR-023–026)

Open http://localhost:3000 → click Nicholas's claw node → expanded panel shows
skills, tools, badges (CML, pyATS…), freshness, pending approvals, and a Chat
button. Byrn's node (not federated) shows state only.

## 6. Sever (FR-004)

> "Kill federation with Nicholas"
(`n2n_kill` — agent confirms first) → channel drops, inventories purge, state
`severed` within 10 s. **BGP stays Established** — verify:
`curl -s 127.0.0.1:8179/status` still shows the peer, HUD keeps the claw node
with a severed badge. Re-federating requires fresh mutual consent.

## Verification checklist (maps to Success Criteria)

| Check | Target |
|---|---|
| Consent→federated wall time | < 5 min (SC-001) |
| Capability query latency | < 5 s (SC-002) |
| Non-allowlisted invoke | explicit refusal, audited both sides (SC-003) |
| Secrets in any N2N payload | none (SC-004 — run the no-secrets test) |
| Tool round-trip | < 30 s (SC-005) |
| Kill switch | < 10 s, BGP unaffected (SC-006) |
| Chat first token | < 15 s (SC-007) |
| HUD reflects changes | < 30 s (SC-008) |
| 24 h three-claw soak | zero N2N-attributable BGP flaps (SC-009) |
