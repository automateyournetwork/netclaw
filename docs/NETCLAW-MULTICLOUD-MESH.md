# NetClaw multi-cloud mesh: GCP and Azure

How NetClaw Borders in **GCP** and **Azure** form one mesh. Design source: `specs/198-azure-multicloud-ha/mesh-design.md` and
`specs/198-azure-multicloud-ha/contracts/cross-cloud-federation.md`. Deployment guides: [NetClaw in GCP](NETCLAW-IN-GCP.md),
[NetClaw in Azure](NETCLAW-IN-AZURE.md).

> ## !! NOT BEHIND ANY AUTHENTICATION !!
> Every Border in this mesh has NO sign-in, NO users and NO access control today. Keep every URL and IP address private.
> Users, SSO and RBAC are a much later roadmap phase (R15-R17).

**Status (read this first).** Live-proven in spec 198, evidence in `specs/198-azure-multicloud-ha/verification.md`: each three-Border group
works on its own cloud (operations through every Border with durable ACKs, leader loss and rejoin), and an Azure group and a GCP group ran
side by side. Also live-proven (2026-11-16, two builds): the signed union catalog from every Border of both groups (followers included, after the follower-epoch fix),
the relay with re-authorization in the receiving group's own ledger (origin recorded), the federation surviving an authority change (epoch 33 to 85),
certificate rotation, and one cross-cloud operation completing with a durable ACK (a GCP-entered operation on an Azure subnet member).
**Still pending live proof (three gaps):** an Azure-entered operation completing on a GCP member, cross-group operations through every follower Border,
and a completed GCP operation after a leader change. They were refused or not reached on an unstable operator link; see verification.md and the contract's live findings.

## Shape

```
        GCP group (gc)                              Azure group (az)
  nne1  ew1  ase1  (3-voter TLS etcd,         nne1  ew1  ase1  (3-voter TLS etcd,
  own authority epoch, own manifest)           own authority epoch, own manifest)
        \   |   /                                   \   |   /
         Members (on-prem Mac, cloud NetBox, ...) dial OUTBOUND to every Border they are enrolled in
```

- **Two three-Border groups**, one per cloud. Each group is a complete HA cluster (Spec 179/182): its own etcd quorum, its own authority
  and epoch, its own cluster manifest, anchor key and generation. A six-voter etcd is not used (an even quorum, slow commits across oceans).
- **Each Border is its own sandboxed node** (OpenShell + DefenseClaw + guarded gateway + workspace + HUD), reachable at its own HTTPS name.
- **Any Border is an ingress.** The owner enters an operation on any of the six Borders (VS Code, one connection per Border).

## What crosses and what never does

| Path | Port | Trust |
|---|---|---|
| Owner to Border HUD | 443 (public, restricted to the operator's CIDR) | trusted TLS (ACME); cluster anchor fingerprint pinned in the client |
| Member to Border | 7444, member dials outbound | mutual TLS, pinned keys; the member's certificate is enrolled in the group's ledger |
| Border to Border inside a group | 7443 | pinned-key mutual TLS from the signed manifest |
| Border to etcd inside a group | 12379, **private network only** | TLS with RBAC; policy allows exactly the two remote voters by private DNS name |
| Border to Border across groups | defined by the cross-cloud contract | pinned peer anchors and an explicit peer grant (design; live proof pending) |

Nothing crosses clouds over etcd: the two groups never share a quorum, so a cloud outage cannot stall the other cloud's authority.

## Members in the mesh

Members dial every Border they are enrolled in. Enrollment is per group (one-shot ledger entry, all Borders of the group stopped), so a
member that serves both groups has an enrollment in each. A member executes one operation at a time per enrollment; concurrent operations use
separate runtime names, so two groups can use the same host without colliding. A failed result fences the member in the group that issued it.

## Cross-group delegation (partly live-proven; three gaps open)

Protected mode refuses the legacy eN2N execution routes by design and stays on. Reaching a member enrolled only in the other group therefore uses a
protected delegate path (see the contract): the ingress Border signs a delegation carrying the origin cluster, operation, approval digest,
principal and a nonce; the receiving group verifies it against the pinned peer anchor and an explicit peer grant, then **re-authorizes in its own
ledger** with a new operation id, its own admission, lease and epoch, and its own member durable ACK. It never accepts the origin principal as its
own authority. Delegation is send-once, and `(origin cluster, operation, nonce)` is unique so a replay is refused. Both audit trails carry both ids.
Required negative tests: no grant, stale epoch, replayed nonce, revoked peer, wrong audience.

## Audit and recovery

Each group records its own authority, approval, dispatch and result references; a delegated operation records the origin reference in the receiving
ledger and the receiving reference in the origin. Unknown outcomes stay retained and are never automatically replayed. Recovery of a stopped Border
is local to its group: restart the sandbox, wait for posture 200 (about three minutes), and the Border rejoins as a follower.

## Limits (honest)

- Cross-group execution is live-proven in one direction only so far, and not through every follower Border (see Status).
- Member admissions go through the lowest-id Border today; a nearest-Border change is written and tested offline but not live-verified or merged (contract, 'Qualified-code change added offline').
- The member host must stay awake and on a stable network: sleep kills the member processes, and a stale Docker network or memory pressure makes hosted calls fail (`agent_produced_no_tool_evidence`). Restart Docker Desktop if a container cannot reach api.anthropic.com.
- Far-region admission: under a degraded two-of-three quorum with a distant leader, `admission_ms=4500` can be exceeded and the operation refused.
- No automatic release for a fenced member; enroll a fresh identity.
- Cost: six small VMs run about USD 0.7 per hour in total; the USD 25 cap and USD 15 pause apply across both clouds through one ledger.
- Release gate: VS Code, mobile and HUD builds that expose multi-region Borders stay unpublished until you approve a release.
