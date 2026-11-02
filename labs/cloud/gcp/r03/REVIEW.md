# Unreleased R03 maintainer infrastructure packet

Source artifacts only; this directory does not grant cloud, DNS, SSH, secret
upload, service activation or teardown authority. R01's private state, public
pilot and secret remain outside this module. No public installation recipe or
release is implied. Exact creation/activation/destruction packets and the owner's
CAD100 total monthly ceiling must be reviewed before any billable change.

The provider-neutral role contract/launcher lives in `scripts/protected-role.py`.
`render_host.py` consumes explicit paths and emits files without installing or
starting them. It selects the dedicated production HUD on loopback13003, with
federation/HUD under `netclaw-r03` to preserve the existing owner0600 bridge.
Caddy uses separate `netclaw-r03-edge`, cannot read the private claw home, and
alone receives `CAP_NET_BIND_SERVICE` for80/443. Federation/HUD have no
capabilities, gateway, Docker or tool/model service. The activation packet must
verify actual service confinement; unit text is not running-system evidence.
Caddy access logs remain off. Its global runtime/error logger deletes the entire
request and response-header objects, including custom CSRF/bootstrap headers and
URI/query values; local upstream-failure probes must verify this before activation.

The fixed layout is `/opt/netclaw-r03/` for root-owned read-only source, native
interpreters, dependencies and binaries; `/var/lib/netclaw-r03/claw` for the
dedicated private home; `/var/lib/netclaw-r03/` for owner-private contracts;
root-only `/var/lib/netclaw-r03/network` for the spent traffic allocation;
`/var/lib/netclaw-r03-edge` for edge certificate state; and `/etc/netclaw-r03/`
for its root-owned Caddyfile. Provision these exact directories/accounts and
verify ownership in the reviewed activation packet. Never copy a repository
`.env`, R01 home or an initial mutable identity archive over a live installation.
The network config is fixed at `/var/lib/netclaw-r03/network/config.json`;
every ancestor of the guard config/allocation must be root-owned and not writable
by group/other. The top-level `/var/lib/netclaw-r03` is root-controlled; only
the dedicated `claw` subtree is writable by the application UID.

`project_secret.py` retrieves only a numerically pinned R03 Secret Manager
version using VM identity. Its complete payload is JSON with exactly
`schemaVersion:1`, `installationId`, and `environment` containing only the
43-character URL-safe `NETCLAW_PROTECTED_OPERATOR_TOKEN`. A private projection
config pins the full version name and payloadSHA256. It writes only
`<home>/netclaw-federation/protected-operator.env`, requires owner0600/private
parents and matching existing installation, and refuses to replace a different
token. Keys, certificates, owner authority and installation state are separate
first-create-only reviewed provisioning. No secret payload enters OpenTofu state.

The module has10 foundation resources: dedicated network/subnet/service account,
empty operator secret and one secret-level accessor binding, one regional IPv4,
IAP ingress, private-destination egress denial, default egress denial and one
Shielded Ubuntu24.04 e2-small VM with20GiB auto-delete standard boot disk.
Only IAP22 is initially reachable. No startup package download or application
service is present. Frozen tools/dependencies transfer through reviewed IAP.

After the host guard is proven, a separate reviewed `network_activated=true`
plan adds3 rules: public80/443, iN2N42102 from1–4 reviewed /32 sources, and
new outboundTCP80/443. eN2N42101, admin/routing/model/MCP interfaces remain
private. There is no peering, VPN, CloudNAT or cloud route to on-prem LAN.
GCP stateful firewall responses and mandatory platform metadata connectivity
are distinct from new egress permissions; host enforcement covers responses.

`host_guard.py` installs one named nftables total-byte quota over **every
non-loopback output packet**, plus a whole-interface tcTBF rate at most1Mbit/s.
The maximum allowance is10GiB; the exact packet may select less. Its private
allocation is durably spent before opening output. Re-entry, reboot or a partial
start cannot allocate a fresh quota. It requires exactly one UP non-loopback
interface (dormant kernel tunnel devices may exist), refuses unrelated qdisc
state, and never flushes another nft table. Applications have no NET_ADMIN
capability to activate another interface; root remains part of the trusted host.
The guard must run before applications/public ingress. Configuration-free DROP
precedes parsing configuration/state, and expiry close reads neither. A separate
configuration-free baseline runs before network startup and permits only
loopback plus link-local DHCPv4 (UDP68→67 to169.254.169.254/255.255.255.255),
so networkd can configure the interface without permitting Internet traffic.
The one-use allowance activates after network-online; reboot consumes no new
allowance and closes output. Install `networkd-r03-guard.conf` as
`/etc/systemd/system/systemd-networkd.service.d/70-netclaw-r03-guard.conf` and
verify the actual image uses only that reviewed manager, with no earlier DHCP or
alternative interface activation. The dependency prevents networking when the
baseline cannot start; a soft `network-pre.target` ordering alone is insufficient.
Missing tools cannot themselves install DROP and must be supplied offline.
Missing quota support fails after the closed ruleset is installed. Docker
Desktop's kernel lacks NFT_QUOTA; local failure-closure is tested, but effective
quota/rate/boot behavior remains an actual GCP-host qualification gate.

The GCE absolute stop time is at most48h and never slides on restart. An additional
absolute host timer closes output. Both must be observed in the actual packet.
GCE can begin automatic stop up to30s late. Kernel byte counts, shaping burst,
offload/packet overhead and platform traffic require measured margins; these
controls are not a GCP spending cap. Unchanged R01 exposure, accrued charges,
taxes and other account services still prevent an unsupported hard-total claim.

Exhaustion or guard re-entry deliberately closes IAP replies too. Normal
federation/HUD service restarts preserve the guard; a VM reboot does not reopen
it. Export evidence before expiry/exhaustion. Recovery requiring a new allowance,
disk attachment or new resource is a new exact reviewed action, never automatic.
Native STOP retains disk/IP/secret charges. Only the reviewed teardown removes
them; separately export and verify evidence before preparing its destroy plan.

`review_plan.py` supports only private init/plan/show, including a destroy **plan**.
It requires a fresh private directory/backend, explicit project/run variables,
rejects foreign-state resources and never runs apply/import/destroy. A saved
plan's digest and resource summary are review evidence, not authorization.
Current charge visibility and the cost gate deliberately remain unresolved in
every generated review receipt until the coordinator separately closes them.

Primary interfaces: [GCE absolute runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime),
[GCP firewall behavior](https://docs.cloud.google.com/firewall/docs/firewalls),
[nftables stateful quota objects](https://wiki.iptables.org/wiki-nftables/index.php/Stateful_objects),
[Caddy server limits](https://caddyserver.com/docs/caddyfile/options), and
[Caddy proxy headers](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
