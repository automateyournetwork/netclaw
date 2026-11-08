# R08 measurements — incomplete qualification

The first sections are measured local FIXTURE results. A later section
(`REAL local-Docker runs`) records timings from REAL runs 07-09; it is explicitly
a local, single-host, polling-coarse record. No number below is a WAN latency or
regional SLA, and none is a pure election time.
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

## REAL local-Docker runs (runs 07, 08, 09)

Private root `~/.local/share/netclaw/roadmap-r08-20261107/` (all paths below are
relative to it). One Docker host, loopback/bridge networks, three etcd voters, qwen3:0.6b
on CPU. Every number is a single observation unless samples are listed. All
elapsed values are derived from the cited timestamps; nothing is estimated.

### Leader-loss (SIGKILL of the authority-holding Border), detection to new authority

Method limit: the observer was a shell polling loop that slept 2 s per iteration
and began 1 s after the kill. Each figure is `observed_at_ms` of the first
poll that showed a new authority minus `kill_at_unix`. It therefore includes up to
about 2 s of polling granularity plus the 1 s start offset and is an upper-bound
"time to observable new authority", NOT pure detection or election time. The
fixture bounds (3 s Raft election, 12 s lease, 3 s renewal) are not directly
separable from these samples. Which of lease expiry versus Raft election dominated was not
instrumented.

| Sample | Source | Kill (unix s) | Observed new authority (ms) | Elapsed since kill | Observed state/epoch |
|---|---|---|---|---:|---|
| run-07 | `real-run-07/leader-loss-01/timing.txt` | 1794151407.552 | 1794151418788 | 11.236 s | leader, epoch 32 (killed holder border2 had epoch 6 at op1) |
| run-08 | `real-run-08/leader-loss-08/timing.txt` | 1794152593.113 | 1794152606538 | 13.425 s | follower-view, epoch 17 (also a transient poll TypeError "NoneType" while waiting) |
| run-08b, first reading | `real-run-08/leader-loss-08b/timing.txt` | 1794153249.304 | 1794153251634 | 2.330 s | epoch 26, state follower; NOT final, epoch advanced afterwards |
| run-08b, final | same | 1794153249.304 | 1794153263822 | 14.518 s | leader, epoch 29 (`ok` at ...825) |
| run-09 | `real-run-09/leader-loss-09/timing.txt` | 1794153759.213 | 1794153775501 | 16.288 s | follower-view, epoch 8 |
| run-09b | `real-run-09/leader-loss-09b/timing.txt` | 1794155241.744 | 1794155254084 | 12.340 s | leader, epoch 73 |

Samples (s): 11.236, 13.425, 14.518, 16.288, 12.340 (run-08b uses the final
reading; the 2.330 s first reading is excluded from the set because the observed
epoch changed again afterwards). n=5; min 11.236, max 16.288, median 13.425. The
self-reported `after N s` figures in the files (10.1, 12.1, 2.0, 16.1, 12.1) use
the loop's own clock and differ by the loop offset; the table uses the
timestamp subtraction. Five samples across three separate cluster instances are
not percentiles. Epoch numbers jump (for example 6 to 32) and are reported as
observed; this record does not claim their per-increment meaning.

A post-failover operation was admitted each time: `real-run-07/export-op4-leaderloss-border1`
reserved at 1794151424780, 6.0 s after the first new-authority observation, with
epoch 32 in approval and ACK. The matching post-fault op gates in runs 08/09 are
in the run records, not re-derived here.

Not separately recorded in any REAL file: first detected loss, the committed
election instant, and first successful native operation after the fault on a
monotonic clock. The packet's first-distinct-operation instant is only bracketed
by `reserved_at_ms` and the ACK `accepted_at_ms` below.

### Member kill and full restart

| Event | Source | Result |
|---|---|---|
| Approve then member SIGKILL | `real-run-09/member-kill-09/timing.txt` | `approve_start` 1794155307.448, `approve_returned` 1794155307.993 (0.545 s), `member_killed` 1794155308.014 (0.021 s after return). Detection/recovery time of the member not recorded in this file |
| Whole-cluster stop and restart | `real-run-09/full-restart-09/{stop_at,voters_started_at,border_ready_at}` | stop 1794155445; voters started 1794155472 (+27 s); Border ready 1794155500 (+28 s; 55 s stop-to-ready). Whole-second granularity (+/-1 s). Container states in `voters-stopped.txt` and `voters-restarted.txt` |

### No-quorum (two voters paused)

| Run | Source | Interval |
|---|---|---|
| run-08 | `real-run-08/noquorum-08/timing.txt` | paused 1794153198.787, healed 1794153225.006: 26.219 s |
| run-09 | `real-run-09-clients/evidence/fault-pause/pause-v{1,2}.started.json`, `fault-unpause/unpause-v{1,2}.started.json` | `docker pause` v1 at 16:09:40.256Z and v2 at 16:09:40.342Z; unpause v1 at 16:10:21.887Z and v2 at 16:10:21.982Z: 41.631 s and 41.640 s command-start to command-start (return codes 0) |

These are pause durations, not election or refusal latencies. Client refusal
timing inside the window (editor `no_quorum` report `real-run-09-clients/evidence/e06`,
browser `browser-05`, iOS `ios/evidence/no-quorum.json`) records pass/fail
checks, not measured refusal time.

### Approval to signed ACK latency per operation

From `original-approval.json` `issued_at_ms`, `original-member-result.json`
`finished_at_ms` and `successor-ack.json` `accepted_at_ms` in each export packet.
`issued_at_ms` is signing time of the approval, not the human click. Total
"approval to ACK" below is ACK minus approval issuance. `reserved` is the budget
claim `reserved_at_ms`.

| Operation | Surface | Epoch | reserve to approval | approval to member finish | finish to ACK | approval to ACK | etcd rev |
|---|---|---:|---:|---:|---:|---:|---:|
| `real-run-07/export-op1` | runner | 6 | 650 ms | 31167 ms | 3245 ms | 34412 ms | 14 |
| `real-run-07/export-op2-border1` | runner | 6 | 121 ms | 28721 ms | 2231 ms | 30952 ms | 22 |
| `real-run-07/export-op3-border2` | runner | 6 | 107 ms | 27097 ms | 3855 ms | 30952 ms | 30 |
| `real-run-07/export-op4-leaderloss-border1` | runner | 32 | 126 ms | 28264 ms | 2745 ms | 31009 ms | 41 |
| `real-run-08/export-hud-op` | hud | 6 | 701 ms | 32784 ms | 27707 ms | 60491 ms | 15 |
| `real-run-09/export-vscode-op` | vscode | 8 | 829 ms | 29747 ms | 9004 ms | 38751 ms | 16 |
| `real-run-09/export-mobile-op` | mobile | 8 | 1992 ms | 28969 ms | 1236 ms | 30205 ms | 36 |

Seven samples (ms): 30205, 30952, 30952, 31009, 34412, 38751, 60491; min 30205,
median 31009, max 60491. Member finish time is dominated by CPU-model inference
(see the ollama figures below). The two long finish-to-ACK values are 27707 ms
(HUD, run-08) and 9004 ms (VS Code, run-09); the packets do not attribute the
delay (client polling versus Border acceptance), so no cause is claimed. The
budget limits are 180 s per operation and 60 s per inference; no sample reached
either. `real-run-08/export-unknown-vscode` is an unfinished/unknown VS Code
operation (`receipt_sha256: null`, actual inferences null in its budget
reservation), so it has no ACK latency; see Host load below.

Per-operation ollama accounting (`measured-artifacts.json`, `ollama-accounting.json`):
`elapsed_ms` 19678, 17161, 16268, 17373 (run-07 op1-4), 20465 (run-08 HUD), 17963
(run-09 vscode), 17778 (run-09 mobile). Each recorded 843 prompt and 123 completion
tokens and zero provider charge.

Client-side phase timings: report filenames carry a millisecond start
timestamp, for example `real-run-09-clients/evidence/e01/1794154073652-*`
(editor original) through `e09/1794155269917-*`. The reports contain pass/fail
checks and request lists, not phase durations, so no per-phase latency was derived.
The iOS records (`real-run-09-clients/ios/evidence/*.json`) are Simulator evidence
with only UTC `observed_at` values on enroll/prepare/approve steps (for
example prepare 16:20:24.810Z, approve 16:21:02.674Z) and are classified
`REAL_NATIVE_REQUIRES_BACKEND_CORRELATION`; they are not physical-device
latency.

### Resources

Configured and inspected. `retirement/stopped.json` for run-07 (`netclaw-r08-3ce9161730`), run-08
(`netclaw-r08-fb75cf1a0a`) and run-09 (`netclaw-r08-b8e487ea0c`) show each voter with
`Memory` 536870912 (512 MiB), `MemorySwap` 536870912 (no extra swap), `NanoCpus` 600000000 (0.6 CPU),
`OOMKilled` false. etcd flags in the same file: heartbeat 300, election 3000, quota 134217728,
auto-compaction 1m, TLS 1.3 minimum, client-cert auth. Run-09 voters ran
16:31:12Z to 16:32:11-13Z at retirement (clean exit code 0). The signed manifest limits in
`real-run-09/voters/cluster-identity/manifest.json` (`manifest.limits`):
`admission_ms` 3000, `clock_uncertainty_ms` 250, `leader_lease_s` 12, `renewal_s` 3,
`max_members` 32, `max_operations` 1024.

Voter disk (du of `real-run-0N/voters/voter{0,1,2}-data`): runs 04, 06, 07, 08 and 09 are
77 MiB per voter (each ran etcd); runs 01, 02, 03, 05 are 0 B (voters never
wrote data). For run-09 voter0: WAL file `member/wal/...wal` 64000000 B (preallocated
segment) and `member/snap/db` 16801792 B (about 16.0 MiB), far below the 128 MiB quota.
The other voters and runs were not itemised beyond the 77 MiB du total.
No live NOSPACE or quota-pressure event was observed in these runs.

Agent and model container samples per operation (`docker stats` as captured in
`measured-artifacts.json`): agent container limit 1.5 GiB (1610612736 B), 256 PIDs,
read-only, capabilities dropped. Agent observed 285.8-341.1 MiB early and
446.7-480.1 MiB late (18 PIDs), CPU 140-169 % early and 0-5 % late. Model
container limit 2 GiB; observed 11.7-41.4 MiB when idle to 1.508-1.562 GiB while
loaded, CPU up to 200.25 %. These are four point samples per operation, not
continuous series.

Not captured in REAL runs: etcd voter live CPU/memory time series, voter
fsync/disk latency, and Border/member process resource use.

### Snapshot, journal and counter consistency

Exported cluster snapshot record counts (`real-run-0N/retirement/final.snapshot.json`,
`records` and `revision`): run-07 61 records at revision 44; run-08 40 at revision
29; run-09 104 at revision 82. (Earlier runs 04 and 06: 3 records, revisions 5 and 6.)

Model counter versus journal, as relayed by the coordinator: run-07 8 model POSTs for 4
operations (2 inferences each), run-08 HUD operation 2, run-09 total 4 for 2
operations. Each export packet independently records 2 finished inference claims
per finished operation. Not verified here: I could not locate a persisted model-request
counter file for these totals. `execution-evidence.json` reports the
independent model/guard/native counter artifacts as `available: false`
(`reason: not_present`), `globally_consistent_snapshot: false`, and packet
`actual_effect_totals` are `null`. The `model_requests` 0 in
`real-run-0N/model/qualification-evidence.json` is the pre-run
qualification probe, not the run total. The agreement is therefore a
claimed/journal-level match, not a proven independent execution count.

### Host load

An earlier VS Code attempt (run-08, retained as `real-run-08/export-unknown-vscode`, outcome 'unknown')
failed while heavy Xcode/Flutter builds ran concurrently on the same host. Load
was not measured at the time, so this is a coincidence note, not a proven cause. The editor reports `editor-01` (falsy-document assertion) and retry `editor-01b` (passed) are in `real-run-08-clients/evidence/`; I did not verify they are the same attempt as the unknown operation. Other recorded client retries: browser-01 (20 s
selector timeout), browser-07 (assertion), editor e02 (assertion, passed as e02b).
No host CPU/IO series exists for these windows.

### Not measured

- Pure election time and pure failure-detection time (polling-based figures only).
- Injected 300 ms RTT availability in REAL: the fixture shows quorum-path
  delay of nominal 300 ms RTT is refused beyond the 3 s admission window (see
  Observed latency safety); the REAL runs did not repeat it.
- Physical host suspend/resume and host clock stepping; clock rows are
  injected inputs only.
- WAN, cross-region or multi-host latency and failover (R09).
- Disk-full on a real device and tail disk latency.
- Voter and Border live resource series; percentiles (sample counts are 5-7).
- Physical iOS device timing, and client-side per-phase durations.
- Independent model/guard/native counters.

## Required remaining measurements (still open after runs 07-09)

Capture monotonic fault start, first detected loss, first committed new authority
and first distinct successful native operation separately, with a finer observer
than a 2 s poll. Add continuous voter resource/disk series, independent
model/guard/native counters, and the host-level items listed under Not measured. T041
should be completed only when these, or explicit accepted exclusions for them, are
correlated with signed results; the runs 07-09 timings above are the
interim record.
