# Quickstart: R10 Azure

> Current resumption: [resume-20261124.md](resume-20261124.md). The owner resumed
> bounded work on November24. Its scope, budget gate and measured latency finding
> supersede the historical status, topology and sequencing below. No new live
> acceptance is implied. The binding peer contract uses ONE group per member.

1. `! az login` (owner), confirm `az account show --query state` is `Enabled`.
2. `bash scripts/ha-r10-preflight.sh` : read-only go/no-go per region, budget alert status, secrets presence.
3. Owner says **go phase 2** : `bash scripts/ha-r10-phase.sh up p2-single` (one Border), enroll Mac subnet member + hosted NetBox member, run operations, record evidence, `bash scripts/ha-r10-phase.sh down p2-single`.
4. Owner says **go phase 3** : 3-region HA, same flow, down.
5. Owner says **go GCP** : single small GCP Border plus Azure Border, federation proof, tear down both clouds.
6. Docs/release-gate update (no cloud cost); nothing published without owner approval.
Dry run any step with `--dry-run`. Emergency teardown: `bash scripts/ha-r10-phase.sh down <phase>` or `az group delete -n <rg> --yes`.
