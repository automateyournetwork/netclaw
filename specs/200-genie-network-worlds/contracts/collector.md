# Local collector process contract — pass03

This is a local Python API, not an MCP adapter-path tool or a read authorization.
Run collector.py through the selected Python3.12 interpreter. Native read policy
must be qualified before using any real adapter; a marker alone is not proof.

`collect(devices, capability_path, parser_version, evidence_root=private_root)`
loads an operator-selected Python module in a fresh subprocess per read. The
module exports `qualified_read_only_capture=True`,
`capture_once(device, command, timeout=seconds) -> str` and
`parse_captured(device, command, output=captured_text) -> dict`.
The parser must use only supplied output, never device execution. The adapter
must bind frozen inventory/trust and the existing selected-runtime read policy;
no raw SSH fallback, session setup commands or transport retries are implied.
No native adapter is shipped or qualified by pass03.

Default initial profile: four devices, three exact commands, two child processes,
serial reads per device,30s per read including import/capture/offline parse and
180s collection deadline. Local teardown may add process-reaping overhead
(up to1s per child); timeout never proves remote command termination. Timeouts
and capture loss retire the device for the rest of this collection; other devices
continue. No restart/resume/replay API exists. Retained unknowns must be reviewed
before future native work; this scheduler is not a durable operation ledger.

Fresh processes use the parent's explicit interpreter and POSIX owned process
groups. SIGKILL ends the group, including descendants that stay in it. An adapter
must not daemonize/escape its group. No forked credential/session state is reused.
Windows is refused; only this Mac/Python3.12 fixture boundary is qualified.

Private0700 evidence_root contains0600 per-read request, capture-started marker,
raw and result files. Atomic writes distinguish complete from partial captures.
A locked shared budget reserves bytes before writing, bounding total retained raw
evidence to8MiB across workers. Parsed transport is separately bounded8MiB/read.
Adapter stdout/stderr are discarded; exceptions are never echoed. Artifacts are
retained for review, referenced by opaque directory name. Source tests use only
synthetic data and temporary directories under ignored .spec200-local/tests.

`complete` describes attempted collection coverage, not success or health.
Observed/empty/parse_failed/raw_only/timeout/unavailable are distinct; budget
rejection uses unavailable plus failure_reason=evidence_limit. A durable
capture-started marker without a complete raw artifact sets
capture_outcome_unknown=true. Internal Python records include private raw/parsed
payloads; they must not be returned as the public closed observation/MCP schema.
Final source/snapshot identity binding and public-envelope adaptation remain T016.

## Explicit detailed profile — pass14

`collect(..., profile='detailed')` selects the fixed six reads per device:
show version, show ip interface brief, show lldp neighbors detail,
show cdp neighbors detail, show interfaces, show interfaces. Default remains
initial; arbitrary profiles/commands are refused. Detailed overall deadline is
240s (initial180s); both retain30s/read,two children,four devices,8MiB raw bound.
Lower overall deadlines are allowed for fault drills. The second interface read
cannot start until at least10s after the first child has completed capture and
offline parsing. The wait occupies no worker and remains inside the overall
deadline. No API can shorten this gap. Each interface read has sample_index1/2,
and request/observation records preserve profile and zero-based command_index.
These are separate planned samples, not retries. Unknown/timeouts still retire
the device; native policy qualification and durable recovery remain open.

`normalize(..., profile='detailed')` accepts the24-record envelope and preserves
coverage. Observed interface payloads and unsupported CDP shapes yield explicit unknown
facts with normalization_unqualified; they are never interpreted using the LLDP
schema or converted into rates. The pass15 CDP extraction below supersedes the
earlier all-CDP-unknown checkpoint. Empty/failed/raw-only outcomes retain their meanings.
Native parser extraction, identity/continuity and graph binding remain T017.
Synthetic process tests qualify this scheduler only, not an installed native adapter.


## Offline CDP extraction — pass15

Detailed normalization recognizes IOS-XE Genie CDP detail index plus exact
total_entries_displayed. Retains up to256claims with source paths,protocol,
exact local_interface/device_id/port_id,typed remote identity,hold_time_seconds
and actual supplied capture interval. Missing or unsafe identity fields stay
null/unknown; never shorten or sanitize an identity into a match. Extra parsed
fields such as addresses/software are not propagated. Unknown shapes/count
mismatch remain normalization_unqualified. Reported zero is an observed count,
not evidence of universal absence. Failed/empty collection outcomes stay distinct.

Claims remain unresolved without qualified inventory bindings. Hold time is only
a reported integer; expires_at stays null without qualified acquisition timing.
The installed25.2 parser was exercised offline with independently synthetic text
and a device.execute trap. This is not native capture/read-policy qualification
or a normalization-to-resolver bridge.

## Offline interface extraction — pass16

Detailed normalization now returns interface_observations for the installed
IOS-XE ShowInterfaces top-level interface mapping, bounded to256rows per read.
Unrecognized/empty/malformed shapes remain normalization_unqualified. Unsafe
names are refused without truncation. These names are parser-reported; Genie
expands names internally, so they are not qualified native identity aliases.
resolved_interface_id remains null pending the inventory binding stage.

Each reading retains observation/device/hash/parser provenance and the supplied
capture interval. enabled,oper_status,line_protocol retain separate exact paths
and values; missing/invalid fields stay unknown. Genie derives oper_status from
line_protocol, so this is not independent physical-link evidence. No combined
health verdict is inferred. Description/address/BW fields are excluded; reported
BW is not qualified directional capacity.

Four bounded counter fields (in/out_octets and in/out_pkts) retain exact unsigned
decimal strings and paths. Zero is observed only when actually supplied; invalid
or absent fields are null with explicit reasons. Values must be parser integers
within unsigned64-bit range; that bound does not establish hardware counter width.
sampled_at,width,incarnation stay null. No rate,utilization,continuity or actual
sample instant is invented from capture finish time or increasing counters.
Installed Genie25.2 was exercised with synthetic text, JSON transport round trip,
and a device.execute trap. Native capture policy and graph binding remain open.


## Offline LLDP extraction — pass20

Both profiles now recognize installed IOS-XE ShowLldpNeighborsDetail total_entries
plus interfaces/port_id/neighbors. Exact count agreement is required; malformed
shapes and collapsed duplicate parser keys stay normalization_unqualified.
Each container and aggregate claims are bounded256; oversize is refused, never
truncated. An observed zero count differs from failed/empty collection and does
not prove absence beyond the reported table.

Claims retain protocol=lldp, field paths, capture interval and parser provenance.
remote_claim comes only from chassis_id with remote_identity_kind=chassis_id;
remote_port comes only from port_id with remote_port_kind=port_id. System-name
keys are not chassis aliases. Missing, oversized, control-bearing and placeholder
identities stay null/unknown. Contradictory nested keys/fields are unqualified.
Descriptions, addresses and other unrelated parser fields are excluded.

Genie expands interface spellings and omits on-wire identity subtypes; both
chassis_id_subtype and port_id_subtype stay null. Text format cannot supply these
subtypes. Native inventory aliases still require proof. Valid time_remaining is
retained as hold_time_seconds, but expires_at stays null without qualified timing.
No resolved device, link or health is invented. Installed25.2 synthetic offline
normal/empty/duplicate-collapse qualification has zero device.execute calls.
LLDP graph assembly, native policy and actual collection remain unqualified.


## Internal native read/parse seam — pass24

native_read.py is not an operator-ready collector module: it intentionally has
no qualified_read_only_capture marker and does not connect or load credentials.
A future frozen native adapter may call capture_once(server,device,command,
timeout=...,source_sha256=...) only after validating selected source/dependencies,
minimal frozen testbed,strict saved SSH identity and safe connection setup.
The source digest is from reviewed operator metadata, never caller/model input.
The five unique fixed profile commands intersect the exact native validator
contract (None permits; all other returns/exceptions refuse). Source origin/hash,
IOS-XE platform, existing connection policy/exec state and <=30s timeout are checked.
No protected validate_arguments/execute_once policy is modified or invoked.
One execute returns raw text for durable capture; no parser, retry or reconnect
fallback occurs there. The outer collector remains responsible for command-index,
profile, concurrency, deadlines, unknown retirement and private byte limits.

parse_captured(command,output=...) constructs the allowlisted IOS-XE parser with
an OfflineDevice containing no live device/session/testbed/credentials. If any
parser tries execute (including on empty text), it fails without device I/O.
Caller preserves raw and reports parse_failed, never recaptures. Installed Genie25.2
source/offline qualification covers interfaces/CDP/LLDP synthetic text; all five
classes resolve. This does not qualify show-version/brief semantic extraction or
native connection/identity behavior. A connected-device posture check alone is
not evidence that prior setup sent no commands. Native qualification remains gated.


## Frozen native preparation — pass25

Internal native_connection.prepare_device accepts an already-parsed <=64KiB
minimal single-device dictionary and operator-frozen document/endpoint digests.
This is a local Python seam, not a tool/approval/collector adapter. Input must be
IOS-XE/IOL with exact SPEC200_PYATS_USERNAME/PASSWORD/ENABLE_PASSWORD ENV references,
one strict SSH endpoint and an owned private trust file whose digest is frozen.
Names/types are inert; custom hooks/classes, extra devices, per-connection secrets
and trust-path shell metacharacters are refused before topology load. Existing
protected_pyats native dependency/source checks are reused without calling or
changing its show-version-only argument or execution policy.

The installed loader resolves those scoped environment references locally. pyATS
adds inherited Credentials to the loaded connection; these must equal the native
testbed credentials. Native objects are retained, not serialized or logged. Loaded
endpoint/platform/freshness must match. PreparedDevice.connection_options(timeout)
rechecks endpoint/trust/freshness/inheritance and supplies existing no-init-command,
no-learning, no-reconnect policy with <=30s timeout. It NEVER calls connect or execute.
Caller still must bind selected native read-policy source, provide private logging,
use collector process/deadline/unknown controls, establish the actual connection
and prove exact emitted commands before qualification. No qualified_read_only_capture
marker is exported. Synthetic installed-loader proof is not actual SSH acceptance.


## Native connection lifecycle — pass26

Internal native_session.connected_capture composes PreparedDevice with the native
read seam. It checks the selected read policy and frozen connection options before
connection, reserves a fresh exclusive0600 log in an owned0700 directory, disables
stdout logging, connects once and executes once. Raw output is yielded so the
caller can preserve it durably BEFORE leaving the context or parsing. Disconnect
is attempted once even after partial connection failure. Capture/cleanup exception
text is sanitized; a cleanup failure after a primary error is retained as a bounded
exception note without replacing the primary error. No success is returned after
cleanup failure. Existing files, symlinks, hardlinks and public log parents refuse.

This is an internal synchronous building block only, with no qualification marker
or launcher. It MUST run inside the collector-owned child/deadline boundary; connect,
execute or disconnect can block and local cleanup cannot prove remote termination.
The native logger reopens its reserved path, so exclusive ownership of the private
directory throughout the child lifetime is required. Synthetic device checks do
not qualify native transport/emitted commands or actual SSH. The protected
show-version-only grant and native read policy remain unchanged.


## Capture context and cleanup uncertainty — pass27

An operator adapter may now supply
`capture_context(device, command, timeout=seconds, evidence_directory=Path)`
instead of capture_once. It returns a synchronous context manager yielding exactly
one raw string. The child reserves the shared byte budget and atomically preserves
raw INSIDE that context, then exits it before offline parsing. The owned private
per-read directory is available for native_session's fresh connection log. This
is a composition interface, not a qualified native adapter or authorization.
The existing capability marker remains required. A present context never falls
back to capture_once when entry, capture, preservation or cleanup fails.

Durable lifecycle-started/lifecycle-finished markers distinguish cleanup from
capture. Incomplete lifecycle sets cleanup_outcome_unknown and retires all pending
reads for that device even when complete raw exists. Preserved raw remains raw_only
(or timeout on deadline); no parsed success can hide cleanup failure. Other devices
continue. A byte-budget refusal still exits/cleans the context and skips parsing.
Parser loss after clean cleanup remains distinct from capture/cleanup uncertainty.
The same child process-group deadline bounds connect, execute and disconnect;
local termination never proves remote completion. Legacy capture_once adapters
retain their prior contract and must themselves guarantee cleanup before return.
Synthetic subprocess tests establish ordering/fault behavior only. Frozen native
source/inventory, strict SSH identity, emitted-command qualification and installed
adapter composition are still required before any real device operation.


## Independent native transport harness — pass28

`tests/genie-worlds/offline_native_transport.py` exercises the installed pyATS
loader and pinned IOS-XE/IOL Unicon plugin against an independent local PTY peer.
It uses the selected server's exact extracted read validator without importing
the operational server. Every nonempty line received by the peer must equal the
one requested command, once. All five allowed commands are covered. An initial
disable prompt must be refused without attempting enable or another command.

The command-based transport exists only in the test harness. It is not accepted
by frozen production preparation and never opens SSH or a device connection.
This evidence cannot qualify SSH host identity/authentication, a real device's
prompt/behavior, the collector's full frozen adapter or native acceptance. Source
and dependency pinning remain unchanged, including protected show-version-only
arguments. Initial direct-Unicon harness failure is retained; the lifecycle
expects a pyATS Device, not the raw Connection is_connected boolean property.


## Internal frozen adapter composition — pass29

native_adapter.FrozenCapture accepts an operator-owned single-device document,
frozen document/endpoint/source digests and the selected native policy module.
It copies the document without loading credentials at construction. Its
capture_context and parse_captured methods match the collector child interface.
Before preparation it revalidates the selected native command policy; preparation
and connected_capture retain all existing frozen trust/plugin and log checks.
The raw value is yielded for the child's durable preservation before disconnect.
Only clean context exit permits parsing the exact device/command/byte digest.
Any attempted context consumes the instance even on refusal; no local retry.

This internal class intentionally exports no qualified_read_only_capture marker
or launcher. It is not a durable authorization/unknown-outcome ledger: constructing
another instance does not grant retry. Use only inside the existing parent process
boundary and reviewed operator capability. No credential-file loader or native
server import is provided. Synthetic tests substitute prepared devices and one
child module loader; actual subprocess import, native transport with this full
composition and SSH identity remain unqualified. Protected show-version-only
policy is untouched. No installed/native acceptance follows from these tests.


## Fresh subprocess qualification — pass31

`tests/genie-worlds/offline_native_collector.py` accepts the selected upstream
policy source path and runs under the selected Python3.12. It copies policy bytes
into an owned synthetic fixture, compiles only the native validator/constants,
and exercises actual collector subprocesses plus frozen preparation. Only this
fixture substitutes an independent local PTY AFTER native endpoint/plugin/trust
validation; sockets are denied and no production adapter capability is installed.
The exact three initial reads occur once in three distinct children, raw persists
through two intentional parse failures, and the LLDP native parser succeeds.
Copied source mutation/frozen inventory drift cause zero commands. A disconnect
failure preserves raw and cleanup uncertainty, forbids parse and retires the device.
This does not qualify actual SSH identity/authentication, selected devices, dynamic
inventory provenance, public tool envelopes or durable cross-invocation recovery.


Owner routed-lab expansion: see [complete collection/verification command table](../collection-commands.md). The six-read source profile is not silently broadened by this document.
