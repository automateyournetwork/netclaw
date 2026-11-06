# R06 concrete activation review

Prepared2026-11-06; **owner approved the full packet on2026-11-06**. Execution evidence is recorded separately. This is the bounded owner
lab qualification for Spec177, not a released cloud deployment recipe.

## Exact scope

Three fresh independent NetClaw organizations form the complete eN2N triangle.
Cloud A/B use separate resources in existing project `netclaw-506315`, Montréal
`northamerica-northeast1-b`. Local C is a new private Mac installation. Existing
R01/R04a, R05, owner OpenClaw/Hermes/pyATS and their authorities remain unchanged.

Run prefix: `netclaw-r06-20261106-a4fd`. Foundation saved plan creates exactly16
resources; runtime activation adds18, for34 total Terraform resources:

| Resource | Count | Boundary |
|---|---:|---|
| VMs |2|e2-standard-2, Shielded, no forwarding/automatic restart |
| Boot disks |2 embedded in VM resources|40GiB pd-standard, auto-delete |
| VPCs/subnets |2each|10.177.0.0/28 and10.177.1.0/28; no peering |
| Service accounts |2|No project role; each can read only its own provider secret |
| Static IPv4 addresses |2|Owned R06, explicitly released during retirement |
| Firewalls |20|Separate per organization, as below |
| Secret containers/IAM bindings |2each|Provider-only, exact numeric version; no device/DNS credentials |

Only R06 resources enter the new private state. No existing resource update,
replacement/import, shared budget adoption or project IAM grant is in either plan.
The fresh pinned Ubuntu24.04 AMD64 image was observed READY:
`ubuntu-2404-noble-amd64-v20261104a`.

## Reviewed network and runtime

IAP SSH22 is private administration. HTTPS443 and native Mobile WSS8443 accept
only the freshly observed Mac public IPv4 /32. Port80 is public solely for ACME
HTTP challenge; other HTTP requests return404. eN2N42101 admits only that local
/32 and the other owned cloud address. Local C dials both cloud Borders; A dials
B. Those three TLS connections carry all six request directions. Local C needs
no internet-facing listener. iN2N42100/BGP1179/daemon8179/gateway19789/workspace13001/
HUD boundary13003 remain private. No public admin, device-write, model or MCP API.

Create only these new GoDaddy A records (TTL600), currently observed empty:

- `r06-a-gcp-montreal.lobsternet.automateyournetwork.com`
- `r06-b-gcp-montreal.lobsternet.automateyournetwork.com`

Create their matching public TLS certificates. Existing local ACME DNS-01 helper
can issue separate native eN2N/Mobile credentials; DNS credential remains on the
Mac. Caddy independently owns its HTTPS certificate. Preserve the existing R01
record and certificate/state. No broad DNS replacement or account change.

Use fresh **ordinary full Borders**, strict TLS and existing eN2N consent,
allowlists, approvals, budgets, tasks and chat. Each has a distinct installation,
AS/router identity, keys, database and trust. Operator/external gateway agents
use the pinned OpenClaw2026.7.1-2 runtime. The operator has only the reviewed
outbound n2n tools. The external agent has only native workspace-limited read and
the existing bounded subnet MCP; no eN2N transit, administration, shell or device
tools. Only the existing subnet-calculator skill is installed in that workspace.
The existing Spec176 arithmetic patch avoids enumerating address spaces.

Separate signer, gateway/provider and HTTPS service users/homes; metadata denied
to long-running applications. Only the exact-version one-shot projection may
retrieve the selected organization’s provider secret. Source, binaries and
configuration are verified before starting. The reviewed source does not modify
or disable a protected cloud profile.

Reuse the owner's existing Anthropic key for Sonnet4.6, through separate private
provider projections. No fallback model. Native turn deadline120s, model output
maximum2048tokens, configured context24000tokens, one concurrent turn per host.
Existing eN2N admission is12requests/40000tokens per peer per day and6requests/min.
Qualification is finite: at most60 operator-issued agent submissions across all
three organizations, with native usage reviewed after each; unknown outcomes are
reconciled by original ID, never resubmitted. Stop further qualification dispatch
at US$10 reported provider usage or unavailable usage. These admission/time/usage
controls are not a monetary hard cap, and an in-flight request may overshoot.

Actual acceptance includes all-six-direction inventory, two-turn contextual chat,
native subnet tool and asynchronous skill/result; identity/consent/scope/budget/
transit refusals; isolated peer loss/original-result recovery; browser, Mac VS Code
and native iPhone simulator QR/Ask Border/attribution/cold recovery. No network
device operation. Physical camera/Secure Enclave qualification is not inferred.

## Time, cost and retirement

Fixed window: **2026-11-06 15:19:35Z → 2026-11-08 15:19:35Z**. Each VM has an
absolute GCE STOP deadline. Each host has a one-use1GiB runtime-egress allowance,
1Mbit/s shaper and absolute expiry. Forwarding is denied. IAP SSH responses remain
available for evidence export; their traffic is outside the runtime quota.

Fresh authenticated CAD Billing Catalog rates estimate **CAD10.95** for both
hosts, both40GiB disks and both IPv4 addresses over48h, using the maximum IPv4
pricing tier and720h/month disk conversion. Excludes provider usage, transfer,
tax and existing R01/R05 costs. Existing project-wide CAD budget was observed and
is preserved; alerts are not a hard spending cap. Private pricing and formula:
`preflight/pricing-cad.json` and `cost-estimate.json`.

After successful qualification, retain the new owner-facing cloud/local setup
only within this window. Export evidence before expiry; retire all owned VMs,
boot disks, IPs, networks, firewalls, service accounts, secrets/IAM, both DNS records,
temporary OS Login access and owned local processes. Inspect actual residue
inventories. A VM stop alone is not cleanup. Use fresh current-state teardown
plans and a verified private export, not old R03/R04/R05 plans. A scheduled Mac
cleanup requires the Mac awake/online; the independent GCE STOP remains in force.

R05's existing **Nov7 19:36:25Z quiesce/export and19:41:25Z teardown** is unchanged.
Original Border's December1 scope and the complete-roadmap release/version hold
remain unchanged. R07 does not start.

## Concrete artifacts and evidence

Private root: `~/.local/share/netclaw/roadmap-r06-20261106/` (0700/0600).

- Executable foundation review: `deployment/foundation-v1-review.json`.
  Saved binary plan SHA256
  `081fa4a2ad677f2ef0dc67ac90bd13ee8f5d08a72c43f35a602a4bb24216e179`.
  Exact-plan check passed; no apply attempt exists.
- `deployment/activation-preview.tfplan` and JSON show all34 resources from empty
  state. **Preview only; never apply this combined plan.** After foundation and
  host guards, save/review the18-create activation delta against observed owned
  addresses. Narrow binding of those outputs does not broaden this scope.
- Host A/B service/Caddy renderings: `deployment/host-a/`, `host-b/`.
  Actual Linux Caddy configuration validation passed. Kernel/systemd enforcement
  requires the actual fresh-host baseline and post-change checks before runtime.
- Fresh native candidate configs/identities/bindings: `runtime-candidates/`.
  Both passed the installed native schema and effective agent/MCP policy checks.
  Endpoint/certificate/secret-version binding occurs only after scoped activation.
- Current public source archive: `source-package-v2/source-r06.tar.gz`, SHA256
  `7f38427f648df9796d637a2e2b68518b56f03a2c451ba72f09dbff8dd70bf0be`;
 971hashed files; no private state/credentials. Manifest SHA256
  `db72bbfbbd0907804e22d525d3517d474d86892779a1c6896465f1b79fc316f9`.
- Pinned Linux OpenClaw/dependency archives and hashes: `artifacts/manifest.json`.
  Fresh Linux AMD64 dependency build and actual HUD/federation imports passed.
  No historical runtime state is reused. Existing source1.18.6/extension1.6.1/
  Mobile1.0.4+7 versions are unchanged.

Saved-plan runner validates source/tool/state/plan hashes and requires a matching
record of actual owner delegation. It durably claims a single attempt before
cloud apply; a timeout or lost reply remains unknown and cannot be replayed.
Cleanup additionally requires verified exported evidence. Preparation is not
activation evidence or100% completion.

The retained roadmap review boundary is in USER.md's Issue310 direction:
“The driver reserves cloud/spend mutations, ngrok account/endpoint changes, IdP
registrations and device operations outside the approved read set for explicit
human action/review.” The owner’s R06 topology answers settle organization/project
isolation; the owner subsequently approved this complete packet: “yes go go go go go” and “get it to 100% yes ?”. No repeated permission is required for this scope.
