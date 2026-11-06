# R07 evidence matrix

All mandatory technical rows are reviewed for the stated scope. Final human
agreement on timing objectives and roadmap acceptance remains T030. New native
client evidence uses controlled workloads; prior actual cloud/provider/device
credit keeps its frozen source, original failures and platform limits.

| Scenario | Reviewed evidence and disposition | Procedure |
|---|---|---|
| Direct Border restart | New actual strict-TLS child restart at same port/key; prior R06 actual stable public address/workspace recovery | Direct Border service restart |
| Border restart with pending work | New production Border/SQLite/WSS dispatch claim interrupted by actual process death; restart retains original unknown; four duplicates add zero effects | Border restart with pending work |
| Member restart | New actual member/native subnet task process loss and same-home result/unknown preservation; prior R04/R05 actual cloud worker recovery | Member restart |
| Endpoint replacement | New actual registry port replacement and same keys; native Code and Mobile explicit identity-checked movement preserve references. Prior R01 relocation remains historical | Endpoint replacement with unchanged identity |
| Network/address unavailable | Real TLS connection loss, bounded cause/refusal and no fallback; native client loss/restoration | Provider network or address unavailable |
| Member key/application certificate revocation | Actual open-channel, reconnect, post-await success/error refusal and real application X.509 expiry; native Mobile durable removal refuses retained key | Member key or certificate revocation |
| Model provider outage | Frozen R05 actual stopped/unknown model outcomes and runner latch/reattest; affected broad guard/latch regressions pass. No new hosted-provider outage claim | Model provider outage |
| Lost reply/ACK | New ordinary async native result recovery; protected SQLite/signature/lost-submit/ACK regressions; frozen R03 actual native ACK-loss and R05/R06 reply-loss credit | Lost reply or acknowledgement |
| Duplicate/cancellation | Six concurrent same-ID ordinary tasks produce one native effect; pre-dispatch cancel zero, post-dispatch unknown. Protected original-ID claim/recovery regressions separately pass | Duplicate submission and cancellation |
| HUD | Actual Chromium production UI, controlled RPC ledger: durable sent markers, reload/reference/nonce recovery, redirect refusal and zero recovery POSTs | HUD, VS Code and Mobile recovery |
| VS Code G12 | Actual Code1.109 production extension, controlled ledger: loss/restart, same-identity endpoint move, wrong-identity refusal, unchanged references/digest and zero recovery POSTs | Endpoint replacement; client recovery |
| Mobile G13 | Eight actual iOS simulator cases with production TLS/enrollment/hello and controlled original record: migration, trust/identity refusal, cold/loss/lifecycle and revocation. Late-dial/store races covered by source tests | Endpoint replacement; client recovery |
| Optional ngrok agent restart | Unselected/unqualified; direct transport is the selected scope | Optional ngrok agent restart |
| Optional ngrok service/account loss | Unselected/unqualified; no implicit direct fallback | Optional ngrok service/account outage |
| Optional ngrok authtoken revocation | Unselected/unqualified; tunnel credentials distinct from NetClaw authority | Optional ngrok authtoken revocation |
| Runbooks and timing | One procedure for every row; measured clocks and limitations in recovery-objectives.md. Human objective agreement remains open | All procedures and closeout |

See [verification](verification.md) for source commits, counters, raw manifest
hashes, failures, cleanup and incidental editor shared-storage limits. The
[runbook](runbook.md) uses the procedure titles above.

Prior sources: [R03](../172-gcp-hybrid-border/verification.md),
[R04](../173-gcp-cloud-member/verification.md),
[R04a](../174-cloud-client-integration/verification.md),
[R04b](../175-cloud-mobile-enrollment/verification.md),
[R05](../176-ollama-members/verification.md),
[R06](../177-external-en2n-federation/verification.md).

## Final review

All18 functional requirements and6 success criteria remain mapped in analysis.md.
No unresolved production safety failure was found within the qualified scope.
SC005/FR013 human review and FR018 final acceptance remain explicitly open.
Browser automatic wire retries do not enlarge the backend effect guarantee;
revocation does not undo already admitted effects; unknown synchronous calls do
not gain deduplication. No physical-device, public-CA, multi-region, optional-ngrok,
external-CRL/OCSP or continuous TLS-leaf-expiry qualification is inferred.
