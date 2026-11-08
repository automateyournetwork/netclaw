# R08 serial fixture matrix

These are maintainer-only drivers for fresh owned R08 resources. Every output is
FIXTURE. Controlled callbacks, actual TCP, actual etcd and actual NCFED do not
constitute real model, guard-provider, native MCP, operating-client or cloud proof.
The coordinator must execute faults serially, correlate original operation IDs and
counter evidence, and retain all failures. This source lane has not executed a
Docker/process/runtime fault.

The preserved `core-03` result contains seven valid narrow rows: three-node mesh,
follower forwarding, one leader lease expiry, stale authority refusal, unknown
reservation preservation, one voter loss and two-voter quorum refusal. It records
two controlled callbacks and no real provider/native execution. It does not close
the full qualification matrix.

## Actual encrypted byte-path matrix

Run from the integrated repository with the isolated Python environment and
`PYTHONPATH=mcp-servers/protocol-mcp`. Use a new private evidence directory for each
invocation. `--row` may repeat with distinct values; retirement must be last.

```text
python -m labs.ha.qualify --suite matrix --fixture /private/owned-fixture --evidence /private/new-evidence --row minority --row asymmetric-request --row asymmetric-response --row threeway --row delay-300ms
python -m labs.ha.matrix --fixture /private/owned-fixture --evidence /private/new-evidence --row stale-member --row clock-forward --row clock-backward --row clock-suspend --row unknown-commit --row lost-result --row lost-ack
python -m labs.ha.matrix --fixture /private/owned-fixture --evidence /private/new-evidence --row record-capacity --row nospace --row quorum-loss-two-voters
python -m labs.ha.matrix --fixture /private/owned-fixture --evidence /private/new-evidence --row leader-loss-each-node --row full-restart --allow-owned-voter-restart --row retired-return
```

Private quorum clients pass through nine loopback byte proxies. The three NCFED
cluster links pass through separate byte proxies using a fixture-scoped outbound
routing shim. TLS, server names, mutual cluster certificates, exporter bindings,
NCFED role proofs, quorum operations and `MemberAdmission` remain production code.
No TLS terminates at a proxy. Each fault row verifies newly dropped byte counts;
old cumulative drops cannot qualify a later row. Clearing a policy closes only
owned relay connections because discarded TLS bytes cannot be repaired in place.
A positive control follows every network fault. The delay row injects 150ms in
each direction and records actual elapsed time; an expired admission fails the
row rather than silently enlarging its deadline.

Ordinary runs prove Border-to-quorum and NCFED link failures. They explicitly do
not prove Raft peer partitions. Actual two-voter pause and owned Docker stop/start
are separately identified. The consensus lost-reply row waits for an actual
successful claim transaction, discards that response after the member deadline,
and verifies exact decision recovery still cannot invoke the expired callback.
The capacity row temporarily fills the actual durable decision counter and restores
only its exact unchanged state; no claim or unknown record is deleted. NOSPACE
activates and observes the actual etcd alarm, then deactivates only the alarm from
this fresh, previously alarm-free fixture. An unknown cleanup outcome stops the
run and retains evidence.

All row output includes the exact scope, source hash, before/after controlled
counters, fault observations, operation/proof/revision references and timing where
available. `complete.json` lists missing requested rows. A source test or parser
success never substitutes for this file's actual recorded execution.

## Fresh proxy-fronted Raft topology

`RaftProxyLab` adds three opaque stdlib relay containers to three fresh voters.
It accepts only an already installed immutable Python image digest selected and
reviewed by the coordinator. It does not pull an image, enable NET_ADMIN, publish
an administrative API, load TLS keys into proxies or alter a retained network.
Every voter has its own proxy peer URL, distinct private peer key and peer TLS
certificate. Each peer certificate includes exactly the three owned proxy DNS
names plus that voter's own name: etcd validates incoming peer SANs against the
remote TCP address, which an opaque proxy changes. Certificate hashes and exact
SAN sets are pinned at preparation/load; older narrow-SAN prepared plans are
refused. TLS verification is never disabled. See the
[official etcd transport-security notes](https://etcd.io/docs/v3.6/op-guide/security/). Actual
Docker source IPs are obtained from exact ID/label/image-verified inventory.
Unknown source IPs are refused. Per-peer request and response cuts are independent.

Coordinator preparation source (these calls create fresh private files/keys but do
not start containers until `start`):

```python
from labs.ha.raft_topology import RaftProxyLab
lab = RaftProxyLab('/private/fresh-raft-fixture', 'reviewed/python@sha256:EXACT_DIGEST').prepare()
lab.prepare_cluster_identity()  # Fresh offline anchor/node keys + separate transport CA; no runtime calls.
# Review /private/fresh-raft-fixture/raft-start-plan.json first.
# It lists exactly six new containers, one new network, image pins and limits.
lab.start()  # Coordinator only, one attempt; preserve partial or unknown starts.
```

`prepare_cluster_identity()` prepares the signed manifest from this exact lab's
cluster/generation and automatically calls `prepare_cluster_transport()`. It holds
nine distinct loopback ports during preparation, then releases them before return;
the actual listener must still bind successfully. Existing identity directories
are refused. The offline root key stays outside all runtime/proxy mounts. After
starting fresh voters, explicitly initialize `Authority(store, manifest, first_node_id).bootstrap(create=True)`
once using the verified signed manifest and scoped lab store. This creates no
member or effect. The independent fresh cluster gets a fresh anchor; disaster
re-enrollment under an old cluster requires the separately retained old anchor. The existing direct fixture is not converted.
Run the same matrix command with `--raft-proxy-image` set to the exact prepared
image pin. The driver applies both the matching Border/quorum cut and the real
Raft peer cut, verifies the proxy policy digest/generation and newly dropped peer
bytes, and records `raft_observations` separately. Without those observations the
row cannot claim a Raft partition. A policy generation change closes only the
proxy's own connections to establish clean TLS sessions after healing.

All six owned container IDs and the network ID must appear in reviewed cleanup.
`container-ids.json` holds the three voters; `proxy-ids.json` holds the three added
relays. Never use global prune. Export before cleanup and preserve unknown starts.

## Restart and restore boundary

The fixture restart path exports a linearizable snapshot before the first stop,
checks exact owned voters and image labels, stops all three, observes their stopped
state, starts those same IDs once, and checks their running state. It reconstructs
all three private etcd clients after bounded old requests settle, requiring fresh
authentication without replaying an old request; previous tokens are not retained.
It preserves the exact reviewed proxy bindings, reconstructs actual NCFED services
and reopens durable member journals, comparing completed,
unknown, claim, reservation and ACK data. It rejects a new operation ID against
unknown member capacity. This is actual voter process restart plus actual service
and journal recreation. The output explicitly sets Border/member **OS-process**
restart qualification false because these controlled services share the fixture
runner process. The coordinator's separately owned real-runtime process launcher
must provide that remaining full-process evidence and actual counters.

Use `recovery_lab.py capture/issue` and `scripts/ha-cluster.py restore-install/
restore-activate` for genuine host-isolated new-generation restore, following
`specs/179-border-ha-authority/lifecycle-notes.md`. After install and again after
activation, run the verifier before starting new Border services:

```text
python labs/ha/recovery_lab.py verify-restored --config-file /private/new-config.json --config-sha256 CONFIG_SHA256 --manifest-file /private/old-signed-manifest.json --snapshot-file /private/old-snapshot.json --out /private/new-restore-check.json
```

The verifier checks every retained source record against the expected fenced
transformation. Before activation it proves campaign refusal. After activation it
obtains a maintenance lease only if no live leader exists, then exercises the
actual fresh-prepare and model/tool admission gates. Each must return
`recovery_fenced` without changing control or spent state. It never steals a live
leader incarnation. The activated verifier requires a snapshot containing at least
one real committed attempt; an empty snapshot cannot qualify admission recovery.

A stale-snapshot case must actually capture a snapshot before later unknown work,
retain the later member/guard evidence, isolate the exact old participants and
prove the new generation's global capacity fence blocks even a new operation ID.
The verifier does not invent that missing-history setup or infer unchanged native
counters from a refusal. The coordinator records those actual inputs/counters.

Actual iN2N multiattachment, topology-role negatives, real-profile runner death,
complete Border/member OS-process restart, HUD, native VS Code and native Mobile
remain separate mandatory qualification rows. None is waived by this fixture
source or by the explicit scope flags in its outputs.

## Measured latency safety, distinct from service availability

The historical combined `delay-300ms` row remains a strict healthy-forwarding
expectation. Its recorded `matrix-network-02` failure is retained: the production
member gate returned `admission_expired` before the controlled callback. It is not
rewritten as a pass. The subsequent explicitly named measurement row is:

```text
python -m labs.ha.matrix --fixture /private/owned-fixture --evidence /private/new-latency-evidence --row latency-safety-300ms
```

This row measures three scopes separately: NCFED cluster links only, Border-to-etcd
HTTPS links only, and those two scopes combined. Each proxy adds 150ms per received
byte chunk in each direction, giving a nominal300ms path round trip; this is an
observed byte-relay fault model rather than a claim of exact WAN packet latency.
Raft peer delay remains zero for these three scopes and is explicitly recorded.
The actual proxy-fronted Raft partition rows remain separate evidence.

Both model and tool admission gates run in every scope. A probe qualifies only if
its actual callback counter increments exactly once, or if it returns precisely
`admission_expired`/`no_quorum` with unchanged counters. Transport ambiguity,
unexpected errors and unexplained effects fail the row. Every scope must then
heal and complete a distinct new operation through a follower; expired/unknown
operations are never retried or cleared. The three-second freshness rule remains
unchanged. `service_availability_qualified=false` and `r09_ready=false` are explicit.

Every probe writes `probe-NNN.json`, even on failure, with elapsed response/effect/
refusal timing, the freshness bound, operation/ingress identity, exact counters,
and read/write request durations/revisions. Timing instrumentation records no
request bodies, credentials, tokens or outputs. Samples include concurrent renewal
traffic and are labeled accordingly; they must not be summed as if all requests
were causally part of one admission.

Source analysis explains the limit without assuming connection warmup: the warm
forwarded path currently performs approximately ten sequential quorum round trips
(route lookup, channel pre/send checks, handler precheck, operation lookup,
transaction snapshot/commit, handler post/send checks and caller final check).
Ten300ms round trips plus a300ms NCFED path already exceed three seconds before
storage, scheduling and cryptographic overhead. SC-005 requires measured detection,
election and service-recovery behavior, and the plan explicitly makes no
zero-interruption promise. Safe refusal can qualify safety under latency while
healthy300ms service remains unsupported for that path. R09 planning must address
this measured sequential-round-trip cost before claiming multi-region service;
blindly extending freshness or dropping atomic membership/principal/leader checks
is not a qualified fix.
