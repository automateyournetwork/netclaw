# R07 evidence matrix

Prior credits retain frozen tested source, exact provider/platform and original
failures. They are not a claim that the current candidate was cloud-deployed.

| R07 scenario | Accepted prior evidence | Remaining R07 proof |
|---|---|---|
| Direct Border service restart | R06/Spec177 verification: actual cloud workspace/federation restarts, stable public address and original-result recovery | Changed internal/client paths on fresh isolated source |
| Border restart/pending work | R03/Spec172 recovery; R05/Spec176 shared worker restart; R06 original task retrieval | New regression and original-ID no-replay correlation |
| Member restart | R04/Spec173 actual same-identity restart; R05 actual shared worker recovery | Affected strict-channel checks after restart |
| Endpoint replacement | R01/Spec168 same-key relocation covers earlier transport; no new client endpoint move credit | Actual registry movement and native clients preserve identity/refs |
| Network/address unavailable | Prior strict wrong-pin/refusal tests are partial | Real strict connection loss, bounded cause, no fallback |
| Member key/certificate revocation | Existing handshake/admission checks; post-await repro fails | Fix and actual open-channel/reconnect/expiry evidence |
| Model provider outage | R05/Spec176 actual stopped/unknown model outcomes, durable runner latch and reattestation; no replay | Focused guard/latch compatibility; precise historical credit |
| Lost reply/ACK | R03 actual R2 ACK reply loss and original signed/ACK recovery; R05 HTTP reply loss; R06 original task lost reply | Source delivery tests and changed client send-marker paths |
| Duplicate submission/cancellation | Existing protected/async admission contracts; R05 actual cancellation of unsent expired sibling | Concurrent/restart same-ID submit and before/after-dispatch cancellation |
| HUD | R05 actual reload GET-only; R06 original history after cloud restart | Durable uncertain markers/redirect refusal/reference recovery |
| VS Code G12 | R04a/Spec174 native restart exact result/ACK; R05 combined and R06 ordinary external recovery | Explicit same-identity endpoint update and wrong-identity refusal |
| Mobile G13 | R04b/Spec175 cold/background, R05 protected combined and R06 ordinary original-result recovery | WSS-port migration, late-dial stop race, native recovery |
| Optional ngrok restart/service loss/authtoken revoke | Not selected | Unselected/unqualified; separate runbook branch, no new claim |
| Runbooks/timings | Prior timing and failure artifacts retained | One procedure each, measured clocks and human objective review |

Source evidence references: [R03](../172-gcp-hybrid-border/verification.md),
[R04](../173-gcp-cloud-member/verification.md),
[R04a](../174-cloud-client-integration/verification.md),
[R04b](../175-cloud-mobile-enrollment/verification.md),
[R05](../176-ollama-members/verification.md),
[R06](../177-external-en2n-federation/verification.md).

No row is newly marked qualified until its concrete R07 evidence is recorded.
