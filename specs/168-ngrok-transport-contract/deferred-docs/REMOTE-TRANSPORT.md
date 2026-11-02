> **Deferred engineering draft — not rollout documentation.** R01 source is
> integrated for maintainer work only. General cloud deployment, version bumps,
> releases, Marketplace publication and deployment guides remain on hold until
> the full issue310 roadmap is complete, including users, SSO and RBAC.
> The owner-operated pilot is a qualification fixture, not a deployment template.

# Direct cloud and private Border transport

Choose a [deployment topology](DEPLOYMENT-TOPOLOGIES.md) first. A cloud Border can
use its provider's stable public address; a private or air-gapped Border uses a
stable private address. Home Borders behind NAT retain [optional ngrok](NGROK-TRANSPORT.md).
Neither direct mode needs an ngrok account, token or process.

Create or select a separate runtime home with an installation identity. Install
the existing protocol/n2n components and their isolated pinned dependencies.
This is the same TLS and application trust contract on OpenClaw and Hermes;
qualification remains platform-specific. Existing homes are not upgraded by these instructions.

Prepare an owned private schema-2 endpoint registry. It has `schemaVersion: 2`,
the selected `installationId`, monotonic `revision`, and an `entries` array.
Each entry includes the fields below; use the exact contract in
[the data model](../data-model.md).

| Field | Direct mode |
|---|---|
| `transport` | `direct_tcp` |
| `address_ref` | Operator reference such as `border-static-ip`; no token or guessed provider ID |
| `routing_host`, `routing_port` | Reviewed reachable IP/DNS and service port |
| `tls_server_name`, `ca_file` | Independently verified certificate name and explicit CA |
| `application_identity`, `application_trust` | Enrolled Border identity and public application anchor/pin |
| `service`, `profile` | `in2n` / `in2n-tls-exporter-v1` or `en2n` / `en2n-tls13-v1` |
| `bind_host`, `bind_port` | Listen entries only: exact NIC address and dedicated port; no wildcard |
| `cert_file`, `key_file` | Listen entries only: private local TLS file references |

Both services can use one static IP with different ports. On GCP the external IP
maps to the VM NIC; bind the application to the VM's exact private NIC IP, not the
external address. All state belongs to the selected installation (0700 directories,
0600 files). Do not include `reservation_id` in schema2. Schema1 remains the original
ngrok-only format and is never silently migrated.

Set `N2N_ENDPOINT_REGISTRY` in the selected private environment. Border mode also
requires `N2N_ROLE=border` and the existing Risk configuration. Prepare keys and
trust separately; a registry does not generate them or approve a remote peer.

```sh
netclaw peering transport register --file /private/reviewed-registry.json --expected-revision 0
netclaw peering transport validate
netclaw peering transport export --id members
```

Review the exported bundle before giving it to the intended member. Import uses
the existing selected-runtime flow, materializes the public CA and selects the
strict member endpoint. Enrollment tokens remain separate, private and one-use.

```sh
netclaw peering transport import --file /private/reviewed-border-bundle.json --expected-revision 0
```

Configure each member's existing role/identity and outbound worker service;
members expose no federation listener. NCFED peers need separate dial entries,
pre-approved application keys and reciprocal consent. NCFED's identification
preamble is followed by TLS; an HTTPS reverse proxy is not a substitute for raw TCP.

Review infrastructure before activation: provider-reserved address, dedicated
VPC, ingress only for selected service ports/sources, IAP/identity-aware admin,
private control listeners, expiry, cost/budget alerts, workload identity and
teardown. No generic wizard action approves cloud spend or firewall changes.

After that review, direct lifecycle commands use the existing owned daemon:

```sh
netclaw peering transport start
netclaw peering transport status
netclaw peering transport stop
```

`render` and `unit` render ngrok configuration only and reject direct mode. Direct
supervision uses the selected federation daemon service. Verify actual listeners,
firewall reachability, TLS and application admission independently. A running
process alone does not prove remote admission.

For an approved address move, use `address --id members --host <new-host> --port
<port> --address-ref <new-reference> --expected-revision <current-revision>` on
the appropriate registries. Identity, trust, transport and bindings remain unchanged.
A transport, NIC binding or certificate/trust change needs explicit full registry
replacement and owned daemon restart. `recover` creates a new revision from the
prior reviewed registry; no automatic fallback occurs. A full runtime migration
additionally needs state fencing and rollback under the later roadmap brief.
