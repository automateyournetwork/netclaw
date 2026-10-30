# Create and test an actual virtual target

1. Discover the installed lab MCP schemas. Record host architecture, available
   capacity, exact installed image/template/version/digest and entitlement.
   Select a supported NetConverter direction and a matching OS image. On ARM64
   Docker, an x86 Junos appliance is not assumed bootable; use a qualified host.
2. Record the authorized run scope, isolation, management/bootstrap plan and
   expected assertions. Create an ownership/attempt entry before each lifecycle
   call. Existing owner labs are not adopted by display name.
3. Create the run-owned topology and actual target. Boot it, poll finitely and
   record actual provider object IDs/states. Reconcile unknown creation by exact
   ownership rather than blindly creating duplicates.
4. Discover actual management endpoints; validate host identity and real show
   output. Bootstrap must be separately scoped and must not hide the migration
   candidate in a node-creation or startup-config payload.
5. Select the verified candidate and review interface/management remapping.
   Preserve original and adapted hashes plus every manual change. Use the existing
   approved configuration route. For the supported Terminal Intent artifact flow,
   the API—not model text—binds candidate, endpoint, active testbed, tool, baseline,
   rollback and one-use APPLY capability. No artifact adapter means apply is
   unavailable; do not fall back to raw exec after denial.
6. Verify commit/readback and run the assertion matrix on the actual target. Use
   a source twin and the same expectations where feasible. Record positive and
   negative traffic, routes/VRFs and adjacency; NAT needs actual translation
   observations when present. A deliberate failed assertion must remain failed.
7. Retain resources and evidence for review. Recovery/stop is limited to the
   authorized run scope; delete/wipe/destroy/snapshot restore is never implicit.

After uncertain application, inspect actual state before further writes. The
private route blocks additional application in that process; restart and new
review follow inspection, never substitute for it. Cancellation holds the exact
inventory/connection guards until the original device work stops. Private baseline
collection uses fresh connections with initialization commands disabled and
private connection logs. Junos candidates require set lines with no semicolon or
pipe separators; unsupported syntax is a review item, never silently rewritten.

## Platform-specific discovery

- CML: current upstream names include `get_cml_node_definitions`,
  `get_node_definition_detail`, `create_empty_lab`, `add_node_to_cml_lab`,
  `connect_two_nodes`, `start_cml_lab`, `get_nodes_for_cml_lab`. Verify installed
  schemas. Definitions alone are not image proof. `configure_cml_node` is an
  inline CREATED-state bootstrap setter, not an approval bypass. Optional CLI
  support depends on installed extras and BOOTED state.
- containerlab: deploy/inspect/exec capability does not imply private file staging
  on its remote host. Startup paths refer to that host. Record image architecture
  and licensing. Exec is not an alternate configuration authorization route.
- EVE-NG: template listing is not installed-image inventory. Starting a node may
  seed its configuration. Qualify this before treating start as a pure boot.
- GNS3: select exact template UUIDs and actual images. Existing MCP lifecycle is
  not a config setter. Export stream metadata is not proof of saved artifact bytes.
- FRR: useful OSPF/BGP peers and traffic experiments. It is neither an established
  NetConverter target nor a replacement for a firewall being migrated.

## Preferred OSPF example

IOS-XE source → NetConverter → Junos router target, with a stable peer and two
synthetic endpoint prefixes. Assert neighbor FULL on both ends, expected route
and next hop, positive reachability, an unadvertised-prefix negative control,
passive-interface behavior and management preservation. Record target image,
commit/readback, warnings and interface adaptations. EIGRP→OSPF is a separate
opt-in protocol redesign. Do not imply that OSPF checks prove NAT, hardware
performance or every feature in a production router.

## Local run ledger

Use `python3 scripts/migration-rehearsal.py --root /absolute/private/state --run UUID ACTION --input /absolute/private/metadata.json` with `begin`, `attempt`, `reconcile` or `evidence`. `report` needs no input. This records metadata only; it neither grants permission nor calls a lab provider.

- `begin`: `provider`, `scope` (image/license/architecture/capacity/isolation evidence and authorized bootstrap), `assertions`.
- `attempt`: actual discovered `tool` and SHA-256 `arguments_hash`; save its returned reference BEFORE calling that tool.
- `reconcile`: `attempt`, exact observed `provider_id`, `ownership` containing the run_id and attempt_id actually carried/observed in the provider resource. A matching display name is insufficient. Unknown ownership remains blocked.
- `evidence`: `assertion`, `verdict`, `evidence_class` and private `artifact` reference. Preserve deliberately failed checks after recovery.

For the private apply path, run managed `pyats_list_devices`, review the local file/hash in Terminal Intent, select the same process and one exact target, and submit the explicit Local/Lab change. The API returns the artifact_ref/grant_ref only after real preparation. IOS/IOS-XE and fixed Junos display-set private collection are implemented; live Junos baseline collection is not yet qualified. Keep that prerequisite explicit even when Junos set-format candidate application is available in source.
