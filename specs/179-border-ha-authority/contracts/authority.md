# NCFED HA authority and transport contract

Version1cluster namespace;protected execution uses explicit v2 envelopes in HA.
Standalone v1 remains byte/schema compatible. No implicit upgrade or downgrade.

## Transport and enrollment

Cluster channels reuse NCFED FederationChannel framing/heartbeat/dispatch over
verified TLS1.3 exporter transport. A separately configured listener/dial endpoint
and cluster enrollment role prevent eN2N/member identities being accepted. Mutual
fresh challenges sign domain-separated(clusterID,generation,nodeID,installation,
incarnation,role,peer challenge,TLS exporter) with separately pinned node keys.
No application RPC before both roles/keys are verified. Membership revocation is
checked before/after awaited handling and outbound delivery. Pre-auth deadline10s.
Only cluster status,metadata forwarding and admission/status RPCs are allowlisted;
there is no arbitrary shell/tool/etcd proxy. iN2N remains member initiated.

## Calls

- `n2n/cluster/status`: generation,node,observed leader/epoch,quorum freshness and
  bounded link/attachment status. Observations cannot authorize effects.
- `n2n/cluster/forward`: narrow operation(method,original request/nonce,principal,
  exact payload digest) over enrolled cluster channel;allowlisted methods only.
  It cannot select arbitrary destinations or transform approval content.
- `execution/admission`: member challenge over authenticated iN2N;kind/ordinal,
  operation/attempt,approval/request digest,member incarnation,cluster audience.
  The serving Border forwards to current leader without manufacturing a new claim.
- `execution/admission-status`: same claim identity,read-only exact commit recovery.
  It never returns a replacement permission for an expired member challenge.

Each mutation compares leader exactvalue+modrevision,control generation/revision,
operation/revocation revision and absent exact claim. Commit yields signed exact
receipt with commit revision. Lost mutation reply remains unknown;no automatic
mutation retry. Exact record readback may establish a commit,not a fresh grant.

## Effect boundary

Before each actual model forward and native tool invocation,the member generates
an unpredictable nonce and records request start(monotonic+wall). Matching response
must satisfy<=3s elapsed and<=250ms wall/monotonic divergence,exact current process
incarnation/request/approval/cluster and durable unspent local consumption.
Recheck immediately at the trusted effect boundary;failure leaves consumed claim
unknown/blocked. Admission commit is the ordering point;already admitted in-flight
effects may begin only within that admission window, then complete under existing
operation deadlines;later boundaries require fresh admission. Effects are not
undone by later quorum/leader loss. No model/agent controls this gate.
Missing HA guard binding,unsupported executor or durable required-marker mismatch
refuses before effect. Returning old epochs and legacy routes cannot bypass it.

## Error states

Fixed public codes:no_quorum,stale_authority,cluster_changed,node_retired,
ha_required,ha_runtime_unqualified,admission_spent,admission_expired,
clock_uncertain,commit_unknown,state_capacity,recovery_fenced.
Errors contain no private endpoints,secrets or provider output. Only proven
pre-admission refusal may say not_submitted;lost replies retain unknown state.

Cluster TLS requires opt-in client certificates and server peer-CA validation,
separate from existing iN2N defaults and etcd PKI. Reuse NCFED framing exactly;
strict duplicate-key/unknown-field rejection is scoped to the new cluster profile.
Forwarded principal is independently validated from device proof or the explicitly
configured open-lab audience;serialized caller assertions alone grant nothing.
