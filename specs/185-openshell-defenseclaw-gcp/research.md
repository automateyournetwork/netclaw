# Research: GCP Borders and HA mesh inside OpenShell and DefenseClaw (R09A)

Read-only research. Nothing was installed, started or created; no secret values were read. Repo facts cite files; upstream facts cite the sources listed at the end and are marked **(unconfirmed)** where a page did not say.

## Headline

The literal reading ("every Border and mesh process runs inside an OpenShell sandbox") is **not achievable with qualified code as written**, for documented reasons (D1). What **is** achievable, and closes the R09 gaps that motivated this stage, is a layered design: OpenShell for the workspace backend and chat gateway (where the provider key lives and where an LLM agent runs), DefenseClaw on every model path, and host/container confinement for the HA core (Border role, ingress, etcd, member executor). That is a decision for the owner at the plan gate (D2). Two cheap experiments (E1, E2) decide whether a deeper OpenShell placement is even possible.

## D1 - Per-component mapping: current confinement vs OpenShell

OpenShell facts that drive every row (upstream docs): the workload keeps `network=none` on Docker/Podman; there is no host networking and no public inbound; the supervisor mediates all egress (policy-evaluated, credentials injected by the supervisor, "the sandbox holds ... no provider credentials"); every workload TCP/UDP socket is bound to the sandbox loopback so it "accepts connections only from inside the sandbox network namespace"; inbound is only through gateway-mediated `openshell forward` / `service expose` (documented for loopback browser traffic); running a container runtime inside a sandbox is not documented; default workload identity is uid 1000; Landlock ABI 3 (Linux 6.2+) is required and the launch **fails closed** without it.

| Component (R09 unit) | Today (repo) | Can sit inside OpenShell? | Blockers |
|---|---|---|---|
| HA Border role (`nc182-border`, uid `nc182`) | systemd unit; launcher validates root-owned immutable source + venv manifests, uid ownership, canonical paths; listens 7443 (internal IP), 7444 (public alias on `lo` + iptables DNAT), 8444 (loopback); etcd client to 3 voters on 2379 | **No, as written** | Sockets are loopback-only in the sandbox, so peers cannot reach 7443/7444; manifest `host` is both bind and dial address (`ha/factory.py`, `ha/node.py`), and the internal/public IPs do not exist inside the sandbox; NCFED/iN2N use end-to-end TLS 1.3 with exporter channel binding, which breaks if the supervisor terminates TLS and is only safe if egress/forward is raw TCP **(unconfirmed)**; launcher's uid/immutable checks assume a root-owned tree and the service uid, not sandbox uid 1000 |
| Public HUD ingress (`nc182-hud`, 443) | Node HTTPS front, proxies to loopback product server | **No** (public listener) | Public inbound 443 is not an OpenShell concept; keep the front outside, sandbox what it fronts |
| Workspace backend (`nc182-wshud`, 127.0.0.1:3001) | separate uid `nc182ws`, frozen read-only tree | **Yes** | Needs a loopback hop from the (outside) ingress via `forward`/`service expose`; needs an image with Node + the frozen backend tree |
| OpenClaw chat gateway (`nc182-gateway`, 127.0.0.1:18789) | `nc182ws`, `provider.env` in its environment, metadata server blocked by iptables | **Yes - best fit** | Egress only to `api.anthropic.com:443`; credential injection by the supervisor removes the key from the agent's reach (closes R09 key-exposure finding); needs OpenClaw 2026.7.1-2 + DefenseClaw plugin compatibility (unconfirmed, E6) |
| Hosted guard / per-operation containers (members) | Docker, created by `protected_docker.py`: `--read-only`, `--cap-drop ALL`, `no-new-privileges`, non-root uid, pids/memory/cpu limits, `tmpfs` noexec, internal relay network, publish `127.0.0.1::4000` | Already a confined container; **not a candidate** to nest in OpenShell | Executor needs the Docker socket (`local_docker_socket_required`); OpenShell does not document Docker inside a sandbox |
| Member role (executor) | host process on the member machine (Mac in R09) | **No** | Same Docker-socket dependency; it must create per-operation containers. Existing spec 057/165/166 host confinement is the control |
| etcd voters | Docker container, host network, mTLS on 2379/2380 | **No** | Host networking is explicitly unsupported; peers must reach it directly |

Decision: record an explicit disposition per row (FR-019). Only the workspace backend and gateway go inside OpenShell; the HA core keeps host/container confinement and gains DefenseClaw-guarded model paths. The repo already made this call once: spec 057 R2 rejected OpenShell for live-infra members ("empty, network-egress-denied containers"; host systemd confinement chosen instead) and `docs/N2N-RISK.md` says OpenShell is optional and the Border is not confined by 057 (optional `border-harden.py` uses OpenClaw's Docker sandbox, network `none`).

What has changed since 057: OpenShell now offers policy-mediated egress with per-binary rules and supervisor-held credentials, so a *loopback-only, one-egress-host* component (the gateway) is now a good fit; a *peer-facing listener* (the Border) still is not.

**Alternatives considered**: sandbox the Border role with a raw-TCP forwarder in front (only if E2 shows raw TCP + exporter binding survive; also needs a product change, D9a); run the ingress inside an OpenShell service expose (rejected: plaintext loopback HTTP only, not public TLS); replace systemd confinement with OpenShell everywhere (rejected: breaks the immutable-launcher model and Docker use).

## D2 - OpenShell install, pin, host sizing; feasibility and fallback hierarchy

Facts: install is `curl .../NVIDIA/OpenShell/main/install.sh | sh` or `uv tool install openshell`; supported hosts Debian/Ubuntu x86_64 and aarch64 plus macOS (Docker Desktop); runtimes Docker v28+, Podman 5.x, Kubernetes 1.29+, MicroVM; current docs describe a gateway + supervisor + sandbox model with no GPU requirement. The repo's older docs and `scripts/netclaw-secure-start.sh` describe `openshell gateway start` as a K3s cluster inside Docker, with `openshell sandbox create --name X --from <Dockerfile dir>` on the base image `ghcr.io/nvidia/openshell-community/sandboxes/base:latest`; the pinned/installed version is **not recorded** in the repo (`defenseclaw-enable.sh` installs from `main` unless `OPENSHELL_REF` is set, behind a user-supplied installer SHA-256). The repo's secure-start script may therefore be written against an older CLI than upstream documents now (E7).

Host sizing: **Kernel is the first gate.** Landlock ABI 3 needs Linux 6.2+. The R09 VMs were Debian 12 (kernel 6.1, ABI 2) - OpenShell would refuse to launch there. Debian 13 (6.12) or Ubuntu 24.04 (6.8) are the candidates; exact GCE image kernels are **unconfirmed** (E1). Docker v28+ is also newer than Debian 12's `docker.io` 20.10, so Docker must come from Docker's repository. Memory: no upstream sizing; e2-medium (4 GB) already carried Border + etcd + HUD + workspace + gateway at ~1.5 GB used in R09, and OpenShell gateway + supervisor + a sandbox add overhead - plan e2-standard-2 (8 GB) and measure. Nested virtualization is only needed for the MicroVM runtime; Docker runtime does not need it.

Fallback hierarchy (what guarantee, what cost):

1. **Full OpenShell per component (literal reading)** - infeasible for Border, ingress, etcd and member executor (D1). Not recommended.
2. **One OpenShell sandbox per node holding the whole stack** - infeasible: `network=none` removes the listeners and etcd reachability.
3. **Hybrid (recommended)** - OpenShell sandbox for workspace backend + chat gateway (egress-limited, key-mediated), DefenseClaw guarding every model path (D4), hardened systemd for the Border role and ingress (spec 057/165 directives: `NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, address-family/syscall limits where the manager allows), Docker hardening for etcd and the guard/agent containers, host iptables for the metadata server. Guarantee: the LLM-facing, key-holding, internet-egressing parts are in OpenShell+DefenseClaw; the authority core is confined by the controls it was qualified under. Cost: one new OS image, Docker 28, OpenShell gateway per node, a sandbox image, one new DefenseClaw sidecar per node.
4. **Deeper (conditional)** - Border role inside OpenShell behind a raw TCP forwarder, only if E2 passes and the owner funds product changes (D9a). High effort, unqualified.

Recommendation to the owner: choose option 3 now; keep option 4 as a gated stretch after E2. State plainly in the spec disposition table that the HA core is not inside OpenShell.

## D3 - Policy design and how it is enforced and tested

Schema in use in the repo (`scripts/netclaw-secure-start.sh`): top-level `version: 1`, `filesystem_policy` (`include_workdir`, `read_only`, `read_write`), `landlock` (`compatibility`), `process` (`run_as_user`, `run_as_group`), `network_policies` keyed entries with `name`, `endpoints` (`host`, `port`, `protocol`, `enforcement`, `access`) and `binaries` (`path`). Upstream says static sections (filesystem, process) are fixed at sandbox creation and network sections can be updated on a running sandbox. **Conflict to resolve (E7):** the repo policy sets `landlock.compatibility: best_effort`, but upstream states core kernel requirements have no best-effort fallback and fail closed; the plan must use the strictest setting and confirm the field semantics against the pinned CLI.

Gateway sandbox policy (design):
- Filesystem: read-only system paths and the frozen OpenClaw tree; read-write only the conversation home and `/tmp`; nothing under `/etc/nc182`, the Border home, or `/var/lib/nc182`.
- Process: non-root sandbox user; no extra capabilities.
- Network: one policy, endpoint `api.anthropic.com:443` (https), binary `/usr/bin/node` only; everything else denied, which includes the cloud metadata server (169.254.169.254) and the Border's loopback services; DNS resolved by the supervisor.
- Credentials: Anthropic key configured as an OpenShell provider credential held by the supervisor/gateway, not as an environment variable in the sandbox.

Enforcement and test: record `openshell policy get` output and its hash per node (FR-003, FR-014); the negative suite (FR-013) runs inside the sandbox: read `/etc/nc182/provider.env` (denied), write the frozen source (denied), connect to 169.254.169.254 and to a non-allowlisted host (blocked, logged), print the environment (no provider key), reach the Border role's loopback ports (blocked). For the non-OpenShell core the same suite runs against systemd/Docker confinement and is expected to pass or produce a recorded gap. Peers for NCFED/iN2N/etcd are not in any OpenShell policy because those components are outside it (D1); their reachability is governed by the VPC firewall and the host rules already used in R09.

**Alternatives**: allow `*.anthropic.com` (rejected: wider than needed); default-allow with a deny list (rejected: not least privilege).

## D4 - DefenseClaw placement, modes, scanning, audit, key mediation

Facts: DefenseClaw has a CLI, a loopback gateway/sidecar (default port 18970), and connectors; the OpenClaw connector installs a plugin that routes each model request to the guardrail proxy on `127.0.0.1:4000` with the original provider in a header; modes are observe, action (blocks at configured severity, CRITICAL by default) and action with human approval; decisions are written to a local SQLite database and can be exported (OTLP, Splunk, webhooks); upstream says DefenseClaw can run "alongside, within, or generate policies for" OpenShell via `defenseclaw sandbox run`, and that it "does not prove an agent is safe" by itself. The repo pins DefenseClaw 1.0.4 (installer checksum-verified), runs the sidecar via `defenseclaw-gateway start` (spec 177, so the CLI can reach it), and documents that the proxy forwards only to registered provider domains and returns 403 for unknown ones. Linux amd64 is supported upstream; the member guard image in `labs/ollama/Dockerfile.guard` derives from the official 1.0.4 image (per-architecture; an amd64 VM guard has **not** been run in R09 - R09's guard ran on the arm64 Mac, E5).

Decision:
- **Sidecar per node** (new, one per Border VM) guarding the OpenClaw chat gateway through the plugin route; blocking (`action`) mode after one observe-mode tuning pass (`docs/DEFENSECLAW.md` advice).
- **Base the guard configuration on the qualified R04A Anthropic file** (`roadmap-r04a-20261103/cloud-plan/member-inputs/guard-config.yaml`: `hook_fail_mode: closed`, `llm_role: judge_and_agent`, strict rule pack, regex-only detection). R09 already showed that an Ollama-derived config is blocked by DefenseClaw (`provider "" is not supported`).
- **Member model calls keep the qualified per-operation guard container** (provider fence, counter, keyless child); this is a second guard topology, not a replacement. The spec must keep the two clearly separated in status.
- **Scanning flow**: `defenseclaw skill scan`, `mcp scan`, `plugin scan` on the skill/MCP set the workspace exposes, at deploy and at every enablement; HIGH/CRITICAL blocks (documented auto-block). Record the scan results in the audit trail.
- **Audit**: SQLite under the sidecar's home per node; export through `defenseclaw alerts` and the OTLP/webhook path; the node status reports guard state and last audit time (FR-014/015).
- **Fail-closed**: the qualified config sets `hook_fail_mode: closed`; proxy refuses unknown provider domains. Whether a *crashed sidecar* (not a policy block) stops the plugin route rather than bypassing it is **unconfirmed** upstream; the repo's posture probe requires the proxy reachable on loopback 4000 and refuses delegation otherwise. Prove it with E8.
- **Key mediation**: two cooperating mechanisms - the OpenShell supervisor holds the credential for the gateway sandbox; the DefenseClaw proxy needs a provider key to forward, so it runs as its own process outside the agent sandbox and holds the key in a private env file (the same pattern as the qualified hosted guard, where the key is absent from the child environment). The agent must never receive the key.

Open compatibility risk: the R09 workspace pins `openclaw@2026.7.1-2`; the DefenseClaw installer says it keeps a newer OpenClaw and its plugin was exercised on a newer one **(unconfirmed for the pin)** (E6).

**Alternatives**: DefenseClaw in observe mode only (rejected: spec requires blocking); run DefenseClaw inside the same OpenShell sandbox as the gateway (possible per upstream; rejected for the key: the proxy would need the key inside the sandbox); skip a Border sidecar and rely on member-side guard only (rejected: leaves the chat path unguarded, the R09 gap).

## D5 - Re-running the 182 acceptance tests and R09 failure matrix; expected overhead

Reuse the R09 harness: the extension-client driver (`discoverCloudBorder`, `OwnerClient`) for catalog/prepare/approve/reconcile, the host-firewall cut procedure (iptables rules tagged `nc182-cut`, healed by exact spec), the leader-watch loop, and the three member kinds' runbooks. Rows to repeat: leader failover on Border stop, NCFED cut, isolated Border reporting no-quorum, one real operation per Border. Because the HA core is not inside OpenShell (D1), its admission path is unchanged; the **admission window is not affected by the gateway sandbox**, since admission runs member-to-Border. Overhead to measure and report (FR-016): chat turn latency with sandbox + supervisor mediation + DefenseClaw proxy (extra hop per model call), and catalog latency if the Border host is under added memory pressure (R09: catalog ~3 s at the leader with 3 members). If option 4 is attempted, every new TCP connection through the supervisor adds setup latency to etcd and NCFED; against a 4.5 s signed window with a ~3 s cross-region baseline, only ~1.25 s of slack remained, so that overhead is the make-or-break number.

## D6 - Two-Border single-region topology and its majority limit

Manifest nodes may be 1-3 (`ha/config.py`). Two Borders with two etcd voters give a majority of 2 of 2: losing either Border loses quorum, so no failover test is possible. Decision: validate with **two Borders plus one witness voter** (etcd only, no NetClaw, a small VM in the same region) so quorum survives the loss of one Border and the stopped-Border and cut tests remain meaningful. This still cannot tolerate losing two nodes and says nothing about regional loss; record both limits (FR-020). Single-region latency (sub-millisecond zone-to-zone) makes the member-handoff window behave differently from R09: elapsed is far below the ~3 s cross-region figure, so `admission_ms` must be signed at the R08 value (3000) rather than 4500, or fast handoffs fail the `remaining <= 3000` rule seen in R09.

**Alternatives**: three Borders in one region (more cost, same-region only); two voters only (rejected: no failure tolerance).

## D7 - Cost model and teardown

Line items for the validation topology, **approximate list prices recalled, not confirmed this session** (the plan must re-check before the owner approves, FR-022): 2 Border VMs `e2-standard-2` (8 GB, ~$0.067/h each); 1 witness `e2-small` (~$0.017/h); 3 x 40 GB pd-balanced disks (~$0.004/h each); 2-3 in-use static IPs (~$0.005/h each); negligible egress; Anthropic API usage billed separately. Roughly $0.18/h, about $130/month if left running; a four-hour validation is about $0.75 plus API tokens. e2-medium (4 GB) is the cheaper option but is already ~1.5 GB used before OpenShell. Ownership and teardown follow R09: GCP label `netclaw-spec=183` and name prefix `nc183-` on every resource; Docker label `netclaw.spec=183`; teardown only on the owner's request against the exact list, then verified empty.

## D8 - Risks and unknowns, ranked, with the cheapest retiring experiment

1. **Kernel / Landlock ABI 3 on the GCE image** (launch fails closed). E1: boot one small VM from Debian 13 and Ubuntu 24.04, record `uname -r` and the LSM list, run OpenShell's own preflight if it has one. Minutes, cents.
2. **Inbound and end-to-end TLS through OpenShell** (decides option 4). E2: install OpenShell on that VM, run a loopback TLS server in a sandbox, reach it through `openshell forward`, and compare the TLS exporter value on both ends; also test egress to a TLS peer that requires a client certificate. About 30-60 min.
3. **Advertised vs bind address in the Border** (code needs a split for any non-trivial placement). Read-only: confirm in `ha/factory.py`/`ha/node.py`; no experiment needed beyond the E2 result.
4. **Docker 28 + OpenShell gateway footprint on an 8 GB VM** and the repo's older K3s-gateway description vs current upstream. E7: record the installed version and gateway process list.
5. **DefenseClaw plugin on the pinned OpenClaw 2026.7.1-2.** E6: install both on the E1 VM or locally and run one guarded turn.
6. **amd64 DefenseClaw gateway/guard on the VM** (R09 ran the guard on arm64). E5: run the sidecar and one guarded model call on the VM.
7. **Crashed-sidecar behavior (fail-closed vs bypass).** E8: kill the sidecar during a chat turn; expect no provider call.
8. **Landlock `best_effort` vs fail-closed policy semantics.** E7: apply the repo policy on the pinned CLI and read the effective result.
9. **Supervisor-mediated egress latency.** Measured as part of E2 and the chat-turn tests.
10. **Memory pressure on small VMs.** Resolved by sizing; measure.

## D9 - Qualified-code changes likely needed (owner review)

a. `ha/config.py`, `ha/factory.py`, `ha/node.py`: separate **advertised** (signed manifest) endpoint from the **bind** address - only if option 4 is pursued. Not needed for the recommended hybrid.
b. Spec 057 posture aggregator (`controls.py`-style probe): today `sandbox_available()` equals systemd confinement; with OpenShell covering only some components, posture must report **per component** and never claim "enforced" for the HA core under OpenShell wording. Wording and probe change for review.
c. `scripts/lib/protected_role.py`: only if the Border role runs under a different uid/layout (option 4); not for the hybrid.
d. DefenseClaw node sidecar and plugin wiring: new deployment tooling (`labs/ha/`/`scripts/ha-r09a-*`), not qualified code, but the **qualified R04A guard configuration** must be reused unchanged as its base.
e. Carry-overs from R09 that remain open for review (not new here): effect admission around pyATS, hosted guard fixes, Border catalog change, forward timeout.

## Sources

- NVIDIA OpenShell README: https://github.com/NVIDIA/OpenShell
- OpenShell Support Matrix: https://docs.nvidia.com/openshell/about/support-matrix
- OpenShell Architecture: https://docs.nvidia.com/openshell/about/architecture
- OpenShell Sandbox Runtimes: https://docs.nvidia.com/openshell/how-it-works/sandboxes/runtimes
- OpenShell gateways/service expose and forward (search summary): https://docs.nvidia.com/openshell/how-it-works/gateways/overview and https://docs.nvidia.com/openshell/sandboxes/manage-sandboxes
- DefenseClaw docs: https://cisco-ai-defense.github.io/defenseclaw/docs/get-started/what-is-defenseclaw/ and https://cisco-ai-defense.github.io/docs/defenseclaw/
- Repo: `docs/DEFENSECLAW.md`, `docs/N2N-RISK.md`, `scripts/netclaw-secure-start.sh`, `scripts/defenseclaw-enable.sh`, `specs/057-in2n-production-enforcement/research.md`, `specs/177-defenseclaw-sidecar-identity/spec.md`, `labs/ollama/Dockerfile.guard`, `scripts/protected-guard.py`, `mcp-servers/protocol-mcp/bgp/federation/protected_docker.py`, `specs/182-multi-region-ha-borders/{live-evidence,workspace-plan}.md`.
- Could not retrieve: DefenseClaw architecture and setup-guardrail pages (404), so crash/fail-closed behavior, exact key-handling flags and amd64 gateway details above rest on the repo's own documentation and are marked unconfirmed.

## Experiment results (2026-11-10, one throwaway VM `nc183-exp-1`, e2-standard-2, torn down afterwards)

Image `ubuntu-2404-noble-amd64-v20261105` (Ubuntu 24.04.5), 8 GB RAM, own VPC with IAP-only SSH.

- **E1 kernel/Landlock: PASS.** Kernel `7.0.0-1017-gcp`, LSMs `lockdown,capability,landlock,yama,apparmor,bpf,ima,evm`, Landlock ABI **8**. A sandbox created with `landlock: compatibility: hard_requirement` started. Debian 12 (kernel 6.1, ABI 2) stays unsuitable; use Ubuntu 24.04.
- **Install facts.** Docker 29.9.3 from `get.docker.com` (>= v28 required). OpenShell **0.1.7** via the upstream `install.sh` (Debian package; resolves latest tagged release). The gateway user service needs: user in the `docker` group (restart `user@UID`), `loginctl enable-linger`, and `OPENSHELL_COMPUTE_DRIVER=docker` in `~/.config/openshell/gateway.env` (auto-detection failed). Register with `openshell gateway add https://127.0.0.1:17670 --local`. `openshell doctor check` validates Docker. Gateway RSS ~137 MB, supervisor ~49 MB, sandbox ~20 MB.
- **Sandbox image rules.** `--from <image>` works with a locally built image; the image must contain the policy's `run_as_user` (here `sandbox`) or provisioning fails with `IdentityResolutionFailed`; the policy must list readable paths (`/app` etc.) or the workload gets EACCES.
- **E2a inbound TLS: PASS.** A TLS 1.3 server bound to the sandbox loopback was reached from the host through `--forward 127.0.0.1:9443` (`[bind_address:]port`, same number on both sides; `0.0.0.0:port` is allowed). The TLS exporter value (pyOpenSSL `export_keying_material`) was **identical on both ends**, so the forward is a raw TCP pass-through and the exporter binding survives.
- **E2b outbound TLS: PASS only with `tls: skip`.** By default the sandbox egress proxy performs **automatic TLS termination** (it terminated the sandbox client's TLS and rejected the self-signed server certificate: `sslv3 alert certificate unknown` at the server). With `network_policies.<name>.endpoints[].tls: skip` the exporter value was identical on client (inside the sandbox) and server (on the host). For `protocol: tcp` endpoints the L7-only fields `enforcement`, `access`, `rules`, `deny_rules` are rejected. The host is reachable as `host.openshell.internal` (policy-mapped to a synthetic address). The gateway recognizes TLS modes UNSPECIFIED/TERMINATE/SKIP/PASSTHROUGH.
- **Overhead.** TLS connect+handshake p50: direct 2.2 ms, inbound via forward 7.4 ms, outbound from sandbox 7.1 ms (p95 <= 9 ms): about +5 ms per hop, negligible against a 3-4.5 s admission window.
- **E5 amd64 DefenseClaw: PASS.** DefenseClaw **1.0.4** installed from the pinned, checksum-verified release installer on x86_64 (`install.sh: OK`), found OpenClaw 2026.7.1; `defenseclaw init` + `setup guardrail --mode action --scanner-mode local --detection-strategy regex_only` succeeded; `defenseclaw-gateway start` listens on `127.0.0.1:4000` (guardrail proxy) and `127.0.0.1:18970`.
- **E8 sidecar loss (partial): PASS for routed clients.** With the sidecar stopped, a request to `127.0.0.1:4000` is refused at the TCP level (fail-closed for any client routed through it). The in-band policy-block test needs the guard capability token (unauthenticated requests get 401 before inspection); it is part of implementation testing, not retired here.
- **Not tested here:** the DefenseClaw OpenClaw plugin on a live chat turn (E6), OpenShell provider credential injection with a real provider, the repo `best_effort` Landlock semantics (the `hard_requirement` path was used), Border-in-sandbox (needs D9a).

### Consequence for the decision

The transport objections to placing the Border inside OpenShell are retired: inbound and outbound TLS keep the exporter binding (`tls: skip`), overhead is ~5 ms, the kernel/arch/Docker gates are solvable with Ubuntu 24.04. What remains for a Border-in-sandbox is product code (D9a): the Border binds the manifest host:port, which is not an address inside a sandbox, so the bind address must be separable from the advertised address; plus image/ownership work for the role launcher's private-file and immutable-source checks. The member executor (Docker socket) and etcd (host network) stay outside by documented disposition.
