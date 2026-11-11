# CLI Contract: `scripts/cisco-iq-enable.sh <subcommand>`

Common flags: `--home DIR` (default `~/.openclaw`), `--dry-run`, `--json`.
Exit codes: 0 ok, 1 operational failure/finding, 2 usage error (bad/missing region, secret on argv).

| Subcommand | Behaviour |
|---|---|
| `enable --region R [--key-stdin]` | validate R; write `CISCO_IQ_REGION`, key (if provided/prompted) to `.env` 0600; add registration; idempotent |
| `update [--region R]` | re-apply registration for R/current region; refresh nothing secret |
| `rotate --key-stdin` | replace `CISCO_IQ_API_KEY` only; private backup; registration untouched |
| `disable [--purge-credential]` | remove registration; keep key unless purge |
| `status` | region, endpoint, key set yes/no, perms, registration present; never values |
| `diagnose [--live] [--endpoint-override URL]` | findings enum; `--live` does initialize+tools/list |
| `policy-check [--tools-file F | --live]` | classify tools allowed/denied/unlisted |

Any flag named like `--key`, `--token`, `--api-key` with a value is rejected (exit 2) with a message that never echoes the value.
