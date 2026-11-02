> Current owner direction: source integration into main is authorized; the whole
> roadmap remains under a release and rollout-documentation hold.

# Spec168 / R01 closure — 2026-11-01

**R01 complete:40/40 tasks for the owner-amended lab scope. Stop after R01.**
Preserve branch `168-ngrok-transport-contract`, baseline
`9ba12ffc8d1033a0130dd8544aa54d95471afcbb` and all existing uncommitted work.
Owner update2026-11-02 authorizes commit/push/main integration only. Publication,
version bumps and general cloud rollout documentation are held until the entire
issue310 roadmap is complete. R02/R03, existing-runtime upgrades and device
operations are not started by that update. Human acceptance still gates R03.
See main-integration.md for integration state and the deferred documentation.

## Working cloud workspace

**https://r01-gcp-montreal.lobsternet.automateyournetwork.com/**

Full HUD: normal browser Chat, Canvas, RAG and federation views. Public GoDaddy
A34.95.60.45/TTL600, trusted Let's Encrypt TLS1.3, exact SAN, expiry2027-01-30,
HTTP308 redirect. Caddy2.11.7 renewal state is private and persistent. Native
operator/gateway/admin APIs remain loopback/IAP; no login is required for this
owner-approved lab. Users/SSO/RBAC remain R15–R17.

Cloud Border and the fresh on-prem Mac member use **Anthropic Sonnet4.6**.
The member is **On-prem Mac · Subnet Calculator**, not an existing pyATS claw.
Normal browser Chat task **845cd3b1-2848-4873-b67e-d1589528cefa** completed on both
cloud and Mac, with matching actual calculator call/result IDs. For192.0.2.0/28:
netmask255.255.255.240, usable192.0.2.1–192.0.2.14, broadcast192.0.2.15,14hosts.
Earlier public API proof task23f0a74f-0d54-4926-8938-eaa4482fced0 also completed.
See [correlated evidence](onprem-answer-evidence.md) and [verification](verification.md).

RAG indexed one harmless public lab guide, retrieved a cited excerpt, transferred
it to the actual Canvas draft, and Canvas sent/received a correct Sonnet answer.
Actual browser screenshots inspected; zero JavaScript errors. Retrieval uses
local cached CPU models, not an external embedding service.

## Authoritative resources and private state

Project netclaw-506315; VM netclaw-r01-20261101, northamerica-northeast1-a.
Ubuntu24.04 e2-small, private10.168.0.2/public34.95.60.45;12 managed IaC resources.
Cloud installation f03c0a7c-5444-4cd6-b745-394471cf328a; Compute instance ID
7647370903424740100 is a separate identity. No existing owner resources changed.

Private evidence root OUT=~/.local/share/netclaw/spec168-direct-cloud-pivot-20261101.
Cloud home /var/lib/netclaw-r01/claw, source /opt/netclaw-r01/source.
OpenClaw2026.7.1-2 in private .setup/prefix; Node24.19.0 /opt/netclaw-r01/node;
protocol venv /opt/netclaw-r01/venv; RAG venv /opt/netclaw-r01/rag-venv.
Five owned units: federation, HUD, public-HUD, HTTPS and gateway.

Mac member OUT/material-v1/member; installation6ac7ac12-a8f9-4e98-966f-6433a8df95c8;
member r01-20261101/onprem; unchanged application fingerprint
`a7ab031e1da2b63f1317e72a58cf7e4db5329bddb89af6b3f659dbadf007bd08`.
Authenticated outbound daemon has zero TCP listeners. Its availability depends
on the Mac being awake/online. External owned worker OUT/external-pilot-worker.py
uses AS64519 toward cloudAS64520; AS64521 is a retired probe retained for audit.
The independent Border fixture has no LLM and proves NCFED transport only.

Authoritative IaC backend OUT/pilot.tfstate; vars OUT/pilot.tfvars.json,
use_relocation_address=true/public_lab_hud=true. Never initialize empty state or
replay stale plans. CAD50 alerts are not a spending cap. Base estimateUS$24.96/720h
excludes traffic/secrets/Anthropic usage/tax/FX. VM stop2026-12-01T00Z; disk/IP costs
persist until separately reviewed teardown. Old reserved34.47.13.89 is unused.

## Completed evidence and preserved limits

Actual Mac→GCP positive/refusal/reconnect, both member launchers, separate NCFED
consent/refusal/recovery and actual public-IP relocation passed. CAS/stale-revision
refusal, no automatic fallback, explicit recovery and unchanged key verified.
Transport tests had zero tasks; later owner-requested model demonstrations are
separately recorded. Optional home/NAT ngrok remains supported but its Free-account
live deployment is unqualified. No paid ngrok dependency exists for this cloud.
WSL/native Windows/Intel Mac strict transport, live strict-cloud Hermes, physical
mobile, meetings, production/HA and independent-organization operations remain
unqualified. Five real-runtime regression skips are retained.

873 federation tests passed/5 skipped;408 HUD tests passed;3 public-ingress HTTP
tests passed; frontend build passes. VSCode150 passed/3 skipped with typecheck/build;
installer23 plus23 subtests/1 skip and32 plus3 effect/deploy/engine cases passed.
Final no-drift, catalog/effects/artifact coverage and whitespace/syntax checks pass.

Private final receipts: r01-final-public-check.json, r01-final-runtime.json,
r01-final-member-key.json, r01-final-member-listeners.json,
r01-closure-no-drift.json/.log, browser-question-proof.json,
browser-onprem-tool-proof.json, browser-rag-canvas-answer.json,
full-hud-rag-final-tests.log, federation-hud-final.log/.xml,
r01-final-coherence.json and gait-r01-closure-full-log.json.

## Repairs and continuation safeguards

Do not restore initial Secret version1 over active.env: its old stack CSV was
corrected to `both`. The authorized provider-only Secret Manager delta was fetched
through workload identity and hash-verified; unrelated active settings preserved.
Never print keys or copy the owner's whole environment into the cloud.

Sonnet5.5 was account-available but rejected the pinned runtime's thinking format;
4.6 is verified. Fresh external subnet MCP source needed the existing reviewed
hash-checked FastMCP patch. Cloud MCP has an explicit loopback BGP_DAEMON_API.
Initial failed tasks/provider/browser attempts remain in receipts, never passes.
The small host needed a bounded120s settings-CLI startup budget; RPC stays10s.

RAG preload needed an accessible owned cwd. Overlapping per-call RAG startup
caused high load and could race interrupted-ingest recovery; serialized HUD calls,
coalesced list/stats polls, bounded queue and no mutation replay fixed the path.
Three new regressions and actual ingestion/retrieval pass. Independent RAG clients
still need operator coordination. Source systemd drop-in and install script are
in pilot/gcp. Do not replay initial activation over the running pilot.

The latest owner delegation already covers completed R01 changes; no approval
question is pending. GAIT branch spec168-dns-https-closure-20261101 contains the
trail; session closure uses gait_log and daily memory. Startup pyATS/MemPalace
were unavailable; no fabricated inventory/diary and no existing runtime altered
for bookkeeping. CUA unavailable; browser evidence uses fresh headless Chrome.
