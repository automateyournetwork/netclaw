# R09 live evidence (2026-11-09)

Deployment: 3 Borders (e2-medium) at nne1/ew1/ase1, `<code>-<id6>.automateyournetwork.com`, Let's Encrypt EC P-256 per host, etcd 3-voter
(heartbeat 500 ms, election 5000 ms), manifest `admission_ms` 6000, lease 15 s / renewal 5 s. One Mac HA execution member (qwen3:0.6b,
native subnet calculator) attached outbound to all three over iN2N (`attachments: 3`, authenticated).

## Facts observed
- VS Code extension `discoverCloudBorder` (real source, bundled) accepted all three DNS URLs; regions Montreal/Belgium/Singapore; leader Montreal.
- HUD (real headless Chrome, explicit "Trust cluster"): Montreal "holds execution authority"; Belgium/Singapore "forwarding to the Montreal authority".
- Real operation `subnet_calculator 192.0.2.0/26` entering via **Montreal**: 2 inference calls + 1 tool call, independent verification true, durable ACK.
- Same operation entering via **Belgium** (follower forwarded to leader): completed, durable ACK, 62 usable / broadcast 192.0.2.63.
- Operation entering via **Singapore**: member refused inference (`inference_refused`, code not in the public list); Border state `member_admitted`,
  may_have_executed true, member admission row `unknown`. Cause NOT established (model-output refusal vs. WAN timing); no evidence either way yet.
- A further operation is refused (HTTP 409) while that unresolved operation holds the single execution slot. Not reset (owner rule).
- Montreal Border stopped 16:33:26Z: leader moved to Belgium by ~29 s (epoch 8 -> 38), Singapore followed; Montreal restarted and rejoined as follower, no authority reclaim.

## Not done / not claimed
- NetBox, pyATS, CML members (new engineering; see members-plan.md). Hosted-model profile still unqualified.
- Firewall partitions, Border-to-Border NCFED cut, clock steps, fenced-restore phase 2.
- Any operation after the Singapore unknown.

## Finding: admission_ms must be <= 3000 (gen1 Singapore unknown and gen2 Montreal unknown explained)
Both stranded operations show the member's first inference `claimed`, then refused, runner latch `uncertain`, and a Border state of
`member_admitted`. Cause: `ha/model_transport.py` requires `CLOCK_ALLOWANCE_MS < remaining <= 3000` at the model handoff and its in-container
helper hard-codes a 3000 ms budget, while `ha/admission.py` computes `remaining = admission_ms - elapsed`. With the signed `admission_ms`
at 6000 a fast handoff leaves >3000 ms and is refused (the 2 slower handoffs that passed happened to cross 3 s). This was NOT region-specific
(the second stranded operation entered via Montreal). Remedy: sign `admission_ms` 3000 (the R08 qualified value) in a fresh generation (gen3);
the leader stays in Montreal so quorum round trips stay ~106 ms. Consequence to measure and report: with Montreal lost, a Belgium-led state
has Belgium-Singapore quorum (~330 ms) and may refuse admissions (R08 refused at 300 ms); that is a degraded mode, not a claim of availability.

## Correction (gen3): admission_ms 3000 also strands; the real constraint is a window, not a ceiling
Gen3 (admission_ms 3000) stranded the first operation too. The agent log shows the member relay returning `403 inference_refused` right after
the model handoff check. Reading `ha/admission.py`: the admission clock starts at the member's own `begin()` (challenge) and includes the
member->Border network trip and the leader's cross-region etcd commit. `ha/model_transport.py` then needs `250 < admission_ms - elapsed <= 3000`.
So the accepted elapsed window is `[admission_ms-3000, admission_ms-250)`: 6000 -> [3000,5750) failed every handoff under 3 s (the passes were
>=3 s); 3000 -> [0,2750) failed every handoff over 2.75 s. Observed elapsed is ~3 s. Gen4 signs 4500 -> [1500,4250).

## Gen4 (admission_ms 4500): all three entry Borders complete real operations
Names: nne1-3d69b5 / ew1-f37491 / ase1-11d078 .automateyournetwork.com. Mac member `nc182-r09/mac-subnet-899eb3` attached to all three (attachments 3).
`subnet_calculator 192.0.2.0/26` entered via Montreal (completed in 38.7 s incl. polling, 2 inference calls, 1 tool call, independent verification,
durable ACK), via Belgium (completed, durable ACK) and via Singapore (completed, durable ACK); each: 62 usable, broadcast 192.0.2.63. Window theory
confirmed: gen1 6000 / gen2 6000 / gen3 3000 each stranded one operation; gen4 4500 stranded none (3 of 3).

## Gen4 failure tests so far
- Montreal Border process stopped (its etcd voter stayed up): leader moved to **Singapore** in ~20 s (epoch 8 -> 34), not Belgium. Leader election does not
  prefer a low-latency region. Montreal restarted and rejoined as follower. To restore a good leader the Singapore Border was stepped down; Belgium took
  leadership in ~22 s (epoch 36); Montreal and Singapore follow. No operation was run while Singapore led (kept for the degraded test).
- With Belgium leading, an operation entering via Singapore: model call 1 and the tool call finished, model call 2's admission was recorded `unknown`
  (member runner latch `uncertain`), the Border resolved it as `failed` (`executor_failed`, durable ACK, may_have_executed true). Per the elapsed-window
  rule above, the likely cause is the admission elapsed time (member challenge -> Border commit) falling outside [admission_ms-3000, admission_ms-250)
  for the Belgium-led topology; not proven. The member latch stays `uncertain` (not reset). Further operations need a verified recovery or a replacement member.
- Product consequence: the member model handoff accepts a 2.75 s wide elapsed window regardless of admission_ms. WAN admission jitter across regions can
  exceed that, so leader placement changes admission reliability. This needs a product change (decouple the helper budget from the admission window) to be robust.

## Gen4b: replacement member and Border-to-Border NCFED cut (closes R08 limit 1 on a real network)
- The stuck member was retired (archived, never reset) and a replacement `nc182-r09/mac-subnet-bb3c50` was enrolled in a ~30 s Border pause and attached to
  all three Borders; Montreal led again (epoch 64) and a real operation via Montreal completed (durable ACK, 62 usable / broadcast 192.0.2.63).
- Real Border-to-Border NCFED cut: host firewall rules (tagged `nc182-cut`) dropped TCP 7443 between Singapore and Montreal in both directions, mid-flow.
  etcd and authority stayed up (leader Montreal epoch 64 unchanged, observed from both Borders). An operation entering via Singapore was refused with HTTP 503
  before anything was sent to the member (fail-closed, no approval consumed). The cut was removed by exact-spec delete (0 rules remain on both hosts).
  Note: a first probe mis-ran because I shadowed the `cut` command in my shell; the rules were in place and the probe was re-run correctly.

## Full workspace on the HA Borders (owner decision: open access for this short-lived deployment, Sonnet 4.6 on qualified OpenClaw 2026.7.1-2)
Each Border now runs the protected edge plus a workspace backend (`nc182-wshud` upstream on loopback, `nc182-gateway`) under a separate UID. `/api/runtime`
advertises label "NetClaw Border" and features overview, chat, canvas, members, peers, skills, runtime, tokenomics, documentation, reference, logs, operations
(no rag). Four rollout failures were fixed on the way: render output dir, the `conversation-home/` path, missing `scripts/runtime-selection.mjs` in the pack,
stale backend tree skipped by the idempotent install. Two product-config gaps found live: OpenClaw `gateway.http.endpoints.chatCompletions.enabled` must be true
(render template fixed), and the metadata-server REJECT for the conversation UID also blocked DNS (GCE resolves via 169.254.169.254), now ACCEPT udp/tcp 53 only.
A real Chat turn through the Montreal HUD edge to Anthropic Sonnet 4.6 completed ("Border chat is working.", 7.4 s). The Anthropic key sits at /etc/nc182/provider.env
(root 0600) on each VM and must be deleted at teardown; the HUD is unauthenticated open-lab, so anyone with a Border URL can spend that key via Chat.

## Region isolation and degraded quorum (real, host firewall cut of TCP 2379/2380/7443)
- Montreal isolated from Belgium and Singapore on the cluster plane (client ports left up): Montreal reported `no_quorum` (epoch unknown, no leadership claim);
  Belgium and Singapore elected Belgium at epoch 90 in ~30 s. Healed (0 rules left): Montreal rejoined as a follower of Belgium, no reclaim, no split.
- A real operation entering via Belgium during the cut (quorum = Belgium+Singapore, ~330 ms): `dispatch_claimed`, the member's first model admission recorded
  `unknown`, runner latch `uncertain`. So a 2-of-3 quorum across the two far regions cannot complete an admission inside the signed window, as R08 predicted at
  300 ms. This is a degraded mode, NOT an availability claim; it also leaves the member latched.
## NetBox hosted member: first live attempt failed, diagnosed, fixed in source
Member `nc182-r09/netbox-09d4c8` attached (3 attachments). First operation stuck at `dispatch_claimed`: the hosted guard's management API port in the derived
config (18970) did not match the health probe (4001), so `start_guard` gave up with `guard_not_ready` before any admission; the refusal left through an anyio
ExceptionGroup, was recorded `outcome_unknown` and no result was returned. Fixed: r09_member writes api_port 4001; protected_docker unwraps a lone
RuntimeRefused/RuntimeUnknown on the hosted path. The same wrapping exists on the Ollama path (unchanged, needs owner review) and probably explains why earlier
refusals surfaced as `outcome_unknown` instead of a signed refusal.

## NetBox hosted member, live debugging (gen4)
Four real attempts, each peeled one layer: (1) guard api_port 4001 mismatch + silent executor failure (fixed); (2) a signed refusal `agent_produced_no_tool_evidence`
whose real cause was the hosted transport's 13 KB request bound vs the 18.6 KB reviewed NetBox skill context (raised to 128 KiB, hosted path only); the agent then
retried and the inference fence refused with `inference_spent_or_unreconciled`; (3) the request now reaches the guard (admission finished) but DefenseClaw answers
`provider "" is not supported ... traffic blocked` because the hosted guard config was derived from the Ollama config instead of the qualified Anthropic one
(R04a cloud-plan guard-config.yaml); fix in progress. Border behaviour was correct throughout: every failure came back as a signed, durably acknowledged
refusal (after the executor unwrap fix) and the Border/other members were unaffected.
## pyATS member (source/tests only so far)
HA effect admission added around the pyATS call, optional private credential_file, hosted+pyats runtime shape, pyats flavor in r09_member (see pyats-member.md);
CML lab NetClaw-Full-Topo is started with R1 reachable on 192.168.2.201:22. Not yet run live.

## RESULT (gen4, 2026-11-09): all three member kinds complete real operations through all three Borders
Members (Mac, outbound over iN2N, attached to all three Borders): `mac-subnet` (qwen3:0.6b, native calculator), `netbox` (hosted Sonnet 4.6, demo.netbox.dev),
`pyats` (hosted Sonnet 4.6, pyATS 25.2 against CML lab NetClaw-Full-Topo, R1 192.168.2.201). Every row below completed with a durable ACK:
| tool | via Montreal | via Belgium | via Singapore |
|---|---|---|---|
| subnet_calculator 192.0.2.0/26 (62 usable, bcast .63, independently verified) | yes | yes | yes |
| netbox_get_object_by_id dcim.device 27 (dmi01-akron-pdu01, DM-Akron, AP7901) | yes | yes | yes |
| pyats_run_show_command R1 `show version` (IOS 17.18.2, uptime 4 d) | yes | yes | yes |
R1 SSH host key (TOFU from the LAN scan): SHA256:8LjcWvuxSbB8SW/Mt+jC0O+4/WKt6CvfByU0GX6KUX8.
## Findings that needed product-side changes (all flagged for owner review; qualified code touched)
1. NetBox hosted: guard API port; executor refusal unwrap (hosted path only); hosted request bound 13 KB -> 128 KiB (NetBox skill is 18.6 KB); guard config now from the
   qualified R04A Anthropic file (derived Ollama-shaped config was blocked by DefenseClaw: provider "" unsupported).
2. pyATS: HA effect admission added around the pyATS call; optional private credential_file; hosted+pyats runtime shape.
3. Border catalog: members asked concurrently (ha/border.py) and the follower->leader forward timeout raised 5 s -> 15 s (ha/node.py). Before: with 3 members the far follower
   (Singapore) answered 503 (leader catalog ~4 s + WAN > 5 s). After: Montreal 3.1 s, Belgium ~3.7 s, Singapore ~5.9 s catalog with 3 members.
4. Model-handoff admission window: member accepts only 250 < admission_ms - elapsed <= 3000; signed admission_ms 4500 works for Montreal-led admission (~3 s observed); other
   leader placements can fall outside it. Region isolation: a 2-of-3 quorum between the far regions cannot admit (degraded, not available).
## Not claimed
Spend limits/egress filtering on the hosted guard; Anthropic key at /etc/nc182/provider.env on each VM (delete at teardown); HUD is open-lab (anyone with a Border URL can use Chat);
Ollama-path ExceptionGroup wrapping unchanged; Mobile and published VS Code/HUD builds NOT released (release gate stands); teardown not started (owner request + exact resource list needed).

## Teardown (2026-11-09, on the owner's instruction after the G2 screenshot)
Deleted by exact name, then verified empty: GCP project netclaw-506315 — 3 spec-182 VMs + boot disks, 3 static IPs, 3 firewall rules, network nc182-r09 + 3 subnets;
and (owner's explicit choice) the old standalone VM netclaw-r01-20261101 with its disk, 2 reserved IPs, 3 firewall rules, subnet and network (project now has only
the default network). GoDaddy: the 12 spec-182 A records (nne1/ew1/ase1-<id6>); other records untouched. This Mac: member processes, 82 `netclaw-r08-*` containers and 28
networks (all created 2026-11-09, label netclaw.spec=179), all `~/.local/share/netclaw/r09-*` directories incl. the gen1-gen4 evidence archives, the build worktree,
temp files. The Anthropic key on the VMs went with the VMs. Not touched: equinix-*, pyats-mcp, gateway5 containers; the Anthropic/NetBox/GoDaddy values in the
owner's .env files (the owner may rotate them); the lego binary; the nested mcp-servers/netbox-mcp-server clone. The repo docs are now the only record.
