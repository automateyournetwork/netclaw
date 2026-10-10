# Install and first-use readiness

NetClaw's installer checks host prerequisites, installs isolated component runtimes,
merges selected MCP registrations, and then checks tool discovery. A file on disk is
not evidence that a gateway can call a tool. The final private
`<runtime-home>/logs/install/run-*/readiness.json` records these stages separately.

## Supported bootstrap

OpenClaw installation currently requires Node `>=24.16.0 <25 || >=26.1.0`; prefer
Node 26 with your existing version manager. This is the declared target contract in
`config/installer-runtime.json`, checked against [upstream](https://docs.openclaw.ai/install/node-compatibility)
on 2026-10-10. Hermes retains its own Node requirement for Node-based components.
The installer checks the same rule in preflight and installation.

Use Python 3.12 for the broadest declared component coverage. CPython 3.14 runs on
Apple Silicon; some selected packages have tighter Python or architecture bounds.
On Homebrew, install compatible prerequisites and select their executables before
retrying, for example:

```bash
brew install python@3.12 uv
export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
export NETCLAW_PY="$(brew --prefix python@3.12)/bin/python3.12"
./scripts/install.sh --profile recommended --preflight
```

`uv` supplies managed pyATS/GAIT environments; no specific uv release is pinned.
Forward additionally requires Go 1.25+, CGO and a working C compiler/Apple Command
Line Tools. `--all` includes Linux-only components; inspect preflight on macOS and
select compatible components. The prerequisite report lists all known blockers.

For npm 11.16+ the installer uses the narrow `--allow-scripts=openclaw` option;
older npm omits it. npm 11.16 warnings alone do not establish that scripts were
blocked; npm 12 changes that policy. See [OpenClaw installation](https://docs.openclaw.ai/install).
An unwritable global prefix selects `--prefix "$HOME/.local"` for this installation
without rewriting npm configuration. Keep that directory's `bin` on PATH in new
shells. Failures stop installation; the installer does not retry npm under sudo.

## Tool access

These formerly skill-only integrations now get selected native MCP registrations:

| Component | Native server(s) | Launch path |
| --- | --- | --- |
| pyats | pyats-mcp | Existing stdio bridge → managed private loopback HTTP child |
| netbox | netbox-mcp | Recorded Python, `netbox_mcp_server.server`, source `src` path |
| servicenow | servicenow-mcp | Recorded isolated SDK1 Python, `servicenow_mcp.cli` |
| nvd-cve | nvd-cve-mcp | Recorded Python, `mcp_nvd.main --transport stdio` |
| subnet-calc | subnet-calc-mcp | Recorded Python, calculator script |
| wikipedia | wikipedia-mcp | Recorded Python, Wikipedia script |
| markmap | markmap-mcp | Node, installed Markmap build |
| drawio-rfc | drawio-mcp, rfc-mcp | Declared npx packages |
| packet-buddy | packet-buddy-mcp | Recorded Python, Packet Buddy script |
| nmap | nmap-mcp | Recorded Python, scanner source directory |
| gtrace | gtrace-mcp | Installed `gtrace mcp` binary |
| tts | tts-mcp | Recorded Python, speech script |

`config/installer-access.json` declares paths, required settings and expected tools.
`scripts/component-launch.py` is an executable launcher, not a new MCP server: it
passes the existing protocol through unchanged. Native registrations and recognized
legacy `MCP_CALL` skill commands use this same launcher. Custom commands, runtime
policy, approval fields, credentials and existing persona files are preserved.
Registration grants no write approval; production change control still applies.

Skills can also call the component explicitly:

```bash
python3 "$MCP_CALL" --component netbox --list-tools
python3 "$MCP_CALL" --component subnet-calc subnet_calculator '{"cidr":"192.0.2.0/30"}'
```

The second command is a harmless local first-use canary. Verify the tool result
contains the requested CIDR. A model-generated table is not tool evidence. If a
call fails, report the failure; never replace unavailable device data with examples.
This canary does not prove a model will always ground its answers correctly.

## Read the result and retry

- `failed`: install, launch, registration, discovery or configured Ollama check failed;
  the installer exits nonzero. Inspect the named component and its per-run log.
- `configuration_required`: supply the listed settings or resolve a disabled entry;
  the component is not ready. No credential value is included in the report.
- `discovery_verified`: expected tools were exposed through the tested access path.
  Actual device/service operations and a gateway agent turn remain unverified.
- `unverified`: a check was not performed or a component has a separate access path.
  Remote declarations and filesystem checks alone never establish connectivity.

OpenClaw discovery uses its native CLI and checks structured server/tool results,
not just exit status. Hermes currently checks its saved registration and performs
direct stdio discovery; agent-visible Hermes discovery remains explicitly unverified.
HTTP-only Hermes probes remain unverified. Public HTTP pyATS daemons are unnecessary.
For custom HTTP registrations, specify the actual transport (`streamable-http` or
SSE); do not infer it merely from a URL.

Retry failed installation steps with the exact runtime and components you selected:

```bash
./scripts/install.sh --runtime openclaw --add "pyats netbox cml"
```

After editing settings, rerun checks without package installation:

```bash
python3 scripts/installer-readiness.py --runtime openclaw \
  --runtime-root "$HOME/.openclaw/python-runtimes" \
  --config "$HOME/.openclaw/openclaw.json" --components "pyats netbox cml" \
  --output "$HOME/.openclaw/readiness.json" --probe --check-provider
```

For Hermes use its home/config.yaml and `--runtime hermes`; check AI-provider
readiness with Hermes itself. Local/remote Ollama on OpenClaw is checked using the
configured endpoint and model catalog/capabilities. A remote Ollama host requires no
local Ollama executable. Checks never pull models, generate text, or call device
tools. Advertised tool capability is not a completed agent turn.

The original reports did not include six named macOS failures or a reproducible CML
spawn trace. Those remain evidence gaps. Use a harmless authorized read against your
actual target after discovery; neither synthetic fixtures nor CI certify every
external service or package/OS combination.
