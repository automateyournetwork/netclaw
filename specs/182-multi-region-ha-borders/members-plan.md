# R09 members plan: what can attach and run REAL calls today

Read-only survey (stream M). No source was changed. Facts below are from the code named in each line; the live
Borders are `nne1-c8e105`, `ew1-42e2d9`, `ase1-004437` (.automateyournetwork.com), leader Montreal, epoch 3.

## Bottom line

| Member | Attach to the HA cluster with qualified code today? | Real call with qualified code today? |
|---|---|---|
| Local execution member on the Mac (Ollama qwen3:0.6b, native subnet) | **Yes**, same shape as R08 `real-run-07` | **Yes**: `subnet_calculator` (summary) |
| NetBox cloud member (demo.netbox.dev) | No | **No.** Needs new, unqualified wiring (small) |
| pyATS member on the Mac | No | **No.** Needs new, security-sensitive wiring (medium) |
| CML (192.168.2.125) | No tool exists | **No.** Only route is pyATS over CML IOL nodes, which inherits the pyATS gap |

The reason is structural, not a missing config: an HA member is only constructible with a model runtime, and that runtime is
only allowed to run the native subnet summary tool.

- `ha/member.py:12` `ClusterMemberOperations` requires `executor.ollama or executor.hosted`, else `ha_runtime_unqualified`.
- `protected_docker.py:65-84` `validate_runtime_fields`: a config with `ollama` or `hosted` must have `mcp.kind == 'subnet_summary'`
  (`ollama_native_summary_required` / `hosted_native_summary_required`). The only config that allows `netbox` MCP or `pyats` has no model
  runtime, so it cannot be an HA member.
- `protected_docker.py:737-747` `run()` with an `ha_admission` and no `ollama`/`hosted` raises `ha_runtime_unqualified`.
- `protected_docker.py:~780` the `pyats` branch calls `invoke_pyats(...)` with **no** `ha_admission` (the MCP branch passes
  `ha_required/ha_admission`). So there is no quorum admission fence on a pyATS effect today.
- `protected_contract.validate_catalog_entry` treats any `ollama` profile as a calculator-only profile.
- R08 evidence (`verification.md` real-run-07) covers exactly: 3 voters, 3 Borders, 1 member, qwen3:0.6b arm64, native `subnet_calculator`.

Spec 173 (NetBox member) and spec 171/R02 (pyATS) are qualified only on the **non-HA** path. A HA Border does not accept a non-HA
member: `accept_member` requires an enrolled HA member and the `in2n-tls-exporter-v1` attachment profile, and a home with
`ha-required.json` refuses legacy launch (`ha_downgrade_refused`).

## Common to every member: contract, enrollment, dialing

**Role contract (schema 3, role `member`)**: `protected_role.validate` fields: `schemaVersion installation_id role runtime_kind control_only
home source_root python python_sha256 python_env python_env_manifest python_env_manifest_sha256 source_manifest source_manifest_sha256
profile_sha256 origin environment guard_token_file`. `control_only=False`, `origin=None`, `runtime_kind=openclaw`.
`environment` keys limited to `NETCLAW_LOCAL_AS NETCLAW_ROUTER_ID N2N_DISPLAY_NAME BGP_API_PORT BGP_LISTEN_PORT N2N_INVENTORY_REFRESH_S`
(`N2N_EDGE_WS_PORT` is refused for members). `guard_token_file` must be `<home>/netclaw-federation/guard-capability` (43-char urlsafe token).

**Home** (private 0700, owned by the running uid): `netclaw-hud/installation.json`, `netclaw-federation/{owner.json, ha-required.json,
ha-config.json, protected-profile.json, guard-capability}`, `n2n/federation.db` with `risk.role='member'`, `enabled_stacks='in2n'`,
`self_member_id=<member_id>`, `n2n/keys/self.{crt,key}`. Hashed files (`ha-config.json`, `protected-profile.json`) must be written in
canonical JSON bytes (lesson from this deployment).

**HA config (member)**: exactly `schema_version role manifest_file anchor_certificate_file anchor_key_id transport_ca_file certificate_file
private_key_file`; manifest = the signed R09 manifest, anchor = `root.crt`, transport CA = `transport-ca.crt` (public). The member needs
no etcd credential and no manifest-node private key.

**Profile (schema 2)**: `{schemaVersion:2, role:'member', identity:<member binding>, catalog:{member, model_profiles[], tools[]},
runtime:<DockerExecutor config>, ha:{config_file, config_sha256}}`. Member binding fields: `installation_id member_id key_id
enrollment_generation`; `key_id = sha256 key id of the member certificate`. The member certificate must not collide with any Border
identity/key (`member_border_identity_collision`).

**Enrollment (no production path exists)**. `OperationLedger.enroll_member(binding, certificate)` (`ha/operations.py:69`) is called only
by tests and by R08 `real_runtime.start_coordination`. It runs through `Authority.mutate`, which requires `self.leader` (`ha/authority.py:128`),
and `campaign()` refuses while any leader exists. So a member cannot be enrolled into a **running** cluster. Procedure that uses only
existing code: stop all three `nc182-border` services, wait the 15 s lease, run a one-shot as Border 0 on nne1
(`Authority.campaign()`, `enroll_member`, let the un-renewed lease lapse), restart the Borders. This costs one authority epoch bump and
~30 s of unavailability. It is also R08's own pattern ("short provisioning lease is not renewed"). Also limit `max_members` 32.

**Dialing (outbound only)**. `MemberAttachments` dials each manifest node's `endpoints.in2n` (host = public IP, port 7444, `server_name`
= the DNS name) with TLS1.3 and the transport CA. Already prepared on the Border side: public IP aliased on `lo`, DNAT on 7444, firewall
`nc182-allow-public` (7444 from 0.0.0.0/0), node transport certs carry the DNS name, internal IP and public IP in SANs. A Mac behind NAT
needs nothing inbound. All three attachments must come up (`attachments` readiness = 3 authenticated).

## (a) NetBox cloud member

- Qualified today: non-HA only (spec 173; `protected_mcp.py` kind `netbox`, tool `netbox_get_object_by_id`, field allow-lists
  `NETBOX_FIELDS` for `dcim.device` and `ipam.prefix`; token read via `token_bytes(config)`; source closure of 4 `src/netbox_mcp_server/*.py`
  files plus `servers/` pins; skill `netbox-reconcile`).
- **Cannot run under HA with qualified code.** Two relaxations are required (new, unqualified, small):
  1. `protected_docker.validate_runtime_fields`: allow a `hosted` runtime with `mcp.kind == 'netbox'` (today hard-requires `subnet_summary`).
  2. Catalog/tool validation for hosted+netbox in `protected_contract.validate_catalog_entry` (the non-`ollama` branch already validates NetBox
     arguments, so likely no change) and a hosted member catalog entry.
  `invoke_mcp(..., ha_required=True, ha_admission=...)` already exists and is wired for the MCP branch, so the tool-effect admission fence is
  present. The hosted inference admission is my unqualified `ha/hosted_model_transport.py`.
- Model path: only my hosted Sonnet profile is plausible (Ollama calculator profile cannot call NetBox). It needs a DefenseClaw guard whose
  upstream is `api.anthropic.com` (unverified), an Anthropic key in the guard's read-only env file (never the member), and egress
  allow-listing (not enforced). See `model-transport.md` gaps 1-10.
- Where it runs: a GCP VM in one region (amd64). R05 produced amd64 guard/ollama images, but a hosted member needs a guard + relay + agent
  image set for the amd64 hosted profile; none is qualified. Alternative: run it on the Mac (arm64 guard image exists).
- First REAL call: `netbox_get_object_by_id` with `object_type=dcim.device`, a real demo device id, `fields` from the allow-list, `brief=false`.
- Independent observer: NetBox object `last_updated`/changelog (a read call changes nothing, so the proof is the signed result + the
  member and guard request counters).

## (b) pyATS member on the Mac

- Qualified today: non-HA R02 path only: `protected_pyats.py` allows exactly `show version`, `retries == 1`, one device from a reviewed
  testbed, **iosxe/iol only**, pinned pyats/genie/unicon/unicon.plugins 25.2 with a Unicon source digest (Mac-specific), SSH known_hosts,
  credential env.
- **Cannot run under HA with qualified code.** New work: (1) a runtime field set combining `pyats` with a model runtime
  (`validate_runtime_fields` has none); (2) pass `ha_admission` through `invoke_pyats` for the effect fence (today absent: a real-effect fence
  gap, security-sensitive, needs its own tests and a REAL budget); (3) catalog/tool contract for hosted+pyats; (4) member host needs the
  pinned pyATS 25.2 environment and a reviewed testbed whose device is a CML IOL node.
- Where it runs: the Mac (that is the only host pinned for the Unicon digest and with reachability to CML 192.168.2.125).
- First REAL call: `pyats_run_show_command` `{device_name, command:'show version', timeout, retries:1}`.

## (c) CML (192.168.2.125)

No protected HA tool, MCP kind or skill exists for CML (`protected_mcp.py` knows `netbox`, `subnet`, `subnet_summary` only). The qualified
route to CML is indirect: pyATS over a CML IOL node (item b). A CML-API tool would be a new protected MCP kind (source closure, schema
digests, argument allow-list, read-only policy, tests): large and not started. State plainly in any report: **CML is reachable and its
credentials work, but it cannot be exercised through the HA path without new work.**

## What CAN be done now (qualified): local HA execution member on the Mac

Everything exists locally from R05/R08 and is verified present:
- `~/.local/share/netclaw/roadmap-r05-20261105/local-member/runtime-template.json` (agent/relay/guard/model images by ID, guard config,
  qwen3:0.6b arm64 model store, native `subnet_summary` MCP, `ollama` profile family 4, `guard_uid` 503, `model_uid` 21006).
- Docker images present on the Mac: `netclaw-r05-ollama-arm64:176-v2`, `netclaw-r05-guard-arm64:176`, relay/agent images.
- Docker 29.9.2 aarch64 is running; the host is arm64 (the qualified family).
- What is gone: the R08 run root (only `r08-leftovers/untracked-r08.tgz`). The runtime template is reusable but its paths, guard env and
  immutable Python environment must be rebuilt for a fresh member (R08 used the immutable `r04a-owner` venv with manifest).

Needed to stand it up: a fresh member identity (`create_self_signed`), the profile/catalog/home/contract above, a frozen member source
closure (the Border closure of 127 files is not enough: the R08 plan also required `scripts/lib/protected_ollama.py`,
`labs/ollama/qualify.py`, `ha/model_transport.py`, native `servers/subnetcalculator_mcp.py` source and `scripts/protected-tool-broker.py`
copies per its `source_files` map), the model container started by the qualified `labs/ollama/qualify.py prepare` (confinement
measured), the guard started per operation by `DockerExecutor`, and the enrollment window described above.

First REAL call: owner prepares `subnet_calculator` for `192.0.2.0/26` from the HUD of any of the three Borders (or VS Code); the Border
forwards to the authority over NCFED (follower to leader), the member executes, signed result and ACK return. Reproduces R08 on real WAN.

## Operation flow (HUD / VS Code)

HUD "Prepare an exact operation": the catalog lists protected member profiles (today: "No eligible protected member profiles are
available"); owner selects member + tool + exact arguments -> `POST /api/hud/operations` (prepare, review) -> `POST .../decision`
(approve, reserves the budget, sends once) -> status/reconcile. VS Code uses the same `OwnerClient` routes
(`extensions/netclaw-vscode/src/client/owner.ts`). Reviews live ~180 s; admission must land inside the signed `admission_ms` (6000).

## Ordered build list (sizes are my estimates)

1. **Mac HA member, qualified path** (M, risk medium): member identity + catalog/profile/home/contract builder (adapt
   `real_runtime.materialize` member branch to a standalone script), member source/python freeze on the Mac, qualified model start,
   authority enrollment window, start member, verify 3 attachments, run 3 `subnet_calculator` ops (one per ingress Border), then
   the WAN tests. Risks: reconstituting the immutable env and source map; arm64 confinement measurement; enrollment downtime.
2. **Border-loss real operation** (S, after 1): kill Montreal, observe leader move, run an op via another Border (R08 op4 equivalent).
3. **Hosted + NetBox member** (M-L, risk high, unqualified): relax `validate_runtime_fields` (hosted + netbox), amd64/arm64 hosted guard
   with Anthropic upstream, egress allow-list, API key placement, REAL evidence incl. independent counters. Only after 1 is green.
4. **pyATS-in-HA** (L, risk high): add effect admission to `invoke_pyats`, new runtime field set, pinned pyATS env + CML IOL testbed,
   REAL tests; touches an effect fence, so it needs review rather than speed.
5. **CML API tool** (L, not started): new protected MCP kind end to end.

## Honest statement for the owner

With code that exists and was qualified, the three Borders can be proven live with one real execution member. NetBox, pyATS and CML
attach-and-call through the HA Borders is **new engineering**, and the hosted-model path is unqualified. Reachability of CML and
NetBox from this machine is already verified; reachability is not the blocker.
