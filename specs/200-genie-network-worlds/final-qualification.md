# Spec200 final integration qualification — 2026-11-24

The owner requested completing the three remaining integration checks. The
existing Border owns the Genie member; no new Border was created. The five
accepted 120-second Google recordings and their sealed source snapshot remain
unchanged. This record supersedes the November23 open-gate checkpoint, while
preserving its failed attempts and unresolved billing.

## Selected-runtime collector

`collection_request.py` provides operator-owned admission and a closed local
metadata response around the existing capture-once collector. It binds the
selected Python environment, native read policy, source hashes, parser version,
frozen inventory/endpoints and private per-device credential files. Credentials
use the existing literal dotenv reader and enter only the selected child process;
ambient dotenv discovery is disabled. No member gains device credentials or
collection authority.

SQLite commits the original request before collection. Same-ID retries return the
stored result; changed input conflicts. Owner loss becomes unknown and prevents
new collection admission. No capture is resumed or replayed. Each child has its
own process-group deadline, including after parent loss. Raw capture precedes
disconnect and detached parsing. The public response contains observation/source
identities, timestamps, hashes, outcomes and opaque evidence references, never
raw output, parsed payloads, credentials or filesystem paths.

The actual R1/R2/SW1/SW2 run completed **24/24 observed, parsed reads**: version,
interface summary, LLDP detail, CDP detail and two interface samples per device.
Native logs showed exactly one planned command per capture, zero terminal setup
or configuration commands, and confirmed local cleanup for all24. All raw hashes
and snapshot/source bindings verified. Repeating the original request returned
the identical result with zero additional device commands. November23 connection
timeouts remain retained; the new collection does not rewrite them as success.

The initial successful path was followed by a final qualification after using
the canonical dotenv reader:24/24 parsed reads,78,273raw bytes, zero unknown capture/cleanup outcomes. Final results and source hashes are retained under
`.spec200-local/final-qualification/collector/`. No CML lifecycle, configuration,
SSH trust or frozen production-snapshot change occurred. The broader routed-lab
command archive remains a separately collected historical source, not an implicit
expansion of this bounded six-read profile.

## Actual Border → agent → skill → MCP → Google

The existing `spec162-border/genie-worlds-member` reauthenticated with its pinned
identity. It used its isolated OpenClaw2026.10.9/Node24.22.1 runtime and configured
Sonnet4.6 model. The existing Border configuration, environment and identity were
preserved. Enforcement is the recorded **testing posture**, not a claim of
production confinement or broader platform qualification.

Actual agent transcripts and backend state correlate:

- One `genie_world_prepare`, then an exact operator review for the same synthetic
  projection. The viewer's review draft and member's preparation draft have
  distinct local references but the same verified projection hash.
- One `genie_world_start`, through the real MCP, and exactly one Google create.
- Actual Chrome display, deliberate movement and different baseline/navigation
  frames; a12,186,128-byte WebM with final-flush acknowledgement.
- Member status, stop and evidence calls against the original operation.
- An initial pending stop followed by the worker's five-second receipt timeout.
  Reconciliation of that same provider ID returned `interaction.cancelled`;
  zero replacement creates and zero repeated setup/events.
- A subsequent actual member status/evidence call confirmed the provider receipt
  and retained unsettled usage. This is a lifecycle test, not a sixth website
  world or a new fictional-event/fidelity acceptance claim.

The first final report misread the retained historical timeout reason as a
missing current receipt. The status response now distinguishes
`reason: provider_terminal_receipt`, `terminal_event_type` and
`previous_outcome_reason`; the skill explains their separate meanings. The
corrected real agent read reported the provider receipt accurately. The original
incorrect report remains in the private transcript.

The paid viewer is stopped. The member remains connected to an **evidence-only**
backend, which has no Google credential and refuses preparation, review, start,
stop/event writes and live WebSocket upgrades. It can inspect the retained run
through its existing MCP. No new auto-start service or existing runtime upgrade
was installed. Private evidence is under
`.spec200-local/final-qualification/`, with the original member home retained under
`.spec200-local/release-integration/native-member/`.

## Provider usage and the unchanged hard limit

All six original `interactions.get` calls still returned HTTP500. Read-only API
key/project lookup and Cloud Monitoring authenticated using the owner's existing
Google login; no cloud API, billing account or export was activated.

Google's metric
`generativelanguage.googleapis.com/generate_content_usage_output_token_count`
returned seven `model=genie-4`, `output_modality=video` records in the selected
project, covering the six original operation windows and the new member test:

| Operation | Provider-reported video tokens |
| --- | ---: |
| Original independent synthetic qualification | 676,800 |
| Technical blueprint | 689,280 |
| Fantasy | 656,640 |
| Network city | 687,360 |
| Packet scale | 683,520 |
| Data center | 680,640 |
| Actual member qualification | 379,200 |
| Total | 4,453,440 |

At the reviewed US$17.50/million video-token rate, these quantities price to
**US$77.9352 for video**. This is **not a final bill**. Input/text usage and final
invoice totals remain unavailable. The metric exposes project/model/reporting
intervals, not interaction IDs: individual attribution is explicitly correlated
to the distinct operation windows, not represented as an ID-bearing receipt.
Usage is provider-reported, not reconstructed from local video duration.

All seven operations have original-provider terminal receipts. **US$99.810816
remains fully reserved under the US$100 hard cap**, with zero active unknown
sessions, zero settlements and no reservation release. A further standard trial
cannot fit and must be refused. This satisfies the retained usage-evidence
criterion without claiming settled billing or weakening admission controls.
The authenticated original responses, hashes and correlation assessments remain
private; see the [Cloud Monitoring API](https://docs.cloud.google.com/monitoring/api/v3/metrics)
and [reviewed Genie pricing](https://aistudio.google.com/docs/models/genie-4#pricing).

## Acceptance and release boundary

The owner's acceptance of recorded illustrations with documented visual/event
limits remains the visual verdict. The three additional technical checks now
have actual evidence; no renewed visual approval or higher budget is required.
All30tasks close for the owner-accepted Mac prototype using that existing verdict and the actual technical evidence. Local regression passes; hosted CI must pass for the final source before the authorized merge.
Original strict fidelity failures, provider HTTP500s, initial collector timeouts,
terminal-wait recovery and the corrected agent report remain visible.

This qualifies the accepted Mac prototype and its NetClaw integration. Exact
digital-twin fidelity, successful visible events in every video, production member
confinement, Windows/WSL/Mobile live operation and settled invoices are not claimed.
The latter are explicit limits, not hidden claims that another world was made.
Source1.26.0/extension1.6.2 remain the release candidates; this request does not
publish a Marketplace package, tag, website or announcement. Original198 remains
preserved at856bbc88 until200's authorized merge is complete;199 remains AWS.


## Final source verification

- Python collector/policy/provenance/MCP/setup suite:156/156passed.
- Node lifecycle/provider/browser/recording/actual stdio suite:184/184passed, no skips.
- Canonical catalog tests:9/9passed; generated Bash catalog and skill hashes match;
  metadata checks pass. Link check:171verified, zero dead, three retained review cases.
- The earlier Node run had183/184: its crash-recovery assertion still expected the
  historical reason as current after the status correction. The corrected test
  now asserts the terminal receipt, historical disconnect and exact event type.
- Existing Border environment/configuration/installation identity hashes match
  the pre-change baseline. Original198 remains exactly856bbc88. All five gallery
  pages return200; the original ZIP hash remains262d2a34c8dec7b50d6fa2ddd7276a6142131d9a6d4d523c91220fa757ee38e9.
- Final evidence-only MCP read confirms `interaction.cancelled`, preserves
  `terminal_receipt_missing` as history and reports usage unsettled.
- GAIT branch `spec200-final-qualification-20261124` records the technical handoff
  atde24c020. Private logs retain failed attempts and the complete audit.

The prior PR head passed47/47hosted checks. The final source revision requires
its own hosted results; that prior green run is not substituted for them.
