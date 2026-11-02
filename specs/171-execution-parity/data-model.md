# Protected execution data model

Canonical fields and validation are authoritative in contracts/execution.md.

| Record | Durable contents and constraints |
|---|---|
| Border operation | Stable UUID; owner principal; unique client nonce and candidate hash; immutable catalog/member/model/tool review; review digest/revision; expiry, decision, approval hash, dispatch intent, member attempt, verified receipt, ACK and revocation |
| Member approval | Unique approval ID, nonce and operation; canonical payload hash; trusted Border/member generations; consumption timestamp; retained spent tombstone |
| Attempt | Unique operation, attempt UUID, executor/effect claims, deadline and unknown state; immutable signed receipt; claims cannot be reset |
| Receipt/ACK | Immutable unique IDs and hashes; conflicting duplicates refused; Border receipt and ACK commit atomically; ACK delivery can be retried |
| Owner authority | Installation, generation, configured principal; hashed one-use ticket and expiry; hashed session, CSRF, absolute/idle expiry and revocation |
| Audit | Existing GAIT extended with principal and operation/approval/attempt/receipt correlations; required at protected boundaries; no secrets or bearer approvals |

Retain spent authority indefinitely for R02. Unrelated HUD task cleanup must not
restore admission. Private artifacts are immutable, atomic and bounded. Missing
or corrupt artifacts never imply success. SQL transactions do not span external
calls. Bridge credentials live in private .env files; descriptors contain only
non-secret binding metadata.
