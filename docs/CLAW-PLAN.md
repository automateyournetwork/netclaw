# Claw Plan and CLI

All frontends use [schema version 1](../config/claw-plan.schema.json) and `scripts/setup-engine.py`. A plan describes the reviewed source/host, Focused or Risk shape, every claw, input file references, posture and verification choices. The complete [fixture example](../tests/fixtures/setup/plan-valid.json) is illustrative and cannot authorize installation; the [deployment example](../installer/spec-kit/netclaw-claw/example-plan.json) deliberately retains unresolved choices.

From a compatible, reviewed checkout:

```sh
./scripts/install.sh --emit-plan /absolute/private/netclaw-plan.json
./scripts/install.sh --validate-plan /absolute/private/netclaw-plan.json
./scripts/install.sh --explain-plan /absolute/private/netclaw-plan.json
./scripts/install.sh --plan /absolute/private/netclaw-plan.json
```

The interactive authoring tree asks for harness, provider/model/API, channel, shape, capabilities, settings, inventory, identity and posture. It saves a new file without installation. Apply requires a controlling terminal and exact-hash review. There is no `--yes` or assistant approval bypass. Historical installer flags retain their existing behavior; use the plan flags for separate-home provisioning.

Each claw declares an ID, friendly name, resolved harness and inheritance choice, exact supported runtime version, empty home, workspace, independent provider and selected capabilities. OpenClaw uses a child workspace; Hermes uses its home. Seven unique ports cover gateway, HUD API/UI, companion, federation and BGP API/listener. Plan validation rejects overlapping/aliased homes, duplicate ports, unsupported combinations and unclassified settings.

Secret settings contain references such as:

```json
{"kind":"secret","key":"ANTHROPIC_API_KEY","owner":"my-claw","source":"prompt"}
```

No token value belongs in a plan. Native prompts send values directly to the engine; each home receives its own private `.env`. Input files are bounded exact-hash references copied independently into that claw. Literal secrets, unknown properties, duplicate JSON keys, floats and ambiguous JSON are refused. Unresolved decisions block apply.

Selecting `claw-certs` creates a separate pinned-trust host keypair under that home's `n2n/keys/host/`. A private `.setup/claw-certificate.json` bundle preserves the exact pair for interrupted-run recovery; its contents never enter plans, progress or reports. Risk CA/enrollment is separate. ACME registration, rotation and peer trust require their own configuration and evidence.

For Risk members, **on-demand** means the routed worker sleeps until invoked; the local HUD and OpenClaw gateway remain available for management and verification. Wake-up uses the member's owned native service. Copied service source is digest-bound; edits require reconciliation before restart.

The private journal is under the account's `.local/state/netclaw/setup/`, outside checkouts and runtime homes. It records intent before effects and keeps source/home/host locks while writers survive. `status` observes; `resume` requires renewed native review and observes uncertainty before retrying. Native editor disconnect does not cancel installed services.

```sh
python3 scripts/setup-engine.py status --run-id RUN_ID
python3 scripts/setup-engine.py resume --plan /absolute/private/netclaw-plan.json --run-id RUN_ID
python3 scripts/setup-engine.py verify --run-id RUN_ID
python3 scripts/setup-engine.py report --run-id RUN_ID
```

Tiers 1–3 are mandatory: installed artifacts, tool discovery plus a safe canary, and owned runtime/HUD identity. Optional tiers 4–6 require separate native review for a provider turn, each external message, and one read-only device observation. A channel `destinationRef` is only a label; its actual destination is entered natively and omitted from reports. Unknown outcomes stop later checks. Production never falls back to testing automatically.

The catalog is canonical; regenerate derived shell/HUD data with `node scripts/build-catalog.mjs` and `python3 scripts/build-catalog.py`. Component estimates distinguish documented/measured/unknown counts. Unknown tool permissions are not a read-only guarantee. `NETCLAW_SKETCHFAB_ENABLED=true` explicitly selects optional stencil acquisition; otherwise Three.js uses bundled procedural shapes. Setup scopes model caches and disables incidental Hugging Face model downloads.

For setup-owned Hermes claws, native Workspace & Claw saves of SOUL.md, USER.md or IDENTITY.md also bind and refresh that claw's reviewed identity manifest, with a private recovery copy. Other claws and files are untouched. Persona content grants no additional tools or authority. An interrupted file/manifest update remains unknown and blocks restart until reconciled.

Cleanup has its own native review listing services and every file outcome. It verifies ownership and shutdown, removes exact journaled service definitions/enable links, then removes unchanged run-created files. It shares the editor management lock; an unknown cleanup requires explicit setup recovery. Expired reviews change nothing. Cleanup invalidates current readiness and connection candidates while retaining the earlier report privately. Changed, shared or uncertain resources, directories and audit evidence remain.

## Deploying to GCP

The installer, this wizard flow and the Claw Plan flow can place a Border or Member in your own GCP project
(`NetClaw: Deploy a Border or Member to GCP`, or `scripts/netclaw-gcp.py`). See [NetClaw in GCP](NETCLAW-IN-GCP.md).
GCP deployments are **NOT behind any authentication**: keep every URL private; users, SSO and RBAC are a much later
roadmap phase (R15-R17).

A plan describes the Risk shape; cloud placement is a separate reviewed step: choose a topology id (`gcp-border`, `gcp-member`, `gcp-border-onprem-members`, `onprem-border-gcp-members`, `ha-risk`, `distributed-risk`) and run `scripts/netclaw-gcp.py plan`, then enroll the nodes with the Member/Border flow.
