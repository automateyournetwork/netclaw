# Setup: Percepxion and SLC MCP servers

Both servers are Lantronix open-source projects, installed by NetClaw as external components and
registered by the operator.

| Server | Repository | NetClaw component |
|---|---|---|
| percepxion-mcp-server | https://github.com/Lantronix/percepxion-mcp-server | `percepxion` |
| slc-mcp-server | https://github.com/Lantronix/slc-mcp-server | `slc` |

## Install

Select the `percepxion` (and optionally `slc`) component in the NetClaw installer. It clones each
repository at the revision NetClaw has reviewed, applies the FastMCP compatibility patch recorded
in `config/fastmcp-external-patches.json`, and builds a dedicated virtual environment at
`mcp-servers/<repository>/.venv`. Neither server is added to `config/openclaw.json` automatically,
because the install path is specific to each host.

Newer upstream releases add Streamable HTTP and SSE transports, the `azure` and `command`
credential providers, and `_FILE` variants of the credential variables. The tools are the same.
Those features reach NetClaw when the reviewed revision moves forward; until then, use the variables
in the tables below.

## Register

Use the installed interpreter and entry point. Replace `/path/to/netclaw` with the checkout path.

```json
{
  "percepxion": {
    "command": "/path/to/netclaw/mcp-servers/percepxion-mcp-server/.venv/bin/python",
    "args": ["/path/to/netclaw/mcp-servers/percepxion-mcp-server/percepxion_mcp.py"],
    "env": {
      "PERCEPXION_USERNAME": "${PERCEPXION_USERNAME}",
      "PERCEPXION_PASSWORD": "${PERCEPXION_PASSWORD}",
      "PERCEPXION_API_URL": "${PERCEPXION_API_URL}"
    },
    "transport": "stdio"
  },
  "slc": {
    "command": "/path/to/netclaw/mcp-servers/slc-mcp-server/.venv/bin/python",
    "args": ["/path/to/netclaw/mcp-servers/slc-mcp-server/run_server.py"],
    "env": {
      "SLC_DEFAULT_IP": "${SLC_DEFAULT_IP}",
      "SLC_USERNAME": "${SLC_USERNAME}",
      "SLC_PASSWORD": "${SLC_PASSWORD}"
    },
    "transport": "stdio"
  }
}
```

First check after registering: `login_with_env`, then `get_device_list` with `search_query: "*"`.

## percepxion-mcp-server variables

| Variable | Default | Purpose |
|---|---|---|
| `PERCEPXION_USERNAME`, `PERCEPXION_PASSWORD` | | Login, read only by the `env` provider |
| `PERCEPXION_API_URL` | `https://api.percepxion.ai/api` | API base. Change it only for an on-premises or other instance the operator names; a wrong host fails at login |
| `PERCEPXION_CREDENTIAL_PROVIDER` | `env` | `env`, `vault`, `aws` or `cyberark` (see below) |
| `PERCEPXION_DEFAULT_ORGANIZATION_ID` | | Organization used when a call omits `organization_id`. `PERCEPXION_DEFAULT_TENANT_ID` is a deprecated alias |
| `PERCEPXION_REQUEST_TIMEOUT` | `45` | HTTP timeout in seconds; raise it for large log downloads |
| `PERCEPXION_FIRMWARE_DIR` | | Restricts firmware uploads to files in this directory |

The `requires.env` entry in the skill's frontmatter names the `env` provider's two variables
because that provider is the default. Another provider needs its own variables instead.

### Credential providers

`login_with_env` signs in through whichever provider is configured, despite its name.
`reconfigure_credentials` switches the provider at run time; call `login_with_env` again afterwards.
It changes where the server's own Percepxion credentials come from. It doesn't rotate console server
passwords.

| Provider | Variables |
|---|---|
| `env` | `PERCEPXION_USERNAME`, `PERCEPXION_PASSWORD` |
| `vault` | `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_SECRET_PATH` |
| `aws` | `AWS_SECRET_NAME`, `AWS_REGION` (install the `aws` extra) |
| `cyberark` | `CYBERARK_URL`, `CYBERARK_APP_ID`, `CYBERARK_SAFE`, `CYBERARK_OBJECT`; optional mutual TLS with `CYBERARK_CERT_PATH` and `CYBERARK_KEY_PATH` |

### CLI policy

Set on the server process by the operator. The agent can't change it during a session.

| Variable | Default | Effect |
|---|---|---|
| `PERCEPXION_CLI_WRITE_ENABLED` | `false` | `true` allows write commands; read commands are always allowed |
| `PERCEPXION_CLI_MAX_LENGTH` | `512` | Longest command accepted |
| `PERCEPXION_CLI_DENY_COMMANDS` | | Commands blocked in addition to the built-in deny list (`reload`, `factory-reset`, `write erase` and similar) |
| `PERCEPXION_CLI_PERMIT_COMMANDS` | | When set, only these commands and their subcommands are allowed |
| `PERCEPXION_CLI_YOLO` | `false` | Turns off all filtering, including the deny list. Not for production |

Percepxion also enforces its own user permissions and can filter commands per port. A command the
MCP policy allows can still be refused there; report the error and point the operator at the
platform's settings, since the tool call itself can't fix it.

### Roles and `organization_id`

| Percepxion role | Scope | `organization_id` on job, telemetry, content, Smart Group and audit tools |
|---|---|---|
| Tenant User | Organizations granted to the user | Optional, scoped automatically |
| Tenant Admin | One organization | Optional, scoped automatically |
| Project Admin | Every organization in the project | Required |

A Project Admin call without it fails with an error that names the missing parameter. Call
`list_organizations` to find the ID. `organization_id` is the parameter name everywhere; `tenant_id`
and `list_tenants` remain as deprecated aliases.

## slc-mcp-server variables

| Variable | Default | Purpose |
|---|---|---|
| `SLC_DEFAULT_IP` | | Unit used when a `device_id` has no per-device entry |
| `SLC_USERNAME` | `sysadmin` | Default login |
| `SLC_PASSWORD` | | Default password |
| `SLC_TOTP_SECRET` | | Base32 TOTP secret for units with two-factor login |
| `SLC_{KEY}_IP`, `_USERNAME`, `_PASSWORD`, `_TOTP_SECRET` | | Per-unit values. `{KEY}` is the `device_id` uppercased with other characters replaced by `_`: `slc9000-dc-a` becomes `SLC_SLC9000_DC_A_IP` |
| `SLC_KNOWN_DEVICE_IDS` | | `env` provider only: allow-list of `device_id` values |
| `SLC_VERIFY_SSL` | `true` | `false` only for lab units with self-signed certificates |
| `SLC_CREDENTIAL_PROVIDER` | `env` | `env`, `vault`, `aws`, `percepxion` or `cyberark`. `percepxion` looks up each unit's address in Percepxion and still reads credentials from `SLC_{KEY}_*`. Switch at run time with `configure_provider` |

CLI policy for `apply_config_commands` and the Percepxion client tools (`start_px_client`,
`stop_px_client`, `restart_px_client`) mirrors the Percepxion server: `SLC_CLI_WRITE_ENABLED`
(default `false`), `SLC_CLI_MAX_LENGTH`, `SLC_CLI_DENY_COMMANDS`, `SLC_CLI_PERMIT_COMMANDS` and
`SLC_CLI_YOLO`. The built-in deny list blocks `factory-reset`, `write erase`, `erase startup-config`,
`erase flash`, `reload`, `reboot`, `format`, `shutdown`, `power off`, `reset system`, `init 0` and
`halt`. The unit's own user roles apply on top.

## Capability split

| Capability | slc-mcp-server (one unit, synchronous) | percepxion-mcp-server (fleet, asynchronous) |
|---|---|---|
| Port status and settings | `get_slc_port`, `get_slc_ports` | `list_device_ports`, `get_port_telemetry` |
| Attached devices | `get_managed_devices`, `get_managed_device` | `get_security_telemetry`, `get_port_telemetry` |
| CLI with output | `apply_config_commands` (one call) | `send_direct_cli_command`, then `get_cli_command_output` |
| Firmware | `firmware_update`, `get_firmware_update_status`, bootbank tools | `update_firmware_by_smart_group` |
| Configuration backup | `export_config_commands` | `get_device_config` |
| Sessions | `get_sessions`, `terminate_session` | |
| Cellular status | `get_cellular_status` | |
| Reboot | `reboot_device` | `reboot_device` |
| Smart Groups, templates, audit logs | | Yes |

The full tool reference is in each repository's `docs/` folder and `skills/` folder.
