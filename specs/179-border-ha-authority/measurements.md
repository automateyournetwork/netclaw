# R08 measurements — incomplete qualification

These are measured local FIXTURE results. REAL recovery timing and native client
measurements remain open. No number below is a WAN latency or regional SLA.
Private artifacts live under `roadmap-r08-20261107/`; preserve their exact source
maps, process IDs, logs and clock observations alongside these summaries.

## Configured bounds

| Control | Bound |
|---|---|
| Coordination | Three etcd3.6.16 voters, majority required |
| Each voter | 512MiB memory/no swap;0.6CPU;384MiB Go memory target |
| Backend | 128MiB quota; admission refuses on NOSPACE |
| Raft | 300ms heartbeat;3000ms election timeout |
| Border authority | 12s lease;3s renewal |
| Each model/tool admission | 3000ms freshness;250ms wall/monotonic uncertainty |
| Metadata | 1024operations;32members; bounded retained claims |
| REAL qualification | At most10approved operations/20inferences/10native effects; one active operation |
| REAL deadlines | 180s per operation;60s per inference |

Three voters run at once. The separate three opaque Raft proxies each use
64MiB/0.1CPU and no TLS keys or network-admin capability. They are fixture-only.

## Observed latency safety

`matrix-raft-network-01/04-latency-safety-300ms.json` injects150ms delay in each
direction on the named byte-proxy paths. Raft peer delay is0 in this latency row.
Per-chunk delays, connection setup and sequential quorum calls mean this is an
injected nominal path-RTT envelope, not an exact300ms end-to-end operation time.

| Delayed path | Model admission elapsed | Tool admission elapsed | Result |
|---|---:|---:|---|
| NCFED cluster only | 368.996ms | 395.796ms | Both admitted within bound |
| Quorum client only | 3757.066ms | 4373.633ms | Both refused: admission_expired |
| Both paths | 4385.006ms | 4842.046ms | Both refused: admission_expired |

All refused probes added zero controlled callbacks. Separate healed positive
controls completed in83.153ms,99.085ms and79.771ms respectively. Raw per-request
HTTP timings include concurrent renewal/control traffic and say so explicitly.
The earlier strict combined-delay row in `matrix-network-02` remains a failed
availability test. These safety passes neither erase it nor qualify R09 latency.

## Failures and recovery

`core-03` measured15.007s for authority replacement. It is one controlled local
observation, not separate failure detection/election/service-recovery percentiles.
The four directed partition rows took19.985s,20.132s,12.233s and36.248s overall.
Those durations include injection, refusal checks, healing and positive controls;
they must not be presented as election time.

`process-fixture-01` independently observed each killed Border PID, member death,
new process/incarnation identities and all three restarted voter PIDs. It preserved
three controlled callbacks and the consumed journal. It did not record separate
fault-to-detection/election/service-recovery monotonic durations. Its three Border
shutdown TimeoutErrors remain a qualification limit pending corrected cleanup.

Clock rows in `matrix-recovery-01` inject+1s/-1s into the member's wall-clock
observation and a4s advance into both clock observations; delayed receipt waits
past3s. These are controlled clock inputs to the actual admission gate, not host
clock changes or proof of physical suspend behaviour. NOSPACE is an actual etcd
maintenance alarm; it is not a measured physical-disk-full experiment. Tail disk
latency, REAL fault timing and native client recovery timing remain unmeasured.

## Required remaining measurements

Capture monotonic fault start, first detected loss, first committed new authority
and first distinct successful native operation separately in the REAL packet.
Record actual guard/model request observations, native responses/handoffs and
uncertain intervals; reservation rows are not execution counters. Retain resource
inspect outputs and storage/clock observations. Complete T041 only when the
required runtime measurements and their limits are correlated with signed results.
