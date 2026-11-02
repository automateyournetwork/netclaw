# R01 runtime activation review

The owner explicitly delegated this runtime packet, including scoped pilot repairs
and restarts. Activation completed; see current verification and the execution notes below.

The delegated foundation and budget recovery are now complete. A refreshed
read-only plan reports **no changes**, with all11 managed resources present.
This packet covers the next exact effect: turning the empty pilot VM into the
requested control-only Border and privately accessible HUD, then qualifying
fresh on-prem transport participants. No new VM, firewall rule or public port.

## Original frozen activation packet (historical, do not replay)

## Material prepared locally

- Frozen source archive:14,054,745 bytes,850 selected source files. SHA256
  `eae562964574198881d2dd96de34ef1b04db212efd07995bb2d80c8de7434ca9`.
  Excludes repository `.env`, existing homes, testbeds, runtime state, node_modules,
  private keys and roadmap references. No root-environment secret values matched
  the archive during the local check. Exact file hashes are in private
  `source-v1-manifest.json`.
- Fresh cloud-only secret payload:9,833 bytes. SHA256
  `0e52f548c1bfb555f3af09a697ddf182ddd62044ccf6514e74bb36c394506e86`.
  Contains the new cloud installation/configuration, TLS/application keys and
  empty pilot federation state with approved external-peer trust/consent. No
  provider/device credentials, member private key or raw enrollment token.
- Fresh on-prem member and external Border homes remain private on the Mac.
  No service has started. The member's single-use token expires after24hours;
  check expiry before enrollment and never replay a consumed token.
- A fresh operator SSH key is prepared locally. Its public key will be registered
  with OS Login for30days. The VM's host keys came from authenticated Compute
  serial output and are pinned in a dedicated private known-hosts file.

[Material preparation](pilot/prepare-material.py),
[cloud activation](pilot/gcp/activate-runtime.sh), and
[federation](pilot/gcp/netclaw-r01-federation.service)/
[HUD](pilot/gcp/netclaw-r01-hud.service) units are available for review.

## Exact activation scope

1. Confirm the cloud secret still has zero versions and local ports14222,
   13000/13001 are free. Register only the prepared operator public key in OS Login;
   no IAM role grant. Open an IAP tunnel to this VM's SSH22 on local14222.
2. Use strict host-key verification and the selected OS Login identity. Capture
   host/listener baseline and refuse an existing source/home activation.
3. Add the reviewed cloud payload as Secret Manager version1. Upload only the
   frozen source archive and activation script through that SSH connection.
4. On the pilot VM, verify source hash and VM name. Install pinned Node24.19.0
   from its official archive with SHA256 verification, Python3.12 with repository
   dependency pins, and HUD dependencies from package-lock. Build the HUD.
5. Retrieve the exact secret version using the VM's workload identity and verify
   its digest before extracting into new `/var/lib/netclaw-r01/claw`.
   No static cloud credential is written to the VM.
6. Enable/start only `netclaw-r01-federation` and `netclaw-r01-hud` system units
   as unprivileged `netclaw-r01`. Federation listens on10.168.0.2:42101/42102;
   BGP14179, API14180 and HUD13000/13001 stay on loopback. Kernel route changes
   are disabled; there are no device/model credentials or executable workloads.
7. Forward HUD13000/13001 through SSH/IAP to matching local ports and verify the
   actual page/installation before presenting `http://127.0.0.1:13000/` as working.

The exact private driver prints this scope without executing by default:

```sh
python3 "$HOME/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/activate-driver.py"
```

The execution command, only after explicit owner delegation, is:

```sh
python3 "$HOME/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/activate-driver.py" \
  --execute-reviewed
```

That file contains the exact gcloud, SSH, SCP, secret-version and activation
arguments. Its source and material hashes are verified before mutation. Failure
stops the driver and records the outcome; do not rerun over partial activation.
Inspect and repair only this owned pilot within the reviewed scope.

## Qualification scope after activation

Use only the new on-prem member/external peer homes to run iN2N enrollment,
both member launchers/reconnect, NCFED approved-key/consent exchange, and the R01
identity/downgrade/exposure refusals. Transient test identities may enroll/revoke
within this pilot; no device/model/task execution is permitted. Capture matching
cloud membership, local key continuity and HUD status. Restart only the owned
pilot federation/HUD units when qualification or a scoped repair requires it.
No existing local installation is selected or stopped.

The cloud IP relocation remains a separate saved IaC plan and review against
actual state. Teardown also remains separately reviewed. This activation does
not start R02/R03 or authorize commit, publication, production migration or a
public HUD gateway. The IAP HUD is a single trusted-operator interface; cloud
model chat is unavailable in this control-only qualification installation.

## Execution notes (current)

The fresh OS Login key was registered for30days; authenticated IAP/SSH baseline
and strict host-key checks passed. Secret version1 and reviewed source transfer
succeeded. The initial build exposed an archive packaging omission: the HUD
imports `docs/reference/interfaces.json` and `documents.json`. Those exact public
source files were transferred with their hashes recorded; the resumed Linux HUD
build passed. No secret version or identity was regenerated.

The HUD API/page now responds through IAP with the new cloud installation ID.
The federation unit initially could not execute its root-created0700 Python
venv. A scoped repair grants only the `netclaw-r01` service group read/execute
access to the dependency environment and restarts this owned unit. Runtime
secret/home permissions remain0700/0600. The reusable bootstrap now includes
that group access. Actual member admission and browser acceptance remain pending.

## Verified runtime outcome

Both services run and actual Mac→GCP iN2N enrollment plus both launcher reconnects
pass. The token is spent/removed; the member key is unchanged. NCFED positive,
key/name/CA/consent refusals and consent recovery pass. IAP browser verifies the
same active member. See verification.md for receipts and scoped repairs, including
stack/readiness correction and external lower-AS ordering. The owner has since
requested an open read-only lab URL without login; public-hud-review.md contains
the separate exact public-ingress/IP-relocation packet. R15–R17 remain later work.
