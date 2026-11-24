# Spec200 setup and qualification quickstart

Five real-snapshot Google Genie 4 recordings are delivered and the owner accepted
recorded illustrations with documented visual/event limits. Begin with the
[installation guide](../../docs/GENIE-WORLDS.md) for terminal, Risk and VS Code
setup. The existing Border owns its Genie member; setup does not create a second
Border or authorize paid generation. See [integration closeout](integration-closeout.md)
for current tests and remaining qualification, and [production recordings](production-recordings.md)
for media, provenance, terminal receipts and retained billing reservations.

The two source campaigns (32 historical passes, then 50 world-suite passes) are
complete and stopped. Do not restart a loop or replay a production packet.
The commands below exercise the offline source; later historical paid-packet
notes describe the original investigation, not current spending authority.

## 1. Exercise the implemented offline source

Run from this checkout with the explicitly qualified Node. Dependencies are
isolated in `scripts/genie-worlds/`; no existing runtime upgrade is needed.

```bash
cd /Users/john.capobianco/netclaw-spec200-genie
SPEC200_NODE=/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node
bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
umask 077
mkdir -p .spec200-local/tests
NETCLAW_TEST_TMP="$PWD/.spec200-local/tests" \
NETCLAW_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
"$SPEC200_NODE" --test --test-concurrency=1 tests/genie-worlds/*.test.mjs
```

These tests use synthetic inputs and intercepted provider transport, with no paid
request. Browser tests explicitly skip if the executable environment variable is
absent. Preserve prior failed runs; a later pass does not erase their limits.

For the standalone video transport fixture, choose an unused owned private root:

```bash
NETCLAW_GENIE_STATE_DIR="$PWD/.spec200-local/manual-fixture" \
"$SPEC200_NODE" scripts/genie-worlds/cli.mjs serve
```

Open the printed loopback bootstrap URL privately within 60 seconds. Review and
start the fixture; focus the canvas for WASD/arrows, capture checkpoints, mark the
fictional target visible before its event, then stop. This plays deterministic
JPEG media, not Google generation. Ctrl-C closes the manager. Do not remove a
stale lock or choose a new root to evade an existing unknown live operation.
Use the same root and original operation ID for the implemented `status`,
`evidence` and `stop` CLI commands while its manager is running.

The rejected local SVG/3D pages and graph-serving route have been removed. The
old preview on port 58778 is retired. Only the provider-media transport viewer
remains; its fixture is a test harness, not an accepted world. See
[direction-correction.md](direction-correction.md) for realistic/fantasy acceptance
and the exact pyATS command list. Five actual Google recordings are now available; see production-recordings.md.

## 2. Qualify collection separately, offline first

Python unit regression (no device requests):

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python \
  -m unittest discover -s tests/genie-worlds -p '*_test.py' -v
```

The selected-runtime operator CLI is `scripts/genie-worlds/collection_request.py`.
Use the [installation guide](../../docs/GENIE-WORLDS.md#bounded-local-collection)
and [collector contract](contracts/collector.md) for the private pinned capability,
per-device dotenv references and exact invocation. It binds runtime, native read
policy, source hashes, inventory/endpoints and saved strict SSH trust. Detailed
collection performs six fixed reads per device, up to four devices and two workers.

Two actual four-device runs passed24/24, including the final dotenv-backed source.
Exactly one requested show command occurred per capture, with no setup/configuration
commands; hashes, parsing and cleanup verified. The original request is durable
and non-replaying. Raw output and normalized facts stay private. See
[final qualification](final-qualification.md). A new collection is an explicit
operator action; these instructions do not change devices or expand the profile.

## 3. Historical qualification packet notes (superseded by production evidence)

Select repository-supported Node (default25.3.0 is not the qualified choice),
pinned SDK3.6.1 lockfile and source hashes. Verify media decoding,recording codec,
no-retry transport and stop/terminal semantics with recorded fixtures.

The previous packet used `synthetic-museum-v1` (now transport-test input only): two blue routing halls,two amber switching
rooms,three declared corridors; one `north-corridor-dim-v1` event. Exact prompt
is [synthetic-world-prompt.txt](synthetic-world-prompt.txt). Text only; no private
source files or image. Review hash includes model,event and lifecycle policy.

Prepare a fresh realistic synthetic projection/packet first, then a separately
reviewed fantasy projection. The old source manifest is stale after renderer removal.

Later live prerequisites:

- Privately configured selected-installation Google paid-tier API credential;
  report presence/account-access outcome without revealing the value. A Project
  Genie browser subscription does not establish API access.
- Fresh official price/service-duration record and finite allowance. Proposed:
  one20s target session,30s local stop deadline,US$15 reserved against documented
  maximum120s exposure plus bounded input/text margin. This is not a hard cap.
- Exact local review covering uncertain stop/usage,no automatic retry,recording
  and evidence retention. No new paid account,cloud activation or private upload.
- Network/worker health and owner present at viewer; authenticated local review
  returns a one-use grant. No agent-made approval field.

If entitlement/allowance/finite exposure or lifecycle prerequisites fail, return
`BLOCKED_LIVE`. Keep live acceptance open; do not substitute fixture media.
Missing credentials require only a private local path/native entry later, never
secret text in chat. Entitlement checks must not secretly create a billable world.

## 4. Execute one measured demonstration (later)

| Relative time | Intended action | Evidence |
| --- | --- | --- |
| Before send | Consume exact grant,reserve,persist send marker,create once | Hashes,operation,account scope,GAIT |
| First frame within10s | Start recording; baseline view | Timestamped four-structure/three-corridor assessment |
| Frame time+2s to+12s | Move toward northern amber room,turn/look back;>=10s deliberate controls | Key events,viewpoint movement,dropped-frame counts |
| About+12s | Send one fictional corridor-dimming/lamp event while target visible | Event ID/text hash/send timestamp |
| By+17s | Inspect visible change and unchanged structures/connections | Post-event frames,latency,discrepancies |
| By+20s or create-send+30s | Release keys,request complete | Stop intent then provider terminal receipt |
| Next5s | Receive terminal/usage; otherwise one best-effort cancel | Receipt or preserved unknown,never inferred success |
| After stop | Compare three checkpoints,usage and costs; human verdict | AcceptanceRecord + GAIT |

If first-frame delay leaves too little useful time,fail the navigation criterion;
do not extend deadline silently. Stop immediately for contract/privacy/budget
faults. Disconnect does not authorize retry. Recording failure means incomplete
evidence,not a passed demo. A beautiful scene with drift can be storytelling-useful
while failing the network-walkthrough rubric. Retain both observations honestly.

## 5. Real NetClaw skill/MCP acceptance

After useful direct proof,install the thin wrapper and skill into a fresh local
Focused NetClaw through supported setup review,with its own empty home,identity,
workspace,ports and credentials. Select actual harness/provider/model; use only
synthetic context for any hosted agent. Existing owner installations stay intact.
No Border/member/cloud dependency is required.

Discover tools,exercise offline prepare/status/refusals,then perform an actual
agent-driven prepare/start/status/event/stop/evidence workflow under a separately
reviewed live allowance. Human navigation remains in viewer. Record native
agent/tool/session correlation and terminal/usage. A direct API proof or tool
listing does not establish this integration. Run relevant native loss drills
without consuming unreviewed extra generation attempts.

## 6. Close with evidence, not checkmarks

Use SC-001–010 and the quality checklist. Keep failures and unsupported platforms
visible. Owner reviews GO/NO_GO/BLOCKED_LIVE. No100% integration claim without
actual world,collector and native skill/MCP evidence. No release implied.
After accepted feasible200,return to unfinished198,then199AWS. A no-go requires
an explicit decision about ending the investigation; do not quietly redefine it.

## Admission and handoff status

Actual collector, fresh isolated installation, Border enrollment and Google-backed
member qualification are recorded in [final qualification](final-qualification.md).
The owner accepted the recorded-illustration scope and directed completion/merge.
Final source verification precedes merge; original198 follows afterward.

Do not replay the spent production packets or member trial. Their source closures
are historical evidence and later fixes make them stale. All seven full bounds
remain reserved under the US$100 cap; another standard trial cannot fit. The member
currently reads its original operation through `evidence-serve`, which has no
Google credential and refuses all mutations and live WebSockets. See the
[installation guide](../../docs/GENIE-WORLDS.md) for this read-only command.

Mac prototype qualification does not imply production member confinement or
Windows/WSL/Mobile live qualification. No Marketplace, tag, site or announcement
publication follows automatically from this source merge.
