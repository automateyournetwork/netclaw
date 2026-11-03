# R04 protected member contracts

Existing owner routes, principal, signed approval/result/ACK and GAIT remain.
No new public execution endpoint.

1. Actual eligible MCP tools: netbox_get_object_by_id with discovered singular type
   and exact positiveID; subnet_calculator with discovered schema and IPv4 /24–/30.
   Unknown fields, write names, changed IDs/CIDRs and drift refuse before effects.
2. Each approval pins member, exact arguments, runtime/MCP/skill revisions, Sonnet4.6,
   one tool effect and at most two provider calls. No approval reuse or silent fallback.
3. Installed NetBox MCP HTTP client is exact-origin/resource, verified TLS, no
   redirects/proxy/retries, bounded timeout/body and sanitized fixed errors.
4. NetBox token only broker-owned MCP child; provider key only guard. Agent receives
   scoped facade capability and actual reviewed skill context. Prove boundaries.
5. Linux relay uses private owned operation Unix socket; Mac path stays explicit.
6. HUD identity uses full member/tool/arguments. Signed structured tool evidence
   supplies facts; model prose is not authoritative output.
7. Member dials enrolled Border outbound; public/member peers, metadata and unrelated
   secret access refuse. Container forwarding shares finite host egress bounds.
8. Recovery reads status only; actual stop/restart retains IDs/results/ACKs/counters.

Discovery, access, model/MCP execution, isolation and evidence validation are separate
qualification stages. Source readiness is not a successful operation.

## Complete argument and evidence bounds

NetBox approvals include every declared argument, with no implicit expansion:
`object_type`, positive `object_id`, nonempty fixed `fields`, and `brief:false`.
Device fields are `id,name,status,site,device_type,last_updated`; prefix fields
are `id,prefix,status,vrf,last_updated`. Their list order is part of exact approved
arguments. No arbitrary field/filter/URL is accepted. Maximum source response is
256KiB and timeout30s; endpoint/source-schema discovery verifies compatibility
before admitting operations. Subnet arguments are exactly `{cidr:string}`:
canonical IPv4 /24–/30 with valid previous and next network boundaries.

Local source-code/profile/schema/skill/endpoint drift refuses before an effect.
Remote record-content drift can be observed only by an authorized read. That read
consumes its one effect and retains the changed/failed result; it never triggers
fallback, replacement object, hidden retry or replay. Source comparison names
capture times and does not equate a historical snapshot with current state.

Before recovery testing, record/freeze actual heartbeat timing and an unavailability
bound of three heartbeat intervals plus10s. Observe at least60s of no provider/MCP
effect growth while stopped; reconnect backoff is measured separately from effects.
