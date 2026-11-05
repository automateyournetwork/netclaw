# R04b bounded development-pilot update

The owner authorized completing the actual local/cloud client flows and retaining
the usable pilot. The November 5 instruction requires a full stop after R04b.
This update creates no cloud resources, DNS records, IAM grants or new lifetime.
The existing December 1 stop and broader release hold remain unchanged.

Private preparation and execution records are under
`~/.local/share/netclaw/roadmap-r04b-20261104/deployment/`. They contain frozen
before/after hashes, authority baselines, payloads, one-use claims and progress.
Never rerun a claimed apply or restore a historical database over current state.

## Retained member

The only source change is the two-line additive `device-key` principal validation
in `protected_contract.py`; historical local/open-lab principal validation remains.
The source manifest, role manifest digest and runtime-artifact metadata follow that
change. The selected profile, provider/tool scope, credentials, keys, supervisor,
historical operation rows and evidence are preserved.

Root reviewed `member-update.py`, the exact source diff and packet
`dee46c5c5bdb1906a91ce3d678ef35dccfa918069de43bec6b4286a8a29143e4`.
The native role validation and fresh authenticated-member preflight passed.
The helper creates a durable exclusive claim, stops only the exact owned
LaunchAgent, exports a consistent stopped database as evidence, preserves the old
source tree, installs the candidate and starts the same LaunchAgent once. It
verifies unchanged authority/evidence and authenticated readiness afterward.
GAIT pre-change review: `fbeeb57c`. Final outcome is recorded in verification.md.

## Cloud Border and HUD

The candidate retains the fixed pilot installation and runtime identities. It
adds the native enrollment issuer, a loopback-only protected edge listener on
13007, the shared HUD handlers/assets and an exact `/mobile/ws` WebSocket ingress.
No raw daemon/admin route is exposed. The normal workspace gateway and inner HUD
remain running; only the owner federation and outer HUD require restart. Caddy has `admin off`; the exact owned Caddy service is restarted after candidate
validation. Its unit, TLS configuration and storage remain unchanged. No admin
API is introduced.

Root reviewed cloud packet `be2c556dcd06c3a1b0c2373bcca73715fd02f19b8ae4358c72c8a57462cb0370`
and helper `16e0f6ee1a18fa00e74689689ac46956b0bab02393c47609b7eb06cf61a28cc9`.
The 14-file staging and live preflight passed. The apply installed all reviewed
changes, then its strict post-check rejected the role startup timestamp. A separate
read-only settlement verified all installed payloads and preserved authority,
permitting only that exact observed timestamp change. No apply was repeated.
Pre-change GAIT review: `e3d4820a`. The existing frozen source
has one extra root-only Python bytecode file outside its 1,004-file manifest. That
discrepancy is recorded privately and the whole old tree is preserved; candidate
validation uses an exact new source closure. The historical operation authority,
member keys, nftables confinement and unrelated service identities must match the
fresh pre-change baseline.

## Recovery

The helpers refuse replay after creating their claims. On any interrupted result,
inspect the claim, progress, service identities, installed hashes and current
authority before deciding a further action. Old source/configuration is retained
for a separately reviewed recovery; database exports are evidence only. Neither
helper retries enrollment, approvals or provider/device workloads.
