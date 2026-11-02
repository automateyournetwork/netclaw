> Current R01 pilot: DNS/HTTPS, foundation/runtime activation and actual IP
> relocation/recovery are verified. The owner fully delegated these changes and
> requested the full open lab HUD, Anthropic Sonnet and a scoped on-prem subnet
> demonstration. Users/SSO/RBAC remain R15–R17. Use resume.md and verification.md
> for current receipts. Earlier preparation commands below are historical;
> never replay initial activation over the running pilot.

# R01 direct-cloud live qualification

The owner approved direct cloud TCP as primary while retaining home/NAT ngrok,
private/air-gapped sites and the hybrid/multi-region/multi-cloud roadmap. The
original ngrok-only live gate is superseded, not relabeled as passed. Historical
account checks remain in [fresh-pilot.md](fresh-pilot.md) and verification receipts.

## Review before creation and activation

Use the [fresh pilot](fresh-pilot.md) and its [IaC](pilot/gcp/main.tf). Capture the
exact saved plan hash, source/configuration hashes, provider account/project,
region, cost/alert terms, expiry and teardown scope. No default network, owner
runtime, device credentials, provider key or existing endpoint may be reused.
Cloud/account/DNS changes and spend retain the roadmap's exact approval boundary.
A successful read-only plan is not deployment authorization.

Foundation bootstrap does not start NetClaw. Before activating, record actual
allocated routing IPs, exact private listener addresses/ports, fresh installation
IDs, TLS SAN/CA, application identities, approved peer keys/consent and schema2
registry revisions. Direct mode uses no ngrok credential, binary or API discovery.
Use the selected owned daemon controller, not a general process-name kill/start.

## Required observations

1. Record UTC/runtime/source versions and approved configuration. From the Mac,
   measure cloud TCP reachability separately from TLS and application admission.
2. Enroll a fresh member over iN2N, verifying independent TLS name/CA and Border
   application anchor; reconnect using the enrolled identity. Exercise both member
   launcher paths. A member must expose no reachable listener.
3. Complete NCFED identification, TLS1.3, approved application-key possession and
   bilateral consent with the separate external Border. Keep its access outside
   the internal-member scope. State the single-owner pilot qualification limit.
4. Exercise wrong name/CA/pin/Border identity, altered binding, forged possession,
   expired/replayed enrollment, repeated authentication and revocation of new/open
   channels. Confirm durable bounded refusal evidence excludes submitted secrets.
5. Refuse cleartext, TLS1.2, PROXY, BGP/NCTUN/HTTP and member-as-Border attempts.
   Capture actual VPC rules and host listeners: no public shared BGP, admin, model,
   MCP, gateway, broker, HUD or etcd port. Reachability is not authentication.
6. Restart only the owned Border daemon. Reattach to the same stable endpoint,
   prove fresh TLS binding and unchanged identity, and verify no task replay.
7. Prepare/review the exact relocation plan selecting the second reserved provider
   IP. After approval, apply it and explicit registry address updates with expected
   revisions. Prove key continuity, no automatic old-address/profile fallback,
   unavailable state during outage, stale-update refusal and explicit recovery.
8. Retain private raw/sanitized receipts. Stop services only within reviewed scope.
   Releasing IPs, deleting resources and removing pilot secret versions require
   exact teardown review; a stopped VM does not remove ongoing storage/IP charges.

R14 planning counts distinct services separately from public IPs: the illustrative
30–40 services can share per-Border addresses using separate ports. Same-organization
cluster/quorum transport and later topology authority remain future briefs.

T028 remains unchecked until the direct cloud observations exist. Optional ngrok
live acceptance is separately UNQUALIFIED on the owner's Free plan. R02 requires
`next`; R03 requires human acceptance of completed R01/R02 verification.

## Cloud HUD and on-prem evidence

FR026/T040 adds the owner-requested working cloud HUD link. The current access
contract keeps the private operator HUD behind [IAP/SSH](pilot/gcp/README.md)
and provides the owner-selected full open HTTPS lab workspace, without login.
Use [public-hud-review.md](public-hud-review.md); preserve the private API Host/Origin
controls and exact loopback ports. The viewer exposes only bounded status projections. Record the real page, selected
installation ID and its admitted on-prem member, matching the member
certificate/key fingerprint and cloud membership evidence privately. Reconnect
with the same member key and record fresh connection proof. Never publish tokens
or private keys. A candidate URL is not live evidence; provider/chat availability
remains separate from the transport/status acceptance.
