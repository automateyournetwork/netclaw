> **Current integration status — 2026-11-24:** 30/30 tasks complete for the owner-accepted Mac recorded-illustration scope. Actual selected-runtime collection passed 24/24 reads; the existing Border-owned member completed a real Google lifecycle through its skill and MCP. Google reported video usage for all seven runs; all US$99.810816 reservations remain held because final billing is unavailable. The five accepted recorded illustrations are unchanged. Local regression and handoff are complete; hosted CI must pass before the authorized merge. See [final-qualification.md](final-qualification.md). Older checkpoints below are historical, not current authority.

# Feature Specification: Genie Network Worlds

**Feature Branch**: `200-genie-network-worlds`

**Created**: 2026-11-22

**Status**: Recorded-illustration scope accepted; actual collector and Border/member/Google integration qualified; local qualification complete; hosted CI and authorized merge pending.

**Input**: John requested an explorable network walkthrough, using Cisco pyATS
Genie for measured facts and Google Genie for illustration, with a reusable
NetClaw skill and MCP controls over the documented API. The owner has authorized source implementation and explicitly rejected local-rendered
world substitutes. See [direction-correction.md](direction-correction.md).
Work exclusively in `/Users/john.capobianco/netclaw-spec200-genie` on existing
`200-genie-network-worlds`. Preserve198 at856bbc88;199 is reserved for AWS.

## Clarifications and chosen defaults — 2026-11-22

- Owner correction: use Google-generated worlds through the new Genie 4 API;
  remove local-rendered world substitutes and retain Spec200. See the correction
  record for exact collection commands, privacy and current device findings.

- “MCP in place of the API” means NetClaw users operate through a skill and MCP
  tools; Google's official API remains the service underneath. A documentation
  MCP cannot generate worlds. The source skill and MCP now exist; actual member acceptance follows
  the smallest direct proof; neither replaces entitlement or backend controls.
- The latest owner correction requires actual realistic and fantasy worlds from
  Google Genie 4 through the Gemini API. Local SVG/3D rendering is removed from
  scope. The owner subsequently authorized all five recorded styles after the first two captures. Completion still requires actual member MCP/skill
  qualification; the two styles have separate reviewed sessions and allowances.
- The museum metaphor is a replaceable teaching aid: spatial grouping helps a
  learner distinguish router/switch roles and a narrated fictional incident.
  Physical corridors have no routing semantics. No digital-twin claim is made.
- First hosted scenario is independently authored fiction: two routing halls,
  two switching rooms, exactly three declared corridors and one lighting event.
  Real observations can be normalized and inspected locally in a separate run.
- Desktop keyboard controls and a separate readable facts/legend panel are
  required. Audio is optional. Terminal/VS Code setup and HUD capability status are in scope; embedded world players and Mobile controls remain deferred.

## Owner acceptance amendment — 2026-11-23

The owner explicitly selected **“Accept recorded illustrations with documented
visual/event limits.”** The five 120-second recordings satisfy the visual delivery
scope when their actual navigation, attempted fictional event and drift findings
are retained. Exact landmark/link counts and a visibly successful lighting effect
in every recording are no longer completion conditions for this delivery.
Historical strict results remain failed/unassessed, never rewritten as passes.
No topology accuracy, digital twin, persistent world export or free visitor
navigation is implied. The static site provides playback and seeking of the
recorded routes. Facts and uncertainty remain authoritative outside the pixels.

The owner clarified that the **existing Border owns the Genie member**. It owns
membership, enrollment, routing and task authority. The member has isolated state
within that Risk; the backend independently owns Google credentials, generation,
termination, reservations and private evidence. No new Border is required.

## User Scenarios & Testing

### User Story 1 — Prove a useful explorable network scene (Priority: P1)

An engineer turns a small, explicitly synthetic network scenario into an
explorable world and assesses whether spatial metaphors help explain the network.

**Why this priority**: Actual usefulness must be demonstrated before investing
in a full integration or delaying the cloud roadmap further.

**Independent Test**: Generate realistic and fantasy versions as separate bounded
Google sessions. Navigate each and compare its objects, links and one fictional
state change with the declared scenario. Local rendering cannot pass this test.

**Acceptance Scenarios**:

1. **Given** a synthetic two-router/two-switch scenario and available service
   access, **when** the engineer generates and explores its world, **then**
   a recorded session demonstrates movement and identifiable network roles.
2. **Given** a fictional link-down event, **when** the engineer requests that
   visual change, **then** its visible outcome is reviewed and recorded as
   successful, inaccurate, or unsupported; no real device is changed.
3. **Given** unavailable credentials, access, or unacceptable visual fidelity,
   **when** the experiment ends, **then** the result states the exact limitation
   and does not claim a completed integration.

### User Story 2 — Ground scene preparation in measured facts (Priority: P2)

An engineer prepares a local scene description from timestamped pyATS Genie
observations while keeping measured facts distinguishable from invented scenery.

**Why this priority**: An attractive generated world must not become evidence
for a network condition that was never measured.

**Independent Test**: Process a private observed snapshot locally, then compare
the resulting facts and scene instructions with the original observations.

**Acceptance Scenarios**:

1. **Given** successful structured observations, **when** a scene is prepared,
   **then** every claimed device state has its source and observation time.
2. **Given** a failed read, raw-only output or missing adjacency information,
   **when** preparation runs, **then** missing facts remain unknown and no
   connectivity is inferred from inventory, addresses or scene layout.
3. **Given** real network data, **when** a hosted demonstration is prepared,
   **then** private configurations, credentials and topology stay local;
   the initial hosted proof uses an independent synthetic scenario.

### User Story 3 — Repeat and finish a bounded experiment (Priority: P3)

An engineer can review the scene input, set a finite session limit, end the
experiment, and retain enough evidence to decide whether to continue.

**Why this priority**: Experimental generation must have a visible end state
and predictable scope even when the connection drops.

**Independent Test**: Complete a normal session and interrupt a separate
bounded session, confirming the recorded outcomes and absence of blind replay.

**Acceptance Scenarios**:

1. **Given** a reviewed synthetic input and chosen finite limit, **when** the
   session ends, **then** completion and usage evidence are retained.
2. **Given** a lost connection, **when** completion cannot be confirmed,
   **then** the outcome remains unknown and a replacement session is not
   automatically created.

### Edge Cases

- A Project Genie subscription does not establish developer-service entitlement.
- The model changes object counts, text, landmarks or connections during motion.
- A scene suggests connectivity absent from the measured snapshot.
- Stopped CML nodes, stale inventory, failed parsing and unreachable tools differ.
- Dropping the viewer connection may leave hosted generation active.
- Private topology remains private even after names and addresses are removed.
- A documentation assistant is mistaken for a world-generation integration.
- Generated video is mistaken for an exported editable three-dimensional model.
- A successful stop method returns before the service confirms completion.
- Creation is sent but its response, identifier or usage receipt is lost.
- The viewer, MCP client, session worker or whole host fails at different times.
- Duplicate starts/events arrive concurrently or after a restart.
- A late terminal event settles an unknown operation; it must not start another.
- Device text contains instructions, control characters or oversized output.
- Neighbor observations disagree, age out, or cover only one end of a link.
- An event is sent once but its visual outcome is ambiguous or appears too late.
- Private data is embedded in reference-image metadata or a browser screenshot.

## Requirements

### Functional Requirements

- **FR-001**: Establish current local readiness with actual read-only observations;
  distinguish controller readiness, device state, tool availability and parsing.
- **FR-002**: Support an independent synthetic scenario for the first hosted proof.
- **FR-003**: Preserve source, observation time, uncertainty and completeness for
  locally prepared network facts; never fill missing facts with generated content.
- **FR-004**: Keep private configurations, credentials and topology local under
  the repository data-handling policy. An owner-approved exact minimized projection may be hosted; raw configurations, credentials, addresses and management details remain local. Do not treat anonymization as permission.
- **FR-005**: Present the world as an illustrative view with measured facts
  available separately; never use generated behavior to approve network changes.
- **FR-006**: Permit review of the exact scene description before generation.
- **FR-007**: Provide a finite session duration and explicit termination, retain
  usage evidence, and preserve unknown completion states without blind retries.
- **FR-008**: Demonstrate navigation and one fictional state-change visualization.
- **FR-009**: Use supported programmatic access when available; document the
  actual account-access result and any fallback's limits.
- **FR-010**: Record actual visual fidelity against the declared scenario and
  label discrepancies; acceptance requires an observed useful world.
- **FR-011**: Preserve unfinished198 work and reserve199 for AWS. Return to198,
  then199, after the feasible200 scope is completed; report a no-go honestly.
- **FR-012**: Record a reasoned client-impact decision for HUD, VS Code and
  Mobile before expanding beyond the standalone feasibility experiment.
- **FR-013**: Provide one reusable NetClaw workflow and bounded agent control
  tools over the same lifecycle as the standalone viewer. Agents receive status
  and evidence references, never streaming media or provider secrets.
- **FR-014**: Bound each initial collection to four selected devices, three
  allowlisted read types per device, 30 seconds per read, two concurrent workers,
  180 seconds overall and 8 MiB of raw evidence. Retain timeout, unavailable,
  parse-failed, raw-only and observed outcomes separately. No device writes,
  node lifecycle or default-installation repairs are authorized by collection.
- **FR-014a**: Offer a separately selected detailed local profile of at most six
  reads per device: version, interface summary, LLDP detail, CDP detail, and two
  interface-counter samples. Limit four devices, two workers, 30 seconds per
  read, 240 seconds overall and 8 MiB total evidence. Unsupported discovery
  protocols remain unavailable; do not enable them or silently add commands.
- **FR-015**: Every fact carries observation interval, source device identity,
  command, parser/version, evidence digest and classification. Relationships
  require actual neighbor evidence; one-sided and conflicting observations stay
  labeled. Inventory, shared subnets and controller wiring alone prove no live
  adjacency. An empty parsed table is not a collection failure or a universal
  proof of no links.
- **FR-016**: Freeze the observation window and display its age. Mark facts stale
  after five minutes by default; all illustrations remain snapshot-based even
  while fresh. Unknown, stale and fictional values must remain distinguishable.
- **FR-017**: Use independent synthetic input for the first hosted trial. Private-derived input is eligible only through an exact operator-pinned grant matching the registered snapshot manifest, style and outbound/event hashes. The owner authorized core labels, measured data-port pairings, VLAN IDs and OSPF/iBGP relationships for the five recorded worlds. No raw evidence or arbitrary tool-supplied prompt is eligible; identifier removal alone grants no permission.
- **FR-018**: Review and bind the exact outbound text/image, model, event,
  duration, pricing assumption and finite allowance before a paid session.
  Any changed input invalidates that review. Credentials are provided privately
  to the selected installation; browser access or a subscription is not evidence
  of developer entitlement. No secret values are requested in conversation.
- **FR-019**: Keep long-lived credentials in the local backend. The viewer uses
  only a short-lived local capability; it receives no provider key and opens no
  independent provider session. Untrusted strings are rendered as text and never
  treated as executable instructions, URLs or paths.
- **FR-020**: Admit at most one active or termination-unknown paid attempt per selected
  installation/provider account. Persist the send marker before creation; a
  duplicate request returns the original operation. A different identifier,
  process restart or renewed client cannot evade an unknown-outcome hold.
- **FR-021**: The backend owns a finite deadline independent of browser/client
  liveness. User stop, missing viewer heartbeat, deadline and stream failure
  request termination and stop accepting controls. A dispatched completion or
  local connection close is not a provider terminal receipt. Worker/host loss
  retains unknown status until reconciled; no automatic creation or event replay.
- **FR-022**: Retain estimates separately from reported usage and actual billed
  cost. Missing usage is unknown, not zero. Local timers and budget reservations
  are not service-enforced caps. An unverified service duration/cost bound or
  insufficient allowance prevents paid admission; unresolved sessions retain
  their full reservation. A confirmed provider terminal receipt with unknown usage may permit distinct work within the aggregate hard limit, while retaining the full bound. It never settles billing or permits replay.
- **FR-023a**: Provide five distinct Google-generated treatments sharing the same
  sealed real snapshot: futuristic technical blueprint, living fantasy, cinematic
  network city, packet-scale machinery and realistic future data center. Prove
  blueprint/fantasy first. The later owner instruction explicitly authorizes all five recordings; failed fidelity is retained rather than used to claim success. Private-derived hosting needs the exact FR-017/018 review; independent
  synthetic qualification comes first. Preserve declared device identities,
  measured port pairings and VLAN groups as review criteria, with visual drift
  recorded honestly. Local Three.js/SVG scenes cannot replace Google generation.
  Keep local authoritative facts and counter uncertainty separate from pixels.
- **FR-023b**: Counter rates require two timestamped samples of the same interface
  incarnation and valid elapsed time. Missing/reset/wrapped/ambiguous counters
  produce unknown rates, never invented zero. Utilization additionally requires
  measured or explicitly sourced capacity and direction. No automatic polling
  or device change is implied by selecting a view.
- **FR-023**: The viewer keeps readable role labels, topology legend, observation
  times, fiction/snapshot banners and stop/status controls outside generated
  pixels. Support keyboard movement/turning, keyboard-accessible stop, visible
  focus and no dependence on audio or color alone. Disable input on blur/loss.
- **FR-024**: The only trial state-change action is the pre-reviewed fictional
  lamp/corridor-dimming event. Record intent, send time and observed outcome
  separately. Neither movement nor an event can invoke a network configuration
  tool. Acknowledgement alone cannot establish the visible change.
- **FR-025**: Preserve a bounded local recording, sampled frames, control/event
  timestamps, exact input hashes, provider/session identity, terminal receipt,
  usage and human verdict. Raw device evidence stays private, outside committed
  artifacts and hosted payloads. Sanitize summaries; retain original failures.
- **FR-026**: Finish the integration with an actual isolated NetClaw member in
  the selected existing Risk, a skill-to-MCP-to-worker exercise and qualified
  read-only collector evidence. Do not create a new Border or add live-device
  authority to the snapshot-only world member. Tool listing,
  mocked media and prior unrelated NetClaw sessions are not that proof.

### Key Entities

- **Observation**: A timestamped local measurement, source and outcome.
- **Scene description**: Roles, intended visual metaphors, fictional events and
  a data classification; separate from the authoritative observations.
- **Generation session**: Reviewed input, service identity, limits, progress,
  termination status and usage evidence.
- **Acceptance record**: Observed navigation, fidelity, limitations and decision.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every readiness target has an observed pass, failure or unverified
  result, with no healthy verdict inferred from an inventory entry alone.
- **SC-002**: Technical-blueprint and fantasy treatments are actual Google-generated
  sessions with at least ten seconds of deliberate navigation, one attempted
  fictional event with its actual visible outcome recorded and retained drift/terminal/usage assessment. On their actual
  review, deliver the separately authorized network-city, packet-scale and data-center treatments under the same rubric and snapshot identity. Preserve failed criteria; neither prompts nor50iteration records count as generated worlds.
- **SC-003**: Every network fact shown outside the generated scene traces to an
  observation; missing relationships remain explicitly unknown.
- **SC-004**: The initial hosted input contains zero private network facts or
  secrets; it is independently synthetic and reviewable.
- **SC-005**: Each generation attempt has a terminal or explicitly unknown
  status, recorded usage when available, and no unreviewed automatic replay.
- **SC-006**: A human-reviewed result declares go/no-go and lists any topology,
  text or object-persistence discrepancies before200 is called complete.
- **SC-007**: Review baseline, navigation and event checkpoints against the
  four intended device roles and three measured physical links. Record duplicate,
  missing, drifting and unreadable objects/labels; unseen areas remain unassessed.
  The owner accepts the recordings as illustrations with these discrepancies
  disclosed beside the authoritative facts. Exact geometric fidelity is not claimed.
- **SC-008**: At least ten seconds of deliberate navigation produces recorded
  viewpoint changes. Send one reviewed fictional lighting event and retain its
  actual send/checkpoint evidence. Report visible, inaccurate, not visible or
  unassessed outcome without replaying it to improve the appearance. This
  recorded-illustration scope permits unsuccessful visible effects with disclosure.
- **SC-009**: Every admitted attempt records either a provider terminal receipt
  or an unresolved outcome that blocks further paid starts. Successful live
  acceptance additionally requires confirmed termination and usage evidence;
  a duration estimate or closed window cannot satisfy it.
- **SC-010**: The actual isolated NetClaw member in the selected Risk can prepare/review the
  synthetic scene, start its bounded world, report status and obtain termination
  evidence through the planned tools. Private read-only collector facts retain
  100% provenance and are never included in that hosted request.

### Acceptance decisions

`GO` requires SC-001 through SC-010 within their declared scope, actual video
review, confirmed termination, and owner acceptance. `NO_GO` records failed
recognizability, event fidelity, drift, lifecycle or usefulness without erasing
the result. A scene can be useful for storytelling yet fail network-walkthrough
acceptance; changing that target requires a visible specification amendment.
`BLOCKED_LIVE` records unavailable entitlement/allowance/service/qualification;
planning can be complete while this remains open. A no-go can close the
feasibility investigation by owner decision but is not a completed integration.

## Assumptions

- Clarified2026-11-22: an active world exposes session steering (movement and
  text events),not a persistent post-completion object/world API. Retained
  recording/prompt/evidence cannot resume the same world. A later generation
  is a new instance and may drift.

- This is an exploratory visualization, not a routing simulator, validation
  engine, durable digital twin or device-control interface.
- First delivery is a standalone desktop experiment. Existing clients are
  unchanged; their impact must be assessed before any product integration.
- Existing local tool installations can be selected without replacing owner
  runtimes. Readiness does not authorize booting nodes or changing configuration.
- API access, a generation allowance and service termination behavior must be
  established before paid execution. No new paid account is created by this spec.
- No version, publication, cloud-resource deployment or external announcement
  is part of this feasibility stage.

## Historical owner refinement — renderer choice subsequently corrected

The owner requested one cheap synthetic live sample and asked for CDP/LLDP,
real interfaces,links and counters in both a precise Visio-like view and a more
creative network world. Adopt one private fact graph,deterministic local renderers
and a separate hosted illustration. Exact local topology is feasible without
relying on generated object permanence;Google visual fidelity remains an experiment.
No authorization to upload private topology follows from requesting those views.
The initial synthetic proof can precede strict private collector qualification.

The deterministic-renderer choice in that historical paragraph was rejected by
the owner. [direction-correction.md](direction-correction.md) and the current
realistic/fantasy Google-world acceptance supersede it.

## Owner expansion — routed CML evidence

The owner explicitly requested the four-device lab configuration and expanded
collection catalog: /31 router transit, OSPF underlay, loopback iBGP overlay,
router-on-stick VLAN10/20 and30/40, trunks/access ports and STP. See
[actual lab qualification](routed-lab-qualification.md) and
[collection commands](collection-commands.md). This is separate scoped network
authorization; it does not change the read-only product collector or authorize
uploading private topology/configuration. No static data routing is introduced;
existing management routing is preserved.

The local evidence model must distinguish physical discovery links, logical
routing adjacencies, advertised/installed routes, VLAN membership, STP state and
host reachability. Each fact retains its actual source, timestamp and uncertainty.
Illustrated traffic and fictional events never become measured network facts.
The owner's later instruction to save and reuse all output is implemented by the
sealed routed-lab snapshot and its hash-verified offline import. Supported VLAN
and established OSPF/iBGP cues retain source anchors; unsupported entries stay
local and unknown. The reusable live collector remains the qualified initial or
six-read detailed profile. A future live routed profile needs separate command,
parser and bounds qualification; it is not required to regenerate this snapshot.
