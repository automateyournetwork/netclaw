# Contract: Home install wizard

## Flow
1. Deploy mode: `docker` | `k3s`
2. Firewall adapter
3. Wireless adapter  
4. SoT adapter
5. Agent extras: Discord, RAG snapshots, speedtest
6. Risk: detect existing → keep; else create; **ensure guardian-claw**

## Outputs
- `~/.openclaw/netclaw-components.conf` entries for selected home components
- `config/convergence.yaml` (or `~/.openclaw/convergence.yaml`)
- Env keys appended via setup (never commit secrets)
- systemd: home-api/compose or k8s apply; host mesh/members unchanged except guardian ensure
- Summary line: `risk=<name> investigator=<id> deploy=<mode> home-api=<url>`

## Idempotency
Re-run does not duplicate guardian-claw or wipe member envs.
