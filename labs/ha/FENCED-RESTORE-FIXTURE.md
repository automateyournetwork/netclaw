# Owned fenced-restore fixture

`fenced_restore_fixture.py` is a coordinator-only, bounded fixture driver for the
R08 stale-snapshot recovery gate. It uses three actual production `ClusterNode`
OS processes, one actual `MemberAdmission` process, authenticated NCFED/iN2N,
three actual etcd voters, and production snapshot/isolation/restore code. Only
the three effect callbacks and the first signed result are explicitly controlled.
This is **FIXTURE** evidence; it makes no native model, MCP, browser or editor claim.
Importing the module and running `prepare` launch no container or worker.

The coordinator must integrate the reviewed source, freeze it for the complete
run, and select a fresh private absolute packet directory. Use the qualified
isolated Python interpreter; all commands below are explicit separate phases:

```text
python -I -B labs/ha/fenced_restore_fixture.py prepare --packet <fresh-absolute-directory>
python -I -B labs/ha/fenced_restore_fixture.py start-old --packet <directory> --plan-sha256 <reviewed-hash>
python -I -B labs/ha/fenced_restore_fixture.py exercise-isolate --packet <directory> --plan-sha256 <reviewed-hash>
python -I -B labs/ha/fenced_restore_fixture.py start-new --packet <directory> --plan-sha256 <reviewed-hash>
python -I -B labs/ha/fenced_restore_fixture.py restore --packet <directory> --plan-sha256 <reviewed-hash>
```

Review `plan.json` and its source closure before the first live phase. Preparation
creates two fresh direct voter sets offline. Only three voters can run at once:
the original three must be stopped, disconnected and observed absent from the
running-voter inventory before any replacement is started. Other retained R08
voters/proxies must first be retired by the coordinator under their own records.
Unknown running spec179 container roles cause a refusal, never automatic cleanup.
The driver never reuses historical fixture namespaces or reconfigures their RBAC.

Each phase requires its predecessor's completion artifact and the exact reviewed
plan, Python executable, source and prepared private-file hashes. Each mutation
phase creates an exclusive claim before work. An error or lost response leaves
that claim retained and the phase cannot be replayed. Preserve partial state for
inspection; do not delete a claim to retry it. Read-only etcd and host inspections
may retry within their existing bounded implementations. Mutation requests never
receive replacement operation IDs or automatic retries.

The live sequence is deliberately stricter than a stale snapshot alone:

1. Capture all seven actual live host subjects: three exact owned voter container
   IDs, three Border PIDs, and the member PID. Host observations include start and
   command identity; no caller-supplied isolation boolean is accepted.
2. Dispatch controlled operation A, consume one model and one tool admission
   through a follower, and accept its explicitly fixture-signed result and durable
   ACK. Its original resource reservations become released. Export the snapshot.
3. Dispatch operation B on that same member, consume a model admission, hold the
   callback, mark its original operation unknown and export the later ledger.
   Require B and its committed claim to be absent from the stale snapshot, with
   the same resource records changing from A/released to B/reserved.
4. Verify each process identity again and send bounded SIGTERM cleanup. Every
   worker must exit zero; any timeout or unexpected code prevents completion.
   Require closed control sockets and a retained SQLite backup showing B unknown.
   Stop and disconnect only the exact original voters; restart must already be
   disabled. Preserve both the stale and later ledger exports and original IDs.
5. Start the fresh replacement three, prove their namespace is empty, then issue
   the actual host isolation receipt. The receipt is issued after readiness so
   provisioning does not consume its five-minute validity window.
6. Install the stale snapshot with fresh generation/node/install/key identities
   and the same offline enrollment anchor. Check inactive campaign refusal,
   activate status authority, then check new prepare and model/tool admission
   refusals under the global capacity fence. Verify the missing later operation
   and claim have not been silently recreated. Their evidence remains in exports.

The offline enrollment private key stays in the old coordinator-only identity
folder. Replacement workers would receive their own node keys only; the new set
gets the original public anchor and no copy of its private key. The separate host
signer is never passed to workers or mounted in containers.

Inspect `exercise/stale-gap.json`, `processes/owned-process-cleanup.json`, the
immutable `exports.json`, `isolation/owned-baseline.json`,
`isolation/isolation-observations.json`, `isolation/isolation-receipt.json`, and
both `restore-*-gates.json` files. The final result explicitly states that missing
later evidence was **not recovered**, native profiles are unqualified, and the
new voters remain running until separately exported and retired. The driver does
not delete containers, keys, old data, journals or evidence, and does not claim
that a restore recovers capacity automatically.

Historical `process-fixture-01` crash/restart/replay evidence retains its three
Border cleanup timeouts. A passing graceful cleanup here qualifies the corrected
shutdown source; it does not rewrite that earlier failure as a clean run.
