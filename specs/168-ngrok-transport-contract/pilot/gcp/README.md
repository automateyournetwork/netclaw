> Current R01 pilot: DNS/HTTPS, foundation/runtime activation and actual IP
> relocation/recovery are verified. The owner fully delegated these changes and
> requested the full open lab HUD, Anthropic Sonnet and a scoped on-prem subnet
> demonstration. Users/SSO/RBAC remain R15–R17. Use resume.md and verification.md
> for current receipts. Earlier preparation commands below are historical;
> never replay initial activation over the running pilot.

# R01 qualification foundation

This is an isolated qualification host, not the R03 production deployment.
The owner delegated and completed the foundation, scoped runtime, DNS/HTTPS and
relocation changes. No destroy has been executed. See the original
[foundation review](../../cloud-review.md) and current [verification](../../verification.md).

`main.tf` creates a dedicated VPC/subnet, one e2-small VM with a 20GiB disk,
two reserved IPv4 addresses (the second tests relocation), two firewall rules,
one workload service account, one empty Secret Manager secret and its scoped
reader grant, and a project budget alert. Provider and OpenTofu versions are
pinned. Secret values are never Terraform variables or outputs.

Use owner-private absolute paths for tfvars, state, saved plans and receipts.
The local backend has no shared-writer locking: one operator controls this pilot;
coordinate all future changes against the same state. Do not run concurrent
applies or manage the same resources independently through gcloud.

The VM expires by **stopping** at the reviewed timestamp. Its disk, addresses and
secret can keep accruing charges. `teardown-plan.sh` prepares a destroy plan only;
the operator reviews and applies it separately after retaining required evidence.
Destroying a pilot destroys its private runtime; export approved evidence first.

## Current full lab workspace

Public URL: https://r01-gcp-montreal.lobsternet.automateyournetwork.com/.
The full built HUD uses the fixed public-hud.mjs ingress behind Caddy. Chat uses
a private OpenClaw2026.7.1-2 gateway and Anthropic Sonnet4.6; the on-prem member
permits only its actual subnet calculator. The gateway and native administration
remain loopback/IAP. The owner authorized this open lab without a login.

The deployed HUD systemd drop-in is [hud-sonnet-rag.conf](hud-sonnet-rag.conf):
private runtime CLI PATH, separate RAG venv/cache and a bounded120s native
settings-CLI startup budget. Native RPC itself keeps its10s timeout. RAG uses
CPU-only Torch, BAAI/bge-small-en-v1.5 and ms-marco-MiniLM-L-6-v2 cached locally;
normal retrieval runs offline. [install-rag.sh](install-rag.sh) records the actual
installation steps; exact installed versions are retained in the private runtime
receipt. It is not an instruction to replay installation over the running host.
HUD calls serialize RAG helper processes and coalesce status polls, preventing
startup recovery from racing an active HUD ingestion. Independently launched RAG
clients must still be coordinated by the operator.

## Historical initial IAP provisioning contract

The existing HUD has no Internet login. The pilot default is its documented
SSH access, carried through GCP IAP. No new public HUD port, DNS record,
certificate issuance or IdP registration is in this foundation plan.
Both HUD processes use `HUD_HOST=127.0.0.1`, `HUD_UI_PORT=13000` and
`HUD_PORT=13001` in the **new cloud home**. Build and launch the existing selected
OpenClaw HUD with pinned qualified Node; keep its model/gateway unavailable and
report that state honestly. A working transport/status view does not prove chat,
inference, tools or device execution. Use a separately reviewed, secret-free
source archive and fresh pilot identities; never upload the owner's repository
`.env`, existing homes, testbeds or credentials.

After provisioning, verify the VM SSH host key through an authenticated independent
channel before trusting it. Never disable host-key checks. Run:

```sh
bash specs/168-ngrok-transport-contract/pilot/gcp/hud-access.sh \
  netclaw-506315 northamerica-northeast1-a netclaw-r01-20261101
```

The verified IAP browser address is `http://127.0.0.1:13000/` while the owned
forwards run. The separate open lab viewer is prepared in public-hud-review.md.
The page runs on GCP and is forwarded to the operator's loopback. Keep matching
local/remote ports for the HUD's Host/Origin checks. An occupied local port fails
closed. Ctrl-C closes this tunnel only. The owner later delegated the separate named HTTPS lab ingress above. It is
an explicit scoped exception to the ordinary trusted-operator access guidance.

IAP TCP forwarding and OS Login permissions must be verified before connection;
this plan grants no operator IAM roles. OS Login with a VM service account also
requires the operator's service-account-user permission. Do not add broad roles
to work around a denial. [Google's IAP SSH documentation](https://docs.cloud.google.com/compute/docs/connect/ssh-using-iap)
and [OS Login setup](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin)
define those requirements.

## Acceptance evidence to retain

- UTC, source/configuration hashes, cloud installation ID and observed listeners.
- Actual cloud HUD response and browser view of the same Border installation.
- On-prem member enrollment and reconnect with unchanged application key;
  matching cloud membership/admission and HUD status, with TCP/TLS/admission
  recorded separately. Preserve both launcher observations.
- Negative identity, downgrade, exposure and member-to-member results; restart
  and relocation with stable identity and no work replay.
- A sanitized report plus private raw receipts. No token, private key or private
  topology is published. This one-owner pilot is not independent-organization
  operational acceptance or qualification of every platform.
