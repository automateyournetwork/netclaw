# Resume R03 / Spec172

2026-11-03: **technical qualification and cleanup complete; human acceptance
pending.** R01/R02 are complete and accepted. R03 has35/36 tasks closed; T036's
memory/GAIT work is recorded, but human acceptance cannot be inferred from
execution delegation. Do not begin R04 until that gate is accepted.

Read [verification.md](verification.md), [maintainer-handoff.md](maintainer-handoff.md)
and [teardown-review.md](teardown-review.md). The November3 owner delegation in
[activation-delegation.md](activation-delegation.md) resolved earlier spending/
execution questions. Do not ask them again or treat available credit as a target.

## Completed outcome

- Fresh GCP Montréal control-only Border and actual named trusted HTTPS owner HUD;
  four independently approved outbound-iN2N reads from the on-prem member.
- R1/R2/SW1/SW2 each returned IOS17.18.2 from one `show version`, zero setup commands,
  two OpenClaw/Sonnet provider calls, signed results and durable ACKs. Exactly four
  effects/eight provider calls; actual submit/ACK reply loss, same-key service/
  member restart, fresh login and ID-only browser recovery caused no extra effect.
- 62 combined workload/browser/auth checks, actual host/IAM/route/port/metadata
  boundary and finite quota/rate/expiry configuration verified. Actual VM reboot
  and scheduled expiry firing were not tested. Full limits/failures are retained.
- All13 R03 GCP resources, boot disk, DNS A record and temporary OS Login key are
  gone. Actual inventories found zero owned billable residue. Both member workers
  stopped;12 owned stopped containers and4 networks removed. Private homes/evidence,
  images, original inventories and R01 remain preserved.
- R03 existed for under one hour; prorated base estimate CAD0.035 excludes traffic,
  tax, model/secret operations and R01. Actual invoice/credit balance is unknown.
  R01 continues to run and retains its existing costs. R03 hostname is retired.

## Authoritative state and evidence

Branch `172-gcp-hybrid-border` preserves accepted R02 `96cbdf0f`. Runtime source
through `aa861ee3` was deployed from frozen snapshot `fbd41cb1`; November3 changed
private configuration/helpers and maintainer records, not production source.
Source1.18.3/extension1.5.0 unchanged. Do not publish, bump, tag, release, merge a
public rollout recipe or deploy this as a general user cloud Border. Entire
issue310 release hold lasts through R20, including user controls in R15–R17.

Private evidence root: `~/.local/share/netclaw/roadmap-r03-20261102/`.
Actual run: `activation-20261103/`; verification.md indexes the receipts.
Authoritative `foundation-review-20261102T215532Z/r03.tfstate` is now empty,
SHA256 `2a736c2bd6d0fff4bcf2f58cd9cfc2e52d9cdff07c01f30496acedf2a1944455`.
R01 state remains serial6,
SHA256 `62364e466434974c6b4f55c395ef95a9376113aa9fcf4d44518511a160643fbf`.
Never replay initial foundation/activation plans, operator payloads or enrollment.

`activation-20261103/final-preservation/current-r03-state.tar` is the verified
current-state archive, SHA256
`3f9fe622b119b3285532760532bdaee66ffd66b0e87a077b0650076eea432d46`.
It contains private keys/owner state and must remain private. It is preservation,
not an activation payload. Prepared `cloud-runtime-staging/bootstrap-fbd41cb1-final`
is older initial state; never restore it over current records. All failed
browser/export/observer attempts remain alongside the accepted continuation.
R02's unknown/spent operation remains intact and must never be replayed.

GAIT branch `roadmap-r03-activation-20261103` retains delegation `e700f381`,
foundation/network review `b77cd3cf` and final technical/cleanup `1869ca6e`.
Private `activation-20261103/gait-final-log.json` and `memory/2026-11-03.md` retain the session trail. Use
`/Users/john.capobianco/gait_mcp/venv/bin/python` with repository gait-stdio.py;
ambient Python3.14 cannot import GAIT. No MemPalace connector was exposed.

All parallel lanes are complete. Existing private worktrees are retained under
`worktrees/{hud,protocol,cloud,enrollment}`; their source was integrated already.
R02 used passes1–2 and R03 used source/preparation pass3 of the maximum five;
no automatic Ralph hook ran. No device/model action is authorized by retrying a
failed observer or by a new browser session.

## Next gate

Only human R03 acceptance remains. After explicit acceptance, close T036 and use
[the R04 brief](../../docs/roadmap/issue-310/briefs/R04-gcp-cloud-member-netbox.md)
for cloud NetBox/subnet members with a hosted model. Recheck the next free spec
number at kickoff. R05 adds Ollama members. Their resource/runtime plans and
actual qualification remain separate; nothing here starts them or qualifies
arbitrary LLM/harness/cloud combinations.
