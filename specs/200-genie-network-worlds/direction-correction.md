> **Current foundation status — 2026-11-22 Toronto:** 15/30 tasks complete; new world campaign0/50. Six execution MCP tools and the source workflow skill now exist; sealed-snapshot inspection and actual browser/MCP handoff pass. Google generation, private-derived hosting and Risk-member acceptance remain open. Read [foundation evidence](world-suite/FOUNDATION.md), [live review](world-suite/LIVE-REVIEW.md) and [native review](native-review.md). Older counts, “MCP absent” statements and32-pass restrictions below are historical.

> **Latest owner authorization:** new50-pass campaign,10perfive Google Genie-4 worlds, using the sealed offline snapshot and targeting a NetClaw member in a Risk. See [world-suite/AUTHORITY.md](world-suite/AUTHORITY.md). The historical32-pass campaign remains untouched.

# Spec200 correction: Google-generated worlds

Owner correction, 2026-11-22. This supersedes local-renderer requirements and the
pass32 recommendation to continue general recovery work before demonstrating the
service. Keep Spec200 and its branch; no replacement specification is needed.

## Intended product and terminology

Cisco **pyATS Genie** measures the network. Google **Genie 4**, model `genie-4`,
generates interactive worlds through the **Gemini API / Interactions API**.
“MCP instead of API” means a NetClaw control interface over that API, not an
alternative world renderer. A Gemini reasoning/chat model is not the world model.
The current documented lifecycle is create interaction, connect stream, send
world_setup, send navigation/text events, and complete the session.

Primary references checked on 2026-11-22:
- https://aistudio.google.com/docs/genie
- https://aistudio.google.com/docs/models/genie-4
- https://aistudio.google.com/docs/models

The browser displays provider-generated media and sends controls. A Canvas used
to decode/display provider JPEG frames is acceptable; drawing a replacement 3D
world locally is not. Neither Three.js nor another local scene engine satisfies
acceptance. The local SVG/3D pages/routes and preview server have been retired;
source and earlier evidence are archived privately, not relabeled as API output.
Pure fact validation, provenance and non-visual selection helpers are retained.

## Required demonstrations

1. **Realistic:** a recognizable network equipment environment, with two router
   installations, two switch installations and the three declared links presented
   as traceable cable paths. Walk toward equipment, turn and revisit it. Readable
   authoritative labels remain outside generated pixels; do not promise exact
   port lettering or geometric persistence inside generated video.
2. **Fantasy:** the same declared scenario represented as two routing citadels,
   two switching hubs and three light bridges. It must still communicate network
   roles and relationships. Navigate and revisit a landmark.

Each style requires an actual separately identifiable provider session, at least
10 seconds of deliberate navigation, one pre-reviewed fictional link-lighting
change, baseline/post-navigation/post-event evidence, a drift assessment and
terminal/usage evidence. A still image, fixture, prepared prompt, API metadata
response or local 3D scene cannot pass. The first small live session is the
realistic synthetic qualification; the fantasy session follows only with its own
reviewed input and allowance. No two-session spend is inferred from the old
one-attempt proposal. A service failure or poor fidelity remains a recorded no-go.

## What can be retained

Retain the official SDK adapter, backend credential handling, session ledger,
termination/unknown-outcome handling, streaming display and evidence recording;
retain read-only collection, detached parsing, normalization and provenance.
These are source/offline assets, not evidence of live service success. The actual
MCP wrapper is absent. A draft SKILL.md exists under contracts/netclaw-genie-worlds;
it is not installed or native-qualified. Build/promote these after direct proof,
using the existing six-tool control contract and the same backend lifecycle.

All 32 historical loops are retained as history. Do not restart or extend them.
Local-renderer checks are retired, not carried forward as generated-world progress.
The 14 checked source tasks remain historical scope; no percentage implies product
acceptance. T013/T014 now lead the remaining implementation order. Update their
exact packets to the corrected styles and current source before any admission.

## Exact pyATS collection commands

The existing detailed profile makes six logical read requests per device:

| Order | Command | Evidence used locally |
| --- | --- | --- |
| 1 | `show version` | Platform, software and reported uptime; not proof of interface counter continuity by itself |
| 2 | `show ip interface brief` | Interface names, addressing and administrative/protocol state |
| 3 | `show lldp neighbors detail` | LLDP local/remote port and chassis claims, timers and conflicts |
| 4 | `show cdp neighbors detail` | CDP local/remote port and device claims, platform/capabilities and timers |
| 5 | `show interfaces` | First interface state/counter sample |
| 6 | `show interfaces` | Second sample, at least 10 seconds later; rates only with valid identity/continuity/timing |

Four selected devices, maximum 24 logical reads, two workers, no arbitrary command
substitution or configuration by the collector. The existing native show wrapper
can execute again after parser failure; record actual wire counts separately and
do not call a logical request count a capture-once qualification. Missing errors,
discards, speed or other fields remain unknown unless actually supplied and qualified.

Separate configuration preparation/verification uses `show running-config`,
`show ip interface brief`, `show cdp`, `show lldp`, and per-port discovery checks
if necessary. Running configuration, credentials, IP/MAC addresses, serials and
unfiltered CLI output are never a Google prompt. These reads are not an implicit
extension of the six-read production collector contract.

## What Google receives

The first realistic and fantasy qualification inputs are independently synthetic.
For a later real-lab world, prepare a small exact outbound scene projection from
local observations: reviewed device labels/roles, selected relationships, coarse
state/counter cues and explicit unknowns, plus the visual style and fictional event.
This would still disclose topology even after renaming. The original instruction
to keep private topology local remains effective until the owner reviews that
specific exception; no upload is authorized merely by this design correction.
No raw configurations, credentials or unrestricted agent context are outbound.

## Fresh CML and pyATS findings

Authenticated certificate-verified native HTTPS returned ready=true for CML 2.10.
Native TCP reaches all four device endpoints, and attempt03 obtained all 16
requested baseline/status reads. Python errno65 was a runtime-specific result;
it did not establish a network-wide outage. No cause for that difference is claimed.

All four actual `show cdp` results report CDPv2 enabled; all four `show lldp`
results report active/enabled. Running configurations and authenticated CML wiring
identify Ethernet0/0 as management; each has `no cdp enable`, `no lldp transmit`
and `no lldp receive`. No protocol configuration change is needed for this state.
The owner then explicitly requested OSPF/iBGP, router-on-stick VLANs, access ports
and STP. This scoped lab configuration has been applied through API-owned Local/Lab
records and native tools. Actual reciprocal CDP/LLDP now corroborate the three
inter-device links, and routing/switching/probe checks pass. See
[routed-lab qualification](routed-lab-qualification.md) for persistence and limits.
Management configuration and discovery exclusions remain unchanged.

## Immediate next step and owner inputs

The historical pre-change recollection completed 24/24 logical requests with
empty LLDP and raw-only CDP. Preserve it alongside the new populated discovery
and routed-lab evidence; native parser fallback limits still apply.
Prepare the corrected realistic synthetic trial packet with exact provider input,
current source binding, credential reference and cost bound, then run one actual
session when its allowance is authorized. Do not spend more loops on local scenery.
The Google key is present; no new links or credentials are needed. The prior US$15
one-attempt allowance question remains unanswered. The existing packet is stale
following renderer removal and must not be executed. Real private-data export,
and second style spend are not inferred from the separate routed-lab authorization.


Owner routed-lab expansion: see [complete collection/verification command table](collection-commands.md). The six-read source profile is not silently broadened by this document.
