# R08 private maintainer runbook

This is an in-progress source/evidence procedure for the isolated R08 scope.
It is not a public installer or cloud deployment guide. R09 and roadmap release
remain gated. Consult verification.md and the original private owned-resource
packet before operating anything; never reuse a spent qualification command.

## Identities and access

Each Border owns a distinct node ID, installation, application key, TLS key and
HTTPS/WSS endpoint. The signed offline manifest binds those identities to one
cluster/generation. Every eligible ingress can forward protected requests over
NCFED to the current execution authority. Members attach outbound to all three
Borders over iN2N; they do not receive consensus credentials or a listening role.
An eN2N grant does not confer cluster membership, voting or administration.

Only the current majority can commit new protected admission. A reachable HUD,
healthy TCP connection, cached epoch or existing browser window is not authority.
Already admitted work may finish within its original bounds. Every subsequent
model/tool boundary requires fresh permission. No result is fabricated when the
original effect or its acknowledgement is uncertain.

## Inspect and export before maintenance

Use the reviewed immutable Python/source closure and the exact private config
file/hash. `scripts/ha-cluster.py --help` lists the supported commands. `status`
and `export` require the Border config; export additionally requires an absent
absolute private `--out` path. The source CLI verifies manifest/config bindings
and reads the actual quorum. A failed current read must remain a failed current
read; clients may label retained observations separately.

Record the original cluster/generation, node, current authority, source hash,
operation IDs and owned PID/container identity. Export a consistent prefix and
private local ledgers/artifacts before stopping an execution process. Preserve
original signed review/approval/result/ACK and actual GAIT references where present.
Use the REAL runner's `export-unknown` for incomplete work; it records missing
evidence explicitly and keeps the budget slot occupied. Individual database
snapshots are not a globally atomic cross-runtime snapshot.

## Planned maintenance and failure recovery

`drain`, `retire` and `resume` require an exact `--node-id` and explicit
`--acquire-authority`. A busy current authority refuses the maintenance campaign.
Retirement is durable; restarting the old key does not re-enroll it. Re-enrollment
requires explicit new membership/identity under the reviewed manifest process.
Voter changes additionally require a separately pinned private administrator
config. Prepare the exact change, apply it once, and reconcile the original
change ID after any uncertain response. Never retry an unknown mutation as a
new change or force a minority configuration.

After an unexpected loss, select an already trusted alternate endpoint and read
the original operation. Preserve sent-decision markers and exact pending review.
A changed authority can make a pending review stale. It must not automatically
renew that review, resend approval, choose a new operation ID or invoke the tool.
Unknown member/runner reservations remain in force after restart.

## Fenced restoration

Prepare a new, unused generation and distinct node keys under the same reviewed
offline anchor. A UUID change alone supplies no safety. The trusted host capture
must cover all original voters, Borders and execution processes while running.
After exporting the snapshot and local evidence, prove exact owned processes
stopped and containers stopped/disconnected with restart disabled. Keep private
host signing material outside the runtimes. Unlisted or unverifiable executors
prevent a valid isolation receipt.

`restore-install` and `restore-activate` require the old signed manifest, original
snapshot, signed host isolation receipt and pinned host certificate/key ID in
addition to the new config/hash. The receipt has a five-minute validity bound and
one-use activation. Do not restart the isolated old generation. The implemented
restore deliberately retains a global execution-capacity fence, including after
status authority activates. It provides evidence/status recovery; it does not
automatically restore execution availability or clear missing/unknown claims.
No supported command silently unfreezes that capacity.

## Clients and qualification limits

Use only signed manifest alternatives, ordinary TLS verification and the original
cluster/device identity. Browser chat/session state is not replicated by R08.
The HA execution profile selected for qualification is the protected
OpenClaw/DefenseClaw/Ollama/native-subnet path; fixtures and standalone adapters
do not qualify additional HA runtimes. Actual client procedures are in
`labs/ha/CLIENT-JOURNEYS.md`; a build or a unit test is not native acceptance.

The local qualification budget spans runner, HUD, Code and Mobile. A failure
consumes its reserved allowance; unknowns retain the sole active slot. Export
before cleanup. Stop/remove only exact listed R08-owned resources after their
identity and preserved evidence are verified; preserve retained owner homes,
retirement schedules and unrelated resources. End with memory and the GAIT log.
