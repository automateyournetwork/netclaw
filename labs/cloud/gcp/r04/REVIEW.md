# Unreleased R04 two-role qualification tooling

Maintainer-only source. The owner's November3 R04 delegation covers the finite
qualification and cleanup. Exact plans, fresh identities, actual inspection and
no-replay receipts remain required; no public rollout, R05 or release is implied.
R01 resources/state and retired R03 plans/identity archives are never inputs.

## Infrastructure and evidence boundaries

The fresh module creates18 foundation resources: one VPC, two subnets, two service
accounts, three empty secrets and three secret-scoped accessor bindings, two
reserved IPv4 addresses, three initial firewall rules and two Shielded VMs.
The Border is e2-small/20GiB; the member e2-standard-2/40GiB. Both disks auto-delete.
Source roles have separate /28 subnets and workload identities. No provider or
NetBox payload is stored in OpenTofu. No project-level IAM role is granted.
Only IAP22 is initially allowed; there is no startup script or Internet egress.

After host provisioning/guard verification, `network_activated=true` adds six
firewalls: Border HTTPS, Border iN2N from this member's reserved /32, role-scoped
web egress, exact public DNS53 to8.8.8.8, and member42102 egress to this Border's reserved /32. The member never
has application ingress. Private-destination egress remains denied. Both roles
use the registered public direct endpoint even though they share a VPC. Neither
module route, public IP nor TCP handshake itself proves authenticated admission.

`budget_observation.py` checks the observed preexisting budget covers the entire
numeric project, monthly gross spend excluding credits, CAD<=100 and current-spend
50/90/100% notifications. It refuses pagination or narrowed service/label filters.
It never edits or adopts that budget. Budget/name observation stays private and
must be freshly read for actual activation; an alert is not a spending cap. Costs
must include the new VMs/disks/addresses, traffic, secrets/model and preserved R01.
A stopped VM leaves disk/IP costs; only exact teardown removes these residues.

## Host layout and render contract

Both fresh hosts use separate copies of these fixed paths:

- `/opt/netclaw-r04/{source,venv,bin}`: root-owned immutable current source, isolated
  Python3.12 and verified native binaries. No writable import tree.
- `/var/lib/netclaw-r04/claw`:0700 service-owned home (`netclaw-r04`). Contracts
  are0600 owned by that service under the root-controlled `/var/lib/netclaw-r04`.
- `/var/lib/netclaw-r04/network`: root-only spent quota/config; config is exactly
  `/var/lib/netclaw-r04/network/config.json`.
- Member execution state is `/var/lib/netclaw-r04/claw/execution`; this keeps
  operation UUID/broker socket paths within the103-byte native limit.
- Border only: separate `netclaw-r04-edge` account/home `/var/lib/netclaw-r04-edge`
  and root-owned `/etc/netclaw-r04/Caddyfile`.

`render_host.py --config <private-json> --output <new-directory>` renders only;
it does not install, enable or start services. Configuration exact keys:
`schemaVersion:1`, `role: border|member`, `hostname`, `source`, `home`, `python`,
`node`, `caddy`, `role_contract`, `hud_config`, `secret_config`, `network_config`,
`expires_at`. Hostname is the reviewed R04 hostname. Member `node`, `caddy` and
`hud_config` are null, and no HUD/edge files are emitted. Other paths are fixed
under the roots above. Every unit uses a clean environment and no automatic
restart. Federation/HUD have no Linux capabilities. The trusted member broker
alone is in the Docker group to invoke the pinned local Docker daemon; that group
is host-root-equivalent authority. It is not granted to the model/relay/guard or
secret-projection service. Actual image, mounts, socket absence and command policy
remain per-operation verification requirements.

## Exact startup-secret projection

`project_secret.py --config <private-json>` uses VM workload identity. Config keys
are `schemaVersion:1`, `installationId`, `home`, `role` and `secrets`. Border permits
only `secrets.operator`; member permits only `secrets.netbox` and `secrets.guard`.
Each reference has `version` (full same-run numerical Secret Manager version) and
`payloadSha256`. No `latest`, R01/R03 secret, redirect, proxy or mixed run is accepted.

Each secret payload has exactly `schemaVersion:1`, `installationId`, `environment`:

| Secret | Exact environment | Private output under home/netclaw-federation |
|---|---|---|
| operator | NETCLAW_PROTECTED_OPERATOR_TOKEN | protected-operator.env |
| netbox | NETBOX_TOKEN | broker-secrets/netbox.env |
| guard | ANTHROPIC_API_KEY, DEFENSECLAW_GATEWAY_TOKEN | guard-secrets/guard.env plus guard-capability |

`guard-capability` contains only the43-character scoped gateway token. Member role
schema2 adds `guard_token_file` pointing exactly there and derives only
`NETCLAW_R04_GUARD_TOKEN` in the daemon's clean environment. NetBox/provider keys
are never loaded into the general daemon environment. Existing files must have
identical private bytes; no automatic credential rotation occurs. Border role
schema1 remains unchanged and rejects member/provider fields.

## Concrete installation order

1. Prepare an exact fresh source/dependency/AMD64 image manifest and closed role
   contracts. Use new installation IDs, owner authority, TLS and enrollment.
   Role schema2 member also pins real protected enrollment plus one direct dial
   registry. Prepare its complete runtime profile only after enrollment succeeds.
2. Apply the saved18-create foundation once. Read actual VM IDs/image/packages,
   network manager, account UIDs and host keys. Preserve R01 and budget observations.
3. Through exact IAP/OS Login sessions, install the necessary offline package delta
   and immutable source/venv/binaries on each owned host. Install Docker only on
   the member, masking package auto-start until the guard dependency is installed.
   Preserve default local Unix socket; no TCP Docker endpoint. Create service UIDs
   and private directories, including member `execution`; keep root-controlled
   parent/source directories. First-create identity installation must refuse any
   existing target and retain a durable attempt on partial failure.
4. Install baseline/guard/expiry units and `networkd-r04-guard.conf` as the verified
   systemd-networkd drop-in. On the member install `docker-r04-guard.conf` into
   docker.service.d and reviewed `docker-daemon.json` under `/etc/docker/`.
   Install rendered resolv.conf to /etc/netclaw-r04/resolv.conf; the member service
   bind-mounts it and Docker explicitly uses8.8.8.8, avoiding the denied metadata
   DNS server. TCP/UDP53 egress reaches only that resolver.
   Do not overwrite an existing Docker installation or unrelated daemon config.
5. Independently prove actual NFT_QUOTA and TBF in an isolated namespace, Docker
   metadata denial and shared OUTPUT/FORWARD byte counting. Inspect actual systemd
   network ordering. Activate the owned main quota once, before opening firewall
   activation. It permits onlylo+physical and optional defaultdocker0 at activation;
   existing foreign bridges/veth refuse. The exact runtime subsequently creates
   and verifies owned operation networks. All forwarding is metered regardless.
6. Install numerical secret versions through coordinator-owned private upload;
   prepare role-specific projection without starting it while cloud egress is closed.
   No payload enters command arguments/state/logs. After projection, validate the real role contract using `python3 -I -S -B scripts/protected-role.py
   --contract /var/lib/netclaw-r04/role.json validate` as the dedicated service UID.
7. Apply the exact six-create network activation with application services still
   stopped. Start the role-specific secret projection, then validate/start Border
   federation, wait
   for its real private bridge descriptor, then HUD/Caddy and owned DNS/HTTPS.
   Enroll the new member once through protected enrollment, finish/pin its profile,
   then start member federation with existing key/generation. No bootstrap executor
   or temporary unprotected mode is permitted.
8. Inspect actual services/listeners/IAM and negative member/metadata paths before
   browser workload approvals. Stop/restart only applications for recovery; do not
   restart the spent network guard or VM. Export evidence before quota/expiry.

## One-use network and resource execution

`host_guard.py` retains a configuration-free closed baseline and absolute expiry.
One shared named nftables quota meters every non-loopback host OUTPUT and all
FORWARD packets, including native Docker traffic. Container link-local/IPv6 metadata
is dropped before allowance. The physical-interface TBF caps output at1Mbit/s;
quota<=10GiB and one fixed window<=48h. These are engineering bounds, not a monetary
cap. Reentry/reboot/partial activation closes output and refuses a fresh allocation.
Both IAP and application responses close on exhaustion. No weaker fallback.

`review_plan.py --tofu <absolute-real-binary> --variables <private-json>
--private-root <0700-directory> --name <new-name> --budget-observation <private-GET>
--budget-name <exact-observed-budget>` creates a saved plan and receipt only.
Pass `--teardown-plan` for a fresh destroy plan from authoritative `r04.tfstate`.
The helper refuses foreign state, unexpected resource addresses, import/update/
replacement, source ambiguity and unverified budget coverage. It never applies.

`run_plan.py --review <private-review.json> check|apply` verifies source/tool/plan/
state bytes, then spends an exclusive durable attempt before one `tofu apply`.
No retry exists. A timeout/failure requires real state inspection and a newly
reviewed recovery plan. For teardown, also supply `--export-manifest` containing
`schemaVersion:1`, matching `run_id` and `files` mapping canonical absolute private
export paths to SHA256. The coordinator independently verifies its semantic
coverage (identities/SQLite/GAIT/results/runtime/recovery evidence); byte integrity
alone does not establish complete evidence.

After exact24-resource teardown, independently inventory owned VM/disks/addresses,
networks/subnets/firewalls/service accounts/secrets/versions and any snapshot/image
residue. Remove only the recorded owned DNS and temporary OS Login key. Compare
R01 state/DNS and the preexisting budget against baseline; retain empty final state.
