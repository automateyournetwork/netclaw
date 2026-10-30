# Spec162 verification

## Current status

Source implementation and **five explicit Ralph review/fix/test iterations are
complete**. Source version **1.15.0**, extension source **1.5.0**; both remain
unpublished. **41 of 44 tasks are checked**; T034–T036 are open live qualification gates. No real NetConverter job,
image-backed target creation or configuration application is claimed. The owner
signed up for a free account and is waiting for enablement/API key; account
permissions must be discovered when it becomes available.

## Initial planning evidence (historical)

- Owner chose exact-file approval before each hosted submission.
- Owner chose actual creation and testing of virtual migration targets wherever feasible.
- Public upstream research pinned Terminal source `ef28f5613a5f014dca7e8b2e38b8219cb461559f` and PyPI 0.5.0 metadata; see research.md for provenance and limits.
- Three read-only Spec Kit research agents examined transport/approval, installer integration and lab/configuration paths. No live calls, source implementation or credentials were performed by those agents.
- Before Docker startup, the selected daemon socket was unavailable. Later live discovery below supersedes this observation.
- Connected NetClaw read-only inventory request failed with MCP internal error and no job ID. Remote lab availability remains unknown.
- No local NetConverter executable on PATH; bounded repository environment-name checks found no relevant account/lab settings. No credential values read.
- Startup pyATS inventory initially failed. Later direct local MCP discovery below succeeded.

## Open live qualification prerequisites

| Gate | Status | Needed evidence |
|---|---|---|
| NetConverter enabled account and licensed client | Signup complete; account activation/key pending | Operator-provided enabled connection and accepted license; no credentials in chat |
| Exact synthetic transfer approval | Not requested | Concrete file/hash/destination/operation prepared before approval |
| Compatible lab host and actual target image | Unknown | Host/platform, architecture/capacity, installed licensed OS image and management/bootstrap |
| Protected artifact apply route | Source/control fixtures implemented; live runtime policy/vendor acceptance pending | Existing workflow extension and proof that original tool denials still apply |
| Real vendor-target migration rehearsal | Not run | Boot, authorized import/readback and actual assertion evidence |
| Windows/WSL and harness-specific acceptance | Not run | Actual isolated platform observations; no inference from Mac/fixtures |

Owner supplied the local CML environment. Target image/licensing and CML trust/access remain unresolved; account signup is complete and enablement is pending. These gates stay distinct from source checks and must not become fabricated passes.

## Implementation evidence

`python3 -m unittest discover -s tests/netconverter -p test_core.py`: 10 tests passed on Python 3.14.6, after first recording the expected missing-module failure. Tests cover metadata-only results, exact digest/expiry, eight competing claims with one winner, restart unknown state, changed source/snapshot/capability/key/account/executable, receipt integrity, connection-bound jobs, path/link/FIFO/size/no-clobber boundaries and unsupported operations. These are synthetic local boundary tests, not upstream conversion acceptance. Runtime Python 3.12 qualification follows.

## Live local-lab discovery after Docker startup

- Linux ARM64 Docker daemon: 14 CPUs, 8,318,976,000 bytes memory; existing containers preserved.
- Existing local pyATS HTTP MCP: official SDK handshake, 34 tools discovered, `pyats_list_devices` successful.
- Existing four-port SSH relay configuration maps exactly to the owner-identified local device addresses. No testbed edit or active-inventory replacement was needed; DevNet sandbox endpoints were not used.
- `pyats_run_show_command_multi` / `show version`: requested 4, success 4, failed 0. R1/R2/SW1/SW2 hostnames matched; version 17.18.2, distinct routing and L2 IOL images. This establishes live source identity only.
- Raw show output and private addressing remain in ignored local memory. No running configuration was uploaded, no device/lab configuration was changed.
- CML native reachability succeeds; browser HTTPS reports an untrusted certificate. Installed Junos images have not been enumerated.
- Native LAN reachability and Python socket reachability differ on this Mac. Do not infer host downtime from Python's `No route to host`; the existing native relay is functional.

Preferred live scenario: [IOS-XE→JunOS OSPF reference](reference-ospf.md). Account/image/control prerequisites remain open.

Planning verification: 44 sequential unique tasks; 19 FR and 6 SC mapped; all local documentation links and whitespace checks passed. Three design refinements resolved (collector tool specificity, candidate capability issuer/consumer, story priority consistency). This was the T001/T002 checkpoint before implementation; the current task tracker supersedes that historical state.

## Initial implementation checks (before Ralph rounds)

| Check | Actual result and scope |
|---|---|
| Feature suite, isolated Python 3.12.12 / official SDK 2.3.0 / FastMCP 4.0.11 | **47 passed**, 20.165s. Private capture, disclosure grants, real controlled stdio/HTTP peer transport, explicit job association/budget, API signer → Python apply consumer, private collection including fixed Junos command, native PTY settings/approval, rehearsal ownership, Batfish coverage and composition. |
| Managed pinned pyATS / actual schema runtime | **6 passed**, 15.527s. Same 35 tool identities, additive artifact arguments, actual builder/validation and process-bound receipt. Synthetic inventory; no device calls. |
| Setup regression family | **272 run; 240 passed, 32 skipped**, 35.217s. No skipped live stage is a pass. |
| Existing pyATS bridge/recovery | **15 passed**, 3.31s, isolated pytest runtime. Initial invocation with system Python lacked pytest; corrected by using the existing isolated runtime. |
| VS Code full suite | **152 run; 149 passed, 3 skipped**, 27.997s on Node 24.19.0. Subsequent new actual-wizard picker/cancel test: focused **3 passed**. |
| HUD unit suite | **383 passed**, 4.943s. |
| Terminal policy and execution suites | PASS, existing local API/HTTP/idempotency tests, no live Gateway. |
| New migration UI | PASS, real JSX in JSDOM: local file upload, hash display, process/profile review, decline and metadata-only parent state. Not desktop acceptance. |
| HUD production build | PASS; existing large-bundle warning remains. |
| Catalog | PASS: 111 components, 238 skills, 125 registered + 52 external integrations = 177. |
| Skill validator | PASS for adapted skill; original archive retained with matching SHA-256. |
| Native controlling-terminal tests | **2 passed**: both settings modes/cancel/preservation and synthetic exact-digest approval/decline. No real disclosure grant or upload. |
| Desktop automation | CUA failed to start its native pipe. No visual desktop acceptance claimed. |
| Broad MCP reconciliation | Catalog/docs/portability/package/ID checks pass. Dependency/startup checks fail on pre-existing owner checkout/runtime dependencies (including untracked HumanRail clone and missing optional modules/entrypoints). Owner installations were not changed to make this scan pass. |

### Choreography and skill decision checks

The controlled CML-shaped peer received actual official-SDK discover → create →
add-node → start → inspect calls. A second case accepted creation then lost its
response; the harness discovered the exact run/attempt ownership and continued
without a duplicate create. This is a manually selected choreography exercised
through real MCP transport, not an autonomous LLM evaluation or a real lab.

Manual execution-decision review against the current skill/reference contracts:

| Fixture condition | Required decision checked |
|---|---|
| Eligible synthetic image, capacity, scoped bootstrap and ownership | Create/boot/inspect using discovered names; keep candidate out of creation arguments. Actual controlled choreography tests pass. |
| CML definition only, EVE template only, or no remote file staging | Stop eligibility/apply at the missing image/bootstrap/transfer evidence; never invent an image or path. |
| FRR requested as native conversion target | Qualify actual vendor direction; unsupported path is refused by the capability tests. FRR peer use does not become target acceptance. |
| Original configuration route denies/loses response | Private apply result stays unknown; no alternate tool and no replay (actual consumer tests). |
| Deliberately failed negative traffic assertion; Jev disabled | Failed and blocked entries survive the composed local review package; no external provider/ticket call. |

### Private application limits

The real JavaScript API issuer and Python consumer are tested together. Original
configuration-tool identity/annotations remain; no new apply alias or grant tool
is registered. Controlled original-tool denial is verified. Real OpenClaw broker
policy acceptance and a live Junos commit/readback remain live qualification.
Junos set-format collection/application are implemented at the existing identities;
installed Unicon source has commit behavior, but source inspection is not device
acceptance. Cached, ambiguous/proxy/console routes are refused. One candidate/one
endpoint per request; Hermes Local/Lab and production artifact grants unavailable.
Same-OS-user filesystem trust is explicit in the contract and guide.

Source compilation and controlled tests do not make T034–T036 complete. No existing
lab, source device, licensed client, account or provider configuration was mutated.

## Final implementation reconciliation

The final feature suite ran **61 tests, all passed, in 29.700 seconds** on isolated
Python 3.12.12, official MCP SDK 2.3.0 and FastMCP 4.0.11. Run with
`NETCLAW_TEST_NODE=/absolute/node24 /absolute/isolated/python -m unittest discover -s tests/netconverter -p 'test_*.py' -q`.
These are controlled fixtures/SDK transports, not service or appliance acceptance.

| Final check | Actual result |
|---|---|
| API-issued private apply/collection | 16 passed; current endpoint/policy/baseline checks, Junos separator refusal, private initialization/logging, post-write storage fault and cancellation guard retention |
| Real JSX migration UI | PASS in JSDOM; target/mode/profile changes and late file responses invalidate old review |
| Actual managed pyATS runtime/schema | 6 passed, 12.666s; preserved 35 identities, synthetic inventory only |
| Extension 1.5.0 source | TypeScript check and build PASS; 3 focused native-picker/validation tests PASS |
| HUD build after UI fixes | PASS; existing large-bundle warning |
| Setup deployment/effect audit | 7 passed, 0.546s |
| Catalog metadata and declaration reconciliation | PASS: 111 components, 238 skills, 177 integrations; counts and registration portability consistent |
| Website draft | Content generation PASS; Astro check 99 files, zero errors/warnings/hints; draft absent from generated posts and search |
| Provenance/privacy/whitespace | Supplied archive hash matches; new-source private-environment scan and `git diff --check` PASS |

Full initial installer/HUD/extension/bridge results above remain scoped evidence;
unchanged passing suites were not mechanically rerun. The broad owner-runtime
reconciliation failure remains visible and was not relabeled as a pass.

### Requirements and practical limits

| Requirements | Implemented evidence | Remaining qualification |
|---|---|---|
| FR-001–003 | Catalog/installers, guarded registration, fixed modes and isolated SDK transport | Licensed client, real account permissions, native desktop/platform pass (T034) |
| FR-004–005 | Adapted skill/provenance and explicit role/class/text capability tests | Actual account direction/limits; archives and legacy incomplete metadata unavailable |
| FR-006–009, FR-017 | Exact native review, durable single-use attempts, binding/integrity/unknown cases, restricted read surface | Concrete real file approval and upstream job (T035); advanced draft mutations unavailable |
| FR-010–013 | Private pyATS collector, composition contracts, actual controlled CML choreography, ownership ledger, OSPF topology/matrix/local ticket template | Actual licensed target, bootstrap/access, live broker permission and configuration/behavior acceptance (T035–T036) |
| FR-014–016 | 61 controlled feature tests, broader regressions, five recorded iterations, docs and staged article | Live acceptance remains separate; source work is not 100% overall qualification |
| FR-018–019 | Actual JS issuer/Python consumer, original tool identity, guarded cancellation and Batfish failure/coverage tests | Real runtime policy, Junos commit/readback and forwarding evidence; no universal equivalence claim |

SC-001/002/004 have controlled evidence; their real account/native UI scope remains
open. SC-003 has explicit source/lab handoff limits. SC-005 has all five recorded
iterations. SC-006 is **not satisfied by fixtures**: no image-backed target has
been created or behavior-tested in this run.

An authored [synthetic IOS-XE OSPF input](examples/README.md) is staged for later
capability qualification and exact-file review. It has not been uploaded/applied
and does not establish the existing routers' protocol state.

### Resume the live reference

1. The operator stores the enabled key through the selected private setup flow
   and supplies an installed licensed Terminal. Never paste the key into chat.
2. Discover actual account/router capabilities; prepare a concrete synthetic
   source artifact and request native approval of its exact hash/destination.
   Prior policy choice and signup authorize no transfer.
3. Establish CML trust/access and a compatible licensed Junos router image,
   management/bootstrap path and capacity. Existing source identity reads do not
   supply these facts; no OSPF configuration is assumed.
4. Complete T034–T036: real discovery, real conversion, isolated target boot,
   qualified existing runtime permission, baseline/rollback, reviewed candidate
   apply, actual commit/readback and positive/negative OSPF assertions. Record
   failures and retained resources before revising the staged article's claims.

A matching draft exists in the separate `modern_website` repository at
`content/articles/2026-10-30-netconverter-migration-rehearsals.md` with `draft: true`.
No article, external ticket, source release or Marketplace package was published.

### Local audit and handoff

GAIT session `spec162-netconverterai-20261030` records planning, live read-only
observations, implementation and review milestones, including final source
reconciliation `ca420cff`. Ignored daily memory was appended with the later Docker/
local-pyATS findings, changes, actual results and remaining gates. No external
record was created. Final Git checkpoint and GAIT trail accompany the handoff.
