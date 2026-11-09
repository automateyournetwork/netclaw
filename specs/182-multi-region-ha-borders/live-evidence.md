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
