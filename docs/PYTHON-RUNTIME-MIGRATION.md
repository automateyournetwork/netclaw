# Python installation compatibility

The installer requires Python 3.10+ for both `python3` on PATH and the
`NETCLAW_PY` component base. Selecting pyATS or GAIT also requires `uv` on
PATH before component installation begins. Component-specific upper and lower
bounds also apply. Unless `NETCLAW_PY` is explicit, the installer prefers an existing
Python 3.12 on PATH or under the standard Homebrew `python@3.12` prefixes. It does
not download Python during this selection. Python 3.12 matches the staged pyATS
installer's default and the declared component bounds in the current policy.

## macOS prerequisites and recovery

Apple's `/usr/bin/python3` can be Python 3.9. Installing current MCP/FastMCP
packages into environments created from it can produce misleading pip
dependency-conflict messages. Check the actual interpreter version; upgrading
pip alone does not change Python's version.

For Homebrew users, select Python explicitly in the same terminal that runs
the installer:

```bash
brew install uv python@3.12
export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
export NETCLAW_PY="$(brew --prefix python@3.12)/bin/python3.12"
python3 --version
"$NETCLAW_PY" --version
uv --version
./scripts/install.sh --runtime hermes --preflight --components "pyats gait zabbix"
./scripts/install.sh --runtime hermes --components "pyats gait zabbix"
```

Use the desired runtime and selection flags instead of `--runtime hermes --components "pyats gait zabbix"`
when appropriate. Homebrew documents the unversioned `python3` symlink directory
in its [Python 3.12 formula](https://formulae.brew.sh/formula/python@3.12);
see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)
for other platforms.

With the prerequisite/recovery fix installed, a retry detects automatic
component environments whose Python is below the minimum or above a declared
component upper bound (for example, Python 3.14 with Panorama). It preserves
the old directory and uses a separate version-suffixed target, such as
`arista-cvp-component-bounds-py3.12`. A successful dependency installation
records the replacement interpreter; a failure leaves the previous record
unchanged. Existing compatible runtimes are reused. Unknown directories and
symlinks at replacement targets are refused, and explicit `NETCLAW_VENV`
environments are never automatically replaced. Check configuration conflicts
and server discovery before retiring an old runtime.

The same recovery applies to dedicated source environments for ANTA, multivendor
CLI, Zabbix, Percepxion, SLC and Jev. For example, an old `anta-mcp/.venv` is
preserved while installation uses `anta-mcp/.venv-py3.12`. Canonical MCP launch
templates follow the successfully recorded interpreter. Existing custom launch
commands still require reconciliation.

Apple's pip 21.2 cannot install modern editable `pyproject.toml` projects.
The installer upgrades pip older than 21.3 to `pip>=23` inside the component
environment before installing dependencies. It refuses to upgrade system pip.
This addresses the missing `setup.py`/`setup.cfg` errors separately from Python
version errors.

An `--all` retry also needs prerequisites for the selected integrations. Docker,
kubectl, Ollama, packet-capture tools and browser provisioning are separate from
Python recovery. The Computer Use virtual desktop requires Linux. Configure
credentials and reachable services only for the integrations you intend to use;
installing Python packages does not establish that those services are ready.

## Platform and component preflight

`--preflight` runs the same selection checks used before every installation and
exits without creating environments, logs or runtime configuration. It reports all
known blockers together. Checks use `config/installer-preflight.json`, with common
defaults for every catalog component and overrides for known restrictions. MCP
launch templates also supply external `uvx`, Docker and `npx` requirements.
Missing prerequisites must be installed or removed from the selection before
retrying; the entrypoint now stops before its legacy prerequisite-install offers.
Global pip is not required; a selected base must support isolated pip seeding,
or an explicit `NETCLAW_VENV` must have a supported Python and usable pip.

| Selection | Declared prerequisite |
| --- | --- |
| Forward Networks | Go 1.25+, CGO enabled, C compiler; Apple Command Line Tools on macOS |
| Panorama | Python >=3.10,<3.13 |
| Zoom RTMS | Python >=3.10,<3.14; Darwin arm64 or Linux x86_64 with glibc >=2.34 |
| CML, NSO, UML, ThousandEyes Community | Python >=3.12 |
| Memory MCP | Python >=3.11 |
| Computer Use virtual desktop | Linux (Xvfb/XFCE); unavailable in the macOS custom picker |
| RADKit | Explicit Cisco SDK index in `PIP_INDEX_URL`/`PIP_EXTRA_INDEX_URL`, or local `PIP_FIND_LINKS` directory containing the pinned 1.9.0 SDK wheel |

[Forward's prerequisites](https://github.com/forwardnetworks/forward-mcp#prerequisites),
[Panorama package metadata](https://pypi.org/project/iflow-mcp-cdot65-palo-alto-mcp/),
[Zoom's rtms 1.1.0 wheels](https://pypi.org/project/rtms/1.1.0/), and
[Cisco's RADKit package notice](https://pypi.org/project/cisco-radkit-client/)
provide the upstream basis for these restrictions. Obtain vendor packages from
the manufacturer and verify the selected version. Preflight checks explicit
environment configuration for RADKit; it does not inspect pip configuration files,
verify wheel contents or authenticate to Cisco's index.

Docker selections require the CLI and a responsive configured Docker daemon.
Packet Buddy needs tshark; capinfos is optional. kubectl, nmap, Ollama and other
external launchers are checked only when relevant to the selection. These are host
checks with bounded read-only probes; Go probes disable automatic toolchain
downloads. Passing means the declared checks passed, not that every upstream
package can resolve or endpoints, Kubernetes clusters, Ollama models, credentials
and browser provisioning are ready. Linux host checks are covered with fixtures.

Zabbix installs its relative `./vendor/zabbix-mcp-server` requirement from the
component directory, including when reusing a version-suffixed environment.

Each actual install creates a fresh `logs/install/run-<UTC time>-<suffix>/` below
the selected runtime home and prints that exact path. `run-info.txt` records the
host, Bash version, Python path and selection. Component logs never reuse an older
run's errors. Interactive components still use the terminal, so their full output
is not captured automatically. Older logs remain in place; archive the printed
run directory when reporting a new failure.

## Component isolation

The interactive and CLI installers automatically isolate legacy Python components
under the selected runtime home: `~/.openclaw/python-runtimes/<component>` or
`~/.hermes/python-runtimes/<component>`. Each component has its own environment.
System Python protection remains enabled; the installer never passes
`--break-system-packages`.

`NETCLAW_PY` selects the base Python used to create these environments. Existing
component-specific runtimes, including pyATS and multivendor CLI, retain their
own installation paths. An explicit `NETCLAW_VENV` overrides automatic selection;
use it only for a compatible, deliberately selected component runtime.

The helper tries virtualenv, the standard library venv module, then installed uv
with pip seeding. If none can create an environment, installation fails with a
remedy. It does not bootstrap tools into protected system Python. Automatic
legacy environments retain `config/python-shared-constraints.txt` bounds. Components
with explicit bounds under `config/python-components/` use a separate
`<component>-component-bounds` environment, preserving any partially installed
legacy runtime. UML uses this path for MCP2 and FastMCP4; those bounds never
apply to other components or system Python.

Successful Python installs record the exact interpreter. The installer uses it
for MCP Python commands and installed console entry points, with absolute repo
paths. Only successfully installed and artifact-verified selections are newly
registered. Existing onboarded OpenClaw configurations receive missing entries;
provider settings, credentials, unrelated servers and per-server options are
preserved. Custom launch commands produce a conflict requiring reconciliation,
rather than being overwritten. Changed configs get private timestamped backups.
Hermes consumes the same generated selected template through its existing
non-destructive YAML translator; an existing MCP block still requires the
translator's documented sidecar merge.

A failed pip call makes the component and final installer exit status fail even
if a legacy warning handler swallowed its return code. This is conservative:
if a fallback subsequently succeeds, rerun that component to establish a clean
result. Neither package installation nor an artifact check proves endpoint
connectivity. Credentials, reachable services and tool discovery still require
verification appropriate to the selected integration.

## Upgrade and rollback

Rerun the installer with the desired selection. Existing source-tree `.venv`
directories and system packages are not removed or migrated. Unknown directories
at an automatic runtime destination are refused rather than adopted. Keep the
prior environment until startup and tool discovery pass. To undo registration
changes, restore the recorded config backup and restart the gateway when ready.
Do not delete a runtime while a configured server uses it.

Direct users of `netclaw_pip_install` outside the installer still select their
runtime explicitly:

```bash
source scripts/lib/pip-helper.sh
netclaw_venv_create /path/to/component-venv
NETCLAW_VENV=/path/to/component-venv netclaw_pip_install -r /path/to/requirements.txt
```

Configure that server's launcher to use `/path/to/component-venv/bin/python`.
For pyATS, use the dedicated [HTTP migration](PYATS-HTTP-MIGRATION.md).

## Contract tests do not replace operator runtimes

`python3 scripts/run-contract-tests.py --suite all --prepare` creates named
environments under `.contract-test-envs/`, including ANTA, multivendor and Zabbix.
Existing `mcp-servers/*/.venv` operator runtimes stay in place; no manual move or
data migration is needed. Older test environments are not automatically removed.

Preparation refuses to replace an existing environment without its matching
NetClaw contract ownership marker. Preserve an unexpected directory separately
and inspect it before retrying; there is no force-delete option. Refreshing a
marked test environment retains a temporary recovery copy until installation
succeeds. A failed refresh restores the original path. An interrupted process
may leave `<environment>.previous-*` beside the new environment: preserve both,
move the partial new directory aside, then move the recovery copy back to the
original path before using its Python. A relocated virtualenv is not directly
runnable. Contract artifacts remain checksum-verified separately.

MemPalace launches as `python -m mempalace.mcp_server`, which supports both
upstream file and package layouts. The installer records its interpreter in
`MEMPALACE_MCP_PYTHON`; skills use `scripts/mempalace-stdio.py` through the existing
`MEMPALACE_MCP_SCRIPT` setting. Rerun `--add "uml memory-mcp mempalace"` after
upgrading to repair these selections and refresh their launch settings.
