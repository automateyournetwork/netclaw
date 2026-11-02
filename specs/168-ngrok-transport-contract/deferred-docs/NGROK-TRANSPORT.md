> **Deferred engineering draft — not rollout documentation.** R01 source is
> integrated for maintainer work only. General cloud deployment, version bumps,
> releases, Marketplace publication and deployment guides remain on hold until
> the full issue310 roadmap is complete, including users, SSO and RBAC.
> The owner-operated pilot is a qualification fixture, not a deployment template.

# Strict remote federation transport — R01 / spec168

ngrok remains the supported configuration option for making a home/office Border
behind NAT reachable from the Internet. A cloud Border with direct ingress, or a
private/air-gapped on-prem Border, does not require it. Use
[deployment choices](DEPLOYMENT-TOPOLOGIES.md) and [direct setup](REMOTE-TRANSPORT.md)
for those paths. Existing ngrok installations are not changed by the cloud option.


This opt-in source feature carries two application protocols through separate
reserved ngrok TCP addresses. Local socket tests are recorded in
[verification](../verification.md).
Live ngrok, cloud deployment and remote platform qualification remain separate.

```text
member -> reserved iN2N TCP -> owned loopback listener -> TLS1.3/exporter/admission
peer Border -> reserved eN2N TCP -> owned NCFED listener -> TLS1.3/key/consent
```

ngrok forwards bytes; TLS terminates in NetClaw, including the local agent-to-app
hop. No PROXY protocol, traffic policy, payload rewriting or agent/edge TLS
termination is allowed. Members run no ngrok agent or daemon listener in this
profile. The separate public NCFED listener rejects BGP, NCTUN and HTTP. Neither
endpoint exposes HUD, gateway, models, MCP, brokers or etcd. HUD ingress requires
its own review. Arbitrary reserved TCP ports must be reachable outbound; a
443-only egress policy is unsupported.

## Preparation and ownership

Use the existing [separate-claw installer](../../../docs/GETTING-STARTED-VSCODE.md) to create
each installation. Choose OpenClaw or Hermes explicitly. Never borrow another
installation's identity, credential file, model token or device credentials.
This transport adds no integration credential to the Border.

Use Python 3.12 and the isolated protocol environment with the pins in
`mcp-servers/protocol-mcp/requirements.txt`. Strict iN2N needs pyOpenSSL's public
TLS exporter API; stdlib `tls-unique` is not a substitute for TLS1.3. The independent
certificate-helper environment stays separate. Native Windows is unsupported by
the POSIX ownership/locking implementation; WSL/Linux and Intel Mac require their
own strict-profile qualification. See the platform matrix before claiming support.

Resolve the selected installation using the existing runtime selector. For
example, set `NETCLAW_RUNTIME=openclaw` and `OPENCLAW_HOME` to an operator-owned
initialized home, or `NETCLAW_RUNTIME=hermes` and `HERMES_HOME`. These are examples,
not owner-specific defaults. The installation ID is the existing
`netclaw-hud/installation.json` identity; do not invent a new one for a move.

Set these entries in that installation's private `.env` using the existing
private environment writer, with no shell interpolation:

| Setting | Scope |
|---|---|
| `N2N_ROLE` | `border` or `member` |
| `N2N_ENDPOINT_REGISTRY` | Absolute registry path, owned 0600 file under an owned 0700 directory |
| `N2N_BORDER_REGISTRY_ID` | Member's approved iN2N dial entry ID |
| `NGROK_AUTHTOKEN` | Border only; transport authority, not application identity |

An explicitly selected invalid/missing registry fails closed. An absent registry
retains the existing compatibility path. Removing the setting is a reviewed
migration, never an automatic recovery step. Cloud secret-manager/workload-identity
rendering belongs to the cloud briefs; do not deploy static cloud keys on hosts.

Verify the ngrok account's reserved TCP addresses, endpoint quota, TCP entitlement,
regions and actual billing independently. An authtoken does not authorize the
account inventory API. No reservation is allocated by this feature. DNS/certificate
issuance and account/endpoint changes retain operator approval.

## Registry contract

The registry is a schema-1 JSON object with exactly `schemaVersion`,
`installationId`, positive integer `revision`, and `entries` (1–128). It is bounded
to 64 KiB, rejects duplicate keys, foreign identities, symlinks, insecure ownership,
duplicate IDs/addresses and unknown fields. Every entry requires:

| Field | Meaning |
|---|---|
| `id` | Stable local selector such as `members` or `external` |
| `direction` | `listen` on the Border or `dial` toward an approved Border |
| `service`, `profile` | `in2n`, `in2n-tls-exporter-v1` or `en2n`, `en2n-tls13-v1` |
| `routing_host`, `routing_port` | Actual reserved TCP address; port is an integer |
| `reservation_id` | Account-issued reserved-address ID, independently verified |
| `tls_server_name` | Expected DNS/IP SAN; independent of routing address |
| `ca_file` | Absolute private file containing approved public TLS CA PEM |
| `application_identity` | Enrolled `<risk>/border` or external `as<ASN>-<router-id>` |
| `application_trust` | iN2N public application CA PEM; eN2N approved lowercase SHA256 SPKI fingerprint |

A listen entry also requires `bind_host` (loopback IP), `bind_port`, `cert_file`
and `key_file` (absolute private paths). Both iN2N and eN2N listen entries are
required to render/start the owned agent. External peers have separate dial
entries. A member's registry contains its approved dial entry, not another
member. Local schema validation cannot establish account ownership of an address.

The three identities stay separate: the route locates an endpoint; CA/name
verification authenticates TLS; application identity and trust authorize the
Border. Strict iN2N challenges the Border before disclosing an enrollment token
or member proof, and binds admission to the connection's RFC9266 exporter.
Enrollment remains one-use/expiring. Strict eN2N verifies the approved peer key
and requires bilateral consent. Its registered TLS key also signs application
possession; name/CA verification and application enrollment are separate checks.
Renewal with the same key preserves that pin; changing the key requires review.

## Configure and inspect

Commands below operate only on the selected installation. Replace input filenames
and revisions with the reviewed values; commands never infer account addresses.

```sh
netclaw peering transport register --file /private/operator/registry-input.json --expected-revision 0
netclaw peering transport validate
netclaw peering transport render
netclaw peering transport export --id members
```

Register requires the registry setting and initialized installation fence first.
Revision zero means no existing registry. Updates require the exact current
revision; a stale writer changes nothing. Export returns a public bundle with
the route, expected identities and CA, without local paths, private keys or tokens.
Inspect its public trust out of band before transferring it to a member.

```sh
netclaw peering transport import --file /private/operator/border-public.json --expected-revision 0
```

For an initial import, set the destination registry path first. Import writes the
approved public CA privately, binds the registry to the destination's existing
installation ID, and sets the member selector in its private environment. Existing
single-use enrollment tokens travel through existing private provisioning,
separately from the public bundle. An interrupted import needs inspection; it is
not permission to create a replacement identity or replay enrollment.

`validate` means local configuration validity. `status` means owned agent process
status. `/n2n/status`, existing MCP status/posture and the HUD report configured,
TCP reached, TLS verified and application admitted separately. Authentication is
derived from a current channel and matching registry revision. Historical TCP/TLS
observations include their time and are not proof of current admission.

## Activate and recover

Start the selected Border daemon through the existing managed federation service
first. Before starting ngrok, the controller verifies daemon PID/start identity,
the selected registry revision and both actual strict listeners. It writes an
explicit v3 named-endpoint configuration with the shared inspection API and remote
management disabled. It loads only the selected transport token, not provider or
device secrets. The following activate or stop real endpoints and require the
operator's deployment authorization:

```sh
netclaw peering transport start
netclaw peering transport status
netclaw peering transport stop
netclaw peering transport unit
```

`unit` only renders a per-installation systemd unit; installation/enabling is
separate. `scripts/in2n-services.py ngrok-unit` exposes the same renderer. `run`
is the unit's foreground supervisor. Stop checks PID, start time, executable and
owned config; it never selects or kills a global ngrok process. A legacy agent
must be identified and stopped manually during an approved cutover. This tool
never adopts it. Stopping an agent does not release/delete reserved addresses.

Private lifecycle receipts live under `netclaw-federation/ngrok/`. Agent raw output
is discarded to avoid leaking account diagnostics; inspect owned process state
and perform explicit account/config checks for diagnosis. Receipt records are
bounded individually; retention/rotation of the append-only log is operator-owned.
Process readiness is not endpoint or application qualification.

For a reviewed address-only change:

```sh
netclaw peering transport address --id members --host <reserved-host> --port <reserved-port> --reservation-id <reserved-id> --expected-revision <current-revision>
netclaw peering transport recover --expected-revision <current-revision>
```

Updates preserve keys, TLS identity and application identity. `recover` explicitly
restores the previous valid document as a new revision; it is not automatic
fallback and does not repair a corrupt current file. Reconnect reads the current
approved registry. Coordinate updates at both ends, stop the old owned agent and
start with the new config. Existing channels are not evidence for the new revision.
Transport retry never resubmits delegated application work; uncertain outcomes
remain reconciliation work. No new endpoint is allocated as a recovery shortcut.

## Migration and portability

Upgrade both ends before selecting the strict profile. Back up private state,
approve the independent trust bundle, review the exact endpoint configuration,
stop/fence old transport, select the registry, start managed listeners and perform
positive, negative and recovery checks. A legacy peer cannot negotiate down from
this profile. Direct LAN and spec108 cloudflared paths remain separately configured
compatibility options. Do not describe their historical evidence as strict ngrok
qualification.

An address relocation is covered here. A full Border/member move requires fencing
the old process, preserving enrolled identity and authoritative state/audit data,
rebinding secrets via the destination's identity, testing cutover and retaining a
reviewed rollback. Do not run two copies of one installation identity concurrently.
A clone gets a new installation identity, new keys and fresh enrollment. Moving
between clouds must not require this repository owner's project, DNS or credentials.
Cloud IaC, secret migration, authority/quorum and fleet cutover are later briefs;
R01 does not implement or qualify a complete cloud migration.
