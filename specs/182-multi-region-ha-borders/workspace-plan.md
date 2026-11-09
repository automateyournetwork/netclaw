# R09 workspace plan: the full NetClaw workspace on the HA Borders

Status: **plan plus tooling, nothing deployed.** No VM, DNS record, service or secret was touched. The Border and HUD services on gen4
are unchanged. Local verification is listed at the end.

## 1. What the owner sees today, and why

The three HA Borders serve the *protected control-only HUD*: identity, cluster authority (with region and role), and Approved
operations. `/api/runtime` carries no `capabilities.remoteHud`, so VS Code shows only the Cloud Border identity document and the
Prepare/Recover Cloud Read commands. That is the R08 design (Border controls approvals; members execute), not a defect of the deployment.

The standalone GCP Border the owner used (R04a, specs 172-175, old VM `netclaw-r01-20261101`) adds a second component: a normal NetClaw HUD
backend behind the protected edge. The protected server already supports this: `protected-server.js` reads `config.workspace {path, sha256}`,
`remote-hud.js` validates it, and the edge proxies only an exact route map to `workspace.upstream`. The extension turns on Overview, Chat,
Canvas, Members, Peers, Skills, Runtime, Tokenomics, Documentation, Reference, Logs and Operations when `/api/runtime` advertises
`capabilities.remoteHud` with those features (`extensions/netclaw-vscode/src/views/owner.ts`, `client/remote-hud.ts`).

## 2. How the standalone Border does it (specs/174 owner-delivery.md)

- Protected edge and federation run as one UID (10010) with loopback HUD/API; Caddy terminates public TLS.
- The normal HUD and the OpenClaw conversation gateway run as a second UID (10011) with a private conversation home. They share that UID
  and are not isolated from each other. Only the gateway receives the Anthropic provider environment.
- OpenClaw 2026.7.1-2, Sonnet 4.6, explicit open-lab mode ("Unauthenticated lab operator"), 13 workspace features, metadata-server and
  legacy-secret access denied for the conversation UID, no arbitrary MCP/shell/device-write route on the chat path.
- Edge config and backend config are the same schema-1 JSON read by two UIDs (`conversationHome` must differ from the Border home; the upstream
  port must differ from the ingress port; both require open-lab).

## 3. Architecture per VM (identical on nne1, ew1, ase1)

| Component | UID | Listens | Unit | Notes |
|---|---|---|---|---|
| HA Border role | `nc182` | 7443 (NCFED, internal), 7444 (iN2N, public via DNAT), 8444 (edge WS, loopback) | `nc182-border` | unchanged |
| Public ingress + protected HUD | `nc182` | 443 public; product server on an ephemeral loopback port | `nc182-hud` | `hud_ingress_r09.mjs`; gains the pinned `workspace` entry |
| Workspace backend (`ui/netclaw-visual/server.js`) | `nc182ws` (new) | 127.0.0.1:3001 | `nc182-wshud` | env `NETCLAW_OPEN_LAB_WORKSPACE_CONFIG`; sees only the gateway token |
| OpenClaw gateway | `nc182ws` | 127.0.0.1:18789 | `nc182-gateway` | pinned `openclaw@2026.7.1-2`; the only unit that loads the provider key |

Files: edge copy `/var/lib/nc182/workspace/workspace.json` (0600, `nc182`) and backend copy `/var/lib/nc182ws/workspace.json` (0600,
`nc182ws`) are byte-identical (the product pins and re-reads raw bytes). Conversation home `/var/lib/nc182ws/home` (0700, `nc182ws`) holds
`openclaw.json`, `workspace/`, `netclaw-hud/`. Frozen sources: `/opt/nc182/netclaw` (backend tree, root-owned, read-only) and
`/opt/nc182/openclaw`. Secrets: `/etc/nc182/ws-token.env` (generated on the VM, never printed) and `/etc/nc182/provider.env`
(owner step), both `root:root 0600`, loaded by systemd.

Request path: browser/VS Code -> `https://<node>.automateyournetwork.com` -> ingress front checks (Host/Origin/size) -> loopback product server
(exact route map, 409/404 for anything else) -> `http://127.0.0.1:3001` backend -> `openclaw gateway call` -> gateway -> Anthropic.
Approved-operations and cluster routes stay with the protected server; the backend never sees them.

Default features: `overview chat canvas members peers skills runtime tokenomics documentation reference logs operations`. **`rag` is excluded**:
it needs `rag-mcp` (torch/chroma/sentence-transformers) and a proxied upload larger than the ingress's 1 MiB body bound. The list is validated
against the product's own `REMOTE_HUD_FEATURES` (canvas requires chat).

What each panel will honestly show: Overview/Runtime/Skills/Documentation/Reference/Logs/Tokenomics come from the backend's own home.
Members/Peers come from the backend's own federation state (it runs no daemon), so expect empty or "unavailable"; the HA authority, region and
leader view stays in the protected cluster panel. Chat/Canvas are real Sonnet turns. Conversations are **per Border** and not replicated
across failover (R08 stated browser chat/session state is not replicated).

## 4. Model and the owner's key

`labs/ha/r09_workspace.py render --model ...` writes the conversation `openclaw.json`: loopback gateway, token by `${OPENCLAW_GATEWAY_TOKEN}`
reference, one model. Default `anthropic/claude-sonnet-4-6` (the R04a-qualified pairing with the pinned OpenClaw). Sonnet 5.5 needs OpenClaw to
know that model id; 2026.7.1-2 predates it and the latest (2026.11.2) was never qualified here. That is a decision (D4).

Key placement: `scripts/ha-r09-place-provider-key.sh <code> <env-file>` reads `ANTHROPIC_API_KEY` from a file in-process and streams it over the IAP
ssh channel into `/etc/nc182/provider.env` (0600 root). It is not run by the agent, the value never reaches argv, logs or a local copy, and the
repo never contains it. Exposure after placement: the key lives on three internet-facing VMs, in the gateway process environment (readable by
`nc182ws` and root). The HUD is an **unauthenticated open-lab surface**: anyone who can reach a Border URL can spend the key through Chat.
Mitigations I recommend: a dedicated key with a provider-side spend cap; firewall 443 restricted to the owner's IPs while the workspace is on;
rotate and delete the key at teardown.

## 5. Changes to existing tooling

Done in this change set (uncommitted):
- `labs/ha/hud_ingress_r09.mjs`: optional `workspace {path}` input, pinned as `workspace {path, sha256}` in `ingress.json` and `hud.json`
  (absent = exact old shape); `loadOwned` requires hud and ingress to agree; new `frontTimeout` so chat (`POST /api/chat` 600 s,
  `/api/n2n/chat` 330 s, conversation open 135 s, other workspace routes 90 s) is not cut by the 30 s loopback idle bound. Protected-operation,
  owner, mobile and cluster routes keep 30 s. +2 tests (54/54 pass).
- `labs/ha/r09_vm_hud.py`: includes `workspace` in the ingress input when `/var/lib/nc182/workspace/workspace.json` exists.
- `labs/ha/r09_workspace.py` (`render`, `pack`, `features`) and `tests/n2n/test_ha_r09_workspace.py` (16 pass).
- `scripts/ha-r09-vm-workspace.sh` (`install`, `configure`, `start`) and `scripts/ha-r09-place-provider-key.sh`.

Not needed: any extension change (`remoteHud` is already consumed), any manifest/schema change, any change to the Border role or its
`openclaw.json == {"netclaw":{"controlOnly":true}}` rule, which applies to the protected role home only. The conversation home is a different tree,
and `remote-hud.js` refuses a conversation home equal to the Border home.

## 6. Risks

1. **Public unauthenticated chat spends the owner's key** (section 4). Highest.
2. **Chat has no DefenseClaw guard**, as on the R04a Border; the guarded path is the protected member path, unchanged. The gateway config declares no
   tools, but the exact OpenClaw config keys for "no tools/MCP/shell" are validated only when the gateway first starts (open item).
3. **Same-UID gateway/HUD**: the HUD process can read the gateway's `/proc/<pid>/environ`, so the provider key is reachable by backend code
   (same as R04a). Separate UIDs are possible but the HUD reads shared conversation-home state; left as an option.
4. **Memory**: an e2-medium has 4 GB. Border (python) + etcd (1 GiB cap) + ingress/product node + backend node + OpenClaw gateway is tight.
   Expect to watch RSS; resizing to e2-standard-2 is an owner call (D5).
5. **Read-only backend tree**: `server.js` also uses its repo `ROOT` (docs, `SOUL.md`, skills). It is frozen read-only; any write there fails closed.
   Unknown until first start.
6. **Body bound**: the ingress's 1 MiB request cap blocks Canvas attachments and RAG upload; acceptable for chat.
7. The Borders' authority path is untouched, but CPU contention can lengthen admission elapsed time, which is already inside a narrow window
   (see live-evidence.md). Enable on one Border first and re-run an operation.
8. Per-Border chat history is lost if a VM is rebuilt; conversation homes are not in the HA state.

## 7. Ordered build list

| # | Step | Effort | Needs owner |
|---|---|---|---|
| 0 | Decisions D1-D8 below | - | yes |
| 1 | Render per-node configs (`render`, installation id from the gen summary) and `pack` the backend tree at a pinned commit | 15 min | pinned commit |
| 2 | Pilot on **one** Border (suggest nne1, leader-independent): scp artifacts, `install`, `configure`, owner places key, `start`; re-run `r09_vm_hud.py` (HUD restart only; Border service untouched) | 60 min | D1, D2, D7 |
| 3 | Verify via the extension's `discoverCloudBorder`: `remoteHud` features appear; open Overview; one Chat turn (one provider call); one Canvas; confirm 404 for `rag`; run one protected operation to confirm authority path unaffected | 30 min | - |
| 4 | Roll to the other two Borders in parallel | 30 min | pilot accepted |
| 5 | Evidence into live-evidence.md; teardown notes (delete key, units, users) | 20 min | - |

Gen4 can be upgraded in place (only `nc182-hud` restarts); a new generation is not required.

## 8. Decisions needed from the owner

- D1: approve enabling an unauthenticated Chat surface on public Borders using your Anthropic key.
- D2: a dedicated, spend-capped key, and either the path of an env file containing it (I stream it, never read it) or you run the placement script.
- D3: restrict 443 to your IPs during this (give them), or keep 0.0.0.0/0.
- D4: Sonnet 4.6 on the qualified OpenClaw 2026.7.1-2 (recommended), or Sonnet 5.5 on a newer unqualified OpenClaw.
- D5: accept e2-medium memory, or resize to e2-standard-2 (about +$0.07/h each).
- D6: confirm `rag` stays out (default), or accept the heavy rag-mcp install and the upload-size change.
- D7: pilot one Border first (recommended) or all three at once.
- D8: the pinned source commit for the backend tree (default current HEAD) and whether any OpenClaw version override is approved.

## 9. Verification performed (no deployment)

- `node --test labs/ha/hud_ingress_r09.test.mjs`: 54/54 (52 prior + 2 new).
- `pytest tests/n2n/test_ha_r09_workspace.py` (python3.10): 16/16, including the real product `readRemoteHudConfig` (edge) and
  `resolveRemoteHudBackend` (backend) accepting the rendered files and refusing a tampered edge copy.
- Local smoke: the real `ui/netclaw-visual/server.js` started against a rendered backend config answered `/api/runtime` with
  `remoteHudBackend {schema 1, features}`, allowed `/api/chat/models`, and returned 404 for `/api/rag/stats` (feature excluded).
- `bash -n` on both scripts. **Not exercised:** the install/configure/start scripts on a VM, the gateway start with the pinned OpenClaw
  and this `openclaw.json`, a real Chat turn, `ingress prepare` with a real Border home carrying a workspace entry, or the full HUD test suite.
