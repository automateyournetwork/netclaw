# Contract: cloud driver verbs

`scripts/ha-cloud.sh <provider> <verb> [args]`, provider is `gcp` (default, existing behavior) or `azure`. Every verb supports
`--dry-run` (print the exact provider commands, execute nothing) and exits non-zero on failure. No verb prints secrets.

| Verb | Args | Behavior |
|------|------|----------|
| `up` | `<phase> <code> <region> <size>` | create network, firewall/NSG (SSH from owner IP only), static IP, VM; label/tag `netclaw-spec=198 phase=<phase>` |
| `ssh` | `<phase> <code> <command>` | run a command on the VM (GCP: IAP; Azure: key ssh to public IP) |
| `scp` | `<phase> <code> <files...>` | copy files to `/tmp/` on the VM |
| `ip` | `<phase> <code>` | print the VM public IP |
| `stop` / `start` | `<phase> <code>` | deallocate / start (stops compute billing) |
| `down` | `<phase>` | delete the whole phase grouping; then verify none remain by tag |
| `get` | `<phase> <code> <localdir> <remote files...>` | copy files from the VM to a local directory |
| `peer` | `<phase> <codes...>` | full-mesh private connectivity between the phase nodes (Azure global VNet peering; GCP no-op) |
| `list` | `[<phase>]` | list resources carrying the spec tag (used by teardown verification) |

Compatibility: with `provider=gcp` the verbs reproduce the commands currently hardcoded in `ha-r09-*.sh` (project, zone map, IAP).
