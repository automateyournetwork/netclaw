# Implementation Plan: direct cloud transport and TLS identities

**Branch**: `168-ngrok-transport-contract` | **Date**: 2026-11-01 | **Roadmap**: R01
**Spec**: [spec.md](spec.md) | **Baseline**: `9ba12ffc`

## Owner pivot implementation — 2026-11-01

Direct cloud TCP is primary; ngrok remains optional. Retain the existing feature
path, schema-1 behavior, TLS/exporter/security implementation and tests. Introduce
schema 2 with explicit transport (`direct_tcp`/`ngrok_tcp`) and `address_ref`.
Public bundle schema follows its registry schema. Refuse mixed-schema import
until explicit replacement. Keep address-only CAS/recovery transport-stable.

Direct listeners require an exact unicast IP bind (including an explicitly selected
private NIC); no wildcard/multicast. ngrok still requires loopback. Both profiles
reuse the same application TLS and identity paths. Registry status adds the transport.
The existing selected daemon control owns direct lifecycle. The peering CLI dispatches
by explicit registration; direct mode never renders/launches an ngrok agent.

Qualification uses local direct socket positive/negative/recovery tests, retains all
ngrok forwarder regressions and then repeats required observations Mac↔GCP after
exact deployment approval. Pilot: one Montréal e2-small Ubuntu24.04 VM, reserved
external IPv4, two application TCP ports, dedicated VPC, IAP/OS Login, bounded
firewall sources and no load balancer/NAT/ngrok agent. Explicit expiry, workload
identity, budget alerts, cost estimate and teardown remain mandatory in the IaC
review packet. The independent external peer has distinct trust/consent; a single
owner's pilot is not second-organization operational acceptance.

## Summary

Extend existing federation, peering setup and selected-runtime management with an
explicit remote profile. Routing address, verified TLS name, trust and application
identity are separate. Members dial out. Borders expose separate iN2N and
NCFED-only listeners through separately registered TCP endpoints. Strict iN2N uses
TLS 1.3 and RFC 9266 exporters. Existing direct/local and cloudflared contracts
remain explicit compatibility profiles; failure never switches profiles.
The owner's pilot adds reviewed GCP qualification infrastructure and cloud HUD
access through the owner-selected open HTTPS lab workspace, including Chat,
Canvas, RAG and the normal views. A fixed ingress allows these application routes;
raw credentials/configuration, routing/admin and device-write APIs remain private.
The owner authorized Anthropic Sonnet and one scoped subnet-calculator member
for actual question/answer evidence. Users/SSO/RBAC remain R15–R17.
Execution-authority changes and a state migration engine are outside this scope.

## Technical Context

**Language/Version**: Python 3.12 isolated protocol/n2n runtime; Python 3.10+ installer; existing Bash and HUD JavaScript.
**Primary Dependencies**: Existing asyncio/federation stack; pyOpenSSL 26.4.0, cryptography 50.0.2, service-identity 26.1.0. Preserve separate certificate-helper environment. No new MCP server or web framework.
**Storage**: Private installation-owned JSON registry, atomic revision updates, explicit prior-revision recovery; owned ngrok config/process records. No tokens in registry/bundles.
**Testing**: Isolated pytest/pytest-asyncio; actual local TLS sockets and transparent forwarding; existing federation/installer/HUD checks; separate live qualification.
**Target Platform**: macOS development and Linux services. Windows/WSL and Intel macOS strict transport unqualified until exercised.
**Project Type**: Existing MCP-backed federation service and CLI/installer/HUD surfaces.
**Performance Goals**: Handshake 10s, pre-authentication 15s, shutdown 2s; bounded TLS buffers; existing NCFED message/frame/dispatch budgets. No throughput claim before measurement.
**Constraints**: Public APIs, one event-loop owner per TLS connection; no private CPython pointers, blocking socket TLS or global loop changes. Source tests create no public resources or device operations. The owner separately delegated the R01 cloud/HTTPS activation and scoped Anthropic subnet demonstration.
**Scale/Scope**: Registry maximum 64 KiB/128 entries. Two initial services; R14 planning approximately 30–40 TCP addresses plus reviewed HUD ingress. BYO credentials/account selection.

## Constitution Check

Pre-design and post-design: PASS. Implementation and live evidence are recorded in verification.md.

| Principles / invariant | Obligation |
|---|---|
| I–III, VIII; G5/G11 | Isolated transport tests; no execution-model/device changes. Exact-command owner review before infrastructure mutations. |
| IV; G7/G8 | GAIT and bounded federation audit; preserve fixture/local/live distinctions. |
| V–VII | Extend protocol/n2n MCP and existing peering skill; helpers are service internals. |
| IX; G1–G4 | Explicit identity/trust; outbound members; separate NCFED ingress; no public BGP or integration secrets. |
| X–XII | Existing status/HUD projection; every XI artifact assessed; unchanged tool/component counts justified. |
| XIII; G4/G9 | Selected private environment; the R01 pilot and later cloud briefs render secrets with workload identity. |
| XIV, XVII | Local PR/blog drafts, no publication. |
| XV; G8/G10 | Direct/cloudflared/Hermes/single-user compatibility, coordinated migration, per-platform qualification. |
| XVI | Owner's roadmap driver authorizes default decisions; implement only after analysis has no HIGH/CRITICAL. |

G6 starts at R02. R01 adds no owner-specific execution semantics. G9 IaC, expiry,
budget alerts, workload identity and cloud teardown apply to the R01 pilot and
when later briefs create resources. G10 verification records Chat/Canvas, gateway, skills/MCPs, Zoom, Mobile
and VS Code, including retained/unqualified status.

## Design

1. Private versioned registry separates local listeners and remote registrations.
   Reject unknown fields, duplicate service addresses, unsupported profiles and
   malformed identities. Owned files, exclusive locking, expected revision and
   atomic replace prevent lost updates. Keep prior document for explicit recovery,
   never fallback. Address updates preserve identity/trust. Enrollment exports only
   selected public trust and peer metadata, no token/key/local bindings.
2. Public pyOpenSSL MemoryBIO adapter on asyncio.Protocol/StreamReader. Verify
   chain and independent SAN before exposing streams/enrollment. RFC exporter label
   stays exact; application challenge gains a versioned separator. Bound buffers,
   propagate backpressure, preserve partial sends, settle waiters on cancellation,
   timeout and truncation; no 0-RTT.
3. Both member launchers reload the same registration on each reconnect. Verify
   expected Border application identity and pre-provisioned anchor independently
   of TLS. Strictness comes from configuration even behind loopback forwarding.
   One authentication attempt per connection; expired/replayed tokens, unknown or
   revoked keys fail. Revocation closes open channels. Never replay application work.
4. Dedicated public eN2N listener accepts only NCFED identification, then existing
   TLS 1.3/certificate-hash proof. BGP/NCTUN/HTTP/PROXY fail before routing handlers.
   Configured CA/name, pre-approved application key and bilateral consent required;
   no public TOFU. Preserve existing framing and disclosed identification preamble.
5. Extend netclaw peering/peering-setup with registration, validation, render and
   owned lifecycle. Exact named v3 endpoints/reserved URLs; no TLS termination,
   traffic policy or PROXY. Per-installation environment/config/log/PID/start-time
   fences; stop only owned process. No global pkill or first-tunnel selection.
   Incoming endpoint announcements cannot rewrite operator-owned registry fields.
6. Address migration preserves keys/trust/uncertain outcomes. Full runtime-state
   moves belong to later briefs: fence cutover, rebind credentials, verify rollback.
   Clones receive new identity. No account-specific defaults or identity reissue.

## Qualification and cost

Owner follow-up on2026-11-01 requests fresh local/GCP pilot participants for
T028. Prepare the bounded transport-only test-host layout in
[fresh-pilot.md](fresh-pilot.md), with IaC, workload identity, costs, expiry,
budget alerts and teardown for exact action review. This is qualification
infrastructure preparation, not completion of R03's operational cloud deployment.
Cloud/account/endpoint mutations retain the driver's review boundary.

Root API-key inventory now succeeds: zero TCP reservations, one unrelated ephemeral
endpoint, unchanged. The owner confirmed Free and then explicitly removed ngrok
as a mandatory cloud dependency. No upgrade/reservation is needed for direct mode.
Those facts remain relevant only to optional ngrok live qualification.

The owner-delegated cloud pilot is active with12 managed resources after the
HTTPS firewall addition. The [foundation review](cloud-review.md) retains its
original11-resource plan. Estimated base cost is US$24.96 for720hours, plus
traffic/secret use, owner-selected Anthropic usage, taxes and currency conversion. CAD50 budget alerts are not a hard cap. The owner's
GCP credit remains an account reference, not a spending cap.

Map all six brief evidence groups to commands/timestamps/excerpts and scope. Real
local sockets are not live ngrok qualification. Human verification review gates R03.

## Project Structure

- specs/168-ngrok-transport-contract/: spec, plan, research, data-model, contracts,
  quickstart, tasks, analysis, verification, checklists.
- mcp-servers/protocol-mcp/bgp/federation/: endpoint_registry.py, exporter_tls.py,
  internal_security.py, internal_channel.py, service.py, tls.py, runtime.py,
  posture.py; bgp-daemon-v2.py for listeners/dialers.
- scripts/: netclaw, peering-setup.sh, ngrok-control.py, in2n-member.py,
  in2n-services.py, lib/setup_enrollment.py, lib/install-steps.sh.
- tests/n2n/: test_endpoint_registry_168.py, test_exporter_tls_168.py,
  test_ngrok_transport_168.py, test_ngrok_lifecycle_168.py, test_direct_transport_168.py.

The cloud HUD remains a trusted local operator surface. Bind13000/13001 on
loopback and forward both over IAP/SSH with host-key verification. No DNS or IdP
mutation is required for that access. Freeze runtime/source/identity hashes after
the foundation returns actual addresses; exact activation remains separately
reviewed. FR026/T040 requires the real cloud page and matching on-prem admission,
not a planned link. A public HTTPS login gateway, if selected, needs additional
design and exact review before it can replace this default.

Use existing protocol/n2n catalog components; regenerate effects/catalog artifacts
with repository tools when sources change. Update existing federation skill/docs,
.env and HUD panel; do not create duplicate tools/nodes.

## Complexity Tracking

### Cost and account qualification

R01 source development creates no cloud resource. Direct qualification requires a
reviewed provider address and narrowly scoped ingress; optional ngrok remains
unqualified on the current Free plan. No paid-plan purchase is needed for the direct
pilot. G9 IaC/budget/expiry/workload-identity/teardown applies to this qualification
host as well as future deployments. Do not turn the source milestone into a live
pass or mark T028 complete before Mac↔GCP evidence exists.

No constitution exception. Owned TLS adapter maintenance is justified by missing
stdlib exporter access. Public MemoryBIO avoids a second networking framework.
Adversarial socket/lifecycle tests are required; packaging/live limits stay visible.
