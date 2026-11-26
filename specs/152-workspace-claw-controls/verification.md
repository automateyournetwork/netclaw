# Spec152 verification — 2026-10-15

WSL follow-up: [real workspace inspection and qualification limits](wsl-verification.md).
The sections below record the earlier Mac acceptance, not the later WSL results.

Implemented on `152-workspace-claw-controls`, based on main `eb5475e`. The owner first
requested an ephemeral preview, then explicitly authorized packaging and pushing the
feature branch with a WSL handoff for real-runtime file inspection. Merge, live
deployment and Marketplace publication remain held. Candidate provenance and installed
artifact results are recorded separately in [handoff/package.json](handoff/package.json)
and [handoff/acceptance.md](handoff/acceptance.md).

## Scope and implementation

All five stories are implemented: top Connections navigation, six native runtime
Markdown files, reviewed save/upload/overwrite without delete/rename, full verified
owned service Start/Stop/Restart, and verified Save & Restart. Native VS Code documents
supply normal typing, Undo, dirty-close and diff review. File bytes stay out of webview
state. Persistent local management bindings preserve offline Start after editor reload.

OpenClaw native agent discovery must agree with the selected HUD context. Hermes
persona files use the actual selected home; its protected HUD companion deliberately
does not load them. Lifecycle covers the qualified gateway/engine, owned HUD/companion
and configured federation, refusing ambiguous or incomplete ownership. Fixed local
operations, target/code fingerprints, revision checks, original backups, phase journals
and observation-only recovery prevent blind replay. Exact manager actions stop native
services at their owning layer; no process-name/port cleanup is exposed.

## Automated evidence

Commands ran from the repository root under Node **24.19.0**, macOS arm64.

| Check | Result |
| --- | --- |
| Extension TypeScript check and production bundle | Pass |
| Final complete extension suite | 84 tests: 83 passed, 1 optional cached-RAG test skipped, 0 failed |
| HUD regression suite | 372 passed, 0 failed |
| Python selected-runtime golden tests | 2 passed |
| MCP catalog coherence | 111 catalog / 124 registered / 52 external; no gaps |
| Actual installed OpenClaw CLI, isolated configuration/workspace | Passed native workspace resolution and file access |
| Actual managed HUD launcher, both runtime fixtures | API + UI start/stop passed; Hermes companion simulated |
| Native launchd KeepAlive fixture | Full Stop stayed stopped; exact Start recovered |
| Owned-runner crash fault | Fresh explicit Stop attributed the orphan child; later Start recovered without touching a neighbor |

Focused tests cover all six files on both runtimes, private originals, exact UTF-8/BOM/
CRLF/Unicode, empty replacement, missing-file exclusive creation, stale revisions,
wrong target, symlinks/hardlinks, unsafe permissions, invalid encoding/size, no-delete
operation dispatch, changed service scope, acknowledgment/replay refusal, no restart
on Save alone or unverified save, current saved revision before restart, and injected
post-write unknown outcomes. Native real processes demonstrate stop/start/restart and
neighbor isolation. HUD discovery rejects unauthenticated/wrong-installation requests.
DOM tests cover inert text, stale/busy message fencing and no draft persistence.
Existing extension assistant, inventory, security, configuration and topology regression
checks remain in the full suite; no assistant management tools were added.

Local raw logs (not committed): `/tmp/netclaw152-extension-final.log`,
`/tmp/netclaw152-hud-tests.log`, `/tmp/netclaw152-catalog.log`.

## Native source editor acceptance

Actual **VS Code 1.102.0**, macOS arm64, normal Extension Development Host with fresh
user-data/extensions directories and private synthetic runtime homes. This uses real
source HUD servers and real owned processes; engines/federation and provider readiness
are simulated. No owner runtime, provider credential, network device or live service
was changed. The test does not run in an extensionTestsPath host that suppresses native
confirmation dialogs.

**35 checks passed**, including:

- Native local binding review and all six entries from the top Connections panel.
- Native read/edit/review/save for each file of each runtime (12 cases).
- Native upload for each file of each runtime with exact BOM/CRLF/Unicode (12 cases).
- Continuous keyboard input focused once, native Undo and dirty-close Cancel.
- Cancelled save preserves disk and the dirty draft.
- Save & Restart verifies bytes before actual full owned-process replacement.
- Stop removes the HUD; offline Start restores the same installation for both runtimes.
- Actual editor reload while stopped preserves the binding and recovers the same claw.

Light, dark and high-contrast screenshots, a real 360-pixel panel and 200% zoom were
inspected. Measured content width/scroll width matched at 360/360, 902/902 and
1232/1232; no horizontal overflow. Final screenshots show top-panel access, service
scope and file rows. Normal editor scrolling exposes the remaining entries.

Source preview metadata: `/tmp/netclaw-spec152-source-preview.json` (later runs replace
this pointer). Source acceptance profile: macOS temporary directory
`netclaw152-editor-v7whGb`; its `report.json`, `preview.json`, `ready.json` and six
screenshots hold the exact build, paths, identity hashes and native observations.
No private runtime contents are committed as evidence. A [synthetic preview screenshot](evidence/mac-synthetic-preview.png) is included.

## Performance and privacy

20 trials per operation per runtime, 256 KiB UTF-8 files. These measure the actual
extension host client/helper and readback with a synthetic native CLI, excluding human
review delay. All 20 read and 20 save trials per runtime completed within two seconds.

| Runtime | Read median / p95 / max | Save including preparation median / p95 / max |
| --- | --- | --- |
| OpenClaw fixture | 102 / 108 / 364 ms | 277 / 286 / 296 ms |
| Hermes fixture | 77 / 79 / 80 ms | 202 / 217 / 217 ms |

A cold invocation of the installed real OpenClaw CLI took approximately **2.9 seconds**
in its isolated native-discovery test. Fixture results do not establish production CLI
latency. Native lifecycle commands immediately enter VS Code progress before awaiting
helper work and use a 120-second helper observation timeout; timeout is unknown, not
cancellation. A sub-second renderer progress SLA was not separately instrumented.

Journals were inspected for raw synthetic content: none found. Audit records contain
identities, paths, revisions and outcomes, while originals/review drafts remain private
on the selected host. Native document text can enter VS Code's own local editor backups
according to operator settings; no universal no-disk-draft claim is made. Hot Exit and
autosave are off in the ephemeral preview. Markdown is shown as source, so it performs
no external image/link loading. Committed artifacts contain code and synthetic evidence,
not real persona/configuration contents.

## Follow-up: cached native agent discovery (T032) — 2026-11-25

GET `/api/hud/management` ran `openclaw agents list --json` on every request. On a fresh WSL2 Ubuntu 24.04 install of v1.18.6, the CLI took about 10 s of local CPU work per call, with no network connections. Every management request, including setup's Tier 3 probe, waited that long (issue #371).

T032 keeps the projected result (`id`, `isDefault`, `workspace`) in HUD memory. The cache is keyed on:
- the CLI file and its signature,
- the launch CWD and HOME,
- `OPENCLAW_HOME`, `OPENCLAW_STATE_DIR`, `OPENCLAW_PROFILE` and `OPENCLAW_CONFIG_PATH`,
- the config file's signature.

Entries are used for at most 10 minutes. Concurrent requests share one run, failed runs are not kept, and a run that started before a config change is not cached under the new key. The CLI invocation is unchanged. Binding still validates the returned workspace, and `expectedWorkspace` is still resolved with `realpath` on every request.

On that claw, three `managementDiscovery` calls in a row with the HUD service's environment and CWD, loading `management.js` from main `3257133` and from this change, gave:

| Source | Call 1 | Call 2 | Call 3 |
| --- | --- | --- | --- |
| main | 11.78 s | 10.00 s | 10.19 s |
| main + T032 | 9.58 s | 0.00 s | 0.00 s |

Limits:
- The first request after start, after a key change or after expiry still pays the full CLI cost.
- The key covers the main config file only. A change made only in a JSON5 include or an env file that the native reader processes can take up to 10 minutes to appear, or until the HUD restarts.



- No live Linux systemd/WSL or Windows-renderer + WSL-host acceptance occurred on this
  Mac. Native Windows helper management is unsupported; use the actual WSL host.
- Full lifecycle refuses unknown/supervised wrappers and unqualified native Hermes
  messaging gateways. It does not silently omit them or install/adopt a service.
- File rename is not universal CAS against uncooperative external writers; coordinate
  them. Revision checks and private originals protect the managed workflow.
- Saved bytes and ready services do not prove new prompt consumption or provider work.
- The owner-requested WSL handoff opens the exact candidate against the real workspace
  for inspection first. It must record its own actual platform/identity evidence.
- The minimum-version native source test and regression suite passed; not every theme
  multiplied by every width/keyboard workflow was independently replayed. Broader live
  performance and the renderer progress SLA remain qualification work, not claimed passes.

See [WSL-HANDOFF.md](WSL-HANDOFF.md) for the copyable continuation prompt and instructions
that preserve the live checkout, normal VS Code profile and current service owners.
