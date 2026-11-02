# R02 local qualification packet

This is the owner-delegated, read-only local acceptance packet for Spec 171/R02.
It creates fresh private homes and local Docker processes. It changes no cloud
resource, existing installation, device configuration, release or public guide.
The roadmap's human R02 evidence gate remains after qualification and before R03.

## Exact initial operation scope

Two separately reviewed browser operations select the same verified lab R1:
one OpenClaw member and one Hermes member, each using Anthropic
`claude-sonnet-4-6`. Each operation permits only
`pyats_run_show_command({device_name: "R1", command: "show version", timeout: 60,
retries: 1})`, at most two provider dispatch claims and one tool execution.
The second model call is permitted only after retained tool evidence. Approval
expires after five minutes; each model call has a 90-second deadline and the
whole tool child has a 120-second deadline. No command retry or automatic new
operation is allowed after uncertainty. A parser uses the captured output and
cannot run the command again.

The OpenClaw operation deliberately loses its submit reply after durable member
admission while preserving the channel for effect authorization. The Hermes
operation deliberately loses its result-ACK reply after the member
durably records that ACK. Restart/reconciliation must preserve the same approval,
attempt, receipt and ACK and must produce no additional inference or device read.
Refusal probes use the fresh homes and must not reach an unauthorized effect.
HTTP probes may prepare and deny an operation but cannot approve one. Post-run
wire probes use completed authority, altered signatures or an honestly expired
signed specimen; they must leave provider/tool evidence unchanged.

## Pinned components and enforcement

| Component | Qualified revision / immutable local image |
|---|---|
| OpenClaw | 2026.7.1-2; `sha256:813cf7801f24c5fe62877cf6dec50cbdcf2a9ab751dde8b2bf10c07c98ef06d9` |
| Hermes | v0.21.6, source `818c13be1dc4fd28987e1e881a9408224afd4535`; `sha256:c2db95652c69a7cce831fa92cac3412f153561780e08ab256b0e7bc1a78e3132` |
| Fixed-route relay | `sha256:58a0dddf72a36b5cc09227cb962498360b18ad420b09f107b973bc2a0bae09fc` |
| Official DefenseClaw and durable provider fence | DefenseClaw 1.0.4; `sha256:5aec2081925656378df61a978c634f266e743dc5f77bb08cad07bee37a406aa1` |
| Guard configuration | `1fdc7ab50a660051a1f5283eec65ff3d947f05b6518602157d8e455a8f7fa26b` |
| Official 80-file policy manifest | `0c9ad2c85ab64a9965f74076592ff8cbad5f98815a29ef1d398ddfe8c67eaf76` |
| Upstream pyATS MCP | `4a3c1e3404d5ed7a78cb094bf26d2a49065497d9` in a fresh Python 3.12 environment |

The official guard uses action mode, the strict rule pack and local regex
enforcement. It has no observe-mode fallback, hosted judge or additional model
selection. Hermes uses the qualified OpenClaw-compatible HTTP guard adapter and
exact MCP broker; native Hermes hook enforcement is not claimed.

The signed profile must bind the actual runtime image, guard configuration,
policy manifest and host adapter revisions. The tool digest must bind its schema
and execution source closure. Final generated bindings and exact file hashes are
retained in the private packet before activation. A changed pin refuses execution.

Final unused configs were regenerated after source `d6750cba` and the corrected non-root policy image and passed actual
`revision_bindings()`/`validate_execution_bindings()` without executing a process:

| Binding | SHA256 |
|---|---|
| OpenClaw runtime profile | `bb166ccc76b7b60307e896c8609d3ab93847b758991bf80f3a946280edb4ae08` |
| Hermes runtime profile | `101c503fb87740869a4db4031d517f2c48f14d748862f1ae5df5ea931ab1bcfb` |
| Guard policy/config/image contract | `f44bdecaac8115c77b4419cd46c8169c6287883f9407f2951faae9e6d205ec05` |
| Tool schema and enforced source contract | `aeda96b8966036936f9d8ac28f98483e6f9a54126c7fdda402142415880a093f` |

The private runtime JSON hashes are `74ea15fa…` and `4426d1b4…` respectively;
full hashes are retained in `live-qualification/runtime-bindings.json`. The
unused earlier bindings remain archived. Fresh-home state paths do not change
the executable contract; they remain private and installation-owned.

Agent containers run as the owner UID, with read-only root filesystems, all Linux
capabilities dropped, no-new-privileges, bounded memory/CPU/PIDs and a dedicated
internal network. Only the relay can reach the fixed host listener. There is no
Docker socket, testbed or credential mount in the agent. The trusted host and
Docker daemon remain part of the trust boundary; this is not a claim of protection
against a compromised host administrator.

Each operation has its own guard container and provider ledger. Only that guard
mount receives the existing owner-authorized Anthropic key. The official guard
child receives a non-secret provider sentinel; its trusted container shares the
runner's UID/filesystem. The outer model process and Border receive no provider
or device credentials. The native tool child receives only the three selected
device credential aliases. All secrets remain outside Git in private files.

## Device identity and preservation

Fresh authenticated CML inventory confirmed the original lab nodes booted. An
exact-node console read verified R1's management interface and RSA public key;
the SSH endpoint presented that same key. The dedicated known_hosts bytes are
part of the signed endpoint binding. SSH uses no ambient client configuration
or global known-host file and requires the pinned host public key.

The original repository testbed remains SHA256
`59f100edb6128176a4df8e6567eae52b510a9b6778e45bc94856f2d51172d512`.
The alternate owner testbed is also preserved. Qualification uses a fresh
R1-only inventory, frozen source/testbed/host-key copies and captured output.
The baseline console reads were only `show ip interface brief` and
`show crypto key mypubkey rsa`; no device configuration or node lifecycle action
was taken. Exact private addresses, credentials and transcripts stay local.

## Evidence, stop and limits

Private packet: `~/.local/share/netclaw/roadmap-r02-r05-20261102/live-qualification/`.
Each run creates a new directory and retains native worker source hashes, signed
records, provider dispatch counters, raw/parsed tool evidence, containment
inspection, browser screenshots, GAIT references and owned-process cleanup.
The original R01 homes and cloud pilot remain untouched.

Only processes/containers created by this packet may be stopped. Native workers
and HUD launchers have scoped stop markers; containers retain their stopped
state and evidence. Unknown outcomes retain spent authority. A failed run is
recorded honestly and never converted into success by replaying an approval.

This packet is not acceptance evidence until the real operations, recovery and
independent review pass. It qualifies these two pinned Mac/Docker harnesses and
this IOS-XE read only. It does not qualify arbitrary providers/models, Linux/WSL,
device writes, a cloud runtime, general user identity, SSO or RBAC.
