# Focused R08 wire/recovery fixture

This maintainer-only driver fills the explicit T034 gaps left by the earlier
matrix. It uses a **fresh dedicated direct three-voter fixture** and four owned
OS processes. Existing generations, including the isolated restore pair, stay
stopped. Import and tests perform no actual worker, Docker, native or model start.

Run only after integration and coordinator review. Prepare/start the fresh direct
voters and identity with the existing exact-owned EtcdLab workflow. Do not
bootstrap its control namespace first; this driver verifies it is empty and
bootstraps once. It observes the global running voter cap of three and does not
start, stop or remove voter containers itself.

```text
PYTHONPATH=mcp-servers/protocol-mcp:scripts/lib:. /reviewed/python -B labs/ha/wire_recovery_fixture.py run --fixture /private/fresh-direct-voters --evidence /private/new-wire-evidence
```

The source map includes all federation Python and lab Python files. A worker
refuses source changes. Each launch and private control mutation has a new-only
claim; unknown commands are never repeated. Only exact selected endpoints and
owned PID/command identities are used. Limits are four simultaneous workers,
one member enrollment, two production controlled completions plus one final
unknown operation, seven controlled callbacks, zero real model/native calls,
480 seconds overall and a 600-second orphan watchdog per worker. A failed phase
retains the entire evidence directory. A new operation is never substituted for
an unknown original.

| Row | Actual exercised path and observations |
|---|---|
| Topology/trust | Actual member attaches outbound to all three Borders. Fresh member, independent-organization and unenrolled certificates fail each cluster mTLS endpoint and each private etcd listener. Each owned target has positive TLS or scoped etcd controls before and after its negatives. Every cluster negative requires a new matching receiver leaf-certificate verification failure; etcd requires an explicit peer authentication TLS alert or exact auth error payload. Refused connections, resets, timeouts and generic HTTP400 cannot qualify a row. Unenrolled/external keys fail actual iN2N hello; an enrolled key with wrong role or a proof replayed onto another TLS transcript fails hello. Authenticated member sends forbidden methods over the actual channel, bypassing only its caller-side allowlist, and observes the receiver refusal. Scoped Border etcd credentials fail outside-prefix and administration reads. Exact member PID has no TCP listener or consensus credentials. |
| Lost result reply | Production MemberOperations creates a signed controlled result and retains it. After the actual authenticated result RPC, the one-shot hook closes the channel after production result lookup but before the reply write. Original Border has no accepted result. Exact leader is killed; successor performs production reconcile over a surviving iN2N attachment, accepts the same signed result, delivers its ACK and records delivery. |
| Lost ACK delivery | A second production controlled result is accepted. The one-shot hook closes the actual authenticated ACK RPC after receiver delivery but before calling production acknowledge/persistence. Original cluster ACK remains committed; member ACK remains absent. Exact leader is killed. Successor reconcile reuses the original signed result and original committed ACK, and the member persists it. |
| Paused old leader / unaware member | Member captures actual committed model1/tool1 proofs while they are fresh. Exact leader receives SIGSTOP; `ps` records stopped state and the same PID/start/command identity. Other Borders observe a higher authority epoch. The member has received no additional authority proof and rejects both old proofs by its production freshness gate. Exact process resumes; one model2 admission succeeds with a higher-epoch proof. Original operation is marked unknown, retaining its claims/capacity. |
| Durability/cleanup | All workers terminate with the corrected graceful exit contract, sockets are removed, and the original production member SQLite is reopened read-only. Both original signed results and ACKs must match exactly. New voters remain running for coordinator export and exact-owned cleanup. |

The loss hooks are explicit **authenticated RPC delivery-boundary faults**, not
opaque packet-loss claims. They do not modify result bytes, ledger decisions,
production reconciliation or the production ACK store. ControlledExecutor is a
clearly named DockerExecutor subclass only for this fixture; no container,
provider, guard model or native tool runs. This output cannot qualify REAL.

The independent-organization negative uses a fresh external identity certificate;
it does not claim a completed ordinary eN2N grant or endpoint-failover journey.
Member-to-member exclusion is established by the production outbound-only
attachment type, receiver method refusals and actual absence of a member TCP
listener; the private owner UDS is not a member network endpoint.

Each wire row records separate original RPC loss, observed leader death,
replacement authority and original-result recovery monotonic timestamps. The
pause row records actual stopped-process observation, replacement and fresh
admission timestamps. Polling/control latency remains included and is labeled.
These measurements do not retroactively supply missing timestamps in older rows.

`complete.json` is written only after all rows and worker cleanup pass. Export
all original receipts, journals, source/launch/control claims, failures, RPC loss
observations and counters before stopping the three exact owned voters. Preserve
earlier failed fixtures and do not report T034 complete from source tests alone.

The Border worker's TLS verification observer is qualification instrumentation.
It retains the frozen production callback's exact `bool(ok)` result, verification
mode and CA configuration. Only failed leaf certificate hashes, OpenSSL error
codes and monotonic timestamps are written privately. Every negative correlates
a new receiver event with that attempt; old events cannot qualify a later test.
Observer/storage failures latch a fixture failure. The production TLS module is
not edited, and the observer is restored when the worker closes.
