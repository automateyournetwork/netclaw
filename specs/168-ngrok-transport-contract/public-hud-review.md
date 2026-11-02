# R01 named HTTPS lab HUD and address relocation

**Authorized:** the owner explicitly delegated the remaining R01 cloud, DNS,
certificate, activation and relocation work to reach100%. This supersedes the
pending HTTP-only packet; no additional approval question is required within this
scope. Original frozen v1 plans/artifacts remain private and must not be applied.
Users/SSO/RBAC remain R15–R17; the lab viewer is open without login.

Target URL: **https://r01-gcp-montreal.lobsternet.automateyournetwork.com/**.
Live: DNS, public CA validation, relocation and normal browser Chat passed.
The exact initial packet below is retained for audit; do not replay it over the
running pilot. Its two-view/no-model bounds are superseded by the owner amendment below.

## Historical exact HTTPS/relocation packet

- IaC: create one dedicated TCP80/443 Internet firewall rule targeting only the
  pilot service account. In-place change of this VM's public IP34.47.13.89 to
  already-reserved34.95.60.45. No VM replacement or deletion; no new paid service.
- GoDaddy: create only A record `r01-gcp-montreal.lobsternet` in
  `automateyournetwork.com`, value34.95.60.45, TTL600. Read-only API baseline found
  no A/AAAA/CNAME at that name; apex A is present and remains untouched. The
  operator's existing local PAT works and stays local, outside artifacts/cloud.
- VM: install the frozen read-only HUD, pinned Caddy2.11.7 and two owned units.
  Viewer binds127.0.0.1:13002. Caddy binds10.168.0.2:80/443 with a single named
  virtual host, HTTP308 redirect and Let's Encrypt ACME certificate renewal.
  Caddy admin API and HTTP3 are disabled. Certificates/account keys are private
  under a separate unprivileged service account's persistent state directory.
- HTTP APIs remain only two bounded status projections, with all writes,
  WebSockets, queries, private paths and unlisted routes refused. The original
  operator HUD/API and federation admin/routing listeners stay loopback/IAP.
- Update only owned cloud/member/external registry routing addresses with CAS,
  verify the real move, same enrolled identities, failed update/no fallback,
  explicit recovery, no member listener and zero delegated tasks.

Caddy TLS terminates only the browser HUD connection. NetClaw's separate
42101/42102 iN2N/NCFED TLS, trust and application identities are unchanged.
No account/login/model/device/workload operation or later brief is added.

## Concrete implementation and frozen packet

[Viewer](pilot/public-hud.mjs), [viewer unit](pilot/gcp/netclaw-r01-public-hud.service),
[Caddy config](pilot/gcp/Caddyfile), [HTTPS unit](pilot/gcp/netclaw-r01-https.service),
[activation](pilot/gcp/public-hud-activate.sh), [tests](pilot/public-hud.test.mjs).

Private packet root: `~/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/`.

| File | SHA256 |
|---|---|
| https-relocation.tfplan | `54e59fdf8c2966e19a55213d3233df9c5c95fca387c410fffed9fc3c0c704855` |
| public-hud-v2.tar.gz | `27cf46f45f10c57a328db90fde06475eae31cde8e36fb89ff7db3d54ef563635` |
| public-hud-activate-v2.sh | `efab7e946f44e991097c0ed5e3feed0a3d266e03845e16b4f21272d3282d22ff` |

The plan was inspected: exactly one create and one update, only VM network-interface
changes. Caddy's LinuxAMD64 and localMacARM64 release archives match GitHub release
SHA256 digests and the publisher's SHA512 manifest. Local Caddy validate/adapt
confirms only the explicit80/443 bindings. The frozen bundle matches no root
credential values. Both viewer network tests pass;404 HUD tests/build and the
actual local browser/live-cloud feed evidence remain recorded.

The delegated driver verifies frozen hashes, captures a current listener baseline,
refuses existing activation/occupied ports, applies only this saved plan and stages
the two owned units. It starts the loopback viewer; HTTPS starts after DNS readiness:

```sh
python3 "$HOME/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/https-relocation-driver.py" --execute-reviewed
```

The DNS operation uses HTTPS headers in process memory, never secret command-line
arguments. Read the exact named record immediately before write; refuse conflicting
state; create the single record, verify API plus both authoritative nameservers.
Start the owned HTTPS unit, verify a publicly trusted certificate with the exact
SAN, expiry, HTTP redirect, live public browser/member view and denied private APIs.
Run the prepared private relocation qualification harness and capture evidence;
reconcile any partial outcome before retry.

## Cost, expiry and recovery

No additional VM, paid proxy/load-balancer/NAT service, address or DNS zone is added.
The base estimate remains US$24.96/720hours before traffic, secret use, tax and
currency conversion. Existing CAD50 alerts are not a spending cap. Public page
traffic adds possible egress. VM stop remains2026-12-01; disk/IP costs continue
until reviewed teardown. ACME renewal runs while the HTTPS unit is active and
DNS/ports remain available. No root or existing-wildcard certificate is reused.

Rollback stops only the owned public units. A reverse IP/firewall plan is prepared
against actual state if needed; no destroy is part of this execution. Retain DNS
baseline and remove only this pilot's record on explicit eventual teardown.

Automatic HTTPS and renewal behavior is documented by
[Caddy](https://caddyserver.com/docs/automatic-https); validation uses public
[ACME challenges](https://letsencrypt.org/docs/challenge-types/). Public certificate
issuance and final acceptance are established only by the actual receipts.

## Owner amendment: full HUD and Sonnet

The owner rejected the status-only narrowing and explicitly requested the full
workspace, Chat, Canvas and RAG, plus a real question delegated to the on-prem
member. The owner authorized their Anthropic credential and Sonnet. The active
fixed ingress now serves the normal built HUD pages and bounded application
routes/session cookies, while raw environment/configuration, routing/admin and
device-write endpoints remain private. No login/SSO feature is added.

`public-hud-v4-manifest.json` and activation log identify the deployed full HUD.
A separately installed OpenClaw2026.7.1-2 cloud gateway remains loopback-only; the
Mac member is also a separate installation. Sonnet4.6 is selected after5.5 rejected
the pinned runtime's thinking request format. The cloud provider-only secret delta
was retrieved and verified with workload identity; unrelated active state was
preserved. Member permits only the existing subnet-calculator tool; Border permits
only federation status/route/task reads. No pyATS/device credentials were copied.
RAG uses its own Python environment and cloud-owned data/cache. This supersedes
the earlier no-model/task and two-status-view bounds for this requested demo only.
Historical transport tests still correctly record zero tasks during those tests.
