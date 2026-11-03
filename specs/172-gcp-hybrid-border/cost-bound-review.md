# Historical optional R01 pause — not executed

November3 outcome: the owner delegated isolated R03 completion/cleanup and removed
the earlier billing input as an execution blocker. R03 is now qualified and fully
retired. This optional R01 pause was never executed; R01 remains unchanged and
retains its existing costs. The old cost gate below is historical, not current.
See [activation-delegation.md](activation-delegation.md) and
[verification.md](verification.md). Do not execute this preserved proposal.

Prepared2026-11-02; **not executed or delegated**. This is a separate proposed
change to the preserved R01 pilot, not part of the10-resource R03 foundation plan.
It is one concrete way to remove R01's ongoing unbounded public traffic while
qualifying the bounded temporary R03 host. It does not establish accrued billing.

## Exact proposed action and impact

Recheck that project/zone/name still identify instance ID`7647370903424740100`,
currently RUNNING, then run only:

```sh
gcloud compute instances stop netclaw-r01-20261101 \
  --project=netclaw-506315 \
  --zone=northamerica-northeast1-a
```

The R01 public HUD/federation becomes unavailable. The VM is stopped; no disk,
address, DNS, identity, key, source, private state, secret or audit file is deleted
or overwritten. Standard guest shutdown may terminate in-flight sessions; a
terminated/uncertain operation must not be replayed. The current R01 disk and both
reserved addresses remain billable, conservatively approximately CAD18 per744h.
Keep the VM stopped until a separately reviewed restart or retirement; a restart
would reopen its traffic exposure. There is no automatic restart in this proposal.

After the stop, verify the same instance ID is TERMINATED, its disk and two
addresses are retained, and the authoritative R01 Terraform state hash is unchanged.
Preserve any stop timeout as unknown and query state; never infer success or
reissue a mutation blindly. No R03 apply follows unless its separate exact plan is
delegated and the total cost gate is resolved.

## Evidence and remaining cost gate

Private current metadata:
`~/.local/share/netclaw/roadmap-r03-20261102/r01-cost-bound-baseline.json`.
R01 initial fixed STOP remains December1 absent this separate delegation.
Authoritative state SHA256:
`62364e466434974c6b4f55c395ef95a9376113aa9fcf4d44518511a160643fbf`.

R03's47h foundation base is estimated CAD1.63, before traffic/tax/other services;
its later activation proposes at most10GiB output and1Mbit/s with fixed expiry,
then reviewed teardown. Current gross month-to-date billing, tax treatment and
the owner's currency confirmation are still required to reconcile the hard total
CAD100/month ceiling. The native budget alert cannot enforce that ceiling.

Approval is required because the roadmap reserves commands that change cloud
resources for exact review/delegation. The owner may keep R01 running instead;
that requires a separately reviewed finite traffic bound before new R03 spend
can be claimed to meet the total ceiling. No such R01 guard is installed or
silently authorized by this document.
