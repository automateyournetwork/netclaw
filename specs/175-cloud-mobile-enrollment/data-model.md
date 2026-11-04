# R04b data model

- **Offer**: installation UUID, client UUID nonce, token hash, endpoint/origin, created/expiry times, status, optional consumed member ID. States absent→issued→consumed|expired|replaced. Only initial issue returns QR; status and repeated issue never disclose it. One outstanding offer, explicit compare-and-replace nonce.
- **Device binding**: existing member ID and public key fingerprint plus installation UUID, domain/port/path and capability descriptor. Pending binding persists before enrollment send. Private key remains native; QR token is never persisted. Hello proves the same key; successful reply must match expected installation/fingerprint.
- **Device principal**: issuer device-key, UUID subject derived from installation/member/key/enrollment authority, bounded label, role device-operator. Created only by native authenticated channel, not JSON supplied by caller. Revoked/unpinned channels cannot dispatch.
- **Protected reference**: existing review/revision/digest/nonce/decision/result/ACK semantics, installation+device scope. Owner historical records retain original attribution. Device lookups refuse references owned by others without leaking contents.
- **Client transient view**: installation, current nonce, matrix/expiry while visible, issuance uncertainty. Closing/selection-change/expiry/consumption clears matrix. Reopening reads state; it does not issue.
- **Evidence**: private snapshots/hash/count receipts, source pins, deployment plan and native screen proof. No active QR or credential in checked-in evidence.
