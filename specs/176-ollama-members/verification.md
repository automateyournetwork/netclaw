# Verification: R05 / Spec176

## Current state — 2026-11-05

Source implementation integrated on `176-ollama-members`: **26/33 tasks complete**.
Actual temporary local ARM64 qualification completed with two Ollama calls, one
native MCP calculation, signed result and durable ACK. Intended local/cloud members
are enrolled under the approved48-hour window; verified cloud runner recovery
has completed with original operation/claim history preserved. The cloud foundation,
scoped Border backend/HUD update and native client builds are complete. The combined browser and editor success/reopen runs passed. Mobile exposed a real
review-expiry/provider-uncertainty case; the proven profile-rebind recovery step
is now implemented and actually verified. Native completion/recovery and closeout remain open.
No release or R06/R07 work has occurred.

NetClaw baseline `db0c9682d4997d51a15f75cbf2df83b97d3c3f45`, source1.18.6,
extension1.6.1, Mobile1.0.4+7. Existing usable pilot/member and December1 lifetime
remain preserved. Thermidor final historical qualification informs the design;
its exact inspected source hashes and limitations are retained separately.

## Acceptance matrix

| Group | Required current NetClaw evidence | Status |
|---|---|---|
| Local ARM64 | Real guarded IPv4 native MCP, verified arithmetic,2 turns/1 call | PASSED on temporary and intended members |
| GCP AMD64 | Real guarded IPv6 native MCP, verified arithmetic,2 turns/1 call | PASSED |
| Combined browser | One durable parent,two distinct approvals,both results | PASSED; actual reload recovered same results |
| Isolation | Guard positive control and agent/broker/sibling/Border/public denials | PASSED for owned models and recorded vantages; limits below |
| Resource/accounting | Actual swap/cgroup/OOM, CPU/memory,tokens,time,zero provider charges,unload | PASSED; exact idle-unload interval not measured |
| Recovery | One-child failure,lost reply/ACK,process/client restart,no repeat | Actual browser lost reply/unknown, Mobile failed-sibling and owned runner recovery passed; final native/shared restart pending; ACK-loss protocol-tested |
| G12 VS Code | AFFECTED: combined references/reviews/results/recovery; actual Mac editor | LIVE SUCCESS/REOPEN PASSED; sibling-failure case pending |
| G13 Mobile | AFFECTED: combined WSS contract/UI; native simulator/device-key recovery | Actual signed partial and cold/background recovery passed; complete pair pending |
| Regression/portfolio | Existing protected pyATS/NetBox/subnet/hosted models, Chat/Canvas,clients | SOURCE TESTED; live portfolio pending |
| Preservation/lifecycle | Baseline/rollback/export,usable intended delivery,disposable residue inventory | Activation preservation passed; final export/residue inventory pending |
| Human acceptance | Owner reviews current R05 evidence before R06/R07 | PENDING |

Existing capabilities have source regression coverage, not new live qualification. Hermes Ollama, Windows/WSL, physical iPhone camera/SecureEnclave, GPU,
other models, HA and external delegation are unqualified. No new transport claim.

## Preparation checks

- Clean `main` at kickoff; Spec Kit created `176-ollama-members` and selected the
  new feature via `.specify/feature.json`; setup-plan/prerequisite discovery used.
- Read actual sibling Thermidor docs, final evidence, implementation and tests;
  preserved source hash manifest; no writes or tests in that checkout.
- Requirements/checklist,15 functional requirements,6 success criteria and33 tasks
  map to contracts and verification. Artifact checks passed: sequential33 unchecked tasks,100% requirement/success-criteria
  mapping, local links, no unresolved template markers,23 Thermidor hashes plus the
  native MCP source hash, Spec Kit prerequisites and `git diff --check`. Independent
  review found two gaps, both addressed: actual native source capability/reproducibility
  and the member/runner-wide uncertainty latch. No functional tests ran for this
  documentation-only preparation.
- GAIT branch+checkout `r05-spec176-thermidor-sdd-20261105`; kickoff `59ef60a6`.
  Existing `/Users/john.capobianco/gait_mcp/venv/bin/python` works; no install needed.
- Startup `pyats_list_devices` attempted: configured HTTP runtime missing, no device
  contacted. MemPalace server source unavailable at checked local locations; no
  successful search/journal claimed. Daily memory retains this preparation.

## Evidence recording rules

Record exact source/artifact/profile identities, actual commands, timestamps,
platform, observed counts, success/failure/unknown results and private receipt hashes.
Separate unit/fixture/native/container/browser/editor/simulator evidence. Retain all
failed attempts and original approval/result/ACK IDs. A later pass does not erase
earlier unknown outcomes. Never store secrets or raw private topology in source.


The full local GAIT trail is retained at
`~/.local/share/netclaw/roadmap-r05-sdd-20261105/gait-final.json`.
Planning checkpoint is `9394ea82`; integrated source commits are `aa263c70`,
`a8566e43`, `c9a46e8e`, and `201841c6`. Optional Spec Kit auto-commit hooks remain
disabled. No push/PR/publication occurred.

## Integrated source checks — 2026-11-05

- Root: isolated Python3.12 `python -m pytest -q tests/n2n/test_protected*.py`: **665 passed**,21 existing datetime deprecation warnings,15.18s. Private log `roadmap-r05-20261105/integrated-python-tests-all.log`. The first explicit file-list command named a nonexistent enrollment test and ran zero tests; its original log remains.
- Native calculator: actual MCP subprocess tested eight IPv4/IPv6 boundary cases, including /0, /31, /32, /127, /128 and decimal counts. This is actual native arithmetic; provider execution in authority tests is explicitly synthetic. Exact native source before `bfb8bb548aa7096c0b2324a3798c581ce917a26388aa6193ae66eb0708e7dd45`, after `582f3203269612fcf949c5875e41ac557bb096d6476c846e1ac921ba559a6364`. Main ignored native clone is unchanged.
- Client lane, qualified Node24.19: HUD47/47 and Vite build; extension200 passed,3 existing live skips, TypeScript and build; Mobile491 full tests, focused combined/device recovery regressions and analyzer clean. Source-only counts do not close browser/editor/native simulator acceptance. Logs retained by coordinator under private evidence.
- Current actual official DefenseClaw reports1.0.4, commit `be69263d5f1fc5d5a9cc2f61769f82056d3b67fe`. The first `version` subcommand was rejected; `--version` succeeded. Native guard routing/readiness remains a live acceptance item.
- Public CPU/model closure was verified before copying from the sibling cache into fresh private NetClaw artifacts. Fresh ARM64 model image `sha256:43fd0705aa3cc01ac6d7b1a72a2eba75558f78771941db62a57383e7eecdb277`; fresh guard `sha256:415ad07d3924f0b1d5bf2c56d9409ace5f9c06a8e3d004747f0694c66a86d1a1`. No Thermidor runtime/image is deployed. Initial guard build treated a bare local image ID as a registry name and failed before build; the exact local base was tagged, rechecked and the offline build passed.
- Cloud preflight was read-only. Existing Border has2GiB total/about1GiB free and no Docker. A separate8GiB member plan is being prepared; no resize, apply, DNS, IAM, budget or authority mutation occurred.

Artifact dispositions are in `labs/ollama/README.md`. Native MCP, official guard
version, source tests, image builds and live model execution remain separate
evidence classes. Actual R05 inference and signed durable delivery are still open.

### Required local qualification corrections

The initial local preparation used assumed guardUID501; actual `id -u` is503.
The UID gate refused before creating resources. A native profile draft also
refused an incorrectly named skill path; the corrected fresh profile uses the
required `skills/subnet-calculator/SKILL.md` and actual discovered MCP schema.
Both original failures remain recorded.

The first model image's Bookworm base lacks glibc2.38 required by the pinned CPU
libstdc++; its owned model exited before inference (exit1, noOOM). The corrected
image uses the final reference's pinned upstream Python3.13.16/Trixie base; it
started actual Ollama0.40.11 on loopback with CPU-only detection and cloud disabled.
No Thermidor product or transport was imported. The second preparation then
found Docker29.9 does not publish the guard port on an internal bridge: actual
`NetworkSettings.Ports` was empty despite the requested binding. Its model API
positive read passed under the guard UID. The owned model was stopped with its
original evidence retained, zero inference. The required correction keeps the
internal network and uses the trusted host's private Docker execution path to
the guard, with no published model/guard TCP port; hosted profiles stay unchanged.
This is a local topology correction, not a new transport or model qualification.

### Current namespace and cloud foundation

Actual local v3 preparation passes: model0.40.11 before/after positive API read,
guard UID503 nonce control, agent/broker/Border/sibling stand-in UID denials,
modelUID21006 API denial and a fresh peer-container positive guard/negative model
probe. No ports are published. This is namespace/UID evidence; actual external
vantage and application roles are still separate open T026 checks. Private
`local-model-v3/qualification-evidence.json` explicitly records this limitation.
Actual model image is `sha256:257ed45084d79372ab2b18d67e9121ffa76e73338869fe918ae7fbb35e20565d`.

Root integrated private-guard tests: **685passed**,21 existing warnings,15.00s.
The subsequent strict JSON history-normalization correction passed138 scoped
checks. Model/guard native positive inference remains open. The first local
strict-wire driver stopped at a snapshot assertion before any protected operation:
member-side production code derives the exporter binding rather than retaining
an `auth_binding` field. Corrected qualification reads the production binding
and compares both endpoints; original homes/keys/enrollment and failure report
are preserved, and an explicit same-home continuation is prepared.

The owner selected48hours instead of the proposedDec1 new-member retention.
The exact revised plan SHA256
`ca32d0d28314d3f90cd5aa0cf0ef5d923524d46e69b5cc3a141c54b2e14dba30`
was independently checked and applied once:8resources created,0changed,0destroyed.
Actual VM is RUNNING, e2-standard-2, no service-account scopes, STOP deadline
2026-11-07T19:41:25Z. Native Ubuntu24.04.5 reports8124712KiB total/7605368KiB
available. Serial-API ED25519 fingerprint was verified before first strict IAP SSH;
existing owner key worked, with no OS Login key mutation. Initial egress remains
denied; no model deployment or cloud inference has occurred. Baselines, current
state, plan claim and apply log are private under `cloud-plan-48h/` and
`cloud-current/`. The oldDec1plan remains unapplied evidence-only.

### Border/source and native execution progress

The fresh one-use Border packet `7432df297c7f025e7883311a6e66e806b2bd2521aa16d3458ba0863f511cd00d`
staged, checked and applied successfully.1009closed source files,15Python changes,
3HUD server changes and26assets were installed; only owner federation/HUD restarted.
All4old operations/12signatures,3members,23static identity/key/profile files, Caddy,
nft and the existing NetBox member were preserved. Independent post-apply
inspection passed and trusted HTTPS catalog/enrollment both return200; catalog
advertises `calculator_combined_v1`. No operation was sent by that update.

The approved member's exact network activation plan
`abd1f765b0fd66e6b440de8f33f3bbc1ca4a2d74bf481fd9a21f9c8b7711e327`
added only2R05-owned firewall rules: new memberSA→Border/32TCP42101 and new
member/32→BorderSA TCP42101. Eight foundation resources were unchanged. Original
Mac transport rule remains byte-equivalent. The same authoritative backend is
`cloud-plan-48h/state/terraform.tfstate`; no forked/old state may be applied.
The two firewall rules add no VM/disk/IP resource and keep the approved48h expiry.

Original local operation`e52593de-f0f7-46f3-8a03-eeee5f7b8c0e` remains unknown
with zero inference/tool/effect claims: the real guard had started on18970 but
readiness used the hosted4001port. Local-only readiness selection is fixed; the
hosted path remains4001. Its guard exited0 and cleanup was complete.

A separate explicitly reviewed operation`531e514a-75e9-4574-a35a-9d27cf5eea88`
completed1actual Ollama inference (310prompt+35completion tokens) and1actual native
MCP192.0.2.0/26 calculation:64addresses,62usable. Independent native verification
passed. Its second request was refused before dispatch; the failure is signed
and durably acknowledged, with all owned operation containers stopped/noOOM and
an idle runner latch. The retained first response and real pinned OpenClaw image
reproduced the mismatch offline without another provider/tool effect: OpenClaw
normalizes provider call ID`call_m9aee3p2` to`callm9aee3p2`. The exact compact tool
output was already correct. The narrow serializer-bound correction is integrated at959b2174;
no retry/replay of either spent operation is allowed. Actual model unload and
2GiB memory limit/zero swap/zero OOM were independently observed afterward.


### Final native wire correction and fresh member assembly

Integrated959b2174 validates only the actual retained Ollama call ID or the exact
pinned OpenClaw strict-ID alias, requires the assistant/tool pair to match, and
restores the original provider ID before the second forward. Exact arguments,
tool name and authoritative tool output remain enforced. A private allowlisted
refusal code aids diagnosis without exporting request content. The actual retained
second request passes offline; inference/MCP counts and latch rows were unchanged.
Protected Python/lifecycle suite: **712passed**,15.06s;141focused checks passed.

The new cloud VM received exactly six new offline OS packages, no upgrade/removal.
Docker/containerd remained masked/inactive with no socket; no enrollment or model
was started by that installation. Native read-only runtime checks verified303
closed source files and94hashed offline wheels against final source959b2174.
The final installation and activation receipts are separate private artifacts.

Fresh intended local member source is frozen at959b2174,5088files, manifest
`ab728737675962220cacc2dc2a0415d47451335d7998250c34420012fbbe401d`.
Review caught a stale initial Bookworm image/UID in the prepared setup packet
before activation. The original packet is retained; the corrected dedicated pin
uses the qualified Trixie image and UID21006. Fresh model namespace
`netclaw-r05-owner-arm64` now passes preparation/actual confinement with no
published ports and no inference. Profile SHA
`77ef8205e4c228a90731dd174150c50830fa0e970b4900893e93206c5f79a285`;
runtime template SHA`5697db629edaeecc5da31460653e7cdc6d70b252a54ed9c12abe572673527006`.
This namespace is independent of temporary native qualification and its retained
unknown/failure history. Enrollment and intended-member live success remain open.


### Actual local two-turn receipt and retained limitations

New reviewed operation`0f63fbd6-0595-4e21-b4f9-e09ec13ac872` completed exactly
2Ollama calls and1native MCP effect,966tokens,19.437s and zero provider API charge.
Signed result digest`5770f7021b93aab8211d5fed9b0df07b4cc0a56a155c8d026183106a5ed40479`
has a durable ACK. Sampled model memory1.516GiB/2GiB and agent448MiB/1.5GiB;
noOOM. Exact native facts independently verify64total/62usable addresses.
The actual model explanation incorrectly says64usable; it is retained verbatim
and is **not verified arithmetic**. FR004 requires authoritative tool facts to
remain separate from model explanation. Client labels/normalized summary rendering
are being corrected; no prompt tuning or repeated model call is used to hide this.

After actual worker restart, a new strict TLS exporter/binding and unchanged
authorities/receipt/ACK/effect counts are retained. The original final in-memory
report failed while serializing SQLite tuple rows; a read-only reconstruction
`terminal-v3/reconstructed-evidence.json` records exact evidence and that limit.
The first prelaunch witness had the same serialization error before any new
operation; both failures are retained. Old operations/keys/artifacts remain exact.
Guard/agent exited0; relay was stopped137; noOOM; owned workers are gone.

The intended local member enrolled once as`owner-20261104/mac-ollama-ipv4`,
installation`68ec42d4-a4bc-4ad1-ad60-234c052f4ce1`, generation
`02cd2f56-4b7b-49a5-9229-519cb59b221e`. First daemon startup then refused
`invalid_execution_profile`: static catalog validation called a new Ollama
validator requiring signed-operation limits. Root stopped the launchd job;
no operation was submitted by this member. Required static/execution interface
correction preserves mandatory execution limits and this enrolled identity.

The new cloud runtime installed successfully from303closedfiles/94offlinewheels.
A subsequent guest network restart automatically activated its required baseline
service at20:21:12Z; DHCP recovered, but IAP22became unreachable. The output
hook at-300 checked connection state before conntrack(-200); a narrow output
priority correction is being prepared. Forward policy, application isolation,
quota, identity, fixed expiry and existing Border remain unchanged. No cloud
model, enrollment or protected operation exists. Serial and failed read-only
IAP probes remain in private evidence. The hook ordering is documented by the
[nftables project](https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks).


### Intended member activation and client presentation

The static catalog/operation validator correction is integrated at `d87efaea`.
It separates catalog binding checks from mandatory execution-limit checks and
passes the selected model into IPv4/IPv6 tool validation. Real selector constructor
tests cover both families. Root protected/lifecycle suite: **746 passed**, 21
existing warnings, 15.50 seconds. A first command used a nonexistent lifecycle
test filename and ran zero tests; its log is retained separately.

Presentation fix `a9c026fa` shows authoritative native facts separately from
unverified model commentary in HUD, VS Code and Mobile. The original signed
receipt and model text remain unchanged. The actual 62-versus-64 mismatch and
large IPv6 decimal counts are covered by 122 focused checks, successful builds
and a clean Mobile analyzer. The test-only historical-reference archive step
is integrated at `6a91b392`. Native builds preserve existing client identities.

Cloud repair was applied once through a temporary startup script and one VM
stop/start. Actual native Linux reproduction demonstrated the connection-tracking
ordering fault. The guest receipt verifies only output priority changed from
-300 to -150; forward remains -300. IAP returned successfully, original metadata
was restored, and the original VM ID/STOP deadline remain unchanged. The fresh
host activation receipt confirms the 10 GiB allowance, 1 Mbit/s limit and exact
expiry timer. Existing allocation evidence is never reset.

The cloud source/private-parent correction changed exactly two Python files,
the source manifest and service paths, and created an owned 0700 member parent.
Root-owned host controls remain outside it. The initial unit verification refused
while Docker was intentionally masked; all applied changes were settled read-only
without replay, and unit verification passed after the reviewed Docker start.
Four pinned AMD64 images loaded offline; Docker 29.1.3 and actual Ollama model
namespace qualification passed with no published ports. Cloud profile SHA:
`668bfda1e08a0b48f800e47dcb10a67e4a33bbd76d49fe44507333cd227b80e5`.
Operator-Mac probes to owned VM ports 11434/4000/4001/18970/49171 timed out with
zero request bytes; IAP identity and internal model positive controls passed.
This is one external vantage; further actual-role evidence is separate.

Both intended members enrolled once and appear in trusted HTTPS catalog:

- Local: installation `68ec42d4-a4bc-4ad1-ad60-234c052f4ce1`, enrollment
  `02cd2f56-4b7b-49a5-9229-519cb59b221e`, profile revision
  `823f98e1ec32b03c78c5af2a06292a1b72b692dfeacf74428a678495a12ce506`.
- Cloud: installation `0c4964f1-7e99-47fe-bc7e-b9e4df3c75fd`, enrollment
  `dd37ba64-db47-4333-bfca-ac53be09f8de`, profile revision
  `cad4741ef66eb9b6f0775dec958b7889ebba260437680e706cf25d4aa3ebf3a8`.

All four prior registered members, four historical operations and prior keys
were preserved. An assets-only HUD update then preserved federation PID and all
unrelated services, changed only its distribution/manifest hash binding, and
served the new labels over trusted HTTPS. Private before/after snapshots retained
118 files and consistent database backups. No workload was created by deployment.

The first actual combined browser preparation returned `calculator_limits_refused`
before producing operation IDs: private catalogs advertised a 262144-byte output
limit while the combined policy correctly requires at most 32768. The catalogs
were tightened to32768; source policy is unchanged. Rejected client nonce
`60f886bd-5332-458f-bc16-5c4d63a0c888`, browser error and original profiles remain
retained. No model or native tool call occurred in this attempt.


### Intended combined browser success — 2026-11-05 21:02 UTC

Output-bound correction settled the rejected nonce read-only: zero parent/child
rows, all four historical operation rows and all five member bindings unchanged.
Only the two catalog output bounds changed; profiles, model processes, keys,
enrollments and latches remained unchanged. Each member federation daemon was
restarted once. Private receipt: `calculator-output-bound-correction/settlement.json`.

A fresh actual Chrome UI request prepared two immutable reviews with no work,
then approved each child separately. Parent `3e2caeef-58bc-42c3-bd8b-0448e33ce109`
completed; both results were verified, durably acknowledged with delivery complete,
and each retained one attempt. Actual browser reload recovered identical IDs,
results and attempt counts through GET only. No page errors occurred. Private
artifacts: `browser/success-2/` (reviews, decisions, results, reload, network and
screenshots); the earlier refused preparation remains under `success-1/`.

| Member | Operation | Actual usage | Verified native result |
|---|---|---|---|
| Local ARM64 | `f7370611-b8a6-494b-b711-a2422dcf3213` | 38.201s,966 tokens,2 inference calls,1 native MCP | 192.0.2.0/26:64 total,62 usable |
| Cloud AMD64 | `28828be1-e627-4e78-81a1-f183001ff37f` | 91.301s,965 tokens,2 inference calls,1 native MCP | 2001:db8:1234::/48:1208925819614629174706176 addresses,65536 /64 subnets |

Both records report zero provider API charges; cloud compute/transfer remain
separate. Observed model memory was approximately1.52GiB of2GiB on each host;
agent observations remained below their1.5GiB limits. Exact cgroup/OOM/unload
checks are recorded separately from these signed samples. The local model again
incorrectly said64usable addresses. Its original commentary remains explicitly
unverified; the browser displays independently verified62usable tool facts.
No prompt retuning or repeated call was used to mask the discrepancy.

During these exact live operation windows, TCP probes executed in both actual
agent containers with their real UID/network namespace. Each reached its own
relay8090 positive control and was denied direct model/service ports and model
loopback11434. Probes sent zero application bytes and generated no inference.
Further host broker, Border, sibling and external vantages remain separate.


### Actual isolation, resource limits and unload

T026 aggregate `fault-recovery-v1/T026-scoped-aggregate.json`, SHA256
`dfde2eb6fa206a2672cece70dc19238f7452e960a290cf4fe3a3f09be267c326`,
correlates both real operation agents with the actual broker, Border and sibling
service UIDs/network contexts. The agent probes ran inside their exact live
containers; the host probes were additional processes in the measured service
contexts. Both owned model targets were denied. The Mac provided one external
vantage to the cloud member; it is also the local host, not an independent
Internet provider or proof of universal network inaccessibility. Trusted host
Docker administration is outside this TCP-denial claim. No probe sent inference
requests; TCP probes sent zero application bytes.

A broad Mac loopback negative expectation reached an unrelated existing Homebrew
Ollama process, PID1460, started November4. The original failed expectation is
retained. A bounded diagnostic confirmed the owned R05 model address was denied
and identified the unrelated socket owner. No existing host service changed.

Both actual model cgroups reported `memory.max=2147483648`, `memory.swap.max=0`,
zero `oom`/`oom_kill`, and Docker `OOMKilled=false`. Admitted guard-UID reads of
`/api/version` and `/api/ps` succeeded; each model was observed unloaded with
`models=[]`. This establishes eventual unload at the recorded times, not an exact
measurement of the configured30s/local or120s/cloud idle interval. Per-request
agent/model CPU and memory samples and positive token accounting remain in the
signed combined results. Detailed receipts are under `actual-role-probes/`.


### Actual Mac VS Code success and reopen

Native Code1.145.0 used the retained qualification profile and source extension,
without replacing the normal installed extension or owner profile. Parent
`92c64dd7-a257-4159-9f57-a9c2fa80113a` completed after separate native review/approval
dialogs. Local child `d8f2c942-412d-4b13-b68e-ab8b03039bc9` recorded40.346s; cloud
child `6a7ba9d9-2cde-4c87-a474-8f322b014579` recorded83.308s. Each used two model
calls/one native MCP, zero provider API charge, one attempt, verified result and
durable ACK with no pending delivery. Actual dedicated Code restart and native
GET-only recovery preserved the same children, result digests and counts. The
complete native screenshot displays authoritative facts and unverified model
commentary. Private receipts: `native-acceptance/editor/success-completed-pair.json`
and `success-recover-evidence/result-1793913222222.json`.

Test-driver assumptions required corrections: the full remote HUD legitimately
allows an owner binding while local-management commands remain refused; virtual
review/result documents render asynchronously. Original pre-decision failures
created no approval or effect. The expired first parent
`82376155-d510-4f77-b5d5-31c90aae57b9` was cancelled, archived and removed from the
native reference UI with both attempts0 before preparing the fresh pair. A later
stale result screenshot was corrected by waiting for actual terminal rendering;
the successful operations were recovered, never reapproved. Test-only changes
are `eb92add9`, `9e23208e`, `38560ecc` and `ce1f5f6a`. The required live sibling
failure case remains separate from this success/reopen proof.


### Disposable retirement and installed48-hour cleanup schedule

After verified Docker inspect/log export and1270 original artifact hashes,17
stopped prior qualification/fixture/proof/inspection containers and6 empty owned
networks were removed by exact IDs. Each had a fresh identity/stopped/empty check
and its own claim/receipt. No force, pruning, image/volume/private-home deletion
or active-workload change occurred. All12 other existing local containers at that
snapshot, including intended model/peer and current delivery operations, remained.
Receipt `disposable-retirement-preparation-v1/retirement/retirement-receipt.json`
SHA256 `e150665cd8037f35ba8f4f9f3096070d3d3cf969d3ca4a8ec729ec95e11fbaba`;
actual post-inventories and original failed-attempt artifacts remain private.

The coordinator reviewed and installed the existing-authorized48-hour cleanup
job at21:18:49Z. Actual launchd inspection confirmed the new label
`com.netclaw.r05-retire-48h` installed and not running; cleanup has not begun.
Execution manifest SHA256
`c682bea6a853ddb5d63faa58eecf94e4f6c8e0526e6913ac62983d8ed5baafba` binds the
helpers, exact saved destroy plan, unchanged original state lineage/serial3,
SSH commands, frozen Python and module/configuration. No cloud scheduler, IAM,
credential or other cloud resource was added.

The job starts quiescence/export on **November7 at19:36:25UTC /14:36:25 Toronto**,
stopping only the two intended R05 member services and their exact owned
operation/model containers. It preserves private homes and unknown records and
requires verified consistent SQLite/artifact exports before deletion. At or after
**19:41:25UTC /14:41:25 Toronto**, it applies saved destroy plan
`6b0d31a82f705bfcd0a2426f1757338d6782e73790522d76351d072d0bdc0716` once:
10 owned resources, including reserved IP and both connectivity rules; the
40GiB boot disk has verified autoDelete and separate post-delete inventory checks.
R01 configuration/IDs must remain unchanged. The exact installed packet and
future receipts live under `retained-teardown/`.

This is a scheduled action, **not completed cloud cleanup**. The Mac must be
awake, logged in and online, with Docker and existing gcloud/IAP access working.
A missed start, failed export or unknown apply is retained and never automatically
replayed. Independent GCE STOP still bounds VM runtime at19:41:25UTC, but leaves
disk/IP charges if cleanup cannot finish. The CAD5.472448 figure is the reviewed
48-hour estimate excluding existing R01, tax and transfer, not observed billing.


### Browser lost-response and unknown-sibling drill

Actual Chrome preparation reached the Border once; the test deliberately dropped
that HTTP response after retaining it privately. The browser had saved its nonce
before submission and recovered the same parent/children by GET. Parent
`fdbad6d6-19f7-4934-98c5-a1e0cf4d7938` then approved local IPv4 separately and
retained its verified result (`55d6bf8a-a511-47fe-adfc-90364c3f16d6`, one attempt).

Only after that success, the exact idle cloud model was paused briefly and its
existing IPv6 review approved once. The actual outcome was **unknown**, not the
anticipated signed refusal: child `6dfe48bb-2a46-4cba-92ba-a7c8eef95f5b`, attempt
`bc2faf51-f5eb-4be1-887f-d4a4a47716e6`, retained `effect_outcome_unknown` with no
receipt or ACK. The original driver's partial-state assertion failed and remains
recorded. No success, failure receipt or acknowledgement was fabricated.

The reviewed helper unpaused the same model in its finalization path after14.474s.
Read-only settlement confirmed effect_claimed/effect_finished0, no provider DB,
inference row, native-tool artifact or operation container for that child, and
empty owned cleanup. Original model PID/start/namespace/nft/profile and idle
runner latch were unchanged. The cloud's four inference rows still belonged
only to the prior browser/editor successful calls. The exact unknown row and
artifacts remained unchanged under an additional live preflight.

A separate actual browser recovery used the captured pre-submit nonce, displayed
the retained successful IPv4 facts and unresolved IPv6 outcome, then reloaded.
All observed operation requests were GET; IDs, results, states and attempt counts
were unchanged. Evidence: `browser/fault-1/`,
`browser/fault-1-unknown-recovery/passed.json`, and
`fault-recovery-v1/browser-fault/`. The native ACK-loss case remains protocol-tested;
this live drill loses a client HTTP response and does not claim lost native ACK.
Actual shared worker restart and native fault cases remain to be recorded.

Private fault evidence helpers were corrected before their first timed mutation
to serialize actual SQLite BLOBs as length/SHA256, and full snapshot serialization
was added to read-only preflight. Following the real unknown outcome, later fault
preconditions permit only its exact allowlisted case with original passed
zero-dispatch witness, unchanged full row/artifacts, no effect/provider/inference/
receipt/ACK and continued absence of operation containers. Other unacknowledged
or active states still refuse. This changes qualification-helper preconditions,
not NetClaw authority, runtime policy, unknown state or runner latch.


The first actual read-only handoff baseline exposed a verifier-only defect in the
installed cleanup packet: serialized consistent SQLite backups retained WAL header
bytes, so deserialize-to-memory verification incorrectly requested a missing file.
The original archives/error remain. A narrow correction verifies the exact bytes
through a private0600 immutable read-only SQLite file. All23 actual SQLite backups
and2,896 archive entries verified; an actual WAL fixture preserved an unknown row
and rejected corrupt bytes, and the original10 cleanup guards passed.

The coordinator reviewed and applied only this verifier amendment while the job
was confirmed not running and had no workflow/destroy claim. Current armed
execution-manifest SHA256 is
`f76657c05575f5041ce5ab139af7921336e7a52feeb3b69601bd4cd6be9642ff`.
The original `c682bea6...` manifest/helpers/arming receipt are archived under
`retained-teardown-correction-v2/before/`; the correction receipt and successful
read-only readiness check are retained. Saved destroy plan, state, plist,
deadlines and all runtime resources remain unchanged. Actual future cleanup
still requires its own successful export/deletion/residue receipts.


### Actual Mobile partial result and provider fence

Mobile used its retained simulator/bundle/device key. An initial native screenshot
helper followed the old data-container path after an app update; actual WSS
preparation succeeded but visual/report export failed. Read-only Border and both
member checks proved the original parent `f87515ee-1ebd-4abf-9bcc-b678f46224bb`
had no approvals, attempts or member/model effects. Its expired reviews were
cancelled, archived and removed through the native UI; no admission was replayed.
The helper now resolves the current simulator container and writes a durable
private DTO checkpoint before visual export.

Fresh parent `c8fd367b-df61-474f-84e5-1ad91facb608` produced actual signed partial
results: local child `26af6973-0f41-4148-be12-674c351e9485` completed; cloud child
`edba0280-ad5e-48af-8216-cd440595d614` returned verified `executor_failed/finished`
with durable ACK and the correct independently verified IPv6 native tool result.
It is not a complete paired success. The native report and9 result screenshots
are retained, with unchanged device identity.

Separate native test launches/screenshots consumed the review window: cloud start
1793914141537 left82.767s before expiry1793914224304. The first model call completed
with363 tokens, and the native tool ran once. The second call began before expiry
but returned502 at the absolute deadline; its ordinal2 claim has no retained
response. An OpenClaw HTTP retry received403 `approval_expired` without a third
inference claim or provider dispatch. The runner correctly remained **uncertain**
(reservation `d0246951...`), blocking fresh inference. Three operation containers
were stopped, cleanup had no unresolved objects, and original claims/results
remained. Provider uncertainty must not be inferred away from the signed failed
operation or observed stopped agent.

This exposed a missing lifecycle step: NetClaw had verified `RunnerLatch.recover`
but lacked Thermidor's durable idle-only profile rebind after owned model restart
changes the namespace/confinement hash. T017 is reopened for that narrow proven
step and actual recovery. No raw SQLite clearing, substitute latch/database,
replay, deadline relaxation, prompt tuning or paid fallback is authorized. A
native test-driver correction performs the two separately reviewed UI decisions
promptly in one run and defers screenshots; the product still has separate
checkboxes/buttons and no batch-approval endpoint. A fresh success remains gated
on verified owned-model recovery and the new current profile.


The required rebind correction is integrated at `ab475890`, adapting the exact
already-pinned Thermidor ProviderLatch method. It requires idle state after real
recovery, distinct valid old/new profile hashes, exact prior-row/receipt binding
and a host verifier returning literalTrue. The existing SQLite transaction
archives the full prior row and transition receipt atomically; operation,
reservation and recovery fields remain retained. The object's expected profile
changes only after commit. No exposed model/tool API can invoke maintenance.
Thirty new real-SQLite/refusal/rollback cases plus28 existing focused checks passed;
the full root protected/lifecycle suite passed **776 tests**,21 existing warnings,
16.31s (`rebind-integrated-python-tests.log`). Actual owned-model recovery remains
separately gated on the reviewed two-phase packet and observed confinement.

The existing Mobile partial result also passed actual cold/background recovery:
oldPID59818 was terminated and its absence verified; freshPID68842 retained the
same device enrollment/key, then survived XCTest Home/Springboard/foreground with
the same PID and lifecycle events inactive→hidden→paused→hidden→inactive→resumed.
GET-only recovery preserved both attempt1 rows and exact signed/ACKed result
digests. Nine native screenshots and the `.xcresult` are retained under
`native-acceptance/mobile/failure-lifecycle/`. This real signed failed-sibling case
replaces the planned artificial Mobile pause case. It does not close Mobile's
still-required fully successful paired run.

The actual recovery stopped the owned federation worker and model, verified their
original processes were gone, and restarted the same model container. A strict
full nftables comparison refused Docker's changed internal DNS NAT source ports
(TCP32865→40947, UDP60293→50825); the NetClaw table was byte-equivalent. The
original refusal and full before/after witness remain. A separately reviewed
continuation pinned both complete rulesets and the identical NetClaw table,
without repeating stop/start or firewall installation. Real guard-positive,
five-role UID-negative and fresh internal-peer isolation probes passed.

Candidate derivation then exposed a private maintenance-writer defect: its077
umask masked the source file's requested original read mode. Correct source bytes
were installed, but the real member UID could not read the module. This failure
occurred before recovery/rebind or member restart. The exact original mode is
being restored under hash/owner/baseline checks; completed probes are retained,
not repeated. Both failures preserve the original uncertain latch, inference
claims, operation artifacts and keys, with no new model request. Evidence is in
`cloud-runner-recovery-v1/`; neither refusal is counted as successful recovery.

The subsequent actual recovery completed using the original reviewed commit
helper and candidate `07da30506fb257c6a7a8acd58fb53bd7ac8b1fd70e8c4e443c5ac46afa5ddadf`.
Only the original source0444 mode was restored before candidate derivation;
completed stop/start/firewall/probe steps were not repeated. The same cloud model
container has a fresh namespace and verified full policy. New protected-profile
SHA256 is `5129e410a4b41845a9451c4c7cb2a019228f586d5db00977bda05a1edecd5f16`,
runtime revision `8b3723c6d0df9397d84004c40f3086c1711f543832949ea1a9db1721a16f7798`.
An independent real-member-UID review recomputed the revision and verified all303
source files, unchanged identity, tools and limits.

The existing latch recorded recovery `8276d95c3b5f21b522942b937c2aadc0f4543fee4cbe8b64d749d0986bb7d352`
and profile transition `539a3edd1f6a730393e2565b603044aff3f0393df2acf887c9e40213c59ea804`.
It is idle under the new model profile; original ordinal2 remains CLAIMED and its
failed signed result remains unchanged. The complete operations/inference/
artifacts/provider/keys digest was identical before and after:
`e8927cfe35d89f0e51a5181d976d60c6c4b58e4a61d54a9b48bc306ffd65180f`.
The same federation service restarted PID4025→12367 and passed actual factory/
catalog validation. Recovery dispatched zero model requests. Original receipts,
failures, consistent SQLite backups and new durable history are retained in
`cloud-runner-recovery-v1/commit-actual-evidence.tar.gz`; T017 is closed.

The exact scheduler amendment then passed at21:59:36UTC. Its active execution
manifest is `8751f1ff877f0ecf245098550eb28d36f3d6736e29ea29de160cc02788b19437`.
Only the cloud profile pin and export of its newly bound confinement/recovery
proofs changed; the original `f76657c0...` inputs are archived. The installed job
was not running, had no cleanup/destroy claim, and its read-only readiness check
passed. Plan, authoritative state, plist and November7 deadlines are unchanged.
This records an armed future cleanup, not completed deletion or a hard spend cap.
