# Cisco IQ remote MCP

Spec 191, issue #346. NetClaw connects to Cisco's official Cisco IQ remote MCP server through its
existing native remote MCP support. There is no custom adapter, no local Cisco IQ server and no
credential service. Everything below can be run by an administrator without an AI operator.

## What was and was not verified

The connection contract comes from issue #346, which cites the official guide
(https://iq.cisco.com/apidocs/mcp-server). That guide returned HTTP 403 to automated fetching, so
its contents **could not be verified** by the implementer. Verified on 2026-11-11: each regional
endpoint answers an unauthenticated request with HTTP 401 (`www-authenticate: Session realm="Cisco IQ"`),
so the hostnames exist and are reachable. Not verified: tool names and schemas, acceptance of a real
key, service-account behaviour, expiry details, and every workflow in the skill. No live Cisco IQ
key was available. Re-check the official guide before relying on this document.

## Contract (per the issue)

| Item | Value |
|---|---|
| Transport | Streamable HTTP |
| EMEA | https://eu-central-1.iq.cisco.com/mcp |
| US | https://us-west-2.iq.cisco.com/mcp |
| APJC | https://ap-southeast-2.iq.cisco.com/mcp |
| Authentication | one `Authorization: Bearer <API_KEY>` header; the key is used directly (no OAuth or token exchange) |
| Key owner | must be a **user principal**. Service-account-owned keys receive no MCP tools |
| Lifecycle | keys expire; they inherit the owner's current permissions |

The region is chosen explicitly by the administrator. It is never inferred from the NetClaw
server's location, locale, timezone or DNS.

## Set up

```bash
printf '%s' "$CISCO_IQ_KEY" | scripts/cisco-iq-enable.sh enable --region us --key-stdin
# or run without --key-stdin in a terminal for a hidden prompt
scripts/cisco-iq-enable.sh enable --region us --dry-run     # redacted preview
```

This writes `CISCO_IQ_API_KEY` and `CISCO_IQ_REGION` to the private runtime `.env` (mode 0600, atomic
write, same literal-dotenv rules as `docs/ENVIRONMENT-FILES.md`), and adds this registration to the
runtime `openclaw.json` (`~/.openclaw/openclaw.json`, or `~/.openclaw/config/openclaw.json` if that
is where yours lives):

```json
"cisco-iq-mcp": {
  "url": "https://us-west-2.iq.cisco.com/mcp",
  "headers": {"Authorization": "Bearer ${CISCO_IQ_API_KEY}"},
  "env": {"CISCO_IQ_API_KEY": "${CISCO_IQ_API_KEY}"}
}
```

The header is a template; the resolved value is never written to configuration. It is not
pre-seeded in `config/openclaw.json` because the region is mandatory. Reload the OpenClaw MCP
runtime afterwards.

## Credential handling

- Key only in the private `.env`; never on a command line (flags such as `--key` are refused), in a
  prompt to the agent, in committed files, or in examples (`.env.example` has names only).
- Previews, `status`, `diagnose`, errors and `--json` output pass through a redactor that removes the
  key and any Bearer value.
- Do not `source` the `.env` file.

## Operate

| Task | Command |
|---|---|
| Status (no values) | `scripts/cisco-iq-enable.sh status` |
| Diagnose offline | `scripts/cisco-iq-enable.sh diagnose` |
| Diagnose with the network | `scripts/cisco-iq-enable.sh diagnose --live` (opt-in; MCP initialize + tools/list) |
| Rotate the key | `printf '%s' "$NEW" | scripts/cisco-iq-enable.sh rotate --key-stdin` (backs up the env file privately, changes only the key) |
| Change region | `scripts/cisco-iq-enable.sh update --region emea` |
| Disable | `scripts/cisco-iq-enable.sh disable` (keeps the key) or `disable --purge-credential` |
| Tool policy report | `scripts/cisco-iq-enable.sh policy-check --live` or `--tools-file tools.json` |

`diagnose` reports exactly one of: `NOT_ENABLED`, `KEY_UNSET`, `ENV_PERMISSIONS`, `TRANSPORT_FAILURE`,
`AUTH_FAILURE`, `ZERO_TOOLS`, `OK`. `AUTH_FAILURE` lists possible (unconfirmed) causes: expired or
revoked key, wrong region, missing permission. `ZERO_TOOLS` usually means a service-account-owned key.
`--json` is the support output; it is redacted. Use it when asking for help.

## Agent policy

`config/cisco-iq-policy.json` is read-only and deny-by-default. The allowlist ships empty because
Cisco IQ tool names are not published to this project. After reviewing `policy-check --live`, add
reviewed read-class tool names (`verified: true`). Deny patterns for mutating verbs always win. NetClaw's native
remote client has no per-tool gate, so enforcement is the skill's instructions plus DefenseClaw when it is
enabled (`defenseclaw tool block <name>`; the policy report prints the commands). Without DefenseClaw it is not a hard
technical control.

## Validate without credentials

```bash
bash tests/cisco-iq/run-tests.sh
python3 scripts/run-contract-tests.py --suite cisco-iq
```

Offline only: a loopback mock stands in for the endpoint. Live connectivity is reported as
`NEEDS_LIVE_CREDENTIALS` and is not counted as a pass.

## Skill

`workspace/skills/cisco-iq/SKILL.md` describes workflows for assets and product information,
lifecycle and coverage, Cisco bugs, and correlation with an investigation. None is claimed validated.
Availability of any field depends on Cisco IQ's published schemas, the account's data and the key
owner's permissions.
