# Recovery measurements and accepted objectives

**Status: accepted by the owner on 2026-11-07 after the completed evidence review.** These are operator
recovery targets and investigation thresholds for the qualified single-region
scope. They are not statistical availability SLOs, hard implementation deadlines,
or demonstrated worst-case guarantees. A threshold miss never authorizes replay,
weaker trust, automatic transport switching or resetting uncertain state.

## Observed measurements

| Evidence | Duration | Clock and qualification limit |
|---|---|---|
| R04 member outage detection | 1.462s | Historical exact R04 source/environment |
| R04 member recovery | 19.677s | Completed restart receipt to recovery;729.995s total outage includes human review |
| R06 cold workspace history | 33.34s | Actual cloud native history; model discovery33.10s; existing60s native/130s proxy deadlines |
| R07 strict credential expiry | 0.048302s | Request-start to refusal after actual application-cert expiry; no idle/expiry-to-refusal claim |
| R07 Border restart | 0.129518s | Local child start to authenticated reconnect; signal-to-observed-close0.016586s |
| R07 registry endpoint move | 0.007122s | Local revision update to authenticated reconnect; not DNS propagation |
| R07 member restart | 0.181375s | Local child start to authenticated reconnect; signal-to-observed-close0.002154s |
| R07 pending Border restart | 0.316136s | Process spawn through TLS/device auth and original unknown result; signal-to-close0.001495s |
| R07 native Chromium | Import0.666s, reload0.348s, loss0.160s, restored GET0.070s | Production UI/local controlled RPC; exact-SPKI process trust |
| R07 native Code1.109 | Endpoint move0.296s, loss0.003s, restored GET0.076s | Production extension/local controlled RPC; explicit actions, not supervisor timing |
| R07 native iOS migration | 0.257s | Verify action to same-key recovery on new WSS port |
| R07 native iOS cold recovery | 0.694s | Cold gate to original controlled result; actual prior app termination |
| R07 native iOS foreground loss | 0.148049s | Service-close control to ready via explicit reconnect; detection0.085049s |
| R07 native iOS resume | 0.136s | Actual resumed event to retained-key recovery; app closes WSS while inactive |
| R07 native iOS revocation | 0.336881s | Durable-remove control begins to visible refusal; not admission grace |
| R07 native iOS wrong identity/TLS | 0.246s /0.243s | Explicit probe to refusal, original binding unchanged |

Local UI, service and simulator measurements use controlled original-operation
responses. They do not measure cloud/provider latency, physical radio recovery,
background execution, silent network blackholes or worst-case automatic backoff.
Signal-to-close times are not periodic failure-detector guarantees.

## Accepted operator targets

| Scenario | Target after its stated start | Action when missed |
|---|---|---|
| Border/member or network failure visibility | Report unavailable/unknown within120s of observable failure while the client is active | Inspect owned listener, logs, channel status and timestamps; preserve original references |
| Automatic member/ordinary Mobile reattachment | Same identity within180s after the service and validated endpoint are restored and the client is active | Investigate trust, registry revision and backoff; no new enrollment or alternate transport |
| Explicit endpoint move or HUD/editor/protected-Mobile reconnect | Original status/result or an explicit refusal within30s of the action, with destination already healthy | Keep old binding/references and inspect the failed attempt; no repeated decision |
| Cold cloud workspace history | Original history or explicit failure/unknown within130s of the original recovery read | Preserve original request; inspect model discovery and native/proxy timeout evidence |
| Pending work, lost reply/ACK, duplicates and cancellation | Within the applicable30s/130s status-read target, show original completion, pending, cancellation or unknown | Unknown is a valid safe recovery result; do not demand a new execution to resolve it |
| Model provider unavailable | Explicit refusal/unknown by the selected existing call deadline; no new universal provider timeout | Keep the existing guard/runner latch; use the runbook's scoped provider recovery |
| Revoked or invalid application authority | Zero admission grace: every subsequent admission/use/delivery check must refuse; TLS leaf validation remains handshake/reconnect-only | Treat any unauthorized admission/delivery as a failed gate regardless of UI timing |
| Optional ngrok scenarios | No target selected or qualified | Requires separate scoped selection and evidence |

The120s/180s investigation thresholds leave room for existing liveness behavior
and Mobile's60s maximum retry backoff. They are accepted investigation targets, not newly configured
timers or a proof of recovery under every network condition. The30s manual target
is deliberately distinct from automatic retry and cold cloud history. Human
repair time, DNS propagation, unavailable upstreams and OS suspension are excluded
from restoration-to-recovery clocks and must be recorded separately.

Categorical requirements do not relax with time: zero weaker fallbacks, zero new
post-revocation admissions and zero repeated native/provider effects from original
reference recovery. Already admitted effects remain recorded. Human acceptance
of these targets and the bounded evidence is recorded in verification.md/T030.
