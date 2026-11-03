# R03 runtime — actual qualification complete and retired

2026-11-03: actual activation, strict enrollment, four protected reads, loss/restart
recovery, owner controls and independent signed/GAIT verification passed. The
R03 deployment was then retired after verified current-state export. See
[verification.md](verification.md) and [teardown-review.md](teardown-review.md).
[activation-delegation.md](activation-delegation.md) superseded earlier pending
permission/billing language. The historical packet below is spent, not a recipe
to reactivate the retired deployment.

Actual Ubuntu24.04 AMD64 installed only three missing verified offline packages:
python3.12-venv3.12.3-1ubuntu0.17, python3-pip-whl24.0+dfsg-1ubuntu1.3 and
python3-setuptools-whl68.1.2-2ubuntu1.2. No upgrades/removals. Frozen source/runtime
and the intended installation identity were preserved. Actual kernel quota/rate,
service confinement, least-privilege IAM and direct TLS boundaries passed.

A dormant eN2N registration mismatch caused the first federation start to exit.
The scoped CAS1→2 repair changed its application identity/transport-public-key
binding and the role registry digest only; iN2N, source, protected profile and all
keys remained unchanged. The accepted final registry SHA256 is
`4d5e451dfb61f40b2cf5c4026fc446e2eb2bfe2a54fd61c9dbb4893fb4735d79`;
role SHA256 `86f1ee5d24a619787c1af0faf6d336024e6d88ea51fbf14b07f808d57fd2e179`.
Failed helper/start attempts remain retained without device/model effects.

Fresh member installation `9fcc74ba-72b9-44b5-8bed-1d42fc82b96d` enrolled outbound
once as `r03-20261102-a91adf/onprem-pyats`, preserving generation
`415594e7-cf75-407f-8edf-ba065579b8ff` through actual restart. Four immutable profiles
used local credentials, OpenClaw2026.7.1-2 and Anthropic Sonnet4.6. Exactly four
`show version` effects/eight provider calls returned parsed IOS17.18.2 and durable
ACKs; zero extra effects on loss, browser recovery or owned service/member restart.
R1's console-backed host key and the other three existing owner pins/CML metadata
have distinct recorded provenance. Original inventories and known_hosts unchanged.

Actual receipts live under private `activation-20261103/`, indexed by
`cloud-runtime-final-evidence-index.json`, `onprem/lane-completion.json` and
`hud-evidence-lane-completion.json`. The current-state archive in
`final-preservation/current-r03-state.tar` retains the final registry, identities,
closed SQLite, manifests and edge/host evidence. It contains secrets and is not
an activation payload. Do not restore the old first-create archive over it.
All R03 cloud services/resources, DNS/key and local worker/container/network
resources are retired. R01 remains unchanged. Human acceptance is the only R04 gate.

## Historical preparation record — superseded, not executable

2026-11-02. The local preparation and independent source reviews are complete.
This is not the final activation delegation: the new foundation does not yet
exist, so actual VM/OS package delta, public IP/DNS and Secret Manager version
remain unknown. No cloud upload, listener or protected provider operation occurred.
The cost and exact-resource gates in cloud-review.md remain open.

## Preserved first-activation Border

Private packet:
`~/.local/share/netclaw/roadmap-r03-20261102/cloud-runtime-staging/README.md`.
Authoritative prepared state is `bootstrap-fbd41cb1-final/`, installation
`0d02acd4-4349-45a8-951e-215f91a1174e`, Risk `r03-20261102-a91adf`.
Preserve this intended identity; do not regenerate it or replay its archive over
an active home. Earlier incomplete directories are explicitly not activation inputs.

Production initialization created independent self/CA/hub/transport keys and
owner authority, with no enrolled member, ticket, session, model or executor.
The control-only profile, empty environment files and private schema2 registry
validate. iN2N uses the exact reviewed
`r03-gcp-montreal.lobsternet.automateyournetwork.com:42102`, bound to planned
private10.172.0.2. eN2N remains dormant/loopback. DNS must later point to the actual
new foundation address; no public IP is guessed. Private federation transport
certificates are separate from public Caddy HTTPS certificates.

| Prepared input | SHA256 |
|---|---|
| Source archive, runtime commit fbd41cb1 | `c3a8dba7617ac7a23d12a6964bcc0499560d0a43cb12db45386cfadc19f4c7e5` |
| Private initial-state archive | `ee4ff95172d865071beaab39da07bf9201f7563d04d78e792e5a08ece09d5250` |
| Separate cloud-only operator payload | `c1db15f570cbf82a85acf92a8c72672532e821c8a025ae0d7bcc2dc5d1fac967` |
| First-create install packet | `392653eb4de377770503daa9ce8137615b723fdb9e7a56dde1642ab77ad19470` |
| Audited first-create helper | `5e0bd110ec3058481a91195ccf2ace88aa8fb38a052f0272eada84c3eb2e7ff7` |

The four-archive upload is98,919,041 bytes:994 immutable source files,16 HUD assets,
frozen LinuxAMD64 dependencies and private initial state. The state archive
contains private keys and owner state and must stay private and use reviewed IAP/
SSH transfer only. The separate operator payload is uploaded only to the new
cloud secret; record its exact numeric version, never `latest`. No R01 material,
root environment, provider key or device credential belongs on this Border.

Actual network-disabled LinuxAMD64 proofs passed as a dedicated nonroot UID:
role/source/venv validation; first-create installation; wrong-hash refusal before
claim; replay refusal; production no-executor factory with a synthetic operator
token; actual prepared certificate chains/SAN rejection; and protected asset load.
Independent review verified all archive/source/asset hashes and closed claim-parent
fsync and supplementary-group findings. No identity regeneration was needed.
These are offline proofs, not deployed cloud/TLS/network evidence.

## Four-device on-prem preparation

Private `cml-readonly/` has all four actual baseline receipts. R1 uses authenticated
console-to-SSH RSA matching. R2/SW1/SW2 use strict native SSH with preexisting owner
pins plus authenticated CML exact-node metadata. Current expected hostname#,
management interface/address and returned RSA key match. Their historical pin
establishment is unknown; they are not relabeled console proofs. Corrected switch
addresses are retained privately. Original inventories and owner known_hosts are
unchanged. No configuration, lifecycle action, implicit enable or model call occurred.

The diagnostic command set was only `show ip interface brief` and
`show crypto key mypubkey rsa`. It is separate from the four future protected
show-version approvals. Native image availability was rechecked read-only:
qualified OpenClaw, relay and guard hashes remain present as LinuxARM64 images.

Private helper packet and evidence:

- `four-device-member-builder.md`: first-create offline profile builder,37 tests
  independently passing. Actual four host-key inputs validate. The pending input
  manifest deliberately has null cloud/enrollment fields and is not executable.
- `member-worker-review.md`: tokenless same-key strict cloud worker,21 tests;
  transaction-consistent SQLite/file snapshot adapter,10 tests; independent
  cryptographic receipt core,25 tests. Independent review closed a shutdown-task
  supervision gap. No worker was activated and no member profile was installed.
- `member-runtime-preparation.md`: one fresh OpenClaw/Sonnet4.6 member, four
  immutable one-device profiles, one separate approval per show-version, at most
  two provider turns and one SSH command per operation. No local Border fallback.

The fresh member must first complete the strict enrollment-only CLI against the
actual cloud authority. A durable attempt is spent before network use; unknown
outcomes are never reenrolled/replayed. Only actual successful enrollment
generation/public certificates can complete builder inputs. Device credentials
stay in the scoped member file; the Anthropic key stays in the separate trusted
guard file. No model/provider/device credentials reach the Border.

## Final activation and acceptance still required

After exact foundation delegation/apply, capture actual VM identity, image,
package versions, root-controlled path ancestry, selected network manager and
kernel quota/TBF support. The offline150-package cache is not blanket OS upgrade
authorization. Freeze only a necessary exact package delta, actual SSH/IAP
transfer commands, numeric secret version and state-derived DNS/firewall plan.

Install and verify closed boot/network/expiry controls before public activation.
Then project the exact secret, validate/start federation and wait for its real
private bridge descriptor before starting HUD/Caddy. Never fabricate the descriptor.
Verify public trusted HTTPS and owner/session/Origin/CSRF/route refusals before
accepting any execution. Freeze operation-ID-bound loss drills before approval;
recovery may query/reconcile retained state, never repeat a spent effect.

Complete four real browser approvals, exact native/provider transcripts, signed
results/ACKs, GAIT/cloud provenance, negative controls, restart recovery and
unchanged counters. The receipt adapter intentionally reports qualification:false
until those independent evidence gates are supplied. Export actual SQLite backups
and audit closure before separately reviewed R03-only teardown. Then verify no
billable R03 residues, unchanged R01 state and obtain human R03 acceptance. R04,
versions, releases and public cloud rollout remain held.
