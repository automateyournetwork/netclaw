# R04a persistent owner delivery — November 4

The retained connection is **GCP Border · Montréal** at
**https://r01-gcp-montreal.lobsternet.automateyournetwork.com**.
Use **Add Connection → Local / Cloud → Cloud → Name → URL → Connected**.
The extension discovers and pins the installation over trusted HTTPS. No user
sign-in, ticket, installation-ID prompt or access-mode setup is required.
Authentication/SSO/RBAC remain later roadmap work.

Current verification: the no-login Border and member migrations passed, the
owner-supplied replacement key is installed, and authenticated internal federation
is ready. The corrected private extension is installed in regular VS Code.
**Native connection, operation settlement and successful read/restart verification
remain pending because the Mac is locked.** The owner has been asked to unlock
normally; no password is requested. No completion claim substitutes for these checks.

## Retained deployment

The existing Montréal VM `netclaw-r01-20261101` (instance7647370903424740100)
serves the same HTTPS hostname. No new paid resources, resize, DNS, firewall,
service-account or IAM change was made. The actual Border is a native systemd
installation; its source/runtime bundle was updated without building a VM image.
Its private installation is `b164621c-a94e-4c28-a087-d9c9dabcce21`, running as
separate UID10010 with loopback HUD/API and strict federation transport. Actual
metadata and legacy-secret access denial remain verified. The old R01 home and
quiesced305,053,837-byte archive are retained, with four legacy applications
stopped/disabled. Caddy serves the new protected service.

A fresh Mac member, installation `c1b06ef1-bfab-40ed-87b9-3da65870ee0a`, uses the
existing NetClaw NetBox skill/MCP, OpenClaw2026.7.1-2 and Sonnet4.6. It enrolled
exactly once; its identity and profile remain fixed. The catalog supports only
NetBox device1 and prefix1 reads, each reviewed separately, with at most one MCP
and two inference calls. Member credentials never go to the Border or editor.
The owner-supplied replacement NetBox key is used; a temporary diagnostic demo
credential was never installed.

Keep the Mac awake, logged in and online with Docker running. Its dedicated
LaunchAgent supervises only this member; unrelated runtimes and the three original
running containers are preserved. Docker automatic startup, OS reboot/login
recovery and cross-client concurrent operations are not qualified. Use one
operation at a time. Both member and VM remain bounded to the existing
**December1,2026 pilot stop**. Disk/IP charges can remain afterward until reviewed
retirement. This intended deployment/profile is retained, not disposable cleanup.

The VM's former startup script repeated package installation at every boot. One
reviewed metadata fingerprint comparison replaced only that completed bootstrap
with an inert comment; all other instance metadata/resources and scheduling
remain unchanged. Exact original bytes are retained privately. Do not replay the
old pilot IaC/state over this owner deployment. No reboot was performed.

## Editor and operation behavior

Regular `/Applications/Visual Studio Code.app` is Microsoft-signed/notarized
version1.109.0, upgraded from1.108.0 with the app/user data backed up. The private
NetClaw extension remains version1.5.0. Its corrected VSIX SHA256 is
`6180d9f8ff15b62f3136587bfd78f6933f9865133fa2ed03f0d57251ac96449b`, built from
`db1654e9290cb36dbfc093aa0b2bb0de77c623e7`. The installed manifest and all67 other
payload files match. Existing settings, keybindings and14 other extensions are
preserved. This is the regular owner editor, not a development-profile substitute.

Selecting the active cloud profile now opens its view without disconnecting and
clearing the menus. Re-adding the same origin/installation updates the same
profile; a changed installation is refused. Use **NetClaw: Prepare Cloud Read**
for a new catalog read and **NetClaw: Recover Cloud Operation** for existing work.
Read the exact review before approving. Unknown work retains its reference;
never clear it or approve a replacement to bypass uncertainty. Local setup,
legacy Chat, arbitrary MCP/shell and device-write controls remain unavailable on
this protected cloud connection.

The explicit lab mode uses truthful `Unauthenticated lab operator` attribution,
not a user account or hidden session. Internal member mutual TLS remains service
transport. Historical approvals keep their original principal and authority.

## Retained failure and recovery evidence

The first actual editor device1 operation was
`5004c921-82d8-414d-ac70-a13b5b2a340b`, attempt
`3ae3be29-6bfb-4875-8cc0-0270b7dcc5b8`. It was approved once and made exactly one
provider request, one native MCP invocation and one NetBox GET, which returned403.
No object or MCP success result was fabricated. The original unknown pause and
all source/approval/HTTP witnesses are retained. The owner subsequently confirmed
the old credentials were dead; the response body itself was not retained.

The recovery correction validates exact native401/403 failure evidence, original
signed approval/attempt, source/policy, timestamps and stopped containers before
settling that same attempt through the existing signed FAILED/GAIT/ACK path.
It makes no provider, MCP or NetBox call. Missing, conflicting or genuinely
uncertain evidence stays blocked. The replacement credential was checked only
against authenticated API-root metadata before the separately approved new read.

Initial installation also retained a known internal Python `lib64 → lib` archive
refusal and a readiness probe missing its required Host header. Completion-only
helpers verified the exact partial state; neither installation nor effects were
blindly replayed. The final public verifier records Caddy's existing unmatched-Host
response as200 with an empty body and no content type; the protected backend
rejects wrong Host with403. Neither result exposes runtime/catalog data.

The member migration also stopped before replacement because Darwin refused to
move a0555 directory between parents. A private fixture reproducedEACCES and
proved temporary owner-write resolves it. Exact completion packet603a6d7c verified
the original stopped phase, directory identities, source closures and DB backup;
it moved only the two reviewed source roots, restored0555, installed the four
reviewed files and bootstrapped the owned member once. Actual result passed with
authenticated federation and unchanged historical operation. The original failed
claim is retained; no original apply or database restore was repeated.

## Mobile and scope

The existing Mobile QR flow is not supported by this protected cloud Border
as-is: HUD QR issuance, trusted WSS enrollment and protected-operation integration
are missing. [R04b](../../docs/roadmap/issue-310/briefs/R04b-cloud-hud-mobile-enrollment.md)
proposes carrying forward the existing scanner/device-key enrollment. No
replacement manual wizard or user-authentication scheme was added. R04a's existing
separate Mobile cloud screen has bounded no-login compatibility, verified by70
source/widget/regression tests. Historical November3 iOS simulator reads/restarts
remain tied to their original source; new QR/physical-device qualification is not
claimed. See [the QR assessment](mobile-qr-assessment.md).

## Evidence and release limits

Private receipts, backups and authority stay under
`~/.local/share/netclaw/roadmap-r04a-owner-20261104/`, with GAIT branch
`r04a-owner-working-connection-20261104`. Never replay spent enrollment, plans,
approvals or current-state archives. Cloud runtime source is frozen at7f7df355;
the member keeps its c7b70edd closure with seven reviewed7f7 runtime patches and
unchanged profile-pinned adapters. Root integrated source is70240ab2 before this
handoff documentation. [Verification](verification.md) records exact evidence.

Source1.18.4, extension1.5.0 and Mobile1.0.3+6 are unchanged. No public release,
Marketplace publication, tag, blog, general cloud rollout or R05 work occurred.
Human evidence acceptance remains separate before the next roadmap stage.
