> Renderer delivery in this historical contract is retired by the owner.
> Retain fact identity/provenance contracts only; see ../direction-correction.md.

# Private topology view contract

Implementation refinement for FR-014a,FR-023a/b. These views are local-only;
none of these records is a hosted projection or MCP media payload.

## Normalized CDP graph bridge — pass19

`facts.cdp_neighbor_graph(devices, interfaces, observations,
identity_observations, graph_id=..., now=...)` accepts up to four CDP captures,
at most one per device, and validates the full inventory proof catalog before
binding. Exact device-scoped `interface_name` aliases bind the local port;
remote `cdp_device_id` and `port_id` identities retain their types. No hostname,
label, case folding, abbreviation or interface-name fallback resolves a remote
port. The returned private graph uses the existing resolver and shared inspector.

Incomplete, unmatched or ambiguous local identities remain in `unbound_neighbors`
with normalized provenance; they cannot create geometry. Remote unresolved claims
remain in graph discovery. Unknown expiry stays null, including reciprocal claims;
hold time is not converted into freshness. Current health stays separate. Failed,
empty and unqualified captures retain their catalog/normalization outcomes.

This narrow bridge does not yet assemble a whole detailed collection or display
the unbound report in the viewer. Native aliases/capture policy, LLDP extraction,
actual collection and acceptance remain open. Installed Genie25.2 synthetic
offline parser→JSON→graph→JavaScript inspector passed with zero execute calls.

| Record | Required meaning | Rendering rule |
| --- | --- | --- |
| Device | Frozen inventory ID,role,evidence references | Stable entity across styles;label is inert text |
| Interface | Device ID,full port identity,admin/oper observations | Unknown is distinct from down |
| Neighbor observation | Protocol,local port,remote identity/port claim,interval,expiry/evidence | One-sided claim remains one-sided |
| Link | Resolved endpoint interface IDs,supporting observations,certainty | Corroboration/conflict visible;never inferred from shared subnet |
| Counter sample | Interface/incarnation,time,integer,units,width if known,source | No invented values for absent fields |
| Derived rate | Two sample refs,elapsed time,continuity result,value or reason | Unknown on reset,decrease,invalid interval or ambiguous rollover |
| Utilization | Valid directional rate plus sourced capacity | No percentage without denominator provenance |
| Style mapping | Entity IDs → local geometry/color/material | May change appearance,never adjacency/facts |

Exact SVG diagram first;stylized3D is a later local renderer of the same graph.
Measured labels/counters are application overlays,never generated text. Selection
opens provenance locally. No view selection starts a new collection,polling loop,
Google session or device write. The initial detailed profile is finite and explicit.
Google's separate synthetic illustration carries no claim of measured fidelity.

## Counter derivation API — pass04

`facts.counter_rate(first, second, continuity=None, capacity=None)` is a pure local
normalization helper, not an exposed tool or a collection authorization. No native
adapter or renderer currently calls it. Caller records must originate in the
future qualified detailed-profile parser; never fabricate them from inventory.

Each private observed sample has id,device_id,interface_id,incarnation,field,
direction (`in`/`out`),units (`bytes`/`packets`/`errors`),width (32/64/null),
value (canonical unsigned decimal string),started_at,finished_at,sampled_at and
evidence. UTC timestamps have <=6 fractional digits; sampled_at must be within the
capture interval. An absent actual sample timestamp stays unknown; do not replace
it with an invented time. Decimal strings preserve64-bit integers across JSON.
Evidence includes observation_id,source,command,parser_version,sha256,source_path.

Distinct observations and sample IDs must match device/interface/incarnation,
field/direction/units/width; collection intervals cannot overlap. Continuity is
an evidence-bearing record bound to the ordered sample_ids with verdict
`verified_no_reset_or_wrap`. It is a local adapter assertion that still requires
native qualification, not permission or proof by itself. Matching incarnation
strings alone do not establish continuity. Decreasing counters always yield
unknown; no modulo rollover correction. Missing/unavailable/malformed samples,
invalid timing and unverified continuity yield value=null with an explicit reason.
An actually unchanged valid pair may yield zero. Output retains both intervals,
sample IDs, elapsed time, exact decimal delta and bounded provenance.

Optional capacity is bound to the same device/interface/incarnation/direction
and ordered sample pair, with evidence,units=bits/s and positive decimal value.
Only byte rates convert to bit utilization. Missing denominator evidence leaves
utilization unknown without erasing a valid rate; >100% is capacity_conflict,
never clamped. Capacity values and evidence remain inspectable. Derivatives stay
private and hosted_eligible=false; extraneous raw evidence keys are excluded.
This API does not establish staleness presentation or accept private graph payloads
into Google. Native extraction, continuity proof, graph extension and overlays
remain open T016/T017/T018 work.

## Neighbor resolution API — pass05

`facts.resolve_neighbors(devices, interfaces, observations, now=utc_timestamp)`
is a pure private intermediate normalization API. It neither collects nor grants
device access and is not yet wired to normalize(), the collector or localGraph.
Limits:4 devices,1024 interfaces,256 discovery claims,16 identities/entity.
Device records have id and identities; interfaces add device_id. Each identity
has kind,value,evidence. Device kinds:chassis_id,cdp_device_id,hostname. Port
kinds:port_id,interface_name. Identity values match exactly within their type;
no shortened names,case folding,port abbreviations,IP/subnet or controller wiring
inference. The native adapter must qualify any explicit alias binding it supplies.

Claims have unique id,device_id,local_interface_id,protocol(lldp/cdp),
remote_identities,remote_port,started_at,finished_at,expires_at(or null),evidence.
Evidence requires observation_id,device_ref,outcome=observed,source,command,
parser_version,sha256,source_path. Inventory evidence must bind its owning device;
claim evidence must bind its source device and exact protocol command. Extra raw
evidence keys are discarded. Identity and discovery proofs are retained separately.
UTC capture intervals must be ordered and finished by explicit evaluation time.
Expiry must be supplied by a qualified parser; absent expiry is never invented.

All supplied remote identity claims must match and their candidate intersection
must be unique. Unknown/ambiguous identities or ports remain unresolved records;
disagreeing identities and self-neighbors remain explicit conflicts without edges.
Resolved links use actual endpoint interface IDs and retain supporting claim IDs.
Multiple peers claimed at either port mark every affected edge as conflict, even
when some evidence is old; freshness remains independently inspectable.
Reciprocal unexpired,nonstale claims from distinct observations are required for
corroboration. Two protocols from one endpoint do not establish reciprocity.
Missing expiry,expired evidence or >300s age cannot corroborate. Historical resolved
edges remain available as unknown. Discovery alone never sets observed_up; status
is unknown or conflict. Empty claims mean no supplied observations,not no network
links. Collection failures remain in the collector's separate coverage records.

Output is private,hosted_eligible=false and deterministically ordered by claim and
endpoint IDs. No real parser,inventory alias,hold-time extraction or device run is
qualified by these synthetic tests. Interface-oper-state disagreement, detailed
profile parsing, coverage/unknown display and renderer integration remain open.

## Local selection presentation — pass06

Both local renderers use selectionDetails/showSelection from selection.mjs after
localGraph validation. Link summaries identify both full endpoint interfaces and
owning device IDs; recorded certainty never implies current link health. Snapshot
port status is preserved. Evidence source/outcome/interval/age is visible outside
pixels; raw hashes remain in expandable details. Age >300seconds is stale; future
finish times have null age/staleness. Counter values remain explicitly unavailable
until the normalized graph contract carries evidence-backed rates. All labels use
textContent. View selection has no collection/provider effects or egress.

## Private graph bridge — pass07

`facts.local_graph(devices, interfaces, claims, observations, graph_id=..., now=...)`
now calls resolve_neighbors and produces the localGraph envelope. Inputs are
local normalized records, not raw parser output or an exposed tool. Inventory
adds label/role and interface label/status to the resolver identity records.
Every identity and discovery proof must match an observation catalog entry by
ID,device,source,command,parser version,outcome and hash; discovery capture
intervals must match too. Non-unknown port state needs separate interface-command
state_evidence bound to the same device; discovery cannot establish port health.
Native parser field/value and identity/continuity qualification remain required.

The observation catalog is bounded to128 supplied records. Timeout/unavailable
may have null hashes; no hash is invented. Coverage retains outcomes, intervals,
evidence_limit and capture_outcome_unknown. Absence of a supplied record is not
proof a read succeeded or that no neighbors exist. All graph evidence is bounded
and closed;24refs/entity and2048proofs remain explicit refusal limits.

Optional graph discovery/coverage arrays are validated and deeply frozen in JS.
Discovery retains typed remote identity/port claims, unresolved endpoint null,
reason,expiry/staleness and source references without adding geometric entities.
The shared inspector shows related claims and device-level coverage in both SVG
and local3D, including missing supplied coverage. Raw proof records additionally
retain observation_id,device_ref,command,parser_version and source_path. Labels
remain inert text. Existing geometry uses only resolved link endpoints. The
bridge always outputs private classification; the hosted projection rejects it.
No native adapter/normalize caller invokes this bridge yet; counters and state
conflict normalization are still unwired. Synthetic cross-language tests and
separate synthetic browser fixtures qualify these source seams only.

## State versus discovery evidence — pass08

The graph bridge emits interface `state_evidence_id` and claim
`discovery_evidence_id`, each also present in that entity's evidence_ids. The JS
boundary validates the referenced observed record, owning device and exact
interface/discovery command; one proof cannot substitute for the other. Empty
state proof dictionaries are rejected. Older graphs without explicit pointers
remain displayable but cannot produce a state/discovery comparison by guessing
from identity proofs. Native parser semantics and port-path binding still require
qualification; these pointers are source evidence, not a live health verdict.

Both inspectors compare down/conflict snapshots at either claim endpoint against
that specific discovery capture. They say before discovery, after discovery, or
capture intervals overlap; microsecond order is preserved. Temporal separation
must not be mislabeled as simultaneous conflict. Stale/future state ages remain
visible; expired/unresolved discovery remains visible. Link certainty and geometry
are unchanged. Referenced state evidence joins the expanded proof record and
source cards show the command. No collection, polling or hosted effect occurs.
Counters remain unavailable pending the separate counter-result graph binding.


## Counter graph binding — pass09

`facts.local_graph(..., counters=[])` accepts at most512 local counter requests,
each with unique id,interface_id,field,direction,first,second and optional
continuity/capacity records from the pass04 API. It invokes counter_rate; callers
cannot submit a computed value. Supplied samples must name the owning device,
interface,field and direction. Every retained sample proof binds to an observed
catalog `show interfaces` capture with the exact interval,source,parser and hash.
Continuity proof binds to same-device show interfaces/show version; capacity to
show interfaces. Native field/path/incarnation/continuity semantics still require
parser qualification: catalog binding alone cannot establish those semantics.

The optional closed `counters` graph array retains exact decimal delta,approximate
numeric rate,ordered sample IDs/intervals,explicit unknown reason,capacity and
utilization reason. sample_evidence_ids,continuity_evidence_id and
capacity_evidence_id are included in evidence_ids. JS checks owning device,
observed outcomes,commands,intervals,distinct observations,positive elapsed time,
rate/delta arithmetic and capacity-backed percentages,then deeply freezes data.
Unknown never becomes zero; a verified unchanged sample pair can be zero.
Reset/decrease,missing sample,unverified continuity and capacity conflict remain
distinct. The bridge always marks the overall graph private; Google rejects it.

Both inspectors show counter rows near the endpoint summary,with source sample
intervals,stale/future age and directional utilization/denominator. Raw proof IDs
and hashes remain expandable. Desktop evidence scrolls independently; selection
resets its scroll. Narrow layouts retain the full evidence below the scene. No
collection or provider effects are added. Synthetic cross-language/browser tests
qualify these seams only; normalize/native parser still does not call this bridge.


## Local diorama forms — pass12

Role changes only the local chassis footprint/material/emblem. Ports are created
only from graph interfaces and placed on the front face; links share those exact
geometry objects. No decorative ports or connections are introduced. Chassis
faces clip at the camera near plane; role emblems paint with their owning face.
Visit framing at1280/820keeps the selected chassis visible and outside any chassis.
Selected labels clamp to canvas bounds while their anchor remains in front; full
identity/proof stays available in the inspector. Free navigation has no physical
collision guarantee. Links and markers intentionally remain visible through
geometry as disclosed by the legend. Dense graph readability remains unqualified.


## Raw counter observations — pass17

Each graph counter may carry up to two `observed_samples`, tagged first/second.
These records preserve exact unsigned64-bit decimal values, units, capture
intervals, optional actual sampled_at and owning evidence reference independently
of counter_rate qualification. Missing/invalid values are null with unknown
outcome; an absent record is explicitly unavailable. No incarnation, continuity,
width, capacity or sample instant is manufactured. Valid catalog-bound raw counts
remain readable even when a missing pair or unknown timing prevents a rate.

The JS contract binds source/command/owner/intervals, forbids numeric coercion and
overflow, and checks any derived rate's supplied raw sample identities, evidence,
units, instants and exact delta. Both inspectors show counts separately from
rates, with per-sample provenance and unknown timing. Legacy graphs without this
optional field explicitly say no qualified observation supplied. Native parser
to identity bindings remain unqualified; this change supplies the graph boundary,
not a collector grant, identity inference or live proof.


## Interface counter assembly — pass18

`facts.interface_counter_graph(devices, interfaces, observations,
identity_observations, graph_id=..., now=...)` is an offline interface-only bridge.
It accepts at most two show-interfaces captures per device/eight total, validates
the combined observation catalog and inventory proofs with local_graph, then
normalizes parser fields and binds exact typed interface_name aliases within their
owning device. Labels, abbreviations, case folding and parser-expanded names alone
never establish a binding. Real aliases still require native qualification.
Duplicate explicit sample slots are refused; missing slots stay unbound rather
than being inferred from list order or capture timing.

The private result contains graph, bounded normalization and unbound_interfaces
with unmatched_interface/ambiguous_interface/sample_slot_unknown reasons. Counter
entries use collector sample_index1/2 and preserve exact decimal strings and real
field paths. sampled_at/incarnation/continuity/capacity stay unknown. Missing
fields have no invented proof path or observed sample; their reasons remain in
normalization. Invalid present fields retain sourced unknowns. Failed captures
remain in graph coverage; increasing values alone never produce a rate.

The graph passes the existing JavaScript validator/shared inspector. This API
accepts interface captures only, so it cannot silently discard CDP/LLDP input.
It does not bind discovery or combine separate state fields into physical health.
Unbound-interface presentation and full discovery/state assembly remain next work.
No collection, hosted projection, provider call or browser route is introduced.


## Normalized LLDP graph bridge — pass21

`facts.lldp_neighbor_graph(devices, interfaces, observations,
identity_observations, graph_id=..., now=...)` accepts at most four LLDP captures,
one per device. It shares the catalog validation and exact binding implementation
with cdp_neighbor_graph. The wrappers enforce their own protocol/command boundary.
Local interface_name aliases are device-scoped; remote identities require typed
chassis_id and port_id matches. No hostname, parser key, label, abbreviation,
case folding or MAC-format conversion supplies an alias. Inventory aliases still
require independent native qualification.

Normalization retains exact field paths, hold time and null chassis/port subtypes;
the graph retains typed chassis/port claims with unknown expiry. Subtype absence
is not evidence of a wire subtype. Reciprocal claims cannot establish freshness
without qualified expiry. Missing/ambiguous local matches remain in the returned
unbound_neighbors report; unresolved remote claims remain in graph discovery.
Failed, empty and unqualified captures remain distinct. Combined detailed assembly
and viewer presentation of unbound reports remain open. Installed synthetic
Genie25.2 LLDP/CDP→JSON→graph→JS inspector passed with zero device execute calls;
these checks qualify source seams only, not real identities, collection or health.


## Combined detailed collection — pass22

`facts.detailed_collection_graph(devices, interfaces, observations,
identity_observations, graph_id=..., now=...)` accepts one bounded detailed
collection: at most24 captures/four devices, one capture per device/command
except the two explicit show-interfaces sample slots. Unsupported commands,
duplicate capture IDs, repeated commands/sample slots and invalid catalog proofs
are refused. Missing slots remain unknown; input order cannot supply a slot.

The bridge validates the entire catalog before alias use, normalizes the combined
collection, then passes raw bound claims and counter inputs through local_graph
once for joint resolution. It never concatenates already-rendered graphs. CDP
and LLDP claims on identical endpoints share one link; competing protocol peers
are jointly marked conflict. Unknown expiry is not corroborated freshness.

All capture coverage, normalization failures and unbound reports are retained.
`interface_states` separately preserves enabled/oper_status/line_protocol fields,
exact paths, source/parser/hash, capture interval, device and observation identity,
and an exact local interface binding or its explicit failure. State binding is
independent of counter sample-slot availability. No physical health, sample time,
incarnation, continuity, rate or utilization is inferred. Raw decimal counter
observations remain available in the single graph. Outputs are private and never
hosted-eligible; no collection or browser endpoint is added.

Synthetic mixed-protocol/counter/failed-read graphs pass the JS validator/layout
and shared inspector; existing installed Genie CDP/LLDP offline seams still pass.
Native capture/identity qualification, state/unbound viewer presentation and
actual collection remain open. This supersedes earlier combined-assembly gaps
for this source API only, not live/native/owner acceptance.


## Separate parser state in local views — pass23

The detailed bridge now includes optional `graph.interface_states`, bounded to
2048 records (eight captures of at most256 interfaces). The closed JavaScript
boundary requires observed show-interfaces coverage with matching capture ID,
device, source, parser version, hash and exact interval. Duplicate capture/name
pairs, forged ownership or field paths, extra fields and invalid value/certainty/
reason combinations are refused. Records are deeply frozen with the graph.

Each record keeps enabled (boolean), oper_status and line_protocol as separate
parser fields. Observed false is not unknown. Missing fields have no source path;
invalid present fields keep their path and an explicit unknown. No state field
changes interface status, adjacency, certainty, colors or geometry. Native alias
and parser semantics still need qualification; this is not a health authority.

Both local inspectors show bound rows for their device/interface/link selection.
Unbound state rows appear only on their source device, with unmatched/ambiguous
reason; they never attach to an arbitrary port. Source, command, parser, capture
interval, field path and current calculated age are readable; full hashes remain
in expandable raw details. Future age stays unknown. Existing graphs without the
optional array remain supported. Unbound neighbor/counter reports remain outside
the graph and still need a separately bounded presentation contract.
