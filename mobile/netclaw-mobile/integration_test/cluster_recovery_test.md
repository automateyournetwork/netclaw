# R08 native cluster qualification source

This is a coordinator-driven rehearsal, not evidence of a completed run. Use a
fresh owned simulator bundle and source harness. Preserve every R01/R05/R06
application, key namespace, profile and schedule. The harness registers only
`native/R08SimulatorPlugin.swift`, compiles production `X509SelfSigned.swift` and
`ClusterPublicCrypto.swift`, and depends on this Mobile source. Its simulator
software Keychain identity is separate from production Secure Enclave keys.
Never register this plugin in the production app.

First use `mobile_qr_test.dart` and `test_driver/mobile_qr_driver.dart` for the
actual `enroll`, `prepare`, `approve`, `recover` phases documented in
`mobile_qr_test.md`. The exact inspected review must name a REAL guarded native
member/provider/tool, and approve is tapped once. `recover` only reads that
operation after a host-recorded cold restart. Do not turn an uncertain approval
into a new enrollment, prepare, operation ID, or repeated approval. Add
`cluster_id`, `generation`, `anchor_key_id` and `backend_record` to its private
configuration. `backend_record` identifies the coordinator's signed member
receipt/ACK/GAIT/provider/native-counter packet; the UI report does not itself
establish those effects. Keep existing 180-second result wait and one approval.

Then use `cluster_recovery_test.dart` with
`test_driver/cluster_recovery_driver.dart`. Set `NETCLAW_NATIVE_REPORT` to a fresh
file in an existing private 0700 host directory. Atomically place the bounded
private `Documents/r08-qualification.json` after launch. Never use dart-defines,
build assets, stdout or source files for enrollment tokens or private config.
The input has:

- `phase`: `select-node`, `no-quorum`, `stale-review`, `cold-recover`, or
  `background-recover`.
- `profile`: the existing bounded profile directory from the enrollment phase.
- Exact retained `cluster_id`, `generation`, `key_fingerprint`, `device_subject`.
- Original `operation_id`, `client_nonce`, `review_digest`, `backend_record`;
  completed-result recovery also supplies the original `result_digest`.
- `target_node_id` only for `select-node`, taken from the retained signed
  manifest, different from the current node.

`select-node` taps the production recovery form, chooses one of the signed
manifest's at most three HTTPS/WSS endpoints, verifies trusted HTTPS and fresh
WSS device proof, commits the endpoint atomically and reads the original
operation under the same secure-storage audience. It never prepares, approves,
or reconciles. Untrusted names, retired nodes, changed generation/anchor/key or
principal, and manifest rollback must fail without changing the saved endpoint.

For `no-quorum`, `stale-review` and `background-recover`, wait for
`Documents/r08-ready-<phase>.json` before injecting the reviewed real fault.
This marker contains public identity and the original reference. Record the
actual process/network or simulator OS transition in the host packet, then
create `Documents/r08-fault-ready.json`. The wait is bounded to 60 seconds.
The driver taps only **Check same operation** and verifies preserved reference,
send marker, review and device identity. No-quorum and stale-review require
Approve to be disabled. Background recovery requires actual paused/resumed
callbacks; the host must also retain the OS transition receipt. Use a fresh
fault marker per run and retain/export earlier evidence before removal.

`cold-recover` begins after a real host-recorded termination and relaunch and
performs read-only initialization. The driver cannot manufacture that host
event; its report keeps this limitation explicit. No recovery phase has code
that prepares, approves, or reconciles. Counter values in the backend packet,
not a frontend refusal, prove no repeated provider or native effects.

Run phases serially against the coordinator's bounded R08 resources. Export
reports and compare original signed result digest, ACK, GAIT and independently
recorded provider/native effects before owned cleanup. Physical camera capture,
Secure Enclave hardware and Android execution are not qualified by this
simulator harness. Trusted TLS verification remains enabled throughout.
