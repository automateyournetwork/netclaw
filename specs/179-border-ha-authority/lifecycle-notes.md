# R08 lifecycle and recovery implementation lane

This is a private maintainer runbook for the unreleased NCFED R08 scope. It does
not activate retained owner runtimes or authorize a public deployment. NCFED
remains the application identity, channel and execution boundary; etcd membership
operations are private consensus administration.

## Source and validation status

The lifecycle lane implements T022–T024 source, the recovery-inspection driver for
T025, and the private CLI portion of T042. Actual quorum/process/runtime recovery
qualification remains a coordinator task. Controlled test results must never be
reported as REAL provider, MCP, host-isolation or etcd evidence.

`tests/n2n/test_ha_recovery_179.py` exercises majority refusal, stale/retired nodes,
one-at-a-time voter changes, lost membership replies, signed host receipt binding,
invalid/stale receipts, chunked restore, orphan target namespaces, permanent
claims, unknown work and one-use activation. `test_ha_host_recovery_179.py` uses
explicit subprocess fixtures to test Docker ownership, running/paused/disconnected
state, restart policy, PID reuse and OS inspection failures. At the lane checkpoint,
all 111 existing/new `test_ha*_179.py` tests pass. No actual process or Docker fault
was executed in this lane.

## Quorum lifecycle

`Lifecycle(authority).drain(node_id)` commits `nodes[node_id].state=drained` and a
membership revision before the coordinator closes that node's channels. `retire`
requires a prior drain and commits a revocation revision. `resume` reverses only a
drain; retired nodes cannot resume in that generation. The last active Border
cannot be drained. Quorum failure causes no local substitute decision. A self-drain
makes subsequent authority mutations fail while its old lease winds down.

Root integration must validate current peer/self state on each NCFED cluster
request, including already-open channels. Closing a socket alone is insufficient.
Existing operations/claims/resources are never removed by drain or retirement.
Re-enrollment in this implementation is deliberately explicit: a newly signed
cluster generation with fresh node IDs, installation IDs and application keys,
the same organization and trusted offline enrollment anchor, and a higher manifest
revision. It follows fenced recovery; there is no same-generation key reuse switch.

`VoterChanges` separates prepare, one external submission and read-only
reconciliation. The durable submitted record precedes the etcd membership call.
A lost reply leaves that record pending; `apply` cannot send the request again.
Only the exact observed membership delta completes it. No pending change can be
overwritten by another change. A refusal or crash that leaves an unproven outcome
requires reviewed recovery; there is no timed cancellation or force option.

For replacement, add one learner, start that owned learner, remove one old voter
while the current majority remains available, then promote the caught-up learner.
At most three voters and one temporary learner are accepted. Two voters cannot be
reduced to one. `strict-reconfig-check=true` must remain enabled in the reviewed
etcd launch configuration. Etcd itself validates learner catch-up before promotion.
This follows the [official etcd runtime-reconfiguration guidance](https://etcd.io/docs/v3.6/op-guide/runtime-configuration/).
No `--force-new-cluster`, member auto-adoption or automatic endpoint rewrite exists.

## Private CLI

Use the coordinator's isolated Python environment and the merged source checkout.
All configuration/credential/trust references are absolute owned private files.
`--config-sha256` pins exact config bytes and uses the same production
`ha.factory.load_configuration` contract as the actual federation runtime.
The etcd key prefix is derived only from the signed cluster/generation.

```text
python scripts/ha-cluster.py setup --config-file /private/config.json --config-sha256 SHA256 --role border --state-dir /private/n2n
python scripts/ha-cluster.py status --config-file /private/config.json --config-sha256 SHA256
python scripts/ha-cluster.py export --config-file /private/config.json --config-sha256 SHA256 --out /private/snapshot.json
python scripts/ha-cluster.py drain --config-file /private/config.json --config-sha256 SHA256 --node-id NODE_UUID --acquire-authority
```

Setup installs the explicit installation-owned `ha-required.json`; it does not
create a protected profile, start a runtime or silently downgrade an installation.
Status and export do not campaign. Lifecycle/voter commands require the explicit
maintenance campaign flag and refuse a currently held leader lease. The CLI never
adopts a running leader's process incarnation, steals a lease or stops a process.
For online qualification the coordinator can invoke `Lifecycle` against the
actual current live authority instance. The maintenance CLI requires a reviewed
window with runtime campaigning stopped and the old lease expired.

Voter commands additionally require a separately pinned `--admin-config-file`
and `--admin-config-sha256`. The exact private schema is
`endpoints,ca_file,certificate_file,private_key_file,username,password_file`.
These administrative credentials must never be copied into a member or exposed
through an NCFED member/API channel. `voter-prepare` uses `--action` and `--target`;
`voter-apply`/`voter-reconcile` use the returned `--change-id`. A learner must be
started and its real catch-up verified by the coordinator before promotion.

## Exact serial recovery qualification plan

`python labs/ha/recovery_lab.py plan` prints the reviewable nine-step plan and
performs no inspection or mutation. The coordinator substitutes the actual fresh
owned IDs and already reviewed private paths; invented participant IDs cannot
qualify the test.

1. While all old participants run, create an owner-private host signer outside
   every Border/member/container. Pin its public key in the reviewed recovery
   packet. Capture the complete inventory using `recovery_lab.py capture`.
   Record every executor and runner process, not only the visible member daemon.
   Containers require full Docker IDs, exact `netclaw.owner` and `netclaw.spec=179`
   labels, disabled automatic restart and a running baseline. Host process
   selectors require the exact PID, start hash and command hash obtained from
   `recovery_lab.py process-identity --pid PID`. Capture checks actual OS state.
2. Export a single linearizable etcd prefix snapshot with the private CLI. The
   bounded export is at one revision and refuses truncation; no page mixing is
   allowed. Export each member/guard's durable evidence and actual model/MCP
   counters to immutable private files. Build `exports.json` as
   `{"schema_version":1,"artifacts":[{"path":"/absolute/file","sha256":"FILE_BYTES_SHA256"}]}`,
   including the exact snapshot file. This manifest is an integrity inventory,
   not a declaration that post-snapshot execution is absent.
3. The coordinator alone stops recorded Border/executor processes, stops and
   disconnects recorded containers, and verifies no owned restart policy or
   supervisor can bring them back. Preserve old state. A paused container, a
   connected stopped container, a reused PID or a guessed missing object fails.
4. Invoke `recovery_lab.py issue` with the captured root, old/new signed manifest,
   pinned anchor, private host signer, snapshot and exports files. The helper
   performs fresh actual Docker/OS observations and writes new-only observation
   and signed receipt files. It never accepts caller booleans or arbitrary
   inspection callbacks. A missing Docker object is unknown, not proven stopped;
   retain stopped objects until evidence capture completes.
5. Against fresh owned voters and an unused new-generation namespace, run
   `ha-cluster.py restore-install` with the new config plus `--old-manifest-file`,
   `--snapshot-file`, `--receipt-file`, `--host-certificate-file`, `--host-key-id`.
   The same pinned enrollment anchor validates old and new manifests. The install
   first commits inactive control, then imports bounded chunks. Interrupted or
   ambiguous chunks reconcile only their exact digest; no unrelated state is
   overwritten. New issuance must complete before the five-minute receipt limit.
6. Before activation, prove actual campaign and new protected execution are
   refused. Compare all retained claims/resources and original terminal
   result/ACK references against the export. Unfinished work becomes revoked
   `outcome_unknown`; old member enrollment becomes `recovery_fenced`.
7. Invoke `restore-activate` with the same inputs within five minutes. This is a
   one-use transition to status authority. A repeat refuses as already activated.
   The **global execution-capacity fence remains enabled**.
8. Prove original historical status remains available while prepare/approve/
   dispatch/admission, including a fresh operation ID, fail `recovery_fenced`.
   Inspect actual runtime counters for zero additional model/MCP effects. A
   stale snapshot can omit later work, so there is no implicit capacity reset.
9. Export correlated source/image/profile/participant/revision/timing/counter/
   receipt/GAIT evidence and perform the separately reviewed owned-only cleanup.
   Do not reuse spent activation plans or overwrite retired archives.

`capture`/`issue` share `--root`, `--manifest-file`,
`--anchor-certificate-file`, `--anchor-key-id`, `--host-certificate-file` and
`--host-private-key-file`. Capture adds `--owner` and `--subjects-file`; issue adds
`--new-manifest-file`, `--snapshot-file` and `--exports-file`.

A subject is either
`{"kind":"container","role":"voter|border|executor","node_id":null,"id":"FULL_64_HEX_ID"}`
or
`{"kind":"process","role":"border|executor","node_id":null,"pid":123,"start_id":"SHA256","command_sha256":"SHA256"}`.
Border subjects use their actual manifest node UUID instead of null. Exactly
three voters, the complete manifest Border set and at least one executor are
required; executor count cannot be lower than the exported enrolled-member count.
The reviewed coordinator inventory must include separate model/runner processes.

## Explicit limits and integration seams

A host receipt records actual observations under the trusted-owner/host failure
model; it does not defeat a malicious administrator or prove a stopped supervisor
can never be deliberately restarted. Keep the old generation physically isolated
through recovery. The current implementation's permanent capacity fence prevents
new execution even after activation and covers omitted post-snapshot admissions.
There is intentionally no unfreeze-by-boolean, expiry, empty table or new ID.
Reconciliation that safely clears affected capacity is a separately reviewed
future mechanism; this lane does not claim productive disaster restoration.
Etcd's own [disaster-recovery documentation](https://etcd.io/docs/v3.6/op-guide/recovery/)
also warns against forcing a replacement cluster while old members survive.

Root-owned `ha/operations.py` must reject prepare/approve/dispatch/admit when
`control.recovery.capacity_frozen is True`, preserving historical status, revoke
and result reconciliation. Root-owned channel handlers must refuse drained/retired
peers using fresh quorum control. The CLI imports root-owned `ha/factory.py`
lazily; exercise it with the merged production loader before T042 closure.
Installer/catalog discovery and any public deployment surface remain outside this
lane and under the roadmap release hold.

T025 remains open until the coordinator records real quorum, actual owned-host
isolation, fenced restore, stale-snapshot zero-call and cleanup evidence. Source
and unit-test completion alone do not close that acceptance gate.
