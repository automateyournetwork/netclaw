# Spec200 integration closeout — 2026-11-23

**25/30 tasks complete; feature merge remains held.** Source review: [draft PR366](https://github.com/automateyournetwork/netclaw/pull/366). Five actual Google recordings
are delivered. The owner accepted recorded illustrations with documented visual
and event limits, and clarified that the existing Border owns the Genie member.
That acceptance closes the visual scope decision; it does not invent collector,
usage or Google-backed agent evidence. This document supersedes older current-state
headings in the retained loop records.

## Implemented integration

Source version candidate **1.26.0**, VS Code extension **1.6.2**, isolated Genie
component **0.1.0**. Optional `genie-worlds` installation now covers the terminal
installer, `setup.sh`, canonical catalog, native MCP registration, Risk profile,
VS Code setup catalog and documentation, HUD capability card, README/SOUL/TOOLS
and credential-free environment examples. Catalog totals are 117 components,
243 skills and 183 integrations (130 registered, 53 external).

The existing Border owns membership, enrollment, routing and task authority.
The member has its own scoped execution home. Its six MCP controls use a private
loopback backend capability; it receives no Google key, raw snapshot or device
credential. Google session termination and cost reservations belong to the
backend independently of Border/member/browser lifetime. Setup installs the
component but cannot activate paid generation. Static exported videos require
no Google calls on visitor playback.

The custom member specification is named `genie-worlds-member`: the built-in
`genie-worlds` profile ID is reserved by the native specification validator.
The installed source recipe and six-tool stdio discovery were exercised in a
fresh private home. The reviewed real member was subsequently prepared and
enrolled through an existing Border, without replacing or upgrading that Border.

## Actual Border-owned member evidence

Read-only local inspection found the existing Spec162 Border running with one
NetConverter member and Anthropic Sonnet 4.6 configured. An isolated Genie member
was prepared using the supported member-home builder and registered/enrolled by
that Border. Its identity was pinned; the Border routed the actual skill tasks.
The Border's configuration, environment and installation identity hashes remain
unchanged. Its existing member remains present.

The Border's OpenClaw 2026.7.1-2 binary rejected the newer scoped-member schema
before execution. A private OpenClaw **2026.10.9 / Node24.22.1** runtime was installed
for the new member only. Its own database migration completed; tool, workspace,
provider and skill restrictions were checked afterward. A private staging error
had emptied the interpreter record by using the same source/destination; the
record was corrected and actual stdio discovery passed before another agent run.
Earlier failed attempts and truthful missing-tool responses remain recorded.

Actual agent transcript and backend SQLite correlation show exactly one call
each to prepare, start, status, stop and evidence, plus scoped skill reads. The
operator issued a fixture-only review between prepare and start. One original
fixture operation reached active, then the backend terminated it on viewer loss
before the later idempotent stop. It retained terminal evidence and reconciled
zero fixture usage. There were **zero Google provider-create records**. The agent
correctly reported unconfirmed recording, no event and `live_world_proven:false`.
This qualifies native routing/skill/MCP/backend execution in **testing posture**;
it does not qualify production confinement or a Google-backed member run.

Private evidence: `.spec200-local/release-integration/native-member/`, including
review/baseline hashes, registration, pinned enrollment, native tool transcript,
backend ledger, original Border task responses, runtime versions and failures.
The new member/backend were stopped after qualification; no auto-start service
was installed. Their private homes and registration are retained for resumption.

## Read-only collector result

The installed native pyATS inventory was listed. Four frozen minimal testbeds
used the saved strict SSH host keys and pinned pyATS/Genie/Unicon/native read
policy. The detailed profile permits six captures per device, at most two owned
children, 30 seconds per attempt, a 240-second overall bound and 8 MiB evidence.
No setup, configuration or fallback SSH command was permitted.

All four first connection attempts timed out before any raw command output was
captured. The collector retired each device instead of retrying or continuing
its remaining commands. Four capture/cleanup outcomes remain uncertain. A
separate TCP-only diagnostic also timed out for each saved SSH endpoint with
zero authentication attempts and zero commands. This establishes current
transport unavailability, not why the lab is unavailable or its device state.
The sealed 1,011-file production snapshot was not changed or recollected.

Evidence: `.spec200-local/release-integration/native-collector/`. T016/T019 cannot
be closed by the prior snapshot builder or synthetic PTY tests: the public
selected-runtime capability and successful integrated native collection remain
unqualified. No network configuration or CML lifecycle action was taken.

## Google receipts, budget and accepted visual scope

See [production recordings](production-recordings.md) for the independent
synthetic trial, five full 120-second recordings, exact media hashes, provenance,
original-session terminal receipts and known visual/event discrepancies.
The owner accepted those discrepancies as recorded illustrations. Original strict
fidelity failures remain preserved rather than rewritten as passes.

A new read-only lookup of the original first-world interaction still returned
HTTP500. It made zero create calls. All six remote terminal receipts remain
confirmed, with **US$85.552128** fully reserved against the authorized US$100
Google campaign limit. This is not a billed spend figure. Usage/billing is still
unavailable, so no reservation was released and no extra Google trial was run.
Member-model execution is separate from the Google campaign ledger; its token
counts are recorded by the Border and are not represented as settled Google cost.

## Verification

| Check | Result |
| --- | --- |
| Full Genie Node/browser suite after 31-file source-closure update | 182/182 pass, zero skips |
| Full Genie Python suite | 146/146 pass |
| Scoped installation/credential filtering/member spec validation after name fix | 4/4 pass |
| Full setup suite after catalog baseline correction | 277 total: 245 pass, 32 explicitly skipped |
| Member mapping and plan dispatch after routing correction | 52/52 pass |
| HUD suite | 545/545 pass |
| VS Code typecheck/build/tests/package | Builds pass; 221 pass, 3 explicitly skipped; VSIX1.6.2 packaged from2529c777 |
| Byrne PR360 gateway token-resolution tests | 6/6 pass in isolated dependency environment |
| Fresh actual component dependency install + six-tool stdio/backend lifecycle | Pass, fixture only |
| Actual Border/Sonnet/skill/MCP/backend operation | Pass for free fixture in testing posture |
| Actual four-device integrated collector | Four timeouts; not qualified |
| Actual Chrome static gallery playback/seek | All five pass; 120s/720p, mobile layout and HTTP byte ranges verified |
| Catalog metadata/coverage/inventory, dependency and release metadata checks | Pass |
| Workflow skill frontmatter/structure validation | Pass |
| Full Python suite in the freshly installed MCP environment | 146/146 pass with supported Node selected |
| SDD artifact, MCP reconciliation/compatibility/tasks and changed-link checks | Pass |

Private logs retain failed setup attempts, missing test dependencies, stale source
closure failures and the corrected reruns. Passing offline tests do not replace
live qualification. No Mobile client changed. Linux/Windows/WSL live worlds,
production member confinement and physical-host-loss behavior remain unqualified.

## Upstream and remaining gates

Reconciled origin/main **220f79627acd25df25a3a38389edb92dabe428cb** into this branch,
including Byrne Baker PR **#360** (`a4cc75d4`, gateway token re-resolution/log source)
and PR **#359** (Percepxion refresh), preserving upstream source1.25.0 before the
candidate1.26.0 bump. The saved original `198-azure-multicloud-ha` branch remains
at **856bbc883279f4c3584664bfd7b34fe50bc7a57f**. Upstream's unrelated
`198-percepxion-oob-skill-refresh` directory is retained. 199 remains reserved for AWS.

Open tasks:

- **T014:** satisfy the retained usage-evidence criterion; visual scope is now accepted.
- **T016/T019:** finish selected-runtime collector admission/recovery and qualify
  the actual four-device path when its SSH transport is available.
- **T025:** qualify a Google-backed run through the actual member, with an exact
  valid packet and sufficient remaining aggregate allowance. The free fixture
  and earlier standalone Google recordings are separate evidence.
- **T029:** final feature-wide verdict after those gates; the owner's illustration
  acceptance is retained and must not be requested again.

Next implementation step: finish the selected-runtime collector capability and
its durable request envelope using the retained native failure evidence; restore
read-only reachability through the existing selected connection path before
another bounded capture. Reconcile provider usage on original IDs. Do not
regenerate the five videos, replay old packets, bypass a hold or create a new
Border. Merge and resume original Spec198 only after the remaining gates close.

## Source review and handoff

The reviewed source was pushed as2529c777 on `200-genie-network-worlds`, based on
origin/main220f7962. A local-only backup retains earlier unpublished development
commits; the published commit excludes the obsolete private controller address
from the planning brief. Publication-diff checks found no private addresses,
known credential values or tracked `.spec200-local` artifacts. No force push.

Draft PR366 is open; no merge, release/tag or Marketplace publication occurred.
Hosted CI was triggered and was pending at this source handoff. Local VSIX1.6.2
is4,687,969 bytes, SHA256
`a92ad4add7427550a45d9944b00c44848a034bf4f86af8c35c8c05724fc479c6`.
It is a local candidate tied to2529c777, not a published extension.
