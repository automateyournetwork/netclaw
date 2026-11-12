# Contract: `scripts/netclaw-gcp.py`

```
netclaw-gcp.py topologies                                   list topology ids
netclaw-gcp.py plan  --topology T --project P --region R [--region R2 ...] [--prefix-id ID] [--https-cidr CIDR] [--ack-no-auth]
netclaw-gcp.py apply --plan-sha256 SHA --confirm-cost       create (refused without both)
netclaw-gcp.py status --deployment ID
netclaw-gcp.py ssh --deployment ID NODE 'cmd'
netclaw-gcp.py teardown --deployment ID [--confirm-list-sha256 SHA]    list, or delete owned only
```
Exit codes: 0 ok; 2 usage/refused (no ack, no confirm, missing prerequisite); 3 prerequisite failure (message names it); 5 gcloud failure.
`plan` prints the Standard Warning, requires `--ack-no-auth` (or interactive "yes"), prints resources + cost estimate + sha256.
Env: `GCLOUD` overrides the binary (tests). No secret is accepted on argv.
