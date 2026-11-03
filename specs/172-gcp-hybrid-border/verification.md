# R03 verification — technical qualification and cleanup complete

2026-11-03. R01 and R02 are complete and accepted. R03 implementation, actual
GCP/on-prem qualification, independent evidence review and teardown are complete.
**35/36 tasks are closed; T036 human acceptance remains pending before R04.**
Daily memory and GAIT are recorded separately from acceptance. No version,
release or public deployment guidance is authorized. Source1.18.3/extension1.5.0
remain unchanged.

The owner's [November3 delegation](activation-delegation.md) resolved the earlier
execution/spending gate. The stated credit was not verified or treated as a spend
target. [Historical source/preparation evidence](preparation-verification.md)
retains original tests, failures and November2 limits; these actual outcomes
supersede its pending live work.

## Actual hybrid workload

A fresh Ubuntu24.04 AMD64 control-only Border in GCP Montréal dispatched four
separately reviewed and approved reads over outbound iN2N to a fresh Mac member.
The member ran OpenClaw2026.7.1-2 with Anthropic `claude-sonnet-4-6` and the pinned
IOS-XE/IOL pyATS/Unicon25.2 adapter. Each returned parsed IOS17.18.2 from exactly
one SSH `show version`: zero setup, enable, configuration or reconnect commands.
Each used two member-side provider calls, one signed result and one durable ACK.
Totals: **four device commands, eight provider calls**.

| Device | Actual operation ID | Verified result SHA256 prefix | Injected loss |
|---|---|---|---|
| R1 | `4c59de26-7ad0-40cc-8908-ec9779734774` | `767d049d1a58a945` | Submit reply after durable admission |
| R2 | `760e956a-9ab9-4b6e-9cb6-642c5516f68e` | `1a2e49b211d4d372` | ACK reply after durable member ACK |
| SW1 | `c091f8a3-42e8-48c7-8a87-4048dfe74633` | `6222ce14fae4f245` | None |
| SW2 | `5106f821-0b1e-45e5-a86b-b0be7d221ac3` | `4902dd0c2d02cefb` | None |

Real service/member restart, browser reload, fresh owner login and explicit-ID
recovery retained the same operations, enrollment keys and signed results, with
four effects/eight provider calls before and after. Recovery granted no new
approval or operation mutation. The cloud had zero protected model calls.

Host-key provenance is explicit: R1's authenticated CML console public key matched
SSH; R2/SW1/SW2 used existing owner SSH pins plus authenticated exact-node CML
metadata. Their historical pin establishment is undocumented. Original inventories
and owner known_hosts remain unchanged. Private addresses and transcripts stay
outside Git. Earlier diagnostic reads are distinct from these four operations.

## Actual browser, identity and network boundary

Trusted public HTTPS at the named R03 hostname passed before teardown. The
production owner HUD retained and displayed all four verified parsed results.
The workload/browser phases contain46 checks; a separate auth-only phase adds16.
These62 checks include anonymous operational-data refusal, exact installation/
Host/Origin, CSRF, Secure/HttpOnly/Strict cookies, expired/reused tickets, forged
proxy identity, duplicate headers/cookies, native owner revocation, legacy route/
WebSocket refusal and selection/review substitutions. Auth-only probes made no
operation calls. Owner generation advanced1→2 and test sessions were revoked.

Border installation `0d02acd4-4349-45a8-951e-215f91a1174e` ran dedicated non-root
federation/HUD services with no capabilities. Caddy had only CAP_NET_BIND_SERVICE;
the root network guard had CAP_NET_ADMIN. Actual service, UID, source, role,
listener and restart inspection passed. No device/provider key, Docker, local
model/tool executor or cloud-to-LAN route existed on the Border. Its VM service
account had no project roles, no user-managed keys and only its own operator-secret
access. An actual VM-identity request for R01's secret returned403 without reading
a payload. Application-cgroup metadata-ID probes were denied while the same-host
control returned200; no token was requested.

Six actual scoped firewalls and dedicated routes matched the reviewed plan.
External native probes from the reviewed member source reached only80/443/42102
among13 sampled ports. SSH, routing, raw HUD/admin/model/MCP and dormant eN2N
ports were closed. Source restriction is additionally verified in actual GCP
policy; this was not a multi-vantage Internet scan. Admin access used IAP. Strict
fresh outbound enrollment ran without an executor and was never replayed.

## Actual resource bounds, cost and retirement

The10-create foundation and subsequent3-create network activation applied once;
fresh state-derived plans showed10 and then13 no-op resources. Actual kernel
namespace tests exhausted a quota and refused spent reentry. A64-packet empirical
test drained60,288 bytes in0.355s against0.351s nominal1Mbit/s shaping, with93
overlimits and zero drops. The main host's10GiB output allocation activated once;
whole-interface1Mbit/s shaping, selected-networkd dependencies and fixed expiry
timer/Compute STOP were inspected. No allocation reset or extension occurred.
An actual VM reboot or scheduled expiry firing was **not** performed; service
restart and systemd inspection satisfy the stated activation contract.

The saved13-delete teardown succeeded at13:36:26Z. Authenticated post-teardown
queries found zero R03 instances, disks, addresses, snapshots, images, networks,
subnets, firewalls, service accounts or secrets; authoritative state has zero
resources. Both DNS authorities returned NXDOMAIN after exact R03 A-record removal.
The temporary OS Login key is absent; unrelated keys are unchanged. Both member
workers stopped; exactly12 owned stopped containers and4 owned networks were
removed. Images, unrelated resources and all1,729 member-home files were preserved.

The VM existed for less than one hour. Prorating the previously authenticated
CAD1.67/48h base estimate gives approximately **CAD0.035 base**, excluding traffic,
tax, secret operations, model calls and R01. This is not an observed invoice:
actual accrued billing remains unavailable. No R03 billable residue remains.
R01 intentionally remains running; its DNS and authoritative state are unchanged,
and actual trusted HTTPS returned200 after cleanup. Its continuing costs are
outside this R03 retirement. See [teardown-review.md](teardown-review.md).

The R03 hostname is **retired**, not a working demonstration URL. The existing
[R01 lab HUD](https://r01-gcp-montreal.lobsternet.automateyournetwork.com/) remains
the separately authorized pilot; it is not the R03 authenticated deployment.

## Evidence and preserved failures

Private root: `~/.local/share/netclaw/roadmap-r03-20261102/activation-20261103/`.
No credentials, raw device outputs, private state archives or GAIT bundles are
committed to source. Principal receipts:

| Evidence | Private artifact |
|---|---|
| Four IDs, complete digests and parsed results | `operations.json`, `independent-four-tool-results.json` |
| Browser46 and auth-only16 checks | `browser-qualification.json`, `auth-supplement/auth-supplement-report.json` |
| Real P256 approvals/results/ACKs, native output, exact bindings and GAIT links | `receipts/independent-receipt-gait-report.json`, `receipts/inspection-packet.json` |
| Consistent before/after SQLite/GAIT and identical counters | `receipts/cloud-snapshots/{before-restart,after-restart}`, `receipts/member-snapshots/{before-restart-v2,after-restart}`, `coordinator/restart.receipt.json` |
| Actual cloud runtime, service, IAM, network and guard receipt index | `cloud-runtime-final-evidence-index.json` |
| Member enrollment, execution, restart and local cleanup | `onprem/lane-completion.json` |
| Independent evidence and teardown reviews | `hud-evidence-lane-completion.json`, `teardown-peer-review.json`, `final-independent-coverage-review.json` |
| Session GAIT trail | `gait-final-technical-cleanup.json` (commit `1869ca6e`), `gait-final-log.json` |
| Current-state archive verification | `final-preservation/local-verification.json` |
| Retirement, cost and R01 preservation | `teardown-apply-result.json`, `zero-r03-residue-verification.json`, `dns-cleanup.json`, `dns-authoritative-cleanup.json`, `oslogin-cleanup-result.json`, `cost-observation-final.json`, `r01-public-preservation.json` |

The independent cryptographic report's `passed:true` validates its narrow receipt/
GAIT scope. Its `qualification:false` is retained: that report alone never claims
whole-feature qualification. Overall technical completion combines these separate
workload, browser, host, resource and cleanup observations.

The browser summary is deliberately derived: attempt1 had31 checks but a selector
timeout **before any authority/effect**; attempt2 completed41 checks and all four
approved/ACKed reads but timed out waiting for restart coordination. A separate
status-only continuation passed5 recovery checks with no operation mutations.
Original failed reports and hashes remain intact. The approval loop was never
rerun after device execution.

Other retained failures/repairs are bounded and do not conceal extra effects:

- Initial federation startup exited on a dormant eN2N registration binding.
  Registry CAS1→2 corrected only its application identity/public transport key
  binding and role registry digest. Protected profile, iN2N and all keys stayed
  unchanged. The first repair helper failed directory traversal before mutation;
  the corrected service-UID path passed, followed by five stable process samples.
- Private export helpers were corrected for SQLite online-backup header changes,
  actual `acknowledged` state, the non-operation Docker CLI directory and the
  canonical owned empty0600 GAIT lock. Source/device authorization was unchanged.
- Unicon produced four0666 completed logs under0700 ancestors. Export refused;
  exact owned log modes changed to0600 with identical byte hashes. The rejected
  export remains retained; `before-restart-v2` is the accepted member snapshot.
- Namespace observer failures and an aggregate boot-binding assertion failure
  remain recorded. Subsequent read-only diagnosis/exact proof passed without a
  production guard reset. The aggregate failure's cause is not established.
- No R02 unknown/spent operation was replayed. No R01 runtime or original testbed
  was upgraded. Frozen deployed source was `fbd41cb1`, runtime implementation
  through `aa861ee3`; November3 repairs changed private configuration/helpers only.

The final current-state archive contains240 independently verified entries,
including closed SQLite, current identities/registry, source/runtime manifests,
service/guard evidence and edge certificates. SHA256:
`3f9fe622b119b3285532760532bdaee66ffd66b0e87a077b0650076eea432d46`.
It contains secrets, stays private, and is **not an activation/replay payload**.
Never replay the prepared initial archive or any spent resource/activation plan.

## Requirement and acceptance reconciliation

| Requirements / criteria | Result and evidence |
|---|---|
| FR001–004; SC001–002 | Four exact approved reads, refusal probes, independent signed/GAIT chains and unchanged loss/restart counters; T005–T012,T016,T032–T034 complete |
| FR005–007; SC003 | Actual trusted named HTTPS owner HUD,62 browser/auth checks and status-only four-result recovery; T008–T009,T013–T014,T022 complete |
| FR008–010; SC004 | Actual control-only role, confined processes, scoped IAM/network, strict outbound unchanged-key enrollment; T015–T019,T021–T023 complete |
| FR011–013; SC005 | Exact apply/no-drift/retirement, finite safeguards, explicit billing limits and R01/original-file preservation; T001,T020,T024–T031 complete |
| FR014 | Maintainer-only evidence; versions and entire-roadmap release hold unchanged; T035 complete |
| FR015; SC006 | Independent technical evidence complete and task accounting reconciled; **human acceptance pending in T036**, so no overall accepted100% claim and no R04 work |

Source validation remains464 protected/posture tests,453 serialized HUD tests and
production build,82 transport/service tests,53 cloud/role tests plus23 subtests,
with independent enrollment41 and role33 checks. Private helper reviews/tests and
live evidence supplement these; fixtures alone are not cloud qualification.
Shared bounded implementation pass3 covered R03 source/preparation; no automatic
Ralph hook or unbounded execution loop was enabled.

Qualification is limited to the actual Montréal Ubuntu24.04 control-only Border,
Mac OpenClaw/Sonnet member and four pinned IOS-XE/IOL endpoints. Hermes cloud,
arbitrary models/providers/platforms, cloud members, Ollama, CML API execution,
multi-user/SSO/RBAC, writes, HA and multi-cloud are not qualified here. R02's
separate OpenClaw/Hermes evidence remains valid within its recorded scope.
