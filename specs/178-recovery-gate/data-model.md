# Recovery data model

Existing federation and operation tables remain authoritative. Never restore,
clone or reset authority databases to recover work.

| Entity | Fields and invariants |
|---|---|
| Scenario | ID, source, actual/fixture/inherited class, platform, fault/restoration/recovery timestamps, baseline/effect hashes, limitation |
| Identity binding | installation/risk/member, pinned key, TLS name, routing address/port, revision; address cannot alter trust |
| Client reference | installation/principal, original nonce/operation/parent, monotone decision_sent/revoke_sent; bounded and non-secret |
| Revocation | durable state/generation/key and certificate validity; mutation before close, admission/use checks after await |
| Observation | original request/attempt/result/ACK, native/model counts, pending/unknown/complete/cancel state |

Send-marker absent→sent is durable before I/O and never reverses through GET,
reload, import or endpoint change. Endpoint candidate validation precedes commit;
refusal preserves original binding. Late completion after cancellation remains
evidence. New task IDs cannot evade provider-wide unknown latches.
