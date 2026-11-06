# NetClaw R05 guarded Ollama members

Maintainer qualification materials for Spec176. These are NetClaw OpenClaw
members using the existing strict iN2N transport, protected native MCP, signed
approval/result/ACK protocol and clients. No Tailscale or Thermidor service,
package, image, installation identity or private state is required.

Thermidor Spec004 supplied the tested design, public artifact pins and failure
lessons recorded in `specs/176-ollama-members/research.md`. The public Ollama CPU
artifact inventories and Qwen3 manifest are retained with their notices. NetClaw
builds and qualifies its own images and operations. Historical Thermidor outcomes
do not count as NetClaw acceptance.

## Immutable artifacts

`artifacts.py` verifies the entire selected public model/CPU closure before
copying to a fresh private directory. It refuses changed hashes, extra model
files, unsafe symlinks and alternate manifests. It never downloads or runs a
model and never copies a prior runtime home. Existing public caches may supply
bytes only after the same verification as new downloads.

`Dockerfile.model` builds from the reviewed immutable Python/Trixie base plus the verified
official Ollama 0.40.11 CPU bytes. The image retains Ollama's license and CPU
notices; the pinned model includes its Apache-2.0 license blob.
The copied official CPU dependencies require at least glibc2.38; a Bookworm base
fails before model startup. The final reference's Trixie base is required.
`Dockerfile.guard` layers the current NetClaw scripts and pinned PyYAML wheel onto
the reviewed NetClaw official DefenseClaw 1.0.4 image. Record actual final image
IDs, base IDs, wheel hash and build logs privately. No secret enters either build.

## Selected execution and capacity

| Component | Local ARM64 IPv4 | Cloud AMD64 IPv6 |
|---|---|---|
| Model | Qwen3 0.6B, pinned manifest and five layers | Same |
| Model limit | 2 GiB, no swap, 2 CPUs | 2 GiB, no swap, 1 CPU |
| Agent limit | 1536 MiB, no swap | 1536 MiB, no swap |
| Conversation | 16384 context, 1024 output, two inferences, one native call | Same |
| Inference / operation | 60 / 180 seconds | 120 / 180 seconds |
| Keep alive | 30 seconds | 120 seconds |
| Transport | Existing strict iN2N | Existing strict iN2N |

The model API is loopback-only inside its private network namespace. The owned
guard joins that namespace with a different UID. No port is published. The trusted host forwards to guard loopback using bounded
Docker execution with the request/capability on stdin; model port11434 and
management ports remain private.
The namespace firewall limits the model's private workers and guard access.
NetClaw checks current container identity, image, environment, mounts, limits,
namespace and actual firewall digest before each model forward. The agent uses
the existing isolated executor/relay and only its single approved native tool.

`qualify.py prepare` creates only explicitly named, fresh owned model resources
and records real probes before emitting a usable profile. UID stand-ins and
container-network probes are identified as such. Actual agent, broker, Border,
sibling and external-vantage checks remain separate acceptance evidence.
`inspect` checks the owned resources; `stop` is restricted to recorded ownership.
Never replace an uncertain member/runner latch merely by choosing a new operation
ID. Retain the original claims and verify owned-process recovery first.

An owned model restart changes its namespace and can change Docker's generated
DNS NAT ports. Preserve the old profile, full firewall ruleset and consistent
runner/inference databases. Verify the original worker/model processes stopped,
then reattest the same owned model with fresh positive and negative probes. Bind
the new confinement receipt into a newly derived profile. The existing
`RunnerLatch.recover` records the verified stop; its idle-only `rebind` then
archives the prior row and exact profile-transition receipt atomically. Keep
original operation outcomes and unfinished inference claims unchanged. Recovery
does not invent a response or authorize replay.

Only resume the same member after real-UID source/profile validation and durable
history checks. Preserve original file ownership/modes when replacing source;
an077 umask masks requested read permissions during file creation. A later helper
failure requires inspection and continuation of remaining steps, not replay of
completed stop/start/probes. Update any owned cleanup profile pin and export paths
to the verified current profile. Spec176 verification records the actual scoped
recovery and its retained failed helper attempts; those spent packets are evidence,
not reusable activation or maintenance commands.

## Execution review and preservation

The owner authorized source implementation and isolated local qualification on
2026-11-05. Local preparation uses fresh private state and a fresh model network;
it preserves existing Docker containers, networks, installed clients and runtime
homes. Only canonical documentation-prefix calculations are permitted. No device
command or hosted-provider call belongs to this profile.

The existing GCP Border has 2 GiB total RAM and approximately 1 GiB available at
preflight, so it is not the model host. `../cloud/gcp/r05/` prepares a separate
8 GiB member with private authority, no public model listener, no service-account
scopes and finite expiry. The saved plan, exact resources, current quoted cost,
baseline and rollback must be reviewed before cloud apply. A budget alert is not
a spending cap. Existing Border/member identities and historical rows remain.

Private evidence is under
`~/.local/share/netclaw/roadmap-r05-20261105/`, including artifact/build receipts,
capacity observations, exact saved plans, per-operation native evidence and
baseline/rollback records. Source deployment must compare current identities and
authority rows before and after; rollback restores source/configuration only,
never old operation or enrollment authority. Unknown applies are inspected, not
replayed. Export and verify evidence before retiring disposable resources; retain
the intended usable member through its approved expiry.

## Artifact coherence

The existing subnet skill documents the explicit bounded summary capability and
its limits. The installer patch is opt-in through
`NETCLAW_SUBNET_SUMMARY_PROFILE=1`; `.env.example` records that non-secret switch.
The ordinary installer/catalog, default model/config and SOUL are unchanged:
R05 adds an explicit protected profile, not a new general-purpose MCP server or
default provider. Public README, setup guidance, versions, releases and rollout
copy remain held under the roadmap policy. See Spec176 verification for actual
completed evidence and open acceptance; these materials do not imply deployment
qualification on other platforms or with other models.
