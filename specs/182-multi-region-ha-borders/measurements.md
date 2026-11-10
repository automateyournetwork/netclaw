# Measurements (T033), source=measured, 2026-11-08

Method: TCP connect time (SYN to RST/accept) over the VPC internal addresses from each Border VM (e2-medium) to the other two, 60 samples each, port 2379 (refused counts as one round trip). Script: scratchpad `rtt.py`, run over IAP ssh.

| From | To | n | min | p50 | p95 |
|---|---|---|---|---|---|
| nne1 (Montreal) | ew1 (Belgium) | 60 | 90.7 | 106.5 | 118.1 |
| nne1 | ase1 (Singapore) | 60 | 238.1 | 239.1 | 240.7 |
| ew1 | nne1 | 60 | 90.7 | 106.4 | 118.1 |
| ew1 | ase1 | 60 | 324.7 | 327.2 | 332.4 |
| ase1 | nne1 | 60 | 238.2 | 239.0 | 240.6 |
| ase1 | ew1 | 60 | 324.7 | 331.5 | 338.1 |

Estimate vs measured: nne1-ew1 est 85-95, measured 106; nne1-ase1 est 220-250, measured 239; **ew1-ase1 est 160-180, measured ~330** (Google routes it via the US).

## Consequences (decisions)
- Leader in **nne1** (nearest follower ew1 at ~106 ms) or ew1; never ase1 (nearest follower 239 ms).
- A commit costs about one 106 ms RTT; ingress at ase1 forwarding to an nne1 leader adds ~239 ms per sequential hop. With the roughly ten sequential steps in an admission (R08), ase1-ingress admissions need about 2.4 s plus guard time, so the 3 s window would not hold. Start with `admission_ms` = 6000 and tune from measured admission timings; the manifest bound is 100-10000. Record the final value and justification in the evidence matrix.
- etcd: heartbeat-interval 500 ms, election-timeout 5000 ms (default 100/1000 is unsafe at 330 ms RTT). `leader_lease_s` >= 10.
- Losing nne1 leaves ew1 + ase1 at ~330 ms: expect refusal or slow commits; this is a degraded mode, to be measured, not claimed as healthy.
