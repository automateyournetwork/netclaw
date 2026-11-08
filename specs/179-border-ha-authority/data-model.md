# R08 authority data model

All IDs,hashes,limits and fields validate before use. No unbounded or arbitrary
etcd keys are exposed to runtime/client tools. Schema version is explicit.

| Entity | Key / fields | Invariants |
|---|---|---|
| Cluster manifest | cluster UUID,recovery generation,organization,revision,<=3Border bindings,registered endpoint identities,timing/capacity bounds | private owned config;distinct node installations/keys;HA-required marker persists |
| Enrollment manifest signature | offline P256 signer public fingerprint,exact manifest digest/signature | explicit onboarding;private key never in Border/etcd/client;monotone revision |
| Cluster control | generation,active/fenced,membership revision,revocation revision | quorum controlled;restored starts fenced |
| Node enrollment | nodeID,installation,key/cert,roles,status,revision | cluster role separate from member/eN2N;retirement monotone |
| Leader | nodeID,incarnation,generation,election nonce;etcd mod_revision epoch | only leased record;lease renewal never authorizes effects |
| Operation header | operationID,nonce index,principal,review+digest,approval+digest,issuer,member,state,dispatch marker,attemptID | immutable exact review/approval;quorum-wide nonce uniqueness;bounded64KiB |
| Admission | op/attempt,kind(model/tool),ordinal,request digest,member nonce/incarnation,leader tuple,commit revision | single-use/unleased;exact CAS;no automatic retry |
| Resource reservation | member/runner/workload identity,operation,state | unresolved claim blocks anotherID/leader;no TTL release |
| Member journal | challenge,claim hash,incarnation,consumed marker,effect evidence | local synchronous durable transaction;no resume of old process challenge |
| Result reference | original signed receipt/ACK digests,member artifact references,state | raw outputs remain member/owned artifacts;unavailable not permission |
| Edge enrollment | device key/subject,cluster audience,revocation generation,nonce consumption | shared current authority for all node handshakes;private credential refs |
| Client binding | clusterID+generation+principal,node installations/keys,endpoints+manifest revision,operation refs/sent flags | separate from routing;no secrets/claims in frontend;monotone markers |
| Restore receipt | oldcluster/generation,exact stopped/isolated owned identities,export hashes,newgeneration,one-use activation | trusted observation,not caller asserted boolean;unknowns preserved |

## State transitions

Leader absent→leased current authority→expired/retired;new election receives a
new exact epoch/incarnation. No local force-leader transition.
Operation prepared→approved/refused→dispatch_claimed→member_admitted→result_pending
→completed/failed/refused or outcome_unknown. Terminal result can reconcile an
unknown original attempt only with exact verified signed evidence.
Admission absent→committed→member_consumed→finished/unknown. Neither timeout,
cancellation,lease expiry nor cleanup resets consumption or resource reservation.
Node enrolled→active→drained/retired;re-enrollment creates a new generation.
Cluster active→retired;restore creates distinct fenced generation→explicit activation.

## Capacity and retention

Initial bound1024retained operation headers per cluster;64KiB/header;4KiB/claim;
3Border nodes,32members,32edge devices,3endpoints/client list. Reject capacity
before new effects. Spent/unknown records cannot be deleted to make room. Completed
records may be archived only by an explicitly verified future retention workflow;
R08 provides export and refuses saturation. No expiry resets nonce ownership.
Raw result payloads retain existing <=512KiB bound.etcd MVCC compaction preserves
current records and must not remove application evidence. Private snapshots are
read-only evidence and cannot overwrite running authority.
