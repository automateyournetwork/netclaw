# NetClaw multi-cloud mesh: GCP and Azure

How NetClaw Borders in **GCP** and **Azure** form one mesh. Design source: `specs/198-azure-multicloud-ha/mesh-design.md` and
`specs/198-azure-multicloud-ha/contracts/cross-cloud-federation.md`. Deployment guides: [NetClaw in GCP](NETCLAW-IN-GCP.md),
[NetClaw in Azure](NETCLAW-IN-AZURE.md).

> ## !! NOT BEHIND ANY AUTHENTICATION !!
> Every Border in this mesh has NO sign-in, NO users and NO access control today. Keep every URL and IP address private.
> Users, SSO and RBAC are a much later roadmap phase (R15-R17).

**Status.** The bounded November24 Spec198 qualification passed all twelve local/cross-group cells through all six Borders, an Azure-entered physical GCP NetBox read, an operation after actual GCP leader change, native HUD/VS Code approval and GET-only recovery, and a stopped-guard fail-closed test. Original signed results and durable ACKs were independently verified. See [actual closure and limits](../specs/198-azure-multicloud-ha/closure-20261124.md). This is owner-lab evidence; client publication remains held. Live URLs are retired after evidence export.

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
| Border to Border across groups | defined by the cross-cloud contract | pinned peer anchors and an explicit peer grant (live-qualified) |

Nothing crosses clouds over etcd: the two groups never share a quorum, so a cloud outage cannot stall the other cloud's authority.

## Members in the mesh

Each member dials all three Borders in its single enrolled group. Cross-group reach uses the signed relay, never a shared member identity or a second authority for that identity. A failed or unknown operation retains the member fence in its receiving authority. Physical Linux members use the qualified Unix-socket relay and a short private runtime path; the Mac Docker Desktop TCP host alias is not portable to Linux.

## Cross-group delegation (live-qualified)

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

## Qualification limits

- Admission selects the nearest authenticated attachment. The November24 manifests sign `admission_ms=9000`, and the RPC wait derives from that signed bound. Quorum/attestation latency still matters; slower or degraded topologies may correctly refuse an effect. Stable Wi-Fi alone does not repair expiry.
- Four Mac qualification member processes required explicit restart with their unchanged contracts/durable state during the leader exercise. Transparent member process recovery is not claimed.
- After takeover, all twelve original operations remained completed with unchanged digests/counters. Six returned full artifacts and six retained references; old-leader full artifact replication is not claimed. Original member results and ACKs were exported and verified separately.
- Unknown outcomes and fenced identities remain retained. A timeout never authorizes replay or automatic fence release.
- The seven-host final reservation used USD0.93/hour plus fixed historical/provider/transfer/cleanup reserves. USD25 was cumulative; the owner explicitly approved crossing USD15 for the concrete USD23.0075943167 envelope. Future runs require their own current inventory, pricing and spend delegation.
- VS Code, mobile and HUD publication remains subject to explicit approval.
