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
