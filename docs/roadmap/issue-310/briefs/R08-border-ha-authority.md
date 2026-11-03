# R08 — Border HA authority and protected quorum transport

- **Roadmap item:** prerequisite for 4 (multi-Border)
- **Depends on:** R07
- **Gate:** fixture qualification, then real-runtime qualification, both reviewed

## Specify input

Several Borders of one organization form a cluster with exactly one execution
authority at a time. Members accept protected work only from the current
authority and refuse stale ones (member-enforced fencing). Without quorum there
is no new protected execution. Approvals are exact and admission claims are fresh
and one-use. Uncertain outcomes are reconciled, never replayed, including after a
region or provider failure. Border-to-Border cluster links are a new authenticated
relationship, distinct from iN2N and eN2N, and the quorum traffic is protected as
carefully as any other channel.

User stories:
- P1: Leader loss elects a new authority; members follow; nothing replays.
- P1: A partitioned minority stops issuing protected work.
- P1: A stale or returning Border cannot execute anything.
- P2: Any Border serves the HUD; protected actions forward to the authority.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

## Clarify: decisions (recommended default first)

1. Consensus: etcd majority transactions with three voters, porting Thermidor's
   spec005 authority, fencing and unknown-outcome contract.
2. Quorum transport: etcd client and peer paths over reviewed private/direct TCP with mTLS, etcd
   RBAC, stable advertised endpoints and caller restrictions. Member and external
   identities get no etcd access. Alternatives: VPC or private interconnect.
   [HUMAN]
3. What lives in etcd: bounded control state only (authority lease, epochs,
   admission claims, approval index). Never transcripts, memory or the knowledge
   base.
4. Cluster links: a new channel with its own enrollment, not eN2N consent.
5. Optional ngrok endpoint pooling: allowed for HUD ingress; never treated as authority.

## Plan notes

- Thermidor's spec005 qualification is still in progress and its model, guard and
  effect providers in HA drills were synthetic. Qualify with fixtures first, then
  with real guarded runtimes, and label each.
- Do not combine standalone Ollama qualification (R05) with fixture HA results to
  claim HA Ollama support until the real binding passes.
- Voter count is a design choice separate from Border count.

## Acceptance evidence

| Drill | Required outcome |
|---|---|
| Leader loss | New authority; members fence the old epoch |
| Minority partition | Minority issues nothing protected |
| Three-way and asymmetric partitions | At most one authority; no split execution |
| Stale leader | Refused by members |
| Quorum loss | No new protected execution; status explains |
| Clock uncertainty | Leases stay safe under configured skew |
| Full restart | Recovers with reconciliation, no replay |
| Retired node returns | Refused until re-enrolled |
| Fenced restore | Restored state cannot resurrect old authority |
| Labels | Each row marked FIXTURE or REAL |
| VS Code integration | Explicit G12 impact/disposition and evidence: Authority changes and quorum loss appear correctly; stale approvals cannot execute |
| Mobile integration | Explicit G13 impact/disposition and evidence: Affected approval/result flows preserve fencing across failover, quorum loss and reconnect; reasoned no-impact outcome if unaffected |
