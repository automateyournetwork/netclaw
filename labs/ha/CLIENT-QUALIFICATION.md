# R08 actual client qualification drivers

These drivers are source preparation for T038/T039. Importing modules and running
`node --test labs/ha/client_evidence.test.mjs` launches no browser, editor, runtime
or provider. The coordinator alone invokes native phases on the reviewed isolated
cluster. No source test counts as native or REAL execution acceptance.

## Private inputs

Each phase uses a new owned0600 JSON config; the evidence and profile directories
must already exist as owned0700 directories. Never select an ordinary browser or
editor profile. All output artifacts are0600, append-only, and SHA256 inventoried
in the phase report. No private enrollment key is needed.

Common config fields:

```json
{
  "schema_version": 1,
  "classification": "REAL",
  "surface": "browser",
  "phase": "original_result",
  "source_commit": "40-hex-frozen-source-commit",
  "origin": "https://selected-enrolled-border",
  "profile_directory": "/private/owned/browser-profile",
  "evidence_directory": "/private/owned/client-evidence",
  "record_file": "/private/owned/original-records.json",
  "record_sha256": "64-hex-file-digest",
  "counter_file": "/private/owned/cumulative-runtime-counter-export.json"
}
```

Browser adds absolute `playwright_module`, `browser_executable` (or a coordinator-owned
`browser_cdp_url` restricted to `http://127.0.0.1:PORT`) and optional
`headless:false`. Editor uses `surface:"editor"`, the actual retained `profile_id`
for recovery, and `extension_sha256` pinning `dist/extension.cjs`. The launcher
uses `profile_directory` as actual Code user data and requires Code1.109. Browser
uses standard TLS trust, with no certificate-error flag. Editor retains strict
Node HTTPS validation and disables Electron fetch substitution in the isolated
profile. Any custom CA must be installed/provided by the coordinator before launch;
these drivers neither install trust nor relax TLS.

The SHA-pinned record bundle contains:

- `schema_version:1`, `classification:"REAL"`, matching `source_commit`.
- `descriptor`, previously pinned `pin`, and exact cluster `principal`.
- `completed`: `reference` with original `operation_id`, `client_nonce` and
  `decision_sent:true`; complete immutable `review`, `review_digest`,
  `attempt_count:1`, original `result_envelope`, `ack_envelope` and
  `member_certificate`.
- Optional `stale`: original pending reference/review/digest and
  `attempt_count:0`, for the stale-review phase.

The helper verifies the manifest, result and ACK P256 signatures/domains, selected
endpoint and original identities. The current counter export must be the actual
runtime's cumulative counter artifact; the harness reads it before/after and
refuses any change during recovery phases. The coordinator retains provenance and
independent model/MCP counter evidence. Classification text alone is not proof.

## Original operation phases

`phase:"original_once"` requires an absent absolute `once_file` inside an owned
private directory. The driver claims it with exclusive creation before preparing;
any second invocation refuses. Never remove that lock to retry an unknown result.
Use recovery phases with the original profile/IDs instead.

This initial bundle replaces `completed` with `selection` (exact catalog_revision,
member_id,model_profile_id,tool,arguments) and `expected_review` containing exact
principal/member/model_profile/tool_call. The actual UI creates its own nonce and
operation. Both drivers persist the outgoing prepare nonce, complete returned
review, and exact operation ID/revision/digest/sent marker before approval reaches
transport. Only one prepare and one exact approval are allowed. A lost response is
recorded as unknown without a second mutation. `acceptance_complete:false` means
this phase records original native submission only; a later original-result phase
must correlate the original signed receipt/ACK and cumulative real counters.

`phase:"prepare_review"` follows the same one-shot preparation but sends no
approval. It leaves a real pending review in that same native profile for the
coordinator's later leader change and `stale_review` phase. This is a pending
control record, not another claimed provider or native-tool effect.

## Recovery phases

Run one bounded phase per invocation while the coordinator owns fault sequencing:
`authority`, `no_quorum`, `stale_review`, `original_result`, `endpoint_recovery`,
`cold_recovery`. None sends a mutation. They refuse new preparations, decisions,
reconciliation, redirection or replay. A read-only status failure remains failure;
there is no synthetic status replacement.

Browser explicitly imports original IDs through the product's status-only UI when
needed. Another origin never receives copied sessionStorage. `cold_recovery`
requires the same origin/profile's previously retained sent marker. Chromium
sessionStorage lifecycle may require an actual same-tab reload session; a new
process does not imply browser sessionStorage restoration. The driver refuses a
missing marker rather than seeding one. For a same-tab reload journey across
separate driver invocations, use the same coordinator-owned CDP browser; the
driver selects the existing exact-origin tab and disconnects afterward.

Editor recovery requires the actual profile and original references left by the
original native phase. It never seeds internal state. Endpoint recovery drives
the actual Replace cloud Border endpoint picker/input/modal, verifies the old/new
node installations and stable cluster/profile, then uses native retained recovery.
A stale review must be locally ineligible for a decision. No-quorum retained status
must expose its last-observed warning and cannot trigger reconciliation.

Browser invocation: `node labs/ha/client_qualification.mjs /private/config.json`.
Editor uses the existing `extensions/netclaw-vscode/scripts/cloud-editor.mjs` with
`NETCLAW_CLOUD_SCENARIO=ha`, `NETCLAW_CLOUD_CONFIG`, `VSCODE_EXECUTABLE` and
`NETCLAW_TEST_PLAYWRIGHT`. The launcher report and phase evidence retain failures,
original references and screenshots; an unsuccessful run never authorizes replay.
