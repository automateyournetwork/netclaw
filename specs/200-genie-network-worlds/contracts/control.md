# Local control and MCP contract — Spec200

Version1, implemented source with qualified local stdio/backend/browser controls.
These are NetClaw interfaces, not Google's API. Actual Google generation is recorded; Border-owned member qualification is recorded separately in integration-closeout.md. Schema definitions: [schemas.json](schemas.json).

## Shared control semantics

The CLI, viewer and MCP use one private manager/ledger. JSON bodies are closed
(no extra fields),max16KiB. Request ID is an opaque UUID; payload digest is
immutable. Identical duplicate returns retained operation; different payload
under same ID returns `conflict`. Read calls never create or resume effects. For start, `operation_id=request_id`
is known and persisted by the caller before send, so a lost response can be
queried without learning a new identifier.

Common response fields: `schema_version:1`, `request_id`, `status`, optional
`operation_id`, `state`, `outcome`, `usage_state`, `artifact_refs`, `error`.
Typed optional `deadline_at`, `estimated_usd`, `reported_usage`,
`billed_usd`, `manifest`, `acceptance`, and `gate` carry bounded sanitized
status/evidence fields. No provider key/token/raw device output,absolute path or media. Status values:
`ok`, `pending`, `refused`, `conflict`, `unknown`, `error`. HTTP adapter maps
validation400,not found404,conflict409,permission403,rate429; operation-level
unknown is a retained result, not a retryable HTTP failure.

Errors carry stable `code`,sanitized `message`, `retryable:false` for mutations,
and optional `gate`. Codes include `invalid_input`, `private_projection`,
`review_required`, `review_stale`, `credential_missing`, `entitlement_unverified`,
`allowance_insufficient`, `active_or_unsettled`, `unknown_outcome`,
`provider_contract`, `evidence_incomplete`, `unsupported_runtime`, `unavailable`.
Never echo input secrets or provider response bodies into errors.

## Six stdio MCP tools

Use official SDK JSON-RPC initialize/tools-list/tools-call lifecycle. No remote
MCP listener or general shell/device-write method. Read-only annotations describe
behavior, not authorization enforcement; the backend enforces every boundary.

| Tool | Closed input | Result and semantics |
| --- | --- | --- |
| `genie_world_prepare` | `request_id`, exactly one `synthetic_fixture_id` or `private_snapshot_ref` | Validate local input, produce opaque draft/projection ref and classification. Private draft requires an operator-pinned exact snapshot/projection export grant before hosted eligibility. No provider call. |
| `genie_world_start` | `request_id`, `projection_ref`, `review_ref` | Consume exact one-use backend-issued review grant; return original operation/pending. No caller model/duration/price/key/approval boolean. Spend-capable. |
| `genie_world_status` | `operation_id` | Retained state, deadline, estimated vs reported usage and unsettled/unknown reason. Read-only; no provider effect or implicit resume. |
| `genie_world_event` | `request_id`, `operation_id`, `event_id` | Only registered reviewed lighting event; ledger deduplicates across viewer/MCP. Pending/sent is not visible success. Mutating. |
| `genie_world_stop` | `request_id`, `operation_id` | Idempotent termination request; return pending until terminal evidence. Unknown remains unknown. Mutating, never start-capable. |
| `genie_world_evidence` | `operation_id` | Sanitized manifest, hashes, acceptance statuses and opaque local artifact refs; no video/config/key or invented verdict. Read-only. |

No tool mints approvals, imports arbitrary files, supplies private prompts,
clears unknown holds, changes account mapping or upgrades a live duration.
MCP has prepare workspace-write annotation; start/event/stop have readOnly=false;
status/evidence readOnly=true. Model tools cannot stream, perform key-by-key
navigation or obtain provider session tokens. Human navigates local viewer.
Native NetClaw proof must observe these exact names/discovery and actual call
correlation, not rely on a prompt mentioning them.

## Implemented loopback HTTP and viewer channel

Bind only127.0.0.1 to an allocated loopback port recorded in the owned process
manifest; never expose public0.0.0.0. Exact Host/Origin allowlist; no wildcard
CORS. Local anti-CSRF session cookie plus CSRF header for mutations; validate
WebSocket Origin and capability. The owner CLI uses the private owner credential. MCP uses a separate loopback
control bearer that cannot create reviews, read raw facts, bootstrap a browser
or open its WebSocket. Neither credential is passed in a query string. Bootstrap
capability256bits,one use,60s expiry; browser-held session10min maximum, scoped
to one operation. Capability is not authority for new paid operations.

| Route/channel | Purpose |
| --- | --- |
| `POST /v1/drafts` | Prepare using same schema as prepare tool |
| `POST /v1/reviews` | Human local review only; manager creates grant from exact stored projection/policy and explicit allowance; not exposed in MCP |
| `POST /v1/sessions` | Same guarded start operation |
| `GET /v1/sessions/{id}` | Retained state/usage, not auto-reconnect |
| `POST /v1/sessions/{id}/event` | Same fixed once-only event |
| `POST /v1/sessions/{id}/stop` | Same idempotent stop |
| `GET /v1/sessions/{id}/evidence` | Sanitized manifest |
| `WS /v1/view/{id}` | Authenticated local media/control only, no new-session capability |

Review body references stored projection and policy hashes plus explicit
allowance; values cannot expand policy bounds. It is authenticated human UI
intent, not agent-asserted `approved:true`. The user need not be re-asked if an
existing still-valid exact grant authorizes the action. Preparations remain
credential-free and offline.

Viewer control messages: `{type:'heartbeat',seq}`, `{type:'key',seq,key,down}`,
`{type:'event_ready',seq,event_id}`, `{type:'event',request_id,event_id}`, `{type:'stop',request_id}`. Key enum is
w/a/s/d/arrow_left/arrow_right/arrow_up/arrow_down. Strict increasing sequence,
<=10 movement key-down messages/sec; excess releases all held keys and
requests stop. Key-up/release-all and stop bypass this movement limit; they
are never silently dropped. Release keys on blur,
heartbeat loss,stop or disconnect. Before the event,the operator marks target-visible in the viewer; manager
records a one-use readiness flag valid for2s. Event is refused without this
flag and does not consume its send marker; an agent cannot infer visibility
from time. This is operator intent,not visual-model validation. Event and stop
use durable IDs shared with
MCP; movement is transient,never replayed. Server frames carry version,frame
sequence,received time,MIME and binary JPEG. Status retains authoritative
state; video pixels cannot alter facts.

World-suite pass22 adds read-only `session_bounds` to the authenticated draft,
session/evidence responses and viewer status frames. It includes the selected
policy, `accounting_mode` (fixture, campaign-v1 or legacy), total/video estimates,
reservation and campaign soft/hard limits when applicable. Draft values come from
the validated current packet; original-session values come from its retained
record without renewing authority. The viewer renders exact USD amounts through
six decimal places, distinguishes estimates/reservations from billed usage, and
does not substitute campaign limits for a provider spending cap. No admission,
settlement or persisted session schema changes follow from this display.

Video recording uses the viewer canvas only, bounded MediaRecorder with codec
preflight. Upload chunks to a fixed operation-owned artifact sink using the
same capability; no caller filename/path,<=64MiB session total. If recording
fails, preserve failure and stop; no acceptance based on imagined capture.
Readable keyboard controls/stop/focus and text state accompany color lamps.

## Audit and integration

GAIT records preparation/classification,review hash,send marker,event,stop,
terminal/unknown,usage and review verdict. Private ledger/artifacts remain
primary recovery evidence. Default disabled feature; environment needs
`GEMINI_API_KEY`, `NETCLAW_GENIE_STATE_DIR` (owned private root) and
`NETCLAW_GENIE_ENABLED` (explicit opt-in); no default account or borrowed key.
Viewer address and ports are generated local metadata, not secrets in source.
Provider/model/state root are installation-bound and not supplied by an LLM.

Before distribution, register optional component/skill through canonical
installer/catalog/config,document env placeholders and tool counts,run catalog
coverage and relevant existing regressions. Do not change existing installations
or public UI before the utility gate. [Plan](../plan.md) contains the separate
HUD/VS Code/Mobile decisions and publication boundary.


## Qualified focus-loss recovery — pass11

Ordinary release failure uses the same unknown/stop path as release during stop.
The local audit records each key release attempt and its rejected-send uncertainty;
local key removal prevents replay and never proves remote key release. Stop and
its grace deadline remain independent of a blocked release. Late send rejection
after local cleanup cannot mutate the closed operation. A provider receipt can
settle termination; missing usage remains an admission hold. These are synthetic
source tests, not live provider qualification.


## Recording failure evidence — pass13

Authenticated `POST /v1/sessions/{id}/recording-failure` accepts only `{code}` with
recording_start_failed,recording_failed,recording_upload_failed or recording_limit.
It records one durable entry per operation/code and requests stop, never changing
provider terminal/usage state. Evidence returns `recording_failures:[{code,at}]`;
these entries survive restart and cannot be cleared through this API. No caller
message,path,media or secret is accepted. Recording uploads after failure are
refused. Sink exceptions also record failure and request stop. Browser upload and
failure-report waits are bounded3s, with independent stop and backend deadlines;
failed media chunks are not retried. A failed report remains visibly unconfirmed.
These are synthetic/offline source tests; live generation and acceptance stay gated.

## Foundation-first implementation evidence

Canonical entry: `mcp-servers/genie-worlds-mcp/server.py`; implementation:
`scripts/genie-worlds/mcp_server.py`, official SDK2.3.0 `MCPServer`. Discovery
returns exactly the six names above with closed schemas. Refusals are bounded;
no HTTP redirect, proxy, automatic retry or provider key belongs to the wrapper.
The local backend validates opaque refs, UUIDs and fixed source/event identity.

`POST /v1/drafts` stores immutable request/draft digests in the shared SQLite
ledger. `GET /v1/snapshots`, `GET /v1/drafts/{ref}/facts` and `/styles` are owner
viewer routes; the control bearer is refused. Five private-derived styles remain
local-only, never relabeled synthetic. A registry is operator-owned and binds
absolute snapshot paths to trusted manifest hashes; MCP accepts no paths.

Event/stop replies expose current session state and bounded `control_requests`.
Each control retains its original UUID and a handling result: pending, accepted,
refused or unknown. Handling acceptance does not imply event visibility,
termination or billing settlement. At most32 controls per operation and256 drafts
per state root are admitted. A conflicting projection reference on an existing
start UUID is refused, even when the draft content happens to match.

The viewer's **Review for member start** prepares the existing one-use grant,
displays exact MCP start arguments and watches that original ID for60seconds.
The browser attaches promptly after the MCP starts it; no generation is created
by the watch. Actual Chrome plus actual stdio tests prove this handoff against
fixture media. This is not an LLM member turn or Google qualification.

The original response envelope/schema describes the intended unified contract;
implemented status/evidence return the session fields directly, while preparation
and control requests include schema_version/request_id/status. MCP errors use
`{schema_version:1,status,error:{code,retryable:false}}`. Consumers must use actual
tool discovery and the qualified response fields rather than infer optional
planned billing/acceptance fields. No tool supplies a human acceptance verdict.

## World-suite pass26 viewer event evidence ordering

The viewer uses the original session's `event_state: sent` (the backend's fixed
one-use event send result), then requires media received and decoded after that
status before enabling event capture. In-flight pre-acknowledgement decode does
not qualify. The same status disables duplicate viewer sends after member action.
No refusal, uncertainty or missing evidence triggers an event replay. A readable
status distinguishes send acknowledgement, subsequent frame and unassessed visible
effect. Pass27 adds the backend correlation below; neither layer supplies a
pixel outcome or human acceptance.


## World-suite pass27 backend event checkpoint evidence

Event checkpoint POST additionally requires `frame_sequence`, an active original
session with `event_state: sent`, and an existing baseline. The sequence must be
among the last256 worker frames and have arrived after the manager observed the
original worker's sent status. Missing, old and invented sequences refuse without
writing a checkpoint. The viewer submits its last decoded sequence. No replay or
replacement session repairs missing evidence.

After syncing the immutable JPEG, SQLite retains the original operation/event,
send-marker time, manager acknowledgement-observation time, worker frame time,
sequence and source-frame hash, capture time, JPEG hash/size and
`visible_effect: unassessed`. Evidence returns `event_checkpoint` as unconfirmed,
correlated or incomplete; missing/changed JPEG bytes preserve the receipt while
reporting incomplete. Receipt retrieval survives restart without a new worker.
Unconfirmed historical captures are not retroactively qualified.

Correlation proves backend ordering for the viewer-claimed frame sequence, not
that submitted JPEG pixels came from that frame: Canvas recompresses the image.
Decode completion remains browser evidence. Receipt state does not establish
visible effect, drift, provider termination, usage or acceptance. A crash between
JPEG sync and receipt commit leaves an unconfirmed capture; it is not overwritten.

## World-suite pass29 navigation ordering

Navigation checkpoint POST requires frame_sequence, current active original
session and saved baseline. Sequence must identify a recent worker frame newer
than every frame received by the manager when baseline was written. The body is
fully received before state validation. Refusal writes no navigation capture;
existing capture remains immutable. Viewer supplies its last decoded sequence.
The in-memory baseline barrier is not reconstructed on restart. Navigation does
not create an event receipt. Its retained JPEG manifest is not a durable frame
correlation receipt or proof of10seconds deliberate navigation, viewpoint change,
visual fidelity, provider success or human acceptance.
