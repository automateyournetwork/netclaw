# A cloud Border without giving up local access

**Unpublished draft — Spec168/R01 direct-cloud pilot.** Actual Mac→GCP enrollment,
refusal and reconnect evidence is recorded. Public DNS/HTTPS and actual address relocation/recovery are verified. The owner
also requested the full HUD and Sonnet-backed on-prem subnet demonstration; see
verification.md for its actual qualification and limits.

ngrok gives a Border running at home a way to be reached through a commercial
Internet connection. That remains a useful deployment choice. A cloud Border can
instead use its provider's reserved address and firewall. NetClaw now supports
that direct path without an ngrok token, agent or paid account.

Placement follows the work. Cloud-friendly members can live alongside a cloud
Border. A member that needs local SSH or an internal system can stay on premises
and initiate its connection outward. A private or air-gapped site can keep Border
and members on premises without ngrok. Air-gapped operation still needs suitable
offline artifacts and models; an online installer does not establish that readiness.
Hybrid, multi-region and multi-cloud qualification remains in the roadmap.

The transport contract keeps location separate from identity. Each registration
specifies the routing address, the independently verified TLS name and trust, and
the expected application identity. Schema2 explicitly selects direct TCP or ngrok;
existing schema1 ngrok registrations retain their original behavior. Changing an
address cannot silently change transport or trust.

Members connect to their own Border over iN2N. Independent Borders use eN2N/NCFED
and bilateral consent. The two services have separate TCP ports, which can share
a cloud IP. NetClaw terminates TLS. iN2N uses TLS1.3 exporter-bound proofs and
verifies the Border before disclosing an enrollment token. NCFED preserves its
identification preamble, followed by TLS and approved application-key proof.
Routing, gateway, model and tool APIs are not public federation endpoints.

The same contract applies to direct and forwarded connections. Wrong names,
trust anchors, proofs, replayed enrollment and revoked membership fail closed.
Current membership is checked before outbound calls on an open channel as well
as on incoming requests. Registry updates use revision checks, with explicit
recovery and no automatic task replay. Lifecycle control belongs to the selected
installation rather than a shared global process.

The README, shell installer, VS Code wizard and operator guides now describe
these deployment choices consistently. The HUD reports the selected transport
alongside connection and admission state. **873 federation tests passed** with
five real-runtime skips retained; installer, HUD and extension checks also pass.
Local TLS sockets and fixtures remain separate from actual Mac→GCP evidence.

The isolated Montréal pilot now runs a Border and HUD under workload identity,
with budget alerts, expiry and reviewed teardown. A fresh on-prem member enrolls
outbound over iN2N and reconnects through both supported launchers with the same
key. A separate external Border proves NCFED key/name/CA and consent enforcement.
The owner selected the [full open HTTPS lab HUD](https://r01-gcp-montreal.lobsternet.automateyournetwork.com/),
including Chat, Canvas and RAG. Its Mac member is clearly labeled as a subnet
calculator. Sonnet4.6 at the Border delegated a real question; matching cloud and
member task records and the actual calculator call prove where the answer came
from. Private operator APIs stay behind IAP. DNS/certificates and actual address
relocation/recovery are verified. Users, SSO and RBAC remain later roadmap work.

Full runtime migration, operational workloads, HA and multi-user authorization
remain later work. R01 completion is recorded against actual transport and full-workspace evidence,
with the retained platform and runtime limits. See [deployment choices](../../specs/168-ngrok-transport-contract/deferred-docs/DEPLOYMENT-TOPOLOGIES.md),
[direct transport](../../specs/168-ngrok-transport-contract/deferred-docs/REMOTE-TRANSPORT.md) and [verification](verification.md).
