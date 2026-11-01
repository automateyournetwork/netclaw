# NetConverter migrations and virtual rehearsals

Spec162 adds an optional guarded integration with [NetConverter.ai](https://netconverter.ai/)
and its [official Terminal/MCP](https://netconverter.ai/mcp.html). NetClaw prepares
an exact file review, submits only after native operator approval, keeps conversion
evidence private, and composes the candidate with existing lab and validation tools.

Source and controlled-peer tests are distinct from live qualification. On
2026-10-31, the real account and official Terminal 0.6.0 completed approved
synthetic IOS-XE → Junos SET → IOS-XE conversions. Both remain **needs review**.
On November 1, a clean protected application of the reverse candidate to a real
IOS-XE 17.18.2 virtual router passed OSPF FULL, reciprocal routes, bidirectional
5/5 pings and 0/3 negative controls. The fresh native installer pass remains open;
Junos appliance behavior is unqualified. See [current evidence](../specs/162-netconverterai/verification.md).

## Install and select a connection

Select **NetConverter** in the VS Code setup wizard or terminal installer. The
installer installs the NetClaw guard's isolated dependencies. It does not install,
redistribute, execute or accept the license of the official Terminal. Install the
licensed client from its [official repository](https://github.com/valeronlabs/netconverter_terminals)
when using local-Terminal mode.

| Mode | Purpose | Required settings |
|---|---|---|
| `hosted-readonly` | Read existing account/job evidence | Separate API key and local account reference |
| `local-terminal` | Prepare/submit files and verify downloaded artifacts | Same settings plus absolute executable and workspace paths |

Both modes register only `netconverter-mcp`, the guard. They do not expose a second
raw submission server. API keys belong in the selected installation's private
settings; Claw Plans hold secret references. A free-account signup does not prove
router conversion access: discover actual operations, directions, limits and
schemas once the account is enabled. The account label is an operator reference,
not a verified tenant identifier.

The managed submission profile currently accepts nonempty UTF-8 text only.
Source and target roles and their explicit router/switch/firewall class must match
an offered path. UTF-8 XML qualifies when the connection explicitly advertises
text input (the observed Palo Alto XML route does). Binary/archive and non-text
handoffs, including the observed Check Point bundle, and metadata-incomplete
legacy paths remain unavailable. Preview state is retained as
reported or marked unknown; this never enables guided-draft mutations.

Existing terminal installations can run:

```bash
python3 scripts/configure-netconverter.py --env /absolute/claw/.env \
  --home /absolute/claw --interactive
```

Choose the mode, account reference and (for local mode) paths. Key entry is hidden;
cancel preserves existing values. Status distinguishes installation, discovery,
authentication, capabilities, license management and per-request approval.
`netconverter_status(discover=false)` makes no account call. Readiness never claims
that an installed component has converted a file or tested a device.

## Convert an exact private file

1. Collect an authorized file using private artifact output or stage it locally.
   Do not paste configuration into chat/tool arguments. The existing managed
   `pyats_show_running_config(device_name, output_mode="private")` returns a
   private file reference for qualified IOS/IOS-XE or Junos SSH routes. Other inline-only
   collectors are not automatically compatible.
2. Discover capabilities and call `netconverter_prepare_submission` with its
   local path, supported vendor codes, operation and reviewed options. This
   freezes a snapshot inside the selected workspace and returns metadata.
3. The human reviews the concrete request with the selected integration's Python:

   ```bash
   python scripts/netconverter-settings.py --env-file /absolute/claw/.env \
     review REQUEST_ID
   python scripts/netconverter-settings.py --env-file /absolute/claw/.env \
     approve-submission REQUEST_ID --digest FULL_REVIEW_DIGEST
   ```

   Use the interpreter recorded at `<claw>/python-runtimes/records/netconverter`.
   Approval requires a controlling terminal and typing the full digest. It names
   source/hash/size, destination/account, operation, vendor direction and options.
   Agents must never type the operator's approval. This command does not upload.
4. `netconverter_submit_approved` consumes the grant before one upstream attempt.
   Changed bytes, connection, executable or capability evidence require review
   again. An interrupted/lost response is **unknown**, never permission to retry.
5. Read the bound job, inspect private evidence and download through
   `netconverter_download`. Every file is checked for confinement, size and hash
   before a trusted artifact reference is returned. Success does not mean that
   the candidate is safe to deploy.

`netconverter_read` exposes a strict schema-qualified read allowlist. A successful
explicit `get_job_brief` read associates that job with the current connection and
returns an opaque `job_ref`; it does not reconcile an unknown submission by guessing.
Wait calls have a 45-second ceiling and a durable 300-second budget per reference.
Explicit status reads remain available. Reports are private artifacts; known
verdicts, review/manual-work counts, partial/truncated coverage and absent-report
flags may return to the model, including nested hosted evidence envelopes. No raw target tool,
mapping mutation, guided-draft submission or automatic exposure increase is enabled.

## Review and apply a candidate to a lab

Use Terminal Intent's existing **Local/Lab** mode and designate the exact SSH
endpoint. Private artifact application initially supports one selected endpoint
per request. In **Review a local migration candidate**, choose a UTF-8 file up to
2 MiB, inspect its SHA-256/size, select the active pyATS process and verification
profile, and confirm the exact candidate for that target.

The same persistent managed pyATS process must first run `pyats_list_devices`.
Its private receipt binds the actual inventory and ordinary SSH connection.
For clients that close STDIO between turns, explicitly start the authenticated
foreground session described in [dynamic testbeds](DYNAMIC-TESTBEDS.md). A
dynamic testbed does not change the HUD's inventory automatically; both endpoint
identities must match. Restart, changed inventory, ambiguous/proxy/console routes
or cached connections require reconciliation and may leave this route unavailable.

Submit the explicit change intent. PREPARE remains read-only and needs genuine
baseline and actionable rollback files. Private collection can write the record's
baseline with `change_ref`; it does not invent a rollback plan. The collector
writes a bound receipt, and the API and consumer verify the exact baseline bytes
against the retained original. Replacing that file with a reference note is refused.
Only the real API
transition issues a five-minute capability bound to candidate, endpoint, tool,
inventory, process, task, policy, baseline and rollback hashes.

Private collection disables connection-time initialization commands so taking a
baseline cannot first change the device. It requires a fresh connection and sends
connection diagnostics to a private file. Normal upstream connection settings,
including the selected host-key policy, remain in effect.

The artifact form uses the existing **`pyats_configure_device`** identity with
`artifact_ref` and `grant_ref`; omit `config_commands`. It preserves original
tool permission and dangerous-command checks. Denial never triggers a raw SSH,
console or alternate-tool fallback. A durable attempt precedes mutation. Raw
commands, results and upstream logs remain private; `applied_unverified` requires
actual post-checks. Same-OS-user access to trusted files is not sandboxed by this
mechanism. Hermes Local/Lab APPLY and production artifact approval are unavailable;
production retains the existing approved ServiceNow workflow.

Cancellation retains the process lock and inventory guards until the original
device operation finishes; the consumed attempt stays unknown. A lost response or
post-write evidence-storage failure requires actual state inspection before any
further write. Further private application in that process is refused; after
inspection, restart/rebuild/review is necessary for a new authorized request.
Restart never makes the old grant reusable.

Junos application accepts only set-format lines without semicolon or pipe command
separators; block-format loading is unavailable. This intentionally also refuses
descriptions containing those separators until a parser-qualified route exists.
Installed Unicon source shows a commit path, but that is not live Junos acceptance.
The managed private collector adapts the original read identity to the fixed
Junos display-set command; controlled tests verify this boundary. Live Junos
baseline collection remains unqualified. Do not call a Junos rehearsal complete
until its collection, commit/readback and actual behavior checks are qualified.

## Create, boot and test real virtual targets

Use the [rehearsal procedure](../workspace/skills/netconverter/references/rehearsal.md).
Discover current tool schemas, installed licensed image, architecture, capacity,
isolated networks and management/bootstrap support before provisioning. CML,
containerlab, EVE-NG and GNS3 provide different lifecycle capabilities; a template
name does not prove that an image is installed or that configuration can be loaded.
FRR can supply peers/traffic, but is not a demonstrated native converter target.

Record scope and assertions using `scripts/migration-rehearsal.py`, then record
each attempt before the actual lab MCP call. Use exact provider IDs and observed
run/attempt ownership for reconciliation. Retain resources by default; no delete,
wipe, destroy or restore operation is hidden in cleanup.

The preferred routing example is [IOS-XE → Junos OSPF](../specs/162-netconverterai/reference-ospf.md).
Verify FULL adjacency, expected prefixes/next hops, positive traffic, a negative
control, passive-interface behavior and management preservation. EIGRP → OSPF is
a separately approved protocol redesign; do not claim EIGRP translation to Junos.
Router output remains review-required according to the [vendor support matrix](https://netconverter.ai/docs/supported-vendors.html).

## Compose evidence and communicate

NetBox, Nautobot, Infrahub, Catalyst Center and ServiceNow can select the estate;
IP Fabric and Forward can supply scoped observations; pyATS and vendor readers
collect authorized artifacts. Jev is optional advisory review with its own
enablement, budget and disclosure controls. See the [composition matrix](../workspace/skills/netconverter/references/composition.md).

Batfish now reports partial/empty parsing and failed queries as incomplete or
inconclusive. Equal results mean only that the requested modeled queries found
no differences; they do not prove live traffic, NAT, hardware or performance.

Keep observed and proposed diagrams separate. Include hashes, target image,
executed/failed/blocked/not-run assertions, manual changes, recovery plan and
retained resources in the [review package](../workspace/skills/netconverter/references/evidence.md).
The [OSPF review template](../specs/162-netconverterai/review-package-template.md)
provides separate proposed topology, assertion and local ticket sections.
Prepare documents and ticket drafts locally; sending, ticket creation and
production approval remain separate steps.
