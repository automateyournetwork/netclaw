# Data Model

- **Region**: `{emea: https://eu-central-1.iq.cisco.com/mcp, us: https://us-west-2.iq.cisco.com/mcp, apjc: https://ap-southeast-2.iq.cisco.com/mcp}` - constant table in `scripts/cisco_iq.py`; mirrored in docs/catalog and asserted equal by a test.
- **Registration** (`openclaw.json` `mcpServers["cisco-iq-mcp"]`): `url` (= region endpoint), `headers.Authorization` = literal `Bearer ${CISCO_IQ_API_KEY}`, `env.CISCO_IQ_API_KEY` = `${CISCO_IQ_API_KEY}`. Invariant: never a resolved key.
- **Env entries** (`.env`): `CISCO_IQ_API_KEY` (secret), `CISCO_IQ_REGION` (enum). File mode 0600, not a symlink.
- **Policy** (`config/cisco-iq-policy.json`): `{schema_version, mode:"deny-by-default", read_only:true, allow:[{name, verified:bool, note}], deny_patterns:[regex], notes}`.
- **Finding**: `{status, detail, hints[]}` where status in NOT_ENABLED, KEY_UNSET, ENV_PERMISSIONS, TRANSPORT_FAILURE, AUTH_FAILURE, ZERO_TOOLS, OK.
- **State transitions**: absent -> enabled(region) -> enabled(region') via update -> disabled (registration removed, key kept) -> purged (key removed). All idempotent.
