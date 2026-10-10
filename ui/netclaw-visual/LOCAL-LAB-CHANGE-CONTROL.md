# Terminal Intent Local/Lab change control

Production remains the default. A missing ServiceNow instance, a private address,
or a device named Lab never enables this exception automatically.

## Operator setup

1. Restart the NetClaw API when no Intent operation is active; refresh Canvas.
2. In the Intent input panel, open **Change control → Manage lab authorization**.
3. Select only the SSH devices you own/administer as lab devices. Confirm the lab
   designation and choose **Save lab authorization**.
4. Choose **Local / Lab · local change record**, and select the devices involved
   in the request (both routers for a two-ended VPN). Submit your normal request.

The initial lab designation is explicit, but a clear subsequent configuration
request is approval for that task; there is no additional CLI-proposal/send dance.
Questions still authorize only read-only work. Discoverable device facts should
be gathered automatically; unresolved design decisions and secret references may
still require a question. Do not enter PSKs/passwords in ordinary chat.

## Authorization boundary

The localhost-only API validates the chosen mode and selected IDs against a
persisted lab allowlist. Grants bind the ID to its SSH host, port and protocol.
Editing the endpoint invalidates the grant until reauthorized. Revision checks
reject stale settings. New devices are never included automatically. Settings
cannot be changed through the API during an active Intent run. Disabling lab
changes affects future submissions, not a cancellation/rollback of previous work.

This allowlist is distinct from the read-only topology collector scopes. Never
add `config-write` to the collector authorization file. Production or mixed
production/lab requests must use the production workflow and its approvals.
The system never auto-enables an environment-wide `LAB_MODE` switch.

The bundled AGENTS/SOUL/USER policy now explicitly recognizes the local exception.
An external OpenClaw agent workspace must load this owner-approved policy too;
`Install-NetClaw-Lab-Policy.ps1` can install a bounded note into its AGENTS.md.
It does not enable the mode or designate any devices. It preserves the existing
agent instructions and backs them up before adding the note.

## Work phases and audit

- Before contacting the Gateway, the API durably creates a local change record
  for the explicit task, endpoint identities and policy revision.
- **Prepare (read-only):** the agent discovers current state and capabilities,
  resolves necessary questions, saves a real baseline and a scoped rollback plan
  for each selected endpoint at the exact local paths supplied by the API, and
  returns a `prepared` report with evidence using exact device IDs.
- The API requires a baseline and rollback report for each endpoint and checks
  that the local artifacts are nonempty regular files, not symlinks, within the
  record directory, at most 4 MiB each. It records hashes and sizes before sending
  the **APPLY PHASE** instruction. Missing artifacts stop the workflow.
- **Apply/verify:** use installed, authorized configuration tools; verify every
  selected endpoint and preserved connectivity. On failure use the scoped rollback
  plan and verify recovery. Never claim success for a failed or unverified change.
- Agent reports and terminal status are durably recorded. Ambiguous transport or
  audit failure is uncertain, never proof that nothing changed. No auto-replay.

Storage: `OPENCLAW_HOME/netclaw-changes/policy.json` and
`OPENCLAW_HOME/netclaw-changes/records/<run-UUID>/` (by default under `~/.openclaw`).
Each run contains `record.json`, `events.jsonl`, and baseline/rollback artifacts.
The GUI links the local record; it does not expose artifact contents through an API.
Baseline files may contain secrets: keep this directory local, protect it with OS
permissions/encryption, and never commit it. File modes request owner-only access
on POSIX; Windows protection depends on the user's inherited directory ACLs.
Report metadata is bounded and conservatively secret-filtered. Raw configuration
and transcripts are not copied into the metadata. No SQL database is involved.
Records persist until the owner archives/removes them; automatic retention is not
implemented. Existing IDs cannot be submitted again even after an API restart.

## Important limits

This is change-policy orchestration, **not a sandbox or a device-side RBAC layer**.
The API checks selected endpoints, workflow transitions and artifact presence.
Actual command scope and the truth of agent-reported baseline/verification still
depend on installed tools and the agent. File existence does not independently
prove a baseline was collected from the router. Tool-level approvals, credentials,
host-key verification, policy enforcement and destructive-command restrictions are
not disabled. A denied tool may not be bypassed using an ad-hoc SSH script.
The local audit is not cryptographically immutable or a replacement for production
GAIT/ITSM controls; for this explicit lab workflow it is the supported audit path
when GAIT/ServiceNow are absent.

No network-device commands are run when lab mode is merely enabled. A new request
is always required. Live VPN capability and configuration outcomes require testing
against the installed agent/tools; synthetic tests do not establish them.

## Tests

`npm run test:change-policy` covers default production, explicit consent,
endpoint/revision binding, phase gating, missing artifacts, durable records,
restart replay protection, secret filtering, scope errors and localhost guards.
`npm run test:intent-execution` retains production continuation/approval tests.
The synthetic terminal design page supports lab setup without real network access.

## Hermes runtime

Spec 148 offers read-only Terminal Intent assistance through the protected Hermes companion. Local/Lab APPLY and configuration tools are unavailable and rejected before dispatch; this does not weaken the change-control requirements above. Direct terminal presentation remains available under its existing authorization. A hosted-Hermes approval never substitutes for endpoint grants, baseline/rollback artifacts, phase checks, verification or audit. See [Hermes HUD](../../docs/HERMES-HUD.md).
