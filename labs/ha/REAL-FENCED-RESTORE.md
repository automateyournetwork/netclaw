# REAL fenced restore (spec 179, matrix row "Fenced restore")

FIXTURE: actual owned isolation; new generation remains fenced (`fenced-restore-fixture-01`).
REAL (this document): real-profile unknown/reservations retained; stale snapshot gap freezes
affected capacity; no speculative execution. Source: `labs/ha/real_restore.py` (default-off,
additive, never imported by the runner) wrapping the fixture's proven primitives. Tests:
`tests/n2n/test_ha_real_restore_179.py` (source-only: no Docker, process or model).
This is coordinator-operated qualification. Nothing here is run by an agent without the owner's
go-ahead; a fixture or unit pass is not REAL evidence.

## 0. What the REAL restore proves, and how

One fresh REAL run root `R` (its own budget, its own voters). Real operation A (positive) completes
with signed result and successor ACK; a stale snapshot is exported at revision X; real operation B
(unknown-producing) is dispatched and left unknown (member SIGKILL after approve, the run-09
`member-kill` pattern, so `attempt_id` is set, reservations are `reserved`, B has no result/ACK).
The OLD generation (3 voters, 3 Border daemons, member) is stopped and isolated under the host
isolation receipt; a NEW generation (fresh voters, node/installation/key identities, same offline
anchor) is installed from the STALE snapshot (missing B). Production gates must hold:

| Gate | Expected |
|---|---|
| inactive new generation campaign | `recovery_fenced` |
| activate (status authority only) | `capacity_frozen: true` |
| fresh `prepare`, model admission, tool admission on the new generation | `recovery_fenced` (in-process, production `OperationLedger`) |
| B / its claim / its reservations | absent from the new generation (never silently recreated); originals retained in exports and in the old voters' data |
| model access-log request count | unchanged across the restore (coordinator-saved, unverified observation) |
| budget | 2 reservations (A settled, B unknown, slot retained); restore reserves nothing |

Why the refusal probes are in-process and not an operator approval: B's `unknown` holds the single
active budget slot, so `Budget.reserve` refuses any further approval on this run root
(`unresolved_operation_retained`). The probes use `verify_restore`, which drives the production
`Authority`/`OperationLedger` gates against the restored store (campaign, prepare, model, tool).
No new-generation Border/member is started, so there is no path to the model at all. A stronger
operator-level attempt is the optional Phase 2 below.

## 1. Budget accounting

| Item | Reservations | Notes |
|---|---|---|
| A positive operation | 1 | normal `review` -> `approve` -> `export-operation`, settled |
| B unknown-producing operation | 1 | LAST operation of the run; stays `unknown` |
| fresh-admission refusal after restore | 0 | in-process production gates; no operator approval, no model, no tool |
| Total | 2 of the remaining 10 | (the closure plan table's "1 approval" for this row undercounts: A is required to make the stale snapshot non-empty) |

B is unknown-producing, so it is last in its run; nothing may be approved after it (the budget would
refuse). The run is one dedicated fresh run: do not reuse a run root that already had leader loss,
killed Borders or other unknowns (the capture needs all 3 Borders + the member alive, and the gap
check needs exactly one settled and one unknown reservation).

## 2. Phase-by-phase REAL procedure

`$R` = run root, run from `$R/source` with the reviewed Python. `RR` = `python -B -m labs.ha.real_runtime`,
`RS` = `python -B -m labs.ha.real_restore`. Every mutation is one-shot with an exclusive claim; never delete a
claim to retry; an interrupted phase is inspected with its original IDs.

### 2.0 Source and gate
Add to the plan's `source_files` (new frozen packet + new fixture gate per the standing rule):
`labs/ha/real_restore.py`, `labs/ha/restore_verify.py`, `labs/ha/fenced_restore_fixture.py`,
`labs/ha/process_fixture.py`, `labs/ha/etcd_lab.py`, `labs/ha/dependencies.json`,
`scripts/lib/ha_cluster.py` (most already required by the runner closure). The machine must be idle.
Before anything starts: confirm no other spec179 voters are running (the global cap is 3 voters; the
driver refuses unknown running spec179 roles but tolerates this run's `<name>-model` container).

### 2.1 Bring up the REAL profile (existing runner, unchanged)
`RR prepare --plan ...`, `RR model-start`, `RR materialize`, `RR coordination-start`,
`RR start-role --role border0|border1|border2|member`, `RR attachments` (3 authenticated iN2N attachments).
Save the baseline counters `$R/counter-observations/{guard,model,native}.json` (existing convention).

### 2.2 Offline restore preparation (no process, no Docker)
`RS prepare --root $R` -> prints `plan_sha256`; review `$R/restore/plan.json` (pins, old/new voter documents,
limits). It creates `$R/restore/{new-voters,host,isolation,evidence,counters,pre-isolation}`: a second EtcdLab
voter set in the SAME cluster id, a replacement manifest signed with the offline anchor key from
`$R/voters/cluster-identity/root.key` (new generation, fresh node/installation/key IDs, fresh endpoint
ports, no `root.key` copy in the new set), and a separate host isolation signer. Ports must not collide with
the run plan's ports (checked).

### 2.3 Capture the live old authority (BEFORE operation A)
`RS capture --root $R --plan-sha256 H`. Records 3 exact voter container IDs and 4 process subjects (PID, start
id, command digest) read from `homes/<role>/netclaw-federation/daemon.json`, then `HostIsolation.capture`
(no caller-supplied "isolated" boolean). Spawn PID vs daemon PID are recorded side by side.

### 2.4 Operation A (positive; approval 1)
`RR review --node border0` -> review file; `RR approve --node border0 --review-file ...`; wait for completion
(`RR observe`); `RR export-operation --claim-file $R/claim-<id>.json --destination $E/export-A`. Budget: A
`settled`. Save `counter-observations/*` again.

### 2.5 Stale snapshot (revision X)
`RS snapshot --root $R --plan-sha256 H --first-claim-file $R/claim-<A>.json` writes
`restore/stale-snapshot.json`. Gate: A is `completed` with its ACK, A is the only settled reservation, no
unresolved operation, every resource `released`. Do this BEFORE reviewing B: a `review` writes an operations record
(`review_pending`) and B must be absent from the stale snapshot.

### 2.6 Operation B (unknown-producing; approval 2; LAST)
`RR review --node border0`; `RR approve --node border0 --review-file ...` and, right after it returns (run-09:
0.02 s), SIGKILL the member daemon PID (verify PID start id first). Do not retry or approve again.
`RR export-unknown --claim-file $R/claim-<B>.json --destination $E/export-B` (original claim, local journals,
`consensus-evidence.json` = the later linearizable snapshot, budget `unknown`). If consensus is unavailable the export
says so; the gap phase then refuses (`later_consensus_evidence_unavailable`).

### 2.7 Pre-isolation evidence (coordinator, BEFORE any stop/removal)
Into `$R/restore/pre-isolation/` (mode 0600, not rewritten later): `model-access.log` (`docker logs` of the
owned model container, complete, non-rotating), `voter{0,1,2}.log`, `border*-daemon.log` copies, and
`$R/restore/counters/model-before.json` = `{"request_count": <int>, "log_sha256": "...", "observed_at_ms": ...}`
(the access-log request count; same count as the preceding observation, B's failed attempt included). Never
`docker rm` the model container before the final export.

### 2.8 Gap proof
`RS gap --root $R --plan-sha256 H --first-claim-file A.claim --unknown-claim-file B.claim --later-evidence-file
$E/export-B/consensus-evidence.json`. Requires budget = {A settled, B unknown}; A completed in the stale
snapshot, B absent from it and non-terminal later; the two member/runner resource keys changed A/released ->
B/reserved. Unlike the fixture it does not require a committed model claim (a member killed after dispatch may
have none). Writes `restore/stale-gap.json`: `missing_evidence_recovered:false`.

### 2.9 Stop and isolate the old authority
1. `RR stop-role --role border0|border1|border2` (production PID/start-time check). The member is already dead from
   2.6; do not `stop-role member` if the daemon record is gone (record the failure verbatim).
2. `RS isolate --root $R --plan-sha256 H`. Requires `model-before.json` + `model-access.log`; every inventory process must
   be absent (PID reuse counts as not isolated, conservatively); stops and disconnects exactly the 3 recorded old voters
   (restart policy must already be none), proves no running voters remain and `HostIsolation._observe(isolated=True)`.
   The model container is untouched.

### 2.10 Export manifest (immutable, before the receipt)
`RS exports --root $R --plan-sha256 H --export-dir $E/export-A --export-dir $E/export-B [--artifact ...]`. Backs up
(sqlite backup API, closed DBs) member/Border `federation.db`, inference, runner and admission journals into
`restore/evidence/backups/`; adds the budget snapshot, stale snapshot, gap, inventory/baseline, evidence/pre-isolation,
counters, spawn files and daemon logs. At most 256 files, each private regular and digest-bound. Old voter data directories
are retained in place; archive-copy them to private storage if the owner wants more than "retained".

### 2.11 Start the new generation and install
`RS start-new --root $R --plan-sha256 H` (asserts isolation again, running-voter inventory empty, starts the NEW
3 voters, proves the namespace empty). `RS install --root $R --plan-sha256 H`: issues the host receipt only now (5 minute
life), `install_restored` inactive, `verify_restore` inactive (campaign `recovery_fenced`), `activate_restored`
(status authority only), `verify_restore` active (fresh prepare, model and tool admission `recovery_fenced`, control
unchanged, capacity frozen), and proves B's operation and claim keys were not recreated.

### 2.12 Counters and final export
Coordinator saves `restore/counters/model-after.json` (same format, taken after 2.11), then `RS counters`: equality of
`request_count` and `restore consumed no budget`. Then `RR export-instrument`-style final export of `$R/restore`, all
`docker logs` (old voters, new voters, model), `restore-*.json`, receipts and `isolation/*`. Cleanup of the new voters,
the old stopped voters, model and networks is a separate reviewed exact-owned retirement after the export; retained
evidence is never deleted automatically.

## 3. Materializing the new generation (what is and is not done)

The fixture restores into a second voter set without starting any Border or member; the REAL driver does the same
(`replacement_identity`: same cluster id, same public anchor, new generation, node/installation/key IDs, endpoints, no
enrollment private key in the new set; the host signer lives only in `restore/host`). The gates are production
`Authority`/`OperationLedger` code, so no new-generation role processes are needed to qualify this row.

`voters_dir` indirection (implemented, default off). `labs/ha/real_runtime.py` plans accept an optional `voters_dir`: one
lowercase single-component name (`[a-z][a-z0-9-]{0,31}`, not `.`/`..`/hidden, not a reserved run-root directory such as
`source`, `restore`, `homes`, `contracts`, `proxies`, `new-voters`) that resolves to a private directory inside the run root.
Absent, it is `<root>/voters` and behaviour is unchanged. `voters_path(plan, root)` is the single resolver; `Rehearsal.voters`
replaces the hard-coded path in `prepare` (EtcdLab), `materialize` (identity, transport, credentials.json, owned.json, pki),
`start_coordination`, `context`, `validate_review`, `export_operation` and `_consensus_evidence`. `real_restore.Restore.old_lab`
uses the same resolver so the old generation is whatever the plan names; the new generation stays at `restore/new-voters`.
The plan is the reviewed, hash-bound input of every claim, so the choice is recorded with the run.

Optional Phase 2 (NOT implemented; needs owner decision): start new-generation Borders/member and attempt an operator-level
approval. It cannot use this run root's budget (slot held), and the runner still assumes ONE generation per run root:
`homes/`, `contracts/` and the `start_role`/`validate_role`/`operator` path roots are not yet per-generation, and plan
validation would need the second generation's ports. That is a frozen-source-visible change; not made here.

## 4. Risks and limits

1. **Isolation receipt semantics.** The receipt proves the recorded 3 voter containers (stopped, no networks, restart policy none)
   and recorded Border/member PIDs (absent; PID reuse also counts as not isolated) at observation time, from the same host
   account that holds the signer. It is not proof that no other copy of the old authority exists, and it is host-owned, not
   independently attested. The five-minute lifetime is why issuance is inside `install`.
2. **PID identity.** The subjects use `daemon.json` PIDs. If the production launcher forks, the spawn PID and daemon PID differ;
   both are saved (`evidence/spawn-vs-daemon-pids.json`) but only the daemon PID is an inventory subject. A wrong/missing
   `daemon.json` fails `capture` before any fault. Needs all three Borders and the member alive at capture, so no earlier Border
   kill in this run.
3. **Member kill timing.** The kill must land after dispatch (`attempt_id` set, resources reserved). A kill before approval
   leaves a pending review and the gap check refuses (`genuine_stale_operation_gap_required`); there is no second attempt on this
   run (budget). A B that unexpectedly completes is refused as a later terminal state.
4. **No committed claim required.** Gap evidence is operation + reservation records; a model admission claim in the later snapshot
   is reported but not required. The matrix wording "unknown/reservations retained" is met; "claim retained" holds only if present.
5. **Stale snapshot ordering.** Taken after A and before B's review. `review` of B earlier would put B in the stale snapshot and
   void the gap proof.
6. **Counters.** The model counter is a coordinator-saved docker-log count, an unverified observation; absence of a Border/member
   in the new generation is the structural reason no call can occur. The driver never reads the model.
7. **Running-resource cap.** At most 3 voters run at once; the old three must be stopped before `start-new`. Other spec179
   resources (peer proxies, this run's model) are tolerated; anything else running refuses the phase.
8. **Unknown outcomes.** A failed phase keeps its claim and cannot be replayed. A failure during `isolate` after a voter was stopped
   leaves a partially isolated old authority; do not restart a voter: inspect the retained evidence and owner-decide.
9. **Cannot be done safely / not claimed:** automatic recovery of the missing B evidence or of capacity (the fence is global and
   permanent for this generation), qualifying a native profile on the new generation, retiring or deleting the old/new voters
   (separate owned cleanup), and any claim on the full matrix. `native_profile_qualified:false` and
   `missing_evidence_recovered:false` are recorded in every result.
10. **Source freeze.** New files change the source map; a new gate and frozen packet are required, and the driver refuses to run
    outside `$R/source` (`run_frozen_source_required`).
