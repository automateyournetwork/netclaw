Status: coordinator-adopted design; implementation and live qualification pending.

# Protected operation contract v1 — R02

Use existing P-256/SHA-256 identity primitives and enrolled public-key pins (`risk.py:112,135,234,253`). No new signing key service or cryptography dependency. Never treat a certificate embedded in a message as its trust anchor. Store the authority generation/pin used for each approved operation; old receipts may be reconciled against that recorded trust snapshot without authorizing fresh work after revocation.

All signed messages have exactly `{schema, payload, signature}`. `signature` has `{algorithm: "ecdsa-p256-sha256", key_id, value}`; `key_id` is the lowercase SHA-256 public-key fingerprint, `value` is base64url DER ECDSA with no padding. Reject unknown algorithms/fields, wrong schemas and invalid fingerprints before domain processing. Signature verification always resolves the trusted key from enrolled authority plus the operation's recorded generation.

Canonical bytes: UTF-8 JSON of `{schema,payload}`, sorted ASCII object keys, compact separators, no ASCII escaping of ordinary Unicode values, no BOM/trailing newline. Object keys are the fixed schema keys; reject duplicate keys and invalid Unicode. Values are strings, booleans, null, lists, objects and bounded integers; no floats/NaN/infinity. Timestamps are integer UTC milliseconds. Do not normalize/trim/rewrite tool argument strings after review. Python Border/member code owns canonicalization; the HUD receives the server-produced review digest and never computes authority. Include canonicalization/signature golden vectors, including Unicode strings.

Sign `b"netclaw.r02/" + schema.encode("ascii") + b"\0" + canonical_bytes`. Distinct schemas provide approval/result/ACK domain separation. Logical approval/result hashes are SHA-256 of canonical signed payload bytes, excluding the ECDSA signature: re-signing the same payload must not create another logical approval/receipt.

### Shared immutable objects

- `principal`: `{issuer: "local", subject, display_name, roles}`; stable configured owner subject, sorted unique server-assigned roles. Full object is frozen in approval and result; client display changes cannot rewrite history.
- `border`: `{installation_id, identity, key_id, authority_generation}`.
- `member`: `{installation_id, member_id, key_id, enrollment_generation}`.
- `model_profile`: `{profile_id, profile_revision, runtime_kind, runtime_version, provider, model, guard_policy_sha256}`. Every value comes from qualified member capability data; no silent model fallback. Signed effective profile must match what actually executes.
- `tool_call`: `{tool, tool_schema_sha256, arguments, arguments_sha256, device_ref, inventory_revision, endpoint_sha256}`. Arguments are the entire resolved read-only tool input. Endpoint digest covers the reviewed non-secret connection identity, not credential contents. Do not claim host-key verification unless actually implemented and evidenced.
- `limits`: `{expires_at_ms, inference_timeout_ms, tool_timeout_ms, max_inference_calls: 2, max_tool_calls: 1, max_output_bytes}`. Values must fit the qualified profile; retries are explicitly pinned inside tool arguments/policy.

### Approval payload — `netclaw.execution.approval.v1`

`approval_id`, `operation_id` (stable UUIDs); `nonce` (random 256-bit base64url); `issued_at_ms`; `principal`; `border`; `member`; `model_profile`; `tool_call`; `limits`; `change_request_ref: null`; `review_sha256`.

`review_sha256` hashes the full immutable owner review object before signing. The member recomputes every digest and verifies the full binding, active trust and supported policy. Border source record and signed payload must match. A reused nonce, changed payload or reused approval under a different operation is a conflict. Return only existing state for a byte/logically identical admitted operation.

### Terminal member result — `netclaw.execution.result.v1`

`receipt_id`; `operation_id`; `approval_id`; `approval_sha256`; `attempt_id`; `principal`; `border`; `member`; `model_profile`; `tool_call_sha256`; `started_at_ms`; `finished_at_ms`; `outcome` (`succeeded`, `refused`, `failed`); `effect_status` (`not_started`, `finished`); `output` (bounded sanitized structured tool evidence and optional model answer); `output_sha256`; `tool_evidence_sha256`; `usage` (known numeric usage or explicit unavailable); `audit_refs` (approval/dispatch/result correlations); `error_code` (bounded enum/null).

A crash/timeout after possible effect has no invented terminal result: it remains `outcome_unknown` until existing evidence proves a terminal result. Do not overwrite a terminal result with a later model turn. Persist one immutable terminal receipt per attempt; competing hashes for the same attempt are a conflict, never last-writer-wins. Signature establishes attribution/integrity, not that the model's prose is true; the actual tool evidence still needs independent validation.

### Border acknowledgement — `netclaw.execution.ack.v1`

`ack_id`; `operation_id`; `approval_id`; `attempt_id`; `receipt_id`; `receipt_sha256`; `border`; `member`; `accepted_at_ms`; `audit_ref`.

The ACK is signed by the pinned Border authority and persisted atomically with the accepted receipt link before transmission. Reconciliation returns the same receipt/ACK identities and hashes. Repeated matching ACKs are idempotent; mismatched IDs/digests/generations are refused. No new inference, tool call or approval is issued during ACK repair.

## Durable transitions and storage boundaries

Keep the existing SQLite/audit architecture. Add operation/approval/attempt/result/ACK records or columns there; do not create an independent competing audit system. SQLite constraints enforce unique operation, approval nonce, attempt and accepted receipt. Use transactions and compare-and-swap claims; an in-memory worker map is insufficient. Never hold a SQL transaction over a provider/device/network wait.

- **Border:** `review_pending -> approved -> dispatch_pending -> member_admitted -> result_pending -> completed|refused|failed`. Uncertain send or execution enters `reconciliation_required`; lookup by original operation restores known state. `completed` requires successful verified receipt + durable ACK + required audit. ACK transmission can remain pending after this commit.
- **Member:** `admitted -> executor_claimed -> effect_claimed -> result_ready -> acknowledged`. Model refusal/no-call can terminate as a signed no-effect result. `executor_claimed` is persisted before any guarded provider invocation; `effect_claimed` is persisted before calling the integration. On restart, either claim without conclusive receipt becomes `outcome_unknown`, never runnable. No extra provider turn may reconstruct missing evidence.
- **Cancellation:** before executor claim, atomically cancel without effect. After possible dispatch, request cancellation but report unknown until the child/tool status proves otherwise. Cancelled synchronous pyATS work may continue in an executor thread (`scripts/pyats-managed.py:29`); do not release the execution fence while it may still run.
- **Revocation:** durably mark the approval revoked; effect claim checks active authority/expiry and operation authorization. Record which claim won a revoke/claim race. Receiving a late authentic historical receipt does not authorize new work.
- **Files:** immutable private artifacts, file fsync + directory durability where applicable, then transactional references. Orphans are inspectable garbage; a missing referenced artifact never becomes success. Preserve spent claims when result/audit writes fail.

Required RPCs over the existing trusted iN2N channel: `execution.submit(approval)`; `execution.status(operation_id)`; `execution.result(operation_id)`; `execution.ack(ack)`; operation-bound authorization/revocation lookup. No caller-supplied principal overrides. Lookups are owner/Border/member-generation bound; task IDs and filenames never grant access.

HUD contract: create immutable review; approve `{operation_id, review_sha256}`; read status/result; reconcile existing operation; revoke/cancel with explicit semantics. Stable client request ID and server operation ID survive double-click/refresh. HTTP transport retry must not manufacture a new operation. The Python service, not the browser, signs and validates authority.


## Canonical service/API boundary

An opt-in `N2N_PROTECTED_OPERATIONS=1` profile starts a purpose-built operation
service beside the selected federation service. Missing private configuration or
unsupported role/runtime is a refusal, never legacy fallback. Default installations
are unchanged. A protected member rejects legacy agentic/tool invocation surfaces
before inference/effect; only the new signed operation route can execute.

New modules `protected_contract.py`, `protected_store.py`, `protected_service.py`
implement signatures/validation, SQLite atomic state and channel orchestration.
Use a dedicated SQLite connection to the existing installation federation.db,
additive tables, FULL synchronous commits and unique constraints. No transaction
is held across network/model/device waits. Lifecycle recover never schedules an
executor for already-claimed operations. Preserve tombstones indefinitely for
this feature (no automatic purge). Signed envelopes are at most 1 MiB of UTF-8 JSON; output is at most 512 KiB
and arguments at most 64 KiB, each measured as canonical UTF-8 JSON. Refuse an
oversized candidate before signing. If actual output exceeds its bound, retain
private raw evidence and emit a bounded failure receipt with an overflow code and
evidence digest; never silently truncate signed evidence. Identifiers are at most
200 characters; signed time fields are integer milliseconds.
No Python default=str conversion of signed content. Strict JSON decoding rejects
duplicates, nonfinite numbers and unexpected fields.

A private configured catalog supplies supported model/tool/device profiles with
non-secret revisions, endpoint hashes and known read-only argument policy. For R02
the only live tool is the protected execute-once adapter, exposed through MCP
as `pyats_run_show_command` with exact arguments `{device_name, command, timeout,
retries}`. The catalog pins its complete schema and adapter source revision;
`command` must be `show version`, `retries` must be 1 (one total attempt), and
`timeout` and `device_name` must match the reviewed profile. Execute once, then
parse captured output. Preserve the upstream tool for other profiles. No
arbitrary shell, URL, executable, server, file or argument default comes from the
browser/model. The broker independently matches the entire normalized approved
call and rechecks current catalog/profile revisions before its effect claim.

Trusted backend methods for the HUD bridge:

- `catalog({auth_context})` -> `{revision, members:[{member, model_profiles, tools}]}`.
- `prepare({auth_context, client_nonce, catalog_revision, member_id,
  model_profile_id, tool, arguments})` -> public operation DTO.
- `decision({auth_context, operation_id, revision, review_digest, decision})` where
  decision is approve/deny. First valid transition wins; identical repeated
  decision returns state and NEVER resends execution.
- `status({auth_context, operation_id})` or
  `status({auth_context, client_nonce})` -> owned DTO, no dispatch.
- `reconcile({auth_context, operation_id})` -> read existing member state/receipt and
  retry only an existing acknowledgement; never submit or invoke an executor.
- `revoke({auth_context, operation_id})` -> durable revocation and existing status.

The configured single owner is exactly `{issuer:"local",subject:<stable UUID>,
display_name:<configured string>,roles:["owner"]}`. Every operation method,
including catalog, prepare, status and reconcile, requires an active, owned
`auth_context: {principal, auth_generation, session_hash}`. Verify installation,
principal, generation, absolute and idle expiry, and revocation under the owner
lock. Read access checks do not authorize an effect; decision/dispatch additionally
hold the same lock through their final active-session check and durable claim.
Never hold that lock during external I/O. Recheck access before returning data
following external I/O. No conversation cookie, loopback reachability, forwarded
identity header or agent prompt supplies this authority.

Private transport uses a fresh random server bearer held only by the HUD and
backend. Store it in the owned private `protected-operator.env`, loaded by those
trusted processes as `NETCLAW_PROTECTED_OPERATOR_TOKEN`. Never include it in the
agent environment. Descriptor `<runtime>/netclaw-federation/protected-operator.json`
contains only `schemaVersion:1`, `installationId`, loopback `port`, `generation`,
and `credentialVariable:"NETCLAW_PROTECTED_OPERATOR_TOKEN"`; no bearer value.
The environment file is a fixed sibling, not a client-provided path. Validate
ownership, regular-file type, no symlinks, 0600 file modes and 0700 parent mode
for both files. Use HTTP POST `/operator` with strict `{method,params}` and
bounded framing; no arbitrary routing. These calls are private server-to-server
traffic. Missing, foreign or stale bindings fail closed. The backend rechecks
the active owner context and operation ownership independently of the HUD.

Public operation DTO includes `operation_id`, `client_nonce`, `revision`,
`state`, `review_digest`, immutable `review`, approval metadata (ID/digest/expiry,
not bearer), `attempt_count`, `reconciliation_required`, `may_have_executed`,
`result` (verified boolean,digest,durable_ack,ack_delivery_pending,evidence),
`error_code` and `allowed_actions`. Never private key, signed bearer approval,
internal path, token or raw exception. Review carries principal/member/model/
tool_call/limits exactly as signed. The browser does not canonicalize or sign it.

Channel methods use existing authenticated iN2N connections only:
`execution/catalog`, `execution/submit`, `execution/status`, `execution/result`,
`execution/ack` on the member; `execution/effect-authorize` on the Border. Verify
current channel identity, possession and registered member key/generation for
each call. No eN2N/mobile access to this profile. Fresh effect authorization binds
operation, approval digest, attempt and tool-call digest; Border atomically wins
revoke-versus-effect authorization and returns the same answer for exact duplicate
lookups. Absence or lost response does not permit the effect. Revocation after
that claim cannot undo the operation; record the order honestly.

Trusted executor callback provided by the runtime adapter:
`await executor.run(approval_payload, gate)` returns bounded
`{output, tool_evidence, usage, effective_model_profile}`.
Start it only after a durable executor claim and required GAIT. The broker calls
`await gate(proposed_tool_call, invoke_exact_effect)` immediately before its sole
MCP integration invocation. The gate validates the entire approved call, requests
fresh Border authorization, records mandatory GAIT, atomically claims the effect,
and invokes the trusted integration callback exactly once. It retains the actual
result independently of agent prose. A failed check, second invocation or changed
call refuses. The adapter counts provider/tool operations and never retries a
potentially dispatched call. Uncertain cancellation includes worker threads or
children still running. Validate the executor result against retained tool
evidence; model prose is never the authoritative show result.

## Audit and failure policy

Extend existing GAIT event data with structured principal, operation, approval,
attempt and receipt digests. Serialize append/git operations across processes with
an owned lock; no second audit subsystem. Required pre-approval/pre-executor/
pre-effect audit failure refuses that new boundary. Post-effect result/audit
failure preserves spent claims and recoverable evidence; no success until required
result audit and durable acknowledgement complete. Never overwrite a prior
terminal receipt. Separate authentic execution failure, refusal and uncertain
outcome; only evidence proves nonexecution. Reconciliation uses recorded historical
key snapshots for old result verification while revoked generations may never
approve new work.

## Frozen revisions from independent architecture review

Border signing uses the CA-attested hub credential, not its unrelated self key.
Member signing uses the enrolled member self key. Add random durable
`enrollment_generation` on every successful enrollment (including same-key
re-enrollment), return/store it on the member and bind it in protected catalogs,
approvals and channel checks. Legacy enrollment remains compatible; a missing
generation makes the new protected profile unavailable until explicitly renewed.
Never silently re-enroll an existing installation. Border authority generation is
private, explicit configuration; old receipts use operation-recorded trust only.

Reconciliation MUST NOT resend an approval or call submit: it may only query the
existing operation and resend an already-persisted result ACK. Unknown submit
outcome with no conclusive member record remains unknown. Initial decision may
perform exactly one submit after durable intent; no worker restart retries it.

The effect gate is `await gate(proposed_tool_call, invoke_exact_effect)`: it
validates the entire approved call, requests fresh Border authorization, records
mandatory audit and atomically claims the effect, then awaits the provided trusted
integration callback once. The adapter cannot signal success by calling a marker
and manufacturing a result. Preserve raw tool-call/result evidence independently
of agent prose. Two guarded model calls maximum; one effect maximum; max output
512KiB. No provider retry after a call may have been accepted.

Private owner authority is implemented in Python `protected_owner.py`, used by
both the trusted nativeCLI and fixed privatebridge authmethods. SQLite lives at
`<runtime>/netclaw-federation/protected-owner.sqlite`:
- `owner_meta(id INTEGER PRIMARY KEY CHECK(id=1), installation_id TEXT,
  generation INTEGER, principal_json TEXT)`.
- `owner_ticket(ticket_hash TEXT PRIMARY KEY, generation INTEGER,
  expires_ms INTEGER, consumed_ms INTEGER)`.
- `owner_session(session_hash TEXT PRIMARY KEY, generation INTEGER,
  csrf_token TEXT, created_ms INTEGER, expires_ms INTEGER, last_seen_ms INTEGER,
  revoked_ms INTEGER)`.
Allfields except nullableconsumed/revoked timestamps are required. Sessionhash
isSHA256 of raw32bytebase64urlcookie encodedUTF8. NativeCLI andbackend serialize
authority mutations using flock at sibling `protected-owner.lock`; backend holds
the same lock through finalsessioncheck plus durabledecision/dispatchclaim. No
network/model/toolwait underlock. Database/lock owner/no-symlink/0700/0600checks.

Privatebridge authmethods (not modelregistered):
- `owner.login({ticket})` -> `{cookie,csrf_token,principal,auth_generation,
  session_hash,expires_ms,installation_id}`; atomicallyconsume, oneuse.
- `owner.session({cookie})` -> sameprojectionwithoutcookie; enforceabsolute/idle
  expiry/revocation/configgeneration andrefreshlastseen.
- `owner.logout({cookie,csrf_token})` -> revoked; constant-timeCSRFcheck.
- Mutationauthcontext includes `{principal,auth_generation,session_hash}` after
  HUDvalidatesOrigin/CSRF via `owner.session`. Backend verifiesownedactivecontext
  again whilelocked immediatelybeforedecision/dispatchclaim. Ownerauthority never
  trusts fields directly from browser. Other bridge authmethods are notexposed.
- CLI `scripts/protected-owner.py init|ticket|revoke` operates trusted selectedhome;
  ticket rawvalue onlylocaloperatoroutput; no write path throughmodel/browser.

HUDbridge operations carry server-only `auth_context`; no clientprincipal accepted.
Backend validates active session/installation/generation/expiry/idle/revocation
beforefinalnewauthorityclaims. Approved operationsretain immutableprincipal after
sessionexpiry; freshsameowner session may reconcile. Revocationbeforeclaimrefuses;
revocationafterclaim cannotretroactivelyundowork. Node stores no competingauthority
DB; it is a strict HTTP/sessioncookie facade over these fixed privatemethods.

Runtime trusted inference admission facade accepts only POST
`/v1/chat/completions` with an operation-scoped token, strips all caller routing
and provider-auth headers, pins model/profile, durably caps modelcalls and supplies
its private DefenseClaw authentication only on the internal guard hop. Agent
never receives a broad DefenseClaw token. OpenClaw official native streamableHTTP
MCP path exposes only the scoped broker tool. Pin actual protocol support before
live acceptance; no vendor source patch or Thermidor runtime reuse.

The pinned pyATS upstream's parse-then-execute fallback can send a command twice.
R02 must use a narrowly scoped protected MCP adapter that executes showversion
once, then parses the captured output without reissuing it. Preserve normal
upstream behavior for otherprofiles. Review/disable config init commands and
record connection setup separately from the one approved show effect. The exact
adapter/tool-schema revision is part of the signed catalog; never claim one wire
command from a single high-level broker invocation alone.
