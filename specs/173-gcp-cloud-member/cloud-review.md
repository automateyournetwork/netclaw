# R04 exact cloud review — 2026-11-03

The existing owner delegation covers this finite activation and cleanup. Fresh
run `20261103-6e8af1` preserves R01 and does not consume retired R03 state.
Initial deployed source was `8c6b943408899a9e636b1ab457c5c9b1f4fe072e`;
final qualified runtime is `81b35fc9869b3e0c09cd6936bbe3130c4452f620`.
Activation, three workloads, actual recovery, private evidence preservation and
owned retirement passed. Earlier sections record the exact
pre-execution reviews, with actual outcomes in verification.md.

The reviewed foundation plan creates18 owned resources, with no updates,
replacements, imports or deletions: isolated VPC, two /28 subnets, separate
service accounts and reserved addresses, three empty secrets and scoped accessor
bindings, three firewalls and two Shielded Ubuntu24.04 AMD64 VMs. The pinned
Canonical image is `ubuntu-2404-noble-amd64-v20261024`. Border is e2-small/20GiB;
member is e2-standard-2/40GiB. Only IAP22 ingress is initially admitted; Internet
egress and application ingress remain closed until actual host controls pass.

The fixed window ends2026-11-05T17:03:13Z. Both VMs have automatic restart disabled,
scheduled STOP and auto-delete boot disks. Host quota/expiry controls precede the
separate six-firewall activation. STOP alone does not remove disk/address costs;
reviewed teardown after evidence export is required.

Fresh gross CAD50 monthly project budget observation covers both roles with
50/90/100% current-spend alerts and excludes credits. It remains unchanged.
Conservative VM/disk/address base for48h is CAD7.13, excluding preserved R01,
traffic, tax, secrets and bounded model calls. Alerts are not hard caps; no
remaining-credit or invoice claim is made. Two exact NetBox reads and one local
subnet calculation permit at most six hosted model calls in total.

Private saved plan SHA256:
`7b80304158c09ea9153ca779e6b3f29e61f5ce7c268fee16cfcf7dab98847aee`.
The exact source/tool/state hashes and independent before-inventory are in
`~/.local/share/netclaw/roadmap-r04-20261103/cloud/`. Initial state was absent.
The runner spends a durable claim before its sole apply; failure/unknown outcome
requires inspection and a separately reviewed recovery, never blind replay.

Source readiness:643 protected/member/posture/host tests pass, one skip and26
subtests;459 HUD tests pass. Three native AMD64 images and the fresh offline
Border identity validate. None of this establishes actual cloud workload,
credential isolation, browser acceptance or cleanup; their actual outcomes are
recorded separately in verification.md.

Source1.18.4/extension1.5.0 and the complete-roadmap release hold remain unchanged.

## Actual host and network activation review

Both immutable host installs and independent GCP kernel namespace proofs passed.
The main Border and member guard allocations and fixed expiry timers are active.
Actual source/venv hashes match the frozen package; Docker installation was offline
with startup masked until guard activation. The reviewed activation plan SHA256
`d8a93741851ae6dc95ac0706c2f6b2b1a0c098657ffac0ac7385dc8061998135`
has exactly six firewall creates and18 no-ops. It admits Border HTTPS, iN2N only
from the member's reserved /32, member dial only to Border42102, exact public
DNS53 and role web egress. Private-destination deny retains higher priority.
No member application ingress or project IAM grant is added.

Owned R04 DNS creation/readback succeeded; R01 record is byte-for-byte unchanged.
Operator secret version1 is bound only to Border. Provider/NetBox secret version1 was subsequently projected only to the new
member after its actual protected enrollment supplied the installation ID.
GAIT448db2f9 records host work and the network plan before execution.

## Reviewed startup correction and retained failure

The first approved workload stopped before provider or MCP effects with retained
unknown authority. Paired actual-host snapshots independently verify that state;
no original approval is replayed. GAIT910fa93a records the finding.

The reviewed replacement source is81b35fc9869b3e0c09cd6936bbe3130c4452f620. Its
1002-file runtime closure changes only scripts/protected-inference.py to provide
the fixed localhost:80 virtual authority required by the actual MCP SDK. Qualified
HUD/dependency bytes remain identical. The new AMD64 relay retains all prior
layers plus the changed script. Separate real SDK/OpenClaw discovery and61 tests
pass with zero tool/provider calls and hostile-authority rejection intact.

Exact private migration packets bind both original roles, source/profile/registry
hashes, identities, paired preservation receipt and spent guard allocations.
Only application units stop; guard/expiry/Docker never restart. The source exchange
is atomic; the multi-file metadata change is fail-closed while applications are
stopped. Original source/profile/role bytes and all three stopped failed-attempt
containers remain preserved. Native role and all three runtime bindings must
validated before application restart. Actual check/apply/start receipts passed.
A later packaging-only correction uses imagee01e4f557d47/profile6d42cf14 after
nonroot image qualification; both original unknown attempts remain retained.
All three final protected workloads and independent recovery verification passed.

## Completed exact teardown

A fresh plan from the authoritative current R04 state contains exactly24 owned
resource deletions and no other actions. Saved plan SHA256
`aee78980e3d96faf93c6db3ca8521084a35005e20f9a46fc847ddaae7be0d4ea`.
The complete private export manifestd081ad72 and independent review24d59ae3
passed before its sole apply. Receipt5c03870b reports exit0 and current state
contains zero resources. DNS and temporary OS Login retirement passed; actual
12-category inventorycc2a59ad found zero R04 residues. R01/budget preservation
report7fe5955c passed with its explicit metadata scope. No R01 resource or shared
budget was managed by this plan. The original spent plan is never replayable.
