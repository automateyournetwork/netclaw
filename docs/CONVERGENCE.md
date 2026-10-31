# Inspect retained traffic with Convergence

This optional integration connects NetClaw to a separately operated Convergence
service. It adds two read-only tools and a traffic view: choose a ranking, select
an address, and inspect retained records from the **same observation window**.
NetClaw does not install a collector, storage stack, IDS or case-management API.

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

## Upgrade, disable and qualification

Upgrade NetClaw normally; retain the selected installation's private environment.
Re-running the component install refreshes its dependencies without operating the
external stack. To disable, set `CONVERGENCE_ENABLED=false` in that environment and
regenerate the scoped registration as shown above, then restart the selected
HUD/runtime. The view is hidden, tools return disabled, and
external data remains intact. Remove this component's runtime registration through
your normal runtime configuration if you also want the tools absent.

Executed evidence and remaining gaps are in [spec 162 verification](../specs/162-convergence-read/verification.md).
Linux x86_64/ARM64 are the initial qualification targets. macOS, Windows/WSL2,
Hermes execution, physical network capture and full model/gateway investigations
remain unqualified until separately exercised. External service qualification does
not substitute for testing this connector. The [operator skill](../workspace/skills/convergence-observations/SKILL.md)
describes the same read-only workflow.
