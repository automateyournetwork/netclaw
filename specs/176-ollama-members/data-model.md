# Data model: additive parent, existing child authority

## CalculatorProfile

Immutable profile ID/revision, family, member installation/enrollment generation,
hosting location, runtime/guard/source/model/prompt/native-schema digests and bounds.
Historical rows retain their original bytes and bindings. Changed profile produces
a new revision; stale review fails. No secret or endpoint chosen by the caller.

## CombinedRequest

`parent_id`, `client_nonce`, installation/principal binding, canonical request digest,
created/expiry timestamps and two ordered child references. Unique principal+nonce;
same bytes recover existing parent, different bytes conflict. Creation transaction
creates both existing child operation records or none. Parent grants no execution
authority and stores no duplicate signed approval. Cancelled flag is durable.

## ChildOperation

Reuse current protected operation: exact principal/member/model/tool/limits, review
revision/digest, decision, one-use claims, signed result and ACK. Add parent/index
association without changing historical unassociated records. Reuse actual existing
state names; conceptual flow is prepared → approved/denied → claimed → succeeded,
failed or unknown. Unknown is not retryable. Cancellation retains completed/unknown
effects. Exact approval payload covers the new profile revision and all its pins.

## ProviderRequest

Operation-owned durable request claims: request digest, ordinal1/2, canonical request bytes,
profile revision, claimed/finished times, response digest, bounded response and
claimed/finished/unknown state. A dispatched claim is never released for replay.
A separate durable member/provider-instance latch stores busy/uncertain state and
its operation attribution across every operation database and process restart. It
blocks new operation IDs until owned-process termination is verified. A recovery
receipt permits fresh separately approved work; it does not change a spent claim into an unspent one.

## VerifiedCalculatorResult

Family/canonical CIDR, network/prefix, address range, exact decimal-string counts,
family-appropriate masks/host rules and bounded native facts; original native result
digest and independent-verification result. Separate model explanation. Result bound
to signed child, actual model/profile, two inference receipts, one native tool receipt,
elapsed/tokens/resource observations and durable ACK. Never infer missing metrics as0.

## ClientCombinedReference

Installation and principal/device binding, parent nonce/ID, two child IDs and local
decision-submitted markers. Store before sending; keep only bounded identifiers.
Separate stores for different installations/device principals. Reopening performs
status lookup only. Invalid/unrecognized persisted state refuses writes and remains
available for diagnosis rather than silently initiating a fresh request.

## QualificationRecord

Frozen source/artifact hashes, live host/architecture/profile identity, observations,
negative+positive probes, failures and recovery effect comparisons, separate browser,
VS Code and Mobile evidence, owned resource manifest/export/cleanup/retention receipts.
Private artifacts outside source; sanitized references and limitations in verification.md.
