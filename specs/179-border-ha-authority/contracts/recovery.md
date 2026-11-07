# HA lifecycle, recovery and evidence contract

Restart retains same durable state;new process incarnation invalidates old in-flight
challenges. Quorum election never clears operation claims or runner fences.
Drain/retire commits current membership change before closing channels. A returning
old node cannot rejoin merely because it retains its key or local SQLite database.
Voter removal/addition uses actual current majority and refuses unsafe reconfiguration.

Fenced restore requires fresh trusted host observations tied to exact owned voter,
Border and executor process/container IDs;confirm no old authority remains usable.
Export hashes and consistent snapshots precede isolation. New generation starts
fenced with fresh trust,retains all spent/unknown work and requires one-use explicit
activation tied to receipt. Refuse missing,stale,forged or mismatched receipts.
Never overwrite active state with historical backups or replay a spent plan.

For each acceptance row retain:source/image/profile hashes;fixture/real class;
exactparticipants/trust;faulttimestamp+verified directed isolation;quorum revisions;
originaloperation/attempt/approval;actual model/MCP counters;signedresult/ACK;
GAITreferences;timing/clock/storage bounds;failures and cleanup/export receipts.
Measure detection,election and original-result/new-work recovery separately.
No screenshot alone qualifies execution. Zero-call negatives must inspect real
runtime counters rather than infer no effect from a refused frontend response.

A stale snapshot cannot prove no later admission. Recovery reconciles post-snapshot
member/guard/quorum evidence or conservatively freezes affected resources and
runner capacity; it cannot activate clean capacity by omitting missing records.
