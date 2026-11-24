# Genie network worlds

Cisco pyATS Genie supplies measured facts. Google Genie 4 supplies a navigable,
generated illustration. NetClaw keeps the evidence and its uncertainty separate
from generated geometry. The optional component exposes six MCP controls and the
`netclaw-genie-worlds` workflow skill. It does not configure network devices.

The Mac prototype produced five 120-second recorded walkthroughs from a frozen
four-device snapshot: technical blueprint, living fantasy, network city,
packet-scale machinery and future data center. Generated labels, object counts
and connections can drift. This is useful for network storytelling; it is not a
precise digital twin or packet-forwarding simulation. See the
[production evidence](../specs/200-genie-network-worlds/production-recordings.md) and
[actual collector/member qualification](../specs/200-genie-network-worlds/final-qualification.md).

## Install and configure

In terminal installation, select **Genie Network Worlds** under **Analysis &
Diagrams**, or add it to an existing selected installation:

```bash
./scripts/install.sh --add genie-worlds
./scripts/setup.sh
```

Use the existing runtime selection to target the intended home. The installer
adds an isolated Python 3.12/MCP 2.3.0 control runtime and the locked Node backend
dependencies. Node 24.19.x or 26.1+ is required. It installs no global Python
packages, creates no Google world and starts no service.

Setup saves `NETCLAW_GENIE_CONTROL_FILE`, the path to the backend's private
`mcp-control.json`, and the per-installation `NETCLAW_GENIE_STATE_DIR`. A saved
path or successful tool discovery is not proof that the backend is running.
Keep that control file private: it is a capability, though it is not a Google key.

For a free local transport check, start the backend with a dedicated state root:

```bash
NETCLAW_GENIE_STATE_DIR="/absolute/selected-runtime/genie-worlds" \
  node scripts/genie-worlds/cli.mjs serve
```

Open its one-use loopback URL. This mode is visibly labeled **fixture** and makes
no Google calls. Its pictures are transport test data, not generated-world proof.
The manager creates the control file, which the registered MCP then reads.
The operator may use the viewer's **Review for member start** action to issue
an exact review reference; the MCP itself cannot mint one.

## Paid generation is a separate operator action

The backend owns the Google key in an owner-private credential file. The key is
not a member setting, browser value, prompt or MCP argument. Google Cloud login
alone is not evidence of paid Gemini API entitlement. The source uses the
[documented Genie API](https://aistudio.google.com/docs/genie).

An operator must prepare and review a current live packet that pins the source
closure, projection, private credential reference, shared campaign authority and
finite reservation. The first hosted qualification uses independent fiction.
Private-derived facts need an exact operator-pinned projection grant; changing
device names does not make a topology public. Never upload the raw snapshot.
The packet and launch pins are documented in the
[live review contract](../specs/200-genie-network-worlds/live-review.md) and
[control contract](../specs/200-genie-network-worlds/contracts/control.md).

```bash
# Use the exact operator-reviewed environment and packet, not an old campaign.
node scripts/genie-worlds/cli.mjs live-serve /absolute/private/packet.json
```

`live-serve` refuses missing/stale source and campaign pins. Setup does not create
those approvals. The original Spec200 production packets are spent historical
evidence and must never be replayed. New source changes require a new review.

| MCP control | Purpose |
| --- | --- |
| `genie_world_prepare` | Prepare one registered fixture or private snapshot reference |
| `genie_world_start` | Start once with an existing exact backend review |
| `genie_world_status` | Read the original operation and control outcomes |
| `genie_world_event` | Request the reviewed fictional event after target-visible intent |
| `genie_world_stop` | Request backend-owned termination |
| `genie_world_evidence` | Read bounded provenance and artifact hashes |

Save the request UUID before calling start. A timeout means query the same
operation, not start another one. The backend owns deadlines and connection-loss
handling. Closing the browser or transport does not prove remote termination.
Unknown sessions retain their full reservation. Even a confirmed provider
terminal receipt does not settle charges when usage is missing. Do not switch
keys, accounts or state roots to evade a hold.

## A member in a Risk

The existing **Border owns membership, enrollment, routing and task authority**.
Users ask the Border; the Border delegates to its Genie member. The member's
separate runtime home isolates its execution and settings; it is not a separate
Risk or another Border. The private world backend owns Google sessions and
termination even if the Border, member or browser disconnects.

Choose the optional **genie-worlds** OpenClaw member profile in the Border's Risk
setup plan, or use the explicit
[six-tool member specification](../specs/200-genie-network-worlds/contracts/genie-member.json)
through the supported member setup workflow. That custom specification names its
member `genie-worlds-member`, because built-in profile IDs are reserved as custom
specification names. The profile is offered only with
the workflow skill and configured control-file reference. Actual backend
availability and tool execution are still checked separately.

The member receives only the loopback control capability. It does not receive
device credentials, raw evidence or the Google key. Use a separate backend state
directory per installation; keep the campaign authority shared for related paid
work. The default setup does not enroll or upgrade an existing Risk.

Actual stdio MCP/backend/Google/browser execution is proven. An existing Border
enrolled the new member and routed Sonnet through its skill and actual MCP
prepare/start/status/stop/evidence calls against Google Genie4. A preceding free
fixture qualified the same control path. These member exercises used
OpenClaw2026.10.9/Node24.22.1; the older Border binary was preserved. An actual
Google recording, navigation and original-provider terminal receipt are retained.
Same-user application
boundaries are not OS process confinement. See [Risk setup](N2N-RISK.md).

After generation, retain MCP access to original status/evidence without a Google
key or new creation authority:

```bash
NETCLAW_GENIE_STATE_DIR="/absolute/original-session-state" \
  node scripts/genie-worlds/cli.mjs evidence-serve
```

This mode refuses mutation routes and live WebSocket upgrades. A provider terminal
receipt and provider usage are separate: an earlier timeout reason is retained as
`previous_outcome_reason` after `terminal_confirmed` becomes true. Unsettled costs
keep their full reservations. Cloud Monitoring usage records may provide a
project/model/time correlation; they are not a final invoice or permission to
release reservations.

## Bounded local collection

Collection belongs to the operator's selected pyATS runtime, separately from the
snapshot-only world member. `scripts/genie-worlds/collection_request.py` accepts
a private, SHA256-pinned capability binding that runtime, policy source, inventory,
strict endpoints, per-device credential `.env` references and the fixed `initial`
or `detailed` profile. See the [collector contract](../specs/200-genie-network-worlds/contracts/collector.md)
for its fields; paths and hashes come from reviewed operator metadata, never the
agent. The private per-device files contain only `SPEC200_PYATS_USERNAME`,
`SPEC200_PYATS_PASSWORD` and `SPEC200_PYATS_ENABLE_PASSWORD`.

```bash
# Execute with the selected installation's pyATS Python, not the MCP-only Python.
"$SELECTED_PYATS_PYTHON" -B scripts/genie-worlds/collection_request.py collect \
  --state-root /absolute/private/collection-state \
  --request-id "$ORIGINAL_REQUEST_ID" \
  --capability /absolute/private/collection-capability.json \
  --capability-sha256 "$REVIEWED_CAPABILITY_SHA256"
```

Keep the original request ID. `status --state-root ... --request-id ...` returns
the stored outcome without another device read. The same collect request is also
idempotent; a changed capability conflicts. Unknown collection/cleanup blocks new
admission instead of retrying. Raw and parsed output stays private; the response
contains only source-bound observation metadata. Actual Mac qualification covers
24 reads over R1/R2/SW1/SW2, with no configuration or connection setup commands.

## VS Code, HUD and Mobile

VS Code's reviewed setup wizard reads the canonical source catalog. Select Genie
Network Worlds for a focused claw or the eligible Risk member; generated binding
paths belong to that claw's runtime home. Review and apply through the normal
setup engine. The extension does not store or submit a Google key. A component
card indicates registration/configuration, not paid account readiness.

The HUD has a capability/status card. Navigation and generated media use the
standalone loopback viewer. No embedded editor/HUD world player or Mobile world
controls are introduced. WSL is an installer target; live WSL generation and
native Mobile acceptance are unqualified.

## Record once and host playback

Host exported MP4s and posters as ordinary static assets. Visitors can play,
pause, seek and replay the recorded route without Google API calls. They cannot
choose a new route, trigger another generated event or explore an exported
persistent scene graph. No “explore live” button is required.

The delivered Spec200 captures are silent 720p/24fps videos. Their companion
facts identify the historical snapshot and coverage gaps. The supplied CML
diagram is a reconstruction from the saved export, not a live CML screenshot.
The [website-agent handoff](../specs/200-genie-network-worlds/website-agent-prompt.md)
describes the five styles, factual boundaries and static hosting contract.
