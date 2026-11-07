# R08 REAL rehearsal runner

This is coordinator-operated qualification source. It is not an installation
guide and does not itself close T035–T040. Do not run a mutation before the
matching fixture/source gate passes. The source tests create temporary files
only; no model, Docker daemon, native client or retained runtime was started.

`python -B -m labs.ha.real_runtime --help` is inert. `prepare --plan <private.json>`
creates a **new**, externally located 0700 run root. All subsequent commands must
run from that run's immutable `source` directory using the reviewed Python.
No phase automatically advances to the next, and a claim file makes a start or
approval one-shot. An interrupted phase is inspected with its original IDs.

The private plan has exactly these fields:

| Field | Bound |
|---|---|
| `schema_version`, `run_id`, `name`, `root` | `1`, UUID, fresh `netclaw-r08-*`, fresh absolute private path |
| `source_root`, `source_files`, `source_sha256` | Explicit relative-file SHA256 map, at most 20,000 files/512 MiB; map hash is sorted compact UTF8 JSON |
| `fixture_gate_file`, `fixture_gate_sha256` | Private gate with `schema_version:1`, `class:FIXTURE`, `passed:true`, matching `source_sha256` |
| `template_file`, `template_sha256` | Exact reviewed public runtime/tool template; never the retained guard environment |
| `python` | `executable`, `sha256`, `environment`, `manifest_file`, `manifest_sha256`; production launcher checks the whole immutable environment |
| `ports` | Distinct explicit loopback ports: 3 each `cluster`, `in2n`, `https`, `edge`, and 4 `api` |
| `guard_token_variable` | Exactly `DEFENSECLAW_GATEWAY_TOKEN`, matching the pinned public guard wrapper |

The source map must include the entire required production import closure,
scripts/lib role and federation-control helpers, the `labs/ha` runner/helpers,
`labs/ollama/qualify.py`, and current `ha/effect.py`, `ha/mcp_transport.py` and
`ha/model_transport.py`. A final source change requires a new gate and fresh
source packet. Missing dependencies are not fetched or installed.

Preparation verifies public retained model/native Python/source/skill artifacts,
then copies model blobs, native source and skill into a fresh closure. No hard
links are used. The retained `guard.env` is never opened. Fresh guard capability,
per-Border operator credentials, application identities, transport CA and separate
HTTPS certificates are generated privately. Model/helper resources use explicit
spec179/owner labels; existing standalone helper behavior remains spec176.

After preparation, the explicit phases are:

1. `model-start --root ...`: create only the reviewed fresh model namespace and
   measure confinement; API-version probes are not inference evidence.
2. `materialize --root ...`: bind the measured model ID and exact frozen source
   into profile2 and launch-schema3 for three Borders and one native member.
3. `coordination-start --root ...`: start only the fresh three etcd voters;
   bootstrap the new generation and enroll the exact member through production
   authority CAS. Its short provisioning lease is not renewed. No execution is
   dispatched by provisioning.
4. `start-role --root ... --role border0|border1|border2|member`: validate and run
   the actual production role launcher/FederationService. Readiness is separate:
   `attachments` requires a fresh owned daemon record and three authenticated
   iN2N attachments. HTTPS HUD/WSS proxies and scoped browser/Code/iOS trust are
   coordinator-owned companion phases; no system trust store is changed.
5. `review --node borderN`: create one exact native subnet review, preserving its
   nonce before sending. `approve --review-file ... --node borderN` reserves the
   shared budget and claims the sole sender before its single decision request.
6. `observe --operation-id ... --node borderN` reconciles the same operation;
   it never prepares or approves. There is no automatic retry or new-ID recovery.
7. `export-operation --claim-file ... --destination <fresh-private-dir>` verifies
   original approval, member result, successor ACK, current durable member ACK,
   measured inference/native artifacts and actual referenced GAIT commits. It
   exports originals and counters, then settles only successful fully finished
   work. Failed/unknown evidence is retained with its budget slot occupied.
8. `stop-role` uses the production PID/start-time/source ownership check and
   stops only that recorded daemon. Export before cleanup. Model/voter container
   stop/removal and network retirement stay with the coordinator's reviewed
   exact-owned cleanup; the run retains homes, databases, keys and evidence.

One SQLite budget spans every surface: at most 10 approved operations, 20
inferences and 10 native effects, one active operation, 180 seconds per operation
and 60 seconds per inference. Each reservation permanently consumes the full
2-inference/1-effect allowance, including failed approvals. Unknowns retain the
single active slot; destructive/unknown negatives and restore belong last.

For HUD/Code, the actual client first writes its original-review artifact and
waits at most 120 seconds. The coordinator uses `publish-claim --review-file ...
--surface hud|vscode --destination ...`, which commits `reserve` and `claim_send`
before atomically publishing the claim. The client is then the sole sender.
Mobile already has separate actual `prepare` and `approve` phases: reserve and
claim `mobile` after the exported native review, include the claim and run UUID
in the private approve configuration, then launch that phase. A missing,
changed or previously used claim fails before the approve tap.

Claims contain exactly `schema_version`, UUID `run_id`/`claim_id`/`operation_id`,
`client_nonce`, `review_digest`, `surface` (`runner|hud|vscode|mobile`),
`reserved_at_ms`, `limits:{inferences:2,native_effects:1,operation_seconds:180,
inference_seconds:60}`, and `claim_sha256`. The hash covers canonical sorted,
compact UTF8 JSON of every field except itself. It is a local exact-review
handoff, not an independent authentication credential or authority grant.

No packet claims the complete matrix: each REAL export explicitly records
`full_matrix_qualified:false`. Actual leader/quorum/network/clock/admission/
unknown/restart/retirement/restore cases, native client journeys and final
independent correlation remain separate requirements in the qualification
matrix. A runner unit test or a controlled fixture cannot satisfy them.
