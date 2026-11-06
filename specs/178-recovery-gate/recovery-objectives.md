# Recovery measurements and proposed objectives

Human timing agreement follows actual observations. No objective is accepted yet.
A handful of qualification runs is not a statistical availability/SLO measurement.

| Evidence | Observed duration | Meaning and limit |
|---|---|---|
| R04 member outage detection | 1.462s | Historical exact R04 source/environment; not a new R07 measurement |
| R04 member recovery | 19.677s | From restart receipt;729.995s outage includes operator review and is not reconnect latency |
| R06 cold workspace history | 33.34s | Actual cloud native history after cold start; model discovery33.10s;60s native/130s proxy deadline |
| R07 strict credential expiry | 0.048302s | Actual local expiry-to-next-request refusal; no proactive idle-close claim |
| R07 Border process recovery | 0.129518s | Fresh local child start to authenticated reconnect; detection0.016586s |
| R07 registry endpoint replacement | 0.007122s | Local revision update to authenticated reconnect; not cloud DNS/cutover |
| R07 member process recovery | 0.181375s | Fresh local child start to authenticated reconnect; detection0.002154s |
| R07 endpoint/restart/native clients | Pending actual run receipts | Must report detection, restoration and recovery clocks separately |

Security objectives are categorical: zero post-revocation admissions, zero weaker
fallbacks and zero repeated native/provider effects for original-reference recovery.
Already admitted effects are retained even if a later result is refused. Performance
objectives will be proposed from the final observed native/local measurements and
narrow inherited cloud evidence for explicit owner agreement.
