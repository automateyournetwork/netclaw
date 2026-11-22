# Six-Border mesh design (any cloud, any Border)

Owner requirement (2026-11-15): an operation entered on ANY of six Borders (3 Azure, 3 GCP) must reach ANY member, with no
"blocked by design" carve-out. Protected mode stays on. The legacy eN2N execution routes stay refused; the mesh is built on
the protected path instead.

## Topology
- Two three-voter quorum groups, each with its own TLS etcd + RBAC and its own authority epoch: `az` (nne1/ew1/ase1 on Azure) and
  `gc` (nne1/ew1/ase1 on GCP). A six-voter etcd is not used (even quorum, WAN commit latency).
- Every member (NetBox, subnet, on-prem) is enrolled in BOTH groups through the existing one-shot `enroll_member` and dials all six Borders outbound on 7444.
  One member process holds a per-member execution lock so two groups can never run it concurrently (resource fence stays member-wide per group).
- An owner entering on any Border sees the union: the HUD catalog asks the local group, and the group's Border asks the peer group's
  Border over the existing NCFED peer channel for a signed, read-only catalog.

## Cross-group execution (the new work)
1. Ingress Border A (group X) authenticates the owner in X's audience, records the review and approval in X's ledger.
2. A sends a `cluster/delegate` request to a Border of group Y over the pinned-key NCFED peer channel. It carries the X review,
   X approval digest and X's signed authority epoch observation. Y's grant table must hold an explicit peer grant for X and member.
3. Y re-authorizes in its OWN ledger: new operation id, `origin = {cluster, op_id, approval_digest, principal}` recorded, own admission, own
   lease/epoch, own durable ACK from the member. Y never trusts X's principal as Y authority; it trusts only the signed approval digest under the peer grant.
4. Result returns signed by Y's Border and member; X stores it with Y's durable-ACK reference. Both audit trails carry both ids.
5. No replay: `(origin cluster, op_id, nonce)` is a unique key in Y's ledger; delegation is send-once like `route()`.

## Phasing
1. Dual-group member attachment + union catalog (no trust change). Proves any-Border-to-any-member for every member.
2. `cluster/delegate` with peer grants, so a Border reaches members attached to only one group, with correlated audit.
3. Live: build both groups, rotate (cert, lease, member re-enroll), takeover, cross calls, teardown.

Phase 2 changes security-relevant code; it ships with negative tests (no grant, wrong epoch, replayed nonce, revoked peer, wrong audience).

## Status (offline implementation)
Phase 2 (`cluster/delegate`) is implemented as the peer relay in `ha/federation.py`; the binding contract, qualified-code change list,
open decisions and live requirements are in `contracts/cross-cloud-federation.md`. Phase 1's "member in both groups" is not needed:
every group's members appear at every Border through the signed union catalog. Not yet proven live.
