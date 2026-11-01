# Inspect retained traffic with Convergence

This optional integration connects NetClaw to a separately operated Convergence
service. It adds two read-only tools and a traffic view: choose a ranking, select
an address, and inspect retained records from the **same observation window**.
NetClaw does not install a collector, storage stack, IDS or case-management API.

Starting from a fresh Linux machine? Follow the [Ubuntu walkthrough](CONVERGENCE-LINUX.md)
for prerequisites, an isolated synthetic demo, reader installation and a real
OpenClaw gateway chat. Its qualification record distinguishes executed results
from instructions and remaining platform gaps.

## Start with the coverage you have

| Source | What you can inspect |
|---|---|
| Isolated demo | Clearly labeled synthetic traffic; no network equipment or model needed |
| Linux software exporter | Traffic visible on the explicitly selected interface |
| Router or network sensor | Traffic visible at that collection point |

A host interface does not automatically see other devices' traffic. Flow metadata
is not packet IDS, application identification or a threat verdict. Cisco switches,
Proxmox and Kubernetes are not prerequisites for the demo or host path.

## Compatible service and installation

The tested service contract is pinned to
[`byrn-baker/netclaw-convergence` at `f54bafca82f339d8573c55c53795fa05bd9dd843`](https://github.com/byrn-baker/netclaw-convergence/tree/f54bafca82f339d8573c55c53795fa05bd9dd843).
That fork contains the API; the older standalone Convergence repository does not.
There is no assumed stable versioned API: an incompatible response is reported as
a compatibility error instead of being rendered as evidence.

For a new service, follow its [Linux home-lab guide](https://github.com/byrn-baker/netclaw-convergence/blob/f54bafca82f339d8573c55c53795fa05bd9dd843/docs/convergence/home-lab.md).
Use a separate checkout and private bundle. It shows an equipment-free Docker demo,
then an explicit host exporter. The service's [K3s guide](https://github.com/byrn-baker/netclaw-convergence/blob/f54bafca82f339d8573c55c53795fa05bd9dd843/docs/convergence/k3s.md)
is the persistent deployment option. Deployment, retention, upgrades and backups
remain service responsibilities. Keep demo and real observations in separate sites
and bundles. The core service trial collects no flows unless a source is selected.

On the Linux NetClaw host, with Python 3.12+ and your existing OpenClaw installation:

```bash
bash scripts/install.sh --add convergence-read --preflight
bash scripts/install.sh --add convergence-read
```

This installs pinned dependencies in the selected component's isolated interpreter.
It adds to the existing component selection and preserves other runtime credentials.
The connector remains disabled until configured. The IDE catalog does not advertise
macOS/WSL2 qualification for this component; use the Linux CLI path for this milestone.

## Create a read credential

Use a **viewer** API key restricted to the chosen site. The service's generated
`hud.env` currently contains an operator credential: do not reuse that broader key
for this connector. Have the service administrator add a dedicated entry to its
private `API_KEYS` configuration, preserving existing entries, then apply that
configuration through the service's normal lifecycle. Its entry has this shape:

```json
{"id":"netclaw-reader","name":"NetClaw reader","key":"YOUR_RANDOM_PRIVATE_KEY","role":"viewer","sites":["demo"]}
```

For a new disposable demo, add the viewer entry to the private bundle's `compose.env`
before starting it. Generate a random key in your password manager or a private file;
never paste it into chat or commit it. An existing deployment needs its normal
operator-controlled credential update. This integration has no key-creation tool.

## Configure NetClaw

Edit the selected installation's private environment file (the same file used by
its HUD and `component-launch.py`). Preserve unrelated settings. Keep it readable
only by the owning account. Set:

```dotenv
CONVERGENCE_ENABLED=true
CONVERGENCE_API_URL=https://convergence.example.net
CONVERGENCE_API_TOKEN=YOUR_PRIVATE_VIEWER_KEY
CONVERGENCE_SITE=demo
CONVERGENCE_EXPORTERS=127.0.0.1
CONVERGENCE_ALLOW_LOOPBACK_HTTP=false
```

Use the exporter addresses configured by the service; the software demo/host helper
uses `127.0.0.1`. This is the exporter's identity, not an observed endpoint address.
A comma-separated allowlist supports multiple configured exporters. Browser and
MCP arguments cannot override the configured URL, site or credential.

HTTPS verifies certificates. For a same-host Docker trial or local port-forward,
set `CONVERGENCE_API_URL=http://127.0.0.1:4000` (substitute the actual API port) and
explicitly set `CONVERGENCE_ALLOW_LOOPBACK_HTTP=true`. Plain HTTP to a LAN hostname
or non-loopback address is rejected. URLs must be origins, without credentials,
query strings or paths. Redirects are rejected. Do not expose the API publicly just
to connect this view.

After saving settings, project just this component into your selected OpenClaw
configuration. Choose the correct runtime directory; the example is the conventional
single-installation location. The helper preserves unrelated registrations/settings,
backs up changes, and refuses conflicting custom launch commands.

```bash
runtime_home="$HOME/.openclaw"  # replace for a separate installation
python3 scripts/install-mcp-config.py --repo "$PWD" \
  --runtime-root "$runtime_home/python-runtimes" --components convergence-read \
  --output "$runtime_home/convergence-mcp.json" --config "$runtime_home/openclaw.json"
```

Repeat this scoped projection after configuration, upgrade or disable. An initially
disabled registration may contain literal defaults; editing `.env` alone does not
replace those managed defaults with runtime references. The generated file contains
references, not your configured token. Keep it private with the runtime files.

Restart only your selected NetClaw HUD/runtime as normally required for environment
changes. Connect with the installation's normal owned HUD session; there is no
separate browser credential or anonymous bypass for Convergence.

## Verify and inspect

Use the configured runtime environment. If invoking from a shell that does not
already select it, set `NETCLAW_RUNTIME_ENV` to that installation's private `.env`.
From this NetClaw checkout:

```bash
python3 scripts/mcp-call.py \
  "python3 scripts/component-launch.py convergence-read" \
  convergence_flow_summary '{"range":"1h"}'
```

The result is `{ "ok": true, "data": ... }` or a sanitized error with an explicit
code. Successful empty data is distinct from a failed read. In the HUD, open
**Convergence**, select a range, and choose an address. The records request preserves
the returned start/end and exporter selection. No model call is required.

For standalone evidence, copy the summary's exact `start` and `end` values:

```bash
python3 scripts/mcp-call.py \
  "python3 scripts/component-launch.py convergence-read" \
  convergence_flow_evidence \
  '{"address":"192.0.2.10","start":"2026-10-31T00:00:00Z","end":"2026-10-31T01:00:00Z","exporter":"127.0.0.1"}'
```

Those addresses/timestamps are examples, not guaranteed records in your archive.
Allowed summary ranges are `15m`, `1h`, `6h`, `24h`. Evidence intervals must be
ordered and at most 24 hours. Responses are limited to 1 MiB and requests to 20 seconds.
Evidence includes the address as source **or** destination and at most 100 recent
records; it does not reproduce an entire directional ranking total. Coverage and
sampling/duplicate-counting limitations remain visible.

| State | Meaning and next step |
|---|---|
| Disabled | Enable only the intended configured connector; no backend requests occur |
| Not configured | Complete private connection settings or configure a service flow source |
| Empty | No matching retained records in this successful window; try the demo or verify the source |
| Unauthorized | Check the viewer key and site grant with the service administrator |
| Unavailable/timeout | Service could not be read; totals are unknown, not zero |
| Compatibility | The service response does not match the pinned contract |
| Stale cached data | A refresh failed; displayed prior data is labeled stale |

Receipt age is shown separately: quiet traffic alone does not prove a broken
collector. Observed strings are data, never instructions to change the service.

## Ask NetClaw to investigate

After selecting an address and loading its records, choose **Investigate in Canvas**.
NetClaw receives the selected observation, exact window, site/exporter scope, source
coverage and evidence limits. Record samples are bounded and any omissions are
identified. Refresh failed or stale observations before handing them off. The
Convergence panel does not start an autonomous investigation; the normal Canvas
conversation and its permission controls handle the request.

Convergence supplies evidence to NetClaw's coordinating brain, the **Border Claw**.
The Border can correlate it with whichever authorized firewall, IDS, DNS or inventory
tools are available. Missing sources should be reported as gaps. Flow volume alone
does not establish an incident, and opposite flow directions do not prove request
and reply. The latest-100 limit bounds one records response, not the investigation.

A single NetClaw installation can do this without federation. For an existing
OpenClaw [internal Risk](N2N-RISK.md), the `convergence` member profile scopes a
specialist to `convergence-observations` and the existing read connector. Configure
the reader first, then inspect the offered profile using the selected runtime:

```bash
python3 scripts/in2n-profiles.py list
python3 scripts/in2n-profiles.py show convergence
```

Use the Risk's normal member setup/enrollment path; no separate Convergence brain
or new write permission is needed. Each member must use its own private environment.
For an existing Linux OpenClaw Risk with both `n2n` and `convergence-read` installed,
prepare a new member home from the selected Border configuration:

```bash
border_home="$HOME/.openclaw"  # replace with the intended Border installation
member_home="$HOME/.openclaw-example-convergence"  # a new, separate home
NETCLAW_RUNTIME=openclaw OPENCLAW_STATE_DIR="$border_home" \
OPENCLAW_CONFIG_PATH="$border_home/openclaw.json" NETCLAW_RUNTIME_ENV="$border_home/.env" \
python3 scripts/in2n-member-home.py --risk example --member convergence --home "$member_home"
```

This prepares files only; it does not enroll or start the member. It reuses the
selected provider/model, copies only its explicit credential references and the
Convergence settings, and gives the member its own workspace and runtime records.
The member can read its workspace skill and call the two observation tools. The
federation service retains its status/heartbeat/audit base functions. Other Border
skills, communication accounts and memory credentials are not copied. Existing
member homes are preserved rather than overwritten.

Use `--model provider/model` to choose a different declared model or `--provider-env`
to select a private file containing its referenced credentials. OAuth/vault/file/exec
credential providers and custom authentication headers require separate setup; the
helper does not inspect account stores. Set the member's Border endpoint and one-use
enrollment token through the normal Risk enrollment process. Explicit loopback
providers such as local Ollama may omit an API key when they require no authentication;
remote providers must have a configured credential. Then launch with its
private `N2N_MEMBER_ENV_FILE`. The source Risk mode is retained; an absent mode defaults
to production, which must pass the existing controls. Testing mode must be explicit.
The configuration does not prove OS confinement or model answer correctness.

OpenClaw 2026.10.9 and later cannot run an embedded member inside a hardened
`systemd --user` unit: the unit's private mount namespace hides the PID-namespace
identity OpenClaw's ownership check needs. On such hosts run always-on members as
system units (`python3 scripts/in2n-services.py generate --system`, then `enable
--system`; both use `sudo -n` and print the commands if sudo needs a password). The
Risk posture reports confinement unavailable until then. For on-demand members,
`python3 scripts/in2n-services.py coldstart install` adds a confined system template
and a narrow polkit rule so the Border can cold-start them without sudo (see
[N2N-RISK](N2N-RISK.md)). Members are confined, but the Border is not by default. To
keep the Border's own shell and file tools away from Convergence settings, use the
optional [Border hardening](N2N-RISK.md#border-hardening-optional-spec-165) helper.

Configuration readiness is not proof that the remote service is reachable or that
its credential is authorized. Hermes's protected federation remains subnet-only;
this profile does not extend that qualification. Source checks and outstanding live
investigation evidence are tracked in [spec 164](../specs/164-convergence-border/verification.md).
The IDE's existing Mac/WSL component qualification restrictions remain in place;
the Linux CLI path above is the supported source workflow for this milestone.

## Upgrade, disable and qualification

Upgrade NetClaw normally; retain the selected installation's private environment.
Re-running the component install refreshes its dependencies without operating the
external stack. To disable, set `CONVERGENCE_ENABLED=false` in that environment and
regenerate the scoped registration as shown above, then restart the selected
HUD/runtime. The view is hidden, tools return disabled, and
external data remains intact. Remove this component's runtime registration through
your normal runtime configuration if you also want the tools absent.

Connector/browser evidence is in [spec 162 verification](../specs/162-convergence-read/verification.md).
[Spec 163](../specs/163-convergence-linux-qualification/qualification.md) records a
fresh Ubuntu 24.04 amd64 installation and actual OpenClaw 2026.10.9 gateway tool
execution with Ollama Cloud. Both tools preserved the exact window and scope.
Model interpretation remains unqualified: tested answers inferred unsupported
sampling or request/reply meaning and omitted a required evidence bound. Review generated conclusions against the
records; successful tool execution does not establish answer correctness.

Linux x86_64/ARM64 are the initial connector targets. macOS, Windows/WSL2, Hermes,
physical capture and broader end-to-end investigations remain unqualified. External
service qualification does not substitute for testing this connector. The [operator skill](../workspace/skills/convergence-observations/SKILL.md)
describes the same read-only workflow.
