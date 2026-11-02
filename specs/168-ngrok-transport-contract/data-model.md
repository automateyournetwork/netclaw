# R01 data model

Registry schemaVersion1 (legacy ngrok) or2 (explicit transport), installationId, monotonic integer revision and up to128
entries in at most64KiB JSON. Owned0600 file/0700 parent, no symlinks/unknown keys.
CAS under exclusive lock, atomic replace and private prior document. Recovery makes
a new revision; no rollback to older revision numbers or automatic fallback.

| Entry field | Meaning |
|---|---|
| id | Unique bounded local name |
| direction | listen or dial; member accepts dial only |
| service/profile | in2n/in2n-tls-exporter-v1 or en2n/en2n-tls13-v1 |
| transport | Schema2 only: direct_tcp or ngrok_tcp; never inferred from a hostname |
| address_ref | Schema2 only: bounded operator reference to the stable provider address; ngrok mode references its reservation |
| reservation_id | Schema1 only: ngrok reserved-address ID; schema1 retains all original checks |
| routing_host/routing_port | Explicit stable TCP destination, port1–65535 |
| tls_server_name | Independently verified DNS/IP SAN |
| ca_file | Public local trust anchor for strict dialing |
| application_identity | Expected Border identity, not derived from DNS |
| application_trust | Public Border anchor or approved peer fingerprint |
| bind_host/bind_port | Listen-only exact unicast IP; ngrok requires loopback; wildcard/multicast rejected |
| cert_file/key_file | Listen-only local TLS material references; never exported |

Schema2 has no reservation_id; schema1 has no transport/address_ref. Unknown
fields/transports are refused. Bundle schema follows the entry version. Import
into a different schema requires explicit registry replacement first; never silently
upgrade or strip transport. Status includes normalized transport for both schemas.

Duplicate local public addresses are rejected. Address-only updates preserve
identity/trust/profile/transport/bindings. Foreign installation registries cannot be loaded unchanged.
Enrollment export includes selected dial entry/public trust only; no token,
private key, local binding or unrelated peer inventory.

Connection: configured→connecting→tls_verified→application_authenticated→closed.
TCP reachability is independent and never implies admission. Bounded failure event
contains reason/service/revision/time, no secret. Reconnect reads current approved
registry without replaying unknown application outcomes. Exporter is discarded
on close; one authentication exchange per connection. Revocation invalidates new
and open channels.

Direct lifecycle reuses the selected owned daemon record/controller. No transport
agent or credential is required. Mixed listen transports in one lifecycle request
are refused; an explicit replacement/restart is required to change transport.

Owned optional ngrok record: installationId, config digest/path, executable, PID/start stamp.
States absent/running-owned/stale/foreign. Reject foreign/changed process identity.
Agent token comes from selected private environment, not registry or output.

Evidence records scope LIVE/LOCAL/FIXTURE-ONLY/UNQUALIFIED, UTC timestamp, command,
excerpt and limits. Crypto fixtures never advance live acceptance. Platform and
transport qualification remain separate from implementation completion.
