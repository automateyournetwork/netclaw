# Spec162 additional live qualification — 2026-10-31

The owner requested use of the real account and **three additional loops** to move
from controlled evidence to actual service/lab acceptance. These supplement the
five completed implementation iterations; they do not replace or recount them.
Overall qualification remains incomplete until every required live gate is proven.

## Fixed prompt for these three loops

> Re-read the current Spec162 requirements, contracts, tasks and observed evidence.
> Use the explicitly selected live account and qualified lab resources to test the
> real behavior in scope. Discover actual schemas/permissions, inspect new findings,
> fix supported implementation defects and run justified regression and live checks.
> Preserve exact-file approval, original configuration-tool authority, baseline,
> rollback, private artifacts and unknown-outcome recovery. Never infer a live pass
> from a fixture, invent an approval, bypass a denied tool, or weaken a requirement
> to claim 100%. Record actual results, limits and the next concrete unmet gate.

## 1 — Live account, client and discovery (complete)

- Owner identified the private root-environment key by name; value read locally
  into a separate 0600 qualification environment. No key value in chat, source or
  process argv. Existing source environment permissions tightened to 0600.
- Installed official Terminal **0.6.0** into a separate Python 3.12.12 environment.
  Wheel SHA-256 **6b98c11f9d73a6eefb92af28a5bc4cc2ac055ee4a97fb3ea9bd30cd0ef5e5a38**
  matches PyPI metadata. No upstream code redistributed or modified.
- The official client reported license v1.0 unaccepted. The owner explicitly asked
  acceptance on their behalf; `license accept --yes` then succeeded. This delegated
  one-time action does not change the installer's no-automatic-acceptance behavior.
- Actual hosted MCP and local Terminal discovery succeed. Hosted account reports
  API-key authentication and server-enforced strict view. Nine reads qualify for
  the guard; local capabilities qualify 75 operation/path combinations and leave
  seven unqualified. Actual max input is 5 MiB for this connection.
- Real `get_account` returns a success/data envelope. The old guard incorrectly
  reported authentication unestablished and discarded nested report verdicts/counts.
  Added envelope-aware authentication, conservative nested summary projection and
  explicit unsuccessful-envelope refusal. Three new tests first failed; all
  **18 transport tests then passed (23.160s)**. Repeating hosted discovery now
  confirms authenticated/capable without exposing account prose or credentials.
- Real read calls: IOS-XE router OSPF and Junos router OSPF return supported/full
  knowledge-base entries. Junos EIGRP returns unknown (not a supported translation).
  Bounded job listing returned zero jobs. Knowledge search completed; all full
  responses remain private with hashes.
- Preferred live request prepared: synthetic 477-byte IOS-XE OSPF → Junos SET,
  empty options; SHA-256 `1482db1f8f905b59d12d58801ca25e10ee43f97b2ba034f4f86945d333a1cb7f`.
  The owner subsequently completed native exact-file approval; loop 2 records
  the one-time submission and actual result.
- Current Docker pyATS inventory successfully lists R1/R2/SW1/SW2. Direct SDK
  probe first used outdated stream/session signatures, then succeeded using the
  actual SDK's legacy client. These invocation errors changed no runtime/device.
- CUA native pipe still fails; desktop acceptance is not claimed. CML follow-up
  in loop 3 establishes actual access, images, license and resource limits.

## 2 — Real conversion, evidence and downloaded candidate (complete)

- Native operator approval was actually recorded before each of two submissions.
  Each request consumed its one-use grant and was submitted once. No replay,
  broadened approval or production configuration was used.
- Forward: 477-byte synthetic IOS-XE OSPF → Junos SET. Completed **needs review**,
  zero blocking reasons, seven review reasons. Evidence: six warnings, one manual
  review item, partial coverage and truncated digest. The provider's OSPF check
  passed; ACL, reachability, BGP and route-map checks were inconclusive. These are
  provider analysis results, not observed device behavior. Detailed report absent.
- Three downloaded files passed confinement/size/hash verification. The actual
  857-byte Junos candidate SHA-256 is
  `8d870d86554ed10d2df53004579eace4e2e2fad67250cc11bc8760857e4e357a`.
  Local assertions found 20 lines, only SET commands/comments, five OSPF lines,
  the expected router ID, loopback and cost; no pipe/semicolon separators.
  Those assertions are syntax/content observations, not semantic acceptance.
- Reverse: the same 857-byte returned Junos artifact → IOS-XE, with separate
  exact-file approval. Completed **needs review**, zero blocking reasons and
  seven review reasons; six warnings and five manual-review items, partial
  coverage, truncated digest and absent detailed report. Three downloads verified.
  The 736-byte IOS-XE candidate SHA-256 is
  `b13f9f92bcfa7dfe463fe70d2dfac220870bc620b73f80e93dff8358a5477282`.
- Live evidence exposed another summary defect: nested `get_job_brief` evidence,
  manual-work counts, partial coverage and absent reports were omitted. Added two
  regression cases; observed the nested-evidence failure before fixing the fixed
  vocabulary projection. **20 transport tests passed (24.072s)**. Reprocessing
  original private responses now retains every review signal without raw prose.
- Full feature regression: **66 tests passed (30.932s)**, Python 3.12.12, SDK 2.3.0,
  FastMCP 4.0.11, Node 24.19.0. These remain controlled tests, separate from the
  two real service jobs above.
- Corrected overly broad XML documentation: actual Palo Alto XML is advertised as
  UTF-8 text and is eligible; binary/archive and non-text handoffs remain blocked.
  Prescan and guided-draft operations discovered upstream are not exposed by the
  managed convert/validate/optimize profile. Check Point bundle paths remain
  unqualified; no vendor Cartesian product was invented.

## 3 — Actual analysis runtime and target prerequisites (continuing with owner-authorized runtime build)

- CML 2.10.0+build.13 read-only authentication succeeded. The presented certificate
  was trusted only for this isolated request with its advertised DNS identity;
  trust-on-first-use is not independent PKI verification. No global trust change.
- Actual installed image inventory contains 12 images, including IOL XE 17.18.02
  (`483954eb7b0eebc4965f692bb84dc3298b7e3c22ae2b2b6823c07b60807f2c4f`),
  and no Junos image. Forty-five node definitions do not prove their images exist.
- CML reports an active Personal evaluation license (expiry 2027-01-22), eight
  x86 CPU cores, 4.10 GB total RAM and 2.02 GB free at observation. Two IOL nodes'
  default allocation is 2 GiB, exceeding that free capacity before overhead.
  Existing owner labs, running nodes and the reported orphan are untouched.
- Native automation still fails its pipe startup. No live Terminal Intent API or
  OpenClaw Gateway listener was found in the local TCP listener inventory. A
  newly constructed test issuer cannot be substituted for the real protected
  runtime, endpoint designation, baseline and APPLY transition.
- Added a run-owned local Batfish analysis container with only loopback port
  publication, four CPUs and 4 GiB memory cap. This is analysis, not a Junos VM.
  Official ARM64 image digest:
  `29f6ebf61e2c4bb63d4755885872c9fb1fddda6005233918d9762fb2043c3792`.
- Installing the declared Batfish requirements exposed a real startup failure:
  pybatfish 2024.7.22.1569 imports `pkg_resources`, removed by setuptools 82.
  Added its recommended `setuptools<81` compatibility constraint; isolated
  resolution selects 80.10.2. No global/owner runtime packages changed.
- An initial analysis invocation used the newer client's timeout argument after
  resolving the declared older client; corrected the qualification helper to its
  actual signature. The current image listens on 9996 rather than the older
  example's 9997. Stopped the first run-owned container (retained), then started a
  second with loopback 19997→9996. No network-device or owner-container changes.
- Real Batfish engine analysis succeeded using pybatfish 2024.7.22.1569. Three
  snapshots contain the unchanged original source, actual Junos candidate and
  actual reverse IOS-XE candidate, each paired with one authored synthetic peer.
  All six files parsed completely; initialization issues were empty. Modeled
  OSPF session compatibility reports two directed ESTABLISHED rows per snapshot.
  These are computed protocol outcomes, not live adjacency observations.
- Nine modeled traffic checks passed: two positive loopback directions and an
  unadvertised-prefix NO_ROUTE control in each snapshot. Peer next hop remains
  the expected synthetic address; active point-to-point interface cost 10 and
  passive loopback state are preserved in the model.
- **Routing metric equality did not hold for the forward candidate**: the peer's
  route to the converted loopback has metric 10 in Junos versus 11 in source
  IOS-XE. Modeled loopback cost is 0 versus 1. Reverse IOS-XE returns metric 11.
  Original outputs remain unchanged; no silent fix or full equivalence claim.
- Actual Batfish MCP STDIO discovery exposed eight tools. Three real
  `batfish_validate_config` calls returned PASS/complete parsing and explicitly
  `behavioral_equivalence: not_established_by_parsing`, consistent with the
  independent routing observation. This is actual engine/MCP evidence, not fixtures.
- Dependency resolution/check and website Astro check (99 files, zero errors,
  warnings or hints) pass. Source patch version is 1.15.1; extension remains 1.5.0.
  Provider/manual review, native UI and live appliance gaps remain explicit.
- No default OpenClaw installation/executable or local Intent/Gateway listener
  was found. Requested the actual selected runtime and a licensed Junos image
  from the owner; no replacement fixture issuer, fabricated approval or raw SSH
  apply was used. The owner then requested a real minimal NetClaw installation.
  Loop 3 continues with that isolated build and native exact-plan review.
  T034–T036 remain open; **overall live qualification is not 100%**.

### Native minimal runtime continuation

The owner completed the real plan confirmation and three hidden credential
prompts. OpenClaw 2026.7.1-2 and its HUD started in a separate home. The installer
reported `configuration_required`; its original journal is retained. Continuing
qualification found and corrected two source defects:

1. NetConverter's source-tree venv symlink failed native ownership observation.
   Move it under the selected runtime root; preserve the symlink/ownership check.
   A real install-function/observer regression failed before the fix, then passed.
   Scoped repair installed the guard and added only its missing registration.
2. The native pyATS installer still checked out `f11b02f…`, while the staged
   installer qualified dynamic revision `4a3c1e3…`. The older server exited without
   a static testbed. Share the staged installer's revision and required source
   files, including the dynamic builder, between native install and observation.
   The new checkout regression failed before the fix. The actual selected runtime
   was replaced through staged recovery; the old generation remains available.

Owner-directed provider repair changed only the new claw's Anthropic setting to
the selected repository key. HTTP 200 authentication and a real gateway Claude
Sonnet 4.6 response establish provider execution. An actual model tool call then
proved NetConverter discovery/authentication/capability in the selected runtime.
The first call returned generic `upstream_tool_unavailable`: the official
Terminal's license state was separate in this isolated home. Official acceptance
of the same v1.0 license used the owner's existing delegation; the next call
returned installed/discovered/authenticated/capable true. This was not a hosted
file upload or an approval transfer between installations.

Use typed tool evidence: nine allowed reads and 75 qualified operation/path
combinations, seven unqualified. The model's prose miscounted lists; it is not
used to establish those totals. Native OpenClaw probes verify guard 8, pyATS 35,
Batfish 8 and GAIT 23 tools. GAIT is initialized in the selected workspace with a
real audit branch/turn. pyATS reports no active dynamic inventory; listing devices
correctly refuses rather than borrowing another runtime's testbed.

A subsequent actual Claude-driven turn read the empty dynamic inventory, called
Batfish validation for all three snapshots and recorded/logged GAIT. All three
returned complete parsing, with behavior explicitly unestablished by parsing.
Its narrative mislabeled the reverse candidate as a peer in one sentence; the
stored source/candidate hashes and typed evidence establish the actual inputs.
CML native
HTTPS and MCP startup currently time out; the owner has been notified. No target
was created, no candidate applied, and the licensed Junos image is still absent.
No raw SSH or replacement approval issuer was used.

Validation: 67 feature tests, 273 setup tests run (27 optional skips), four runtime
recovery tests and six actual dynamic-runtime tests pass. Catalog coverage and
the owned guard's dependency check pass. The broad dependency scan reports the
separate local HumanRail checkout's unbounded MCP requirement; record the limit.
Source advances to 1.15.2; extension remains 1.5.0. Bound installed source and the
original journal are preserved, with separate private maintenance receipts.
Loop 3 remains open for actual appliance acceptance; T034–T036 remain unchecked.

### CML follow-up — 2026-11-01

Owner requested another CML attempt. Actual native HTTPS API reads now succeed:
HTTP 200, CML 2.10.0+build.13, two labs/six running nodes, 12 installed images,
no Junos image, approximately 1.95 GB free RAM, and Personal EVAL authorization
through 2027-01-22. Existing resources and the reported orphan were not changed.

A scoped loopback TLS adapter, with verified upstream TLS and a read-only rule
plus authentication, enabled actual native discovery of 51 CML tools. HTTP was
first refused by virl2; the TLS probe preserves certificate checks. Discovery did
not establish login: read calls returned authentication failures, and a direct
native HTTPS login using the selected runtime's saved credentials independently
returned HTTP 403. The previous private session still reads the API. The owner
was asked for the current local credential source; no secret value was exposed.
Temporary probe configuration did not replace the live registration. Reachability
is restored; authentication and remaining appliance gates are still open.

## Retained evidence and resources

Full service responses, original/returned candidates, request/grant/job ledgers,
CML discovery, analysis inputs/answers and hash manifests remain in the owner's
private `spec162-live-20261031` qualification directory outside Git. No existing
network configuration was submitted. No candidate reached a live device.

Run-owned analysis containers: `netclaw-spec162-batfish-20261031` is stopped;
`netclaw-spec162-batfish-v2-20261031` is retained for review with loopback-only
API 19997 and CPU/memory limits. No CML target was created. Resource and artifact
IDs, original evidence and precise metadata are retained locally.


### November 1 continuation — actual appliance behavior and discovered control gap

T035 now passes for the available IOS-XE round-trip reference. The owner authorized
stop/start juggling of five enforced CML licenses; genuine owner baselines were
captured and first restoration verified. Two real IOS-XE 17.18.2 nodes booted with
separate management VRFs and an isolated synthetic link. Password length and
legacy IOSv SSH failures remain retained. Reboot host-key changes were independently
verified against actual public keys read through authenticated CML TLS consoles.

Actual native NetClaw composition, private collection, HUD review and API-issued
application succeeded. OSPF FULL, metric-11 reciprocal loopback routes, 5/5 pings
each direction and 0/3 negative controls were observed with management preserved.
The agent nevertheless replaced baselinePath with an artifact reference note.
The actual original stayed private and retained; the API should have rejected
that substitution. A red regression reproduced it. Added collector receipts and
exact baseline/original hash checks in API preparation, issuance and consumption;
18 private apply tests and 69 complete feature tests pass. The original live
record is retained, not rewritten. A clean repeat through the fixed source is
still required, as is fresh native installer acceptance.

Other live defects fixed: missing native HUD reference JSON imports, environment
SecretRef gateway authentication, and OpenClaw per-turn STDIO process termination.
The explicit foreground pyATS session retains the same process across clients
with private bearer authentication and installation/policy binding. Nine actual
pinned runtime/session checks pass, including unauthorized access and stopped
session refusal. No tool identity, live-process check or apply authority was bypassed.

### Clean repeat and final native plan

The clean actual repeat `74ce25ed-b2e7-486e-bb13-b3a7b389e4a1` completed through
the tightened baseline gate. Seventeen typed native tool results retain the
observed bootstrap, genuine collector baseline, single protected application and
actual target checks. Independent peer MCP readbacks confirm FULL adjacency,
metric-11 reciprocal routing, 5/5 positive and 0/3 negative pings and MGMT isolation.
The baseline still matches its private original and all receipt bindings. T036
is complete; the first flawed acceptance remains retained as failure evidence.

A new clean, pinned-source native installation plan validates as apply-ready.
It selects the four affected components, new home/ports, two private credential
prompts and testing posture. CML remains separately qualified in the original
runtime. Native human review is pending, so T034 and live loop 3 remain open;
43/44 tasks are complete. No approval or installer journal has been fabricated.

After the clean repeat, the owned lab was stopped and R1/R2 were restored to BOOTED.
Fresh private running-configuration comparisons match their original pre-juggle
baselines after excluding only display timestamp/size metadata. The second-round
manifest is reconciled with `restore_required:false`. The rehearsal's Local/Lab
authorization was disabled through the actual API; retained records stay intact.
