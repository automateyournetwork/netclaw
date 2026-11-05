# R05 native acceptance driver

This uses the existing Spec174 native editor and Spec175 retained simulator
mechanisms. It is preparation tooling; no live acceptance is implied by source
analysis. Actual approvals require separately reviewed current child JSON.

## Retained bindings inspected on 2026-11-05

- Normal Code: 1.145.0, installed NetClaw 1.6.1, active window `netclaw`.
  Its profile ID is `13d71cca-8cd6-4dc2-b3eb-10b0c76b4311`.
- Dedicated Spec175 user data: `~/.local/share/netclaw/r04b-code-user` (0700).
  Cloud profile `35e11637-94e6-4b1b-8642-e400e42cdb20` pins installation
  `b164621c-a94e-4c28-a087-d9c9dabcce21` at the retained R01 HTTPS pilot.
  The normal owner editor is separate; this driver never installs into it.
- Owned iPhone17 Pro / iOS26.5 simulator:
  `3CB6BF8C-D775-4194-B62A-561D788C65DC`, currently **Shutdown**.
  Bundle `ca.automateyournetwork.qualification.netclawR04bQualification` retains
  its Keychain and Documents. Do not uninstall or replace its bundle identifier.
- Native harness: `~/.local/share/netclaw/roadmap-r04b-20261104/native-client`.
  Its package dependency still targets the historical `netclaw-r04b-mobile`
  checkout; synchronize the selected integrated source before building.

## Editor

Build the selected extension with qualified Node24 before running. Create a fresh
private evidence directory and a 0600 config; keep the old user-data directory.
From `extensions/netclaw-vscode`:

```sh
NETCLAW_CLOUD_SCENARIO=combined \
NETCLAW_CLOUD_CONFIG=/absolute/private/r05/editor-prepare.json \
NETCLAW_CLOUD_EDITOR_PROFILE=/absolute/private/r05/editor-evidence \
NETCLAW_CLOUD_EDITOR_USER=/Users/john.capobianco/.local/share/netclaw/r04b-code-user \
VSCODE_EXECUTABLE='/Applications/Visual Studio Code.app/Contents/MacOS/Code' \
NETCLAW_TEST_PLAYWRIGHT=/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/helper-package-v2/node_modules/playwright-core \
/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node scripts/cloud-editor.mjs
```

The runner launches only its owned qualification editor. It preserves existing
settings, selects the retained cloud profile, and closes that qualification editor
when done. Do not run it while another process owns that dedicated user-data path.
Normal-editor extension activation remains a separately coordinated step.

Common config: `mode`, `origin`, `installationId`, exact `principal`, optionally
`profile_id`. This uses current open-lab Name+URL access; no ticket or cookie.

- `prepare`: exact two `children` catalog selections `{family, member_id,
  profile_revision, cidr}` ordered4/6, and a fresh `claim_file` in a0700 directory.
  It selects native dropdowns, exports both reviews, and chooses Keep for recovery.
- `decision`: previously exported/independently inspected `combined` DTO,
  `child_index`0or1, `decision`approve/deny, and a new `claim_file`. Exactly one
  native child review/modal/button is used; the other child remains separate.
- `recover`: saved `combined` DTO; only status/recovery is used. Optional
  `expected_states` bounds observation of complete/partial/failed/unknown outcomes.
  `preserve_effects:true` compares attempt counts and receipt/ACK fields across an
  actual editor restart. Never create a new claim to repeat an uncertain decision.

Capture backend provider/MCP/effect counters independently before/after every
phase. Screenshots and JSON are private0600 evidence. A failure to export evidence
is not proof that a decision was unsubmitted; retain its claim and references.

## Mobile

Reuse `mobile_qr_test.dart`, `mobile_qr_driver.dart`, and the existing test-only
native plugin from Spec175. Copy the updated integration test into the retained
harness; repoint only its source path dependency to the integrated Mobile package,
run `flutter pub get --offline`, and build under the same simulator bundle ID.
Do not copy or regenerate a device key, re-enroll, clear Keychain or uninstall.

After coordinated simulator boot/source activation, run from the existing harness:

```sh
NETCLAW_NATIVE_REPORT=/absolute/private/r05/mobile-prepare.json \
/opt/homebrew/bin/flutter drive --keep-app-running \
  --driver=test_driver/mobile_qr_driver.dart \
  --target=integration_test/mobile_qr_test.dart \
  -d 3CB6BF8C-D775-4194-B62A-561D788C65DC
```

Supply the fresh private configuration atomically in the retained app's
`Documents/r04b-qualification.json`, as in Spec175. Discover its current data
container with `xcrun simctl get_app_container <UDID> <bundle> data`. The harness
reads/deletes the configuration before network work; never embed it in source,
Dart defines, command arguments or build assets.

Common fields: `phase`, retained enrollment `profile` (`cloud-hud` or
`cloud-vscode`), `installation_id`. Existing completed single-operation references
are preserved; explicitly archive their evidence and use the existing Remove
resolved reference UI before preparing a pair if one occupies this profile.

- `combined-prepare`: exact catalog `children`, same shape as Editor. It only
  prepares, displays both reviews and exports their IDs/review digests.
  Optional `archive_resolved_reference` pins the existing completed single
  operation's `operation_id`, `review_digest`, and `result_digest`. The driver
  requires its verified durable ACK, flushes a fresh private archive, then uses
  the existing Remove resolved reference button. It preserves the archive in
  its report; pending or changed work is never removed.
- `combined-decision`: inspected `combined` DTO, one `child_index`, one `decision`.
  Native checkbox and child button are distinct for each approval.
- `combined-recover`: exact saved `combined` DTO; status-only, including after
  real app termination/relaunch. `preserve_effects:true` checks attempts/receipts.
- `expected_states` optionally waits up to3minutes using status reads only. Include
  `partial`/`unknown` for an independently controlled failure scenario; this driver
  does not induce failures or alter backend/model processes.

Existing `visual_evidence`/`visual_label` handshake is unchanged. Reuse
`~/.local/share/netclaw/roadmap-r04b-20261104/success-verification-20261105/capture-native-visual.py`
with fresh R05 output/handshake paths. Record actual OS restart separately and
compare server counters. The harness exports combined state, retained refs,
uncertainty, same-key reconnect and per-child evidence; no automatic retries.

## Proven cloud source synchronization

Read `specs/175-cloud-mobile-enrollment/deployment.md` and the preserved private
`~/.local/share/netclaw/roadmap-r04b-20261104/deployment/` helpers:
`prepare-packages.py`, `cloud-update.py`, `cloud-transport.py`, `settle-cloud.py`.
These are **spent historical packets**, not scripts to replay. Reuse their design
in a fresh R05 packet: capture current authority/identity/services/hashes; freeze
exact source closure and HUD assets; create a new one-use claim; stop only owned
owner federation/HUD; preserve source and consistent database evidence; install;
validate role/source manifests; start once; compare unchanged keys, historical
rows and unrelated services. Never restore an old database. Spec175's Caddy
restart was for adding `/mobile/ws`; R05 does not need an ingress change merely to
add calculator methods. Its prior timestamp post-check failure required read-only
settlement, not another apply. Preserve that lesson in the fresh packet.
