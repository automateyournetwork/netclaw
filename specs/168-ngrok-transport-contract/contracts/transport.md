# R01 transport interfaces

Extend netclaw peering for registry validate/status/register/address-update and
direct daemon lifecycle and optional ngrok render/start/stop. scripts/ngrok-control.py is the selected-runtime internal
helper, not separately configured integration. Never allocate reservations as a
side effect; tests use private fake processes.

N2N_ENDPOINT_REGISTRY selects an owned registry; N2N_BORDER_REGISTRY_ID selects
member dial entry. Missing/malformed/foreign explicitly selected registry fails.
Absent selection retains existing installation behavior; remote bundles always
select strict mode. Status JSON and /n2n/status/HUD expose service, routing, TLS
name, application ID and separate configuration/transport/admission observations;
no secrets. expected_revision conflicts change nothing. Address-only update keeps
trust/identity unchanged; incoming announcements cannot rewrite registry fields.

## in2n-tls-exporter-v1

1. Dial routing address and negotiate TLS1.3 only.
2. Verify configured CA and independent DNS/IP SAN before enrollment.
3. Derive32bytes with export_keying_material(b"EXPORTER-Channel-Binding",32,context=b"").
4. Existing nonce-signature proof binds b"netclaw-in2n-tls-exporter-v1\0" plus exporter;
   preserve IN2N magic and framing.
5. Verify independently configured Border application identity/anchor and member
   key proof. Reject repeated authentication, expired/replayed tokens and unknown/
   revoked keys. No plaintext/TLS1.2/tls-unique/loopback fallback.

Adapter reader supports read/readexactly; writer write/drain/close/wait_closed/
is_closing/get_extra_info. Exporter has a dedicated extra-info value, never a fake
stdlib SSLObject. One loop owner; bounded handshake/admission/shutdown and buffers;
propagate backpressure and cancellation; no early application data.

## en2n-tls13-v1

NCFED identification precedes existing TLS1.3 upgrade and certificate-hash proof.
Dedicated listener refuses BGP/NCTUN/HTTP/PROXY without invoking routing handlers.
Verify configured CA/name, approved application key and bilateral consent; no TOFU.
Identification metadata is disclosed; application frames are protected.

## Direct cloud TCP (primary)

Schema2 entries explicitly select `direct_tcp` and a stable `address_ref`. Separate
iN2N/eN2N ports may share one provider-reserved IP. Listen entries bind an exact
unicast interface address; wildcard/multicast bindings are refused. Use the
reviewed VPC/host firewall sources/ports. No HTTP/TLS-terminating proxy, PROXY
header or plaintext fallback. A future L4 passthrough load balancer must preserve
the complete NCFED preamble and TLS stream.

`netclaw peering transport start/status/stop/run` delegates direct lifecycle to
the existing selected daemon controller. Direct mode never requires ngrok config,
credentials or binaries. `render`/`unit` remain ngrok-specific and refuse direct
registrations; direct supervision uses the existing daemon service mechanism.
Mixed direct/ngrok listen registrations are refused by the lifecycle command.
An address update takes `--address-ref`; legacy `--reservation-id` remains for
schema1. Changing transport requires full explicit registration and daemon restart.

## ngrok (optional)

Two named endpoints/exact reserved tcp://host:port URLs upstream to matching owned
loopback listeners. No edge/agent TLS termination, PROXY, policy transformation,
HTTP/SNI routing or public BGP. Members run no agent/listener. 443-only egress is
unsupported. Service selection is explicit, never first tunnel from shared4040.
Owned PID/start stamp/config identity fences stop. No automatic reservation deletion.

## Exact registry and enrollment types

`application_trust` is a public CA certificate PEM for iN2N and a lower-case
64-hex SHA256 SPKI fingerprint for eN2N. iN2N `application_identity` ends in
`/border` and its risk prefix must match the provisioned member identity. Listen
entries identify the local Border. Schema1 `reservation_id` is an explicit ngrok reserved
address identifier; local validation checks presence/format, while account evidence
is required to establish that it exists and matches the configured address.

A schema1 or schema2 public bundle contains `endpoint` (dial metadata without local paths),
`tls_ca_pem` and the public `application_trust`. Import into an owned installation
materializes the public CA privately and writes a matching-schema registry with
that installation's ID. Cross-schema imports require explicit registry replacement.
Schema2 exports transport/address_ref; schema1 retains reservation_id. Existing single-use enrollment token travels through the existing private
provisioning mechanism, separately from this public bundle.

Strict iN2N adds one pre-admission `in2n/attest` challenge, before sending a token
or member proof. The Border signs the member nonce plus exporter using its
CA-issued hub key. Verify the provisioned application CA and exact `/border` SAN.
Only then send one enroll/hello attempt. Both stages share the15-second admission
deadline; repeat attest/authentication attempts fail. This is the explicit
versioned wire change; legacy peers never negotiate down into it.

Strict eN2N uses the registered local TLS credential's key for its application
possession proof and requires the separately approved peer SPKI in both directions.
TLS name/CA verification and the application-identity-to-key enrollment are separate
checks, even though this profile uses one local key for both proofs. The legacy
self-key/TOFU path is not used. Certificate renewal with the same key preserves the
application pin; key rotation requires explicit registry review. No wire framing
change is introduced. A configured strict deployment refuses NCFED admission via
the legacy shared BGP dispatcher; its BGP listener is loopback only. Strict member
daemon mode opens no BGP, HTTP, edge or Zoom listener and reports local readiness
through an owned private file; the lightweight member remains outbound-only.
