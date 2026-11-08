# HA client identity and recovery contract

Explicit schema1cluster descriptor is additive to standalone runtime discovery:
clusterID,generation,manifestrevision,servingnodeinstallation/key,registered
HTTPS/WSS endpoints,leader/epoch/quorum observations and capability flags.
Endpoint descriptors are bounded and authenticated through existing trust;an
untrusted advertisement cannot expand the pinned endpoint set. Node identity
remains separate from logical service identity and routing address.

Protected review/approval/result/ACK v2 contains stable cluster audience plus
original node signer binding. Current leader authorization is separate from
historical signed issuer. Old pending review from another epoch must be rejected
for a new decision;already sent/consumed/unknown approval cannot be reissued.

HUD header carries nodeinstallation and explicit cluster audience;open-lab principal
is cluster-derived only in explicit HA. Follower requests preserve principal,
nonce,review digest and original operation identity. No HTTPredirect or automatic
mutation retry. Lost reply triggers same-ID/nonce read-only lookup.

VSCode extends existing profile with bounded trusted cluster endpoint set and
revision,retains profileID and per-principal references,and CAS updates the selected
node only after verified cluster/node/TLS identity. Old standalone migration stays
strict. Cookies/tickets remain origin-scoped and are not copied between nodes.

Mobile QR/retained-key hello explicitly binds cluster audience;shared enrollment
and revocation authority permits the same device key/subject on another enrolled
node. Each HTTPS/WSS address is independently TLS verified. Device secure references
remain scoped to cluster generation+subject;the old standalone namespace survives.
Cold/background reconnect cannot accept late dial results for an obsolete profile.

Browser storage stays origin-scoped. Stable origin can retain its own references;
direct node-origin replacement uses explicit status-only original-reference import/
lookup. No claim of cross-origin sessionStorage replication. Combined child decisions
retain independent sent markers. Clients show readable retained results during
quorum loss with freshness/status warning,and disable new approvals;backend is final.

Golden fixtures must cover standalone,validcluster,wronggeneration,wrongnode,
stalemanifest,staleapproval,unknownoperation and retirednode in all three languages.
Actual browser/editor/iOSsimulator evidence uses original signed real operation
records;controlled DTO tests remain separately labeled FIXTURE.

## Manifest trust establishment

The operator creates a private offline P256 cluster enrollment key distinct from
node/application/etcd keys. Its public fingerprint is pinned during explicit
cluster onboarding over the already verified selected HTTPS endpoint or Mobile QR.
It signs the exact bounded node/endpoint manifest,clusterID,generation and monotone
revision. A client stores the public anchor and verified manifest only;the private
root key never enters a Border/model/client/etcd. Existing sessions cannot switch
from standalone to cluster based solely on advertised metadata. Manifest replacement
requires valid root signature and increasing revision;new generation needs explicit
onboarding. Current quorum membership/revocation remains required for authority,
so a historical valid manifest alone cannot authorize work or reinstate a node.

## Frozen implementation handoff — 2026-11-07

The owner authorized three implementation agents in separate worktrees. Root owns
core NCFED, authority, protected service/factory and all runtime mutations. Client
lanes must preserve standalone contracts and coordinate any change to this wire.

Cluster capability descriptor (additive `cluster` property on existing discovery):

```json
{
  "schema_version": 1,
  "mode": "cluster",
  "cluster_id": "UUID",
  "generation": "UUID",
  "manifest_revision": 1,
  "node_id": "UUID",
  "installation_id": "UUID",
  "manifest": {"schema":"netclaw.ncfed.cluster-manifest.v1","manifest":{},"signature":{}},
  "anchor_certificate": "public PEM",
  "anchor_key_id": "SHA256 SPKI hex",
  "authority": {"state":"leader","leader_node_id":"UUID","epoch":1,"observed_at_ms":0}
}
```

Authority states: `leader`, `follower`, `no_quorum`, `fenced`, `retired`.
`leader_node_id` and `epoch` may be null when unknown. Observations never authorize
execution. The manifest is exactly the signed value in ha/config.py; verify its
canonical P256 signature/domain, its node identities/endpoints, and the separately
pinned anchor. An advertised anchor is not already trusted. Initial onboarding
requires explicit acceptance via verified selected HTTPS or cluster QR pins;
subsequent connections enforce the saved anchor, generation and monotone revision.
Keep per-node installation and key identity distinct from the cluster audience.

Existing `X-NetClaw-Installation` names the selected serving node. HA protected HTTP
requests additionally send `X-NetClaw-Cluster-ID` and `X-NetClaw-Cluster-Generation`.
The private bridge receives open-lab auth_context with exact fields
`access_mode, installation_id, cluster_id, generation`. It derives the stable lab
principal with UUID5(cluster_id, `netclaw.open-lab.operator`). Device-key contexts
must use actual signed device authority; plain serialized principals are refused.

HA review adds exact `cluster` fields:
`cluster_id,generation,manifest_revision,issuer_node_id,authority_epoch`.
Approval/result/ACK schemas are explicit `.v2`; standalone remains `.v1`. Review
`border` stays the original issuing node, so failover must validate it against the
pinned cluster manifest rather than replacing its installation ID. A successor
ACK adds `acceptance:{node_id,border,authority_epoch}` while retaining the original
`border` and `cluster` bindings. See protected_contract.py.

Operation DTO retains existing fields and adds `result_reference` (bounded original
receipt metadata or null) and `authority:{mode,cluster_id,generation,served_by,epoch,
observation_only:true}`. `result` is null if the original artifact is unavailable;
`result_reference` remains visible. Reconcile retrieves the original signed member
artifact and ACK without redispatch. Combined operations retain independent child
sent markers; until explicitly wired, HA catalog advertises `cluster_execution_v2`
only, not `calculator_combined_v1`.

Clients must not redirect or retry mutations after endpoint/authority changes.
Preserve exact pending/unknown IDs and monotone sent flags across explicit endpoint
selection. Different browser origins require explicit status-only reference import.
Tests and native drivers may use controlled fixtures while implementing, but actual
R08 client acceptance must later point at root's REAL signed runtime records.
