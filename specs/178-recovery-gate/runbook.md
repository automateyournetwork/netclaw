# R07 recovery procedures

These procedures apply to the explicitly selected installation and the scope in
verification.md. They do not authorize operating other homes, publishing services,
extending a retained deployment or starting HA. Consult the evidence matrix for
actual qualification and its source/platform limits.

## Before every recovery

1. Identify the selected runtime home, installation, enrolled member/key, current
   registry revision and exact owned process/service. Check expiry and scheduled
   retirement before starting a drill. A spent or unknown lifecycle claim is
   evidence to inspect, never a command to repeat.
2. Capture private baseline: current status, original operation/task references,
   pending decisions, result/receipt/ACK hashes, attempt/provider/native counts,
   process ownership and source hashes. Use consistent SQLite backup for a live
   database. Do not copy authority into another active home or restore an old DB.
3. Record UTC fault/restoration timestamps and monotonic elapsed time. Separate
   failure detection from recovery after restoration; human diagnosis time is
   not service reconnect latency.
4. Recover original references first. An unknown outcome forbids a new submission,
   approval, model inference or tool execution to obtain a more convenient answer.

For an explicitly selected OpenClaw home, existing local inspection is:

```sh
NETCLAW_RUNTIME=openclaw OPENCLAW_HOME="$SELECTED_RUNTIME_HOME" \
  python3 scripts/federation-control.py status
NETCLAW_RUNTIME=openclaw OPENCLAW_HOME="$SELECTED_RUNTIME_HOME" \
  python3 scripts/ngrok-control.py validate
```

Set `SELECTED_RUNTIME_HOME` from the reviewed installation record, not a guessed
path. Hermes uses its existing selected-home contract instead. The second command
inspects the endpoint registry even for direct transport; its historical filename
does not mean ngrok is selected. Do not display private environment contents.

## Direct Border service restart

**Detect:** status/listener/health failure at the existing provider address.
Distinguish workspace/HUD failure from federation/gateway failure.

**Restore:** inspect owned service logs and process record. Under the scoped
change plan, restart only the failed owned component with its existing service
manager. `scripts/federation-control.py restart` is appropriate only when that
selected daemon owns the component; do not also restart a systemd/launchd-managed
copy. Preserve home, certificate, key, registry and provider address.

**Verify:** same installation/key and advertised endpoint, authenticated member
reattachment without a token, original pending/result references, unchanged
provider/native effect counts. Recover a saved result by GET/status. A healthy
HUD alone does not prove member recovery. If ownership or state is uncertain,
stop before another restart and retain the failed attempt.

## Border restart with pending work

**Detect:** disconnect/timeout while an original operation is pending. Save its
nonce, operation/task ID and whether a decision was already sent.

**Restore:** start the same owned Border/home; do not recreate enrollment or reset
its ledger. Inspect original task status. Dispatched work interrupted by restart
may remain unknown and needs reconciliation; do not turn it back into queued.

**Verify:** original request/attempt/result/ACK identity, one original effect or
none and no new decision/provider call. A cancellation request or missing reply
does not establish that execution was absent. Keep unknown state when evidence
cannot establish the outcome.

## Member restart

**Detect:** Border liveness reports the member unavailable; compare timestamp,
actual owned member process and its local status.

**Restore:** restart only the owned member with the same enrollment/key/home.
Let existing strict reconnect authenticate; do not issue a fresh token, change
its key or fall back to a legacy channel. Resolve a wrong/expired certificate
through the separate credential procedure, not by disabling verification.

**Verify:** same member identity/key/generation, live authenticated channel and
original task states. Pending dispatch claims remain claims. Compare effects
before/after GET-only result recovery and record restore-to-reattach time.

## Provider network or address unavailable

**Detect:** preserve the bounded reported cause and registry revision. Check the
selected address/listener/DNS and actual connection result; distinguish network
unreachable, trust refusal, admission refusal and model-service failure.

**Restore:** repair only the reviewed listener/network path or explicitly replace
the address as below. Keep TLS name, CA, application pin and direct transport.
Never disable certificate validation or automatically select another transport.

**Verify:** refusal during outage caused no new admission/effect; restoration
authenticates the same authority and retrieves original records. If the failure
is an identity mismatch, stop rather than treating it as a transient outage.

## Endpoint replacement with unchanged identity

**Baseline:** record the current registry revision, entry ID, trusted TLS name,
CA/application pin, enrolled keys, operation IDs and client references. Prove
the replacement listener belongs to the same installation before routing clients.

**Change:** update only the routing host/port/address reference using the existing
registry writer with an exact expected revision:

```sh
NETCLAW_RUNTIME=openclaw OPENCLAW_HOME="$SELECTED_RUNTIME_HOME" \
  python3 scripts/ngrok-control.py address \
  --id "$REGISTRY_ENTRY_ID" --host "$REPLACEMENT_ROUTING_HOST" \
  --port "$REPLACEMENT_ROUTING_PORT" --address-ref "$REPLACEMENT_ADDRESS_REF" \
  --expected-revision "$OBSERVED_REGISTRY_REVISION"
```

All values come from the reviewed change, not a peer message. Reconnect through
the new registry revision with existing keys. A revision conflict requires a
fresh read/review; never force an overwrite. If rollback is needed, review the
current revision and use the existing registry recovery operation explicitly;
do not copy an old registry file over newer state.

**Clients:** VS Code uses **NetClaw: Replace Cloud Border Endpoint** (tree:
**Replace cloud endpoint**, final native action **Replace endpoint**) and keeps the profile and
original references after same-installation validation. Sessions remain bound to
their original origin. Mobile's qualified change is the same trusted WSS hostname
and path at a new port, verified with the retained device key and installation;
its owner HTTPS origin stays unchanged. Use **Change connection port** from the
protected/reconnect view, or Settings → **Recover connection** for ordinary mode;
enter **Secure connection port**, then **Verify and update port**.
A new trust identity requires separate
enrollment and is not this procedure. HUD uses original ID/nonce/parent recovery
at the validated installation; transferred references contain no credentials.
The HUD **Reference type** offers Operation ID or Client nonce; **Recover combined
reference** offers Parent ID or Client nonce. Imported references are status-only
and do not authorize a new approval or cancellation.

**Verify:** unchanged identity/key/authority, current revision, original references
and results, no preparation/approval replay. Wrong identity/TLS or storage failure
must leave the original binding and records recoverable.

## Member key or certificate revocation

**Baseline:** identify the exact enrollment and open channels, current generation,
pending work and already admitted effects. Revocation is not rollback.

**Change:** use the existing owner-scoped member removal/revocation operation.
Durable state must change before awaiting channel close. Do not revoke unrelated
members, clear databases or re-enroll automatically to make the test green.

**Verify:** new action on the original open channel and reconnect both refuse;
an awaited result is not delivered or accepted as currently authorized after
revocation. Preserve already admitted effects and original audit. Expired/not-yet-
valid member application certificates refuse at strict admission/use. Transport
TLS certificate validation remains at handshake/reconnect, with no external
CRL/OCSP or continuous TLS-leaf expiry monitoring claim. Idle socket closure timing is
not the authority guarantee: no post-revocation action may be admitted.

**Restore:** revocation is intentional. If future access is authorized, use a new
explicit enrollment/credential procedure and preserve retired identity evidence.
Never restore revoked authority by rolling back its database.

## Model provider outage

**Detect:** inspect guard/provider status and original admission/inference claim.
Separate a known pre-dispatch refusal from a dispatched call with unknown outcome.
The client's timeout is not evidence that the provider did no work.

**Restore:** restore only the reviewed provider/model process or upstream path.
Use existing operator recovery/reattest/rebind controls where required. A member-
or runner-wide unknown latch remains authoritative; new operation IDs cannot
bypass it. Do not edit claims, reset budgets or resend a prompt automatically.

**Verify:** clear refusal or retained uncertainty is visible, prior inference/tool
counts preserved, and original result retrieval does not dispatch again. R05
actual model-outage credit is narrow; it does not qualify every hosted provider.

## Lost reply or acknowledgement

**Detect:** preserve original task/nonce/operation/attempt and sent markers. Determine
whether durable admission, result, receipt or ACK already exists.

**Recover:** use original-reference GET/status/result. Use the existing explicit
reconciliation path only when its contract authorizes receipt/ACK convergence;
do not re-prepare, reapprove or resubmit work. Repeated delivery of the same durable
ACK is not permission to re-execute the workload.

**Verify:** exact result/receipt/ACK identity and one original native effect or
none. After process restart, counts and signed artifacts must remain unchanged.
If the original outcome cannot be proven, retain unknown and stop retrying writes.

## Duplicate submission and cancellation

**Duplicate:** original task/protected-operation request IDs deduplicate admission
even across concurrent requests and restart. Observe their original record; do
not mint a new ID. Repeated arbitrary synchronous calls are separate executions,
so an unknown synchronous response must never be automatically retried.

**Cancel:** persist the client send marker before the request. Before dispatch,
confirm cancellation with zero native/provider effects. After dispatch, display
cancel-requested/unknown or actual completed result as appropriate. Cancellation
does not undo a remote tool call. Do not erase a late result or retry a lost cancel
request by clearing the marker.

**Verify:** one original effect or none; original IDs and audit survive. Status
reads cannot turn sent markers back into an action that can be submitted again.

## HUD, VS Code and Mobile recovery

**HUD:** refresh/reopen the original operation. A lost decision remains sent after
reload even if the server still reports review-pending. Refuse redirects. Exact
ID/nonce/parent recovery retrieves state and cannot grant approval.

**VS Code:** reconnect the saved profile, recover existing operation/combined
references, and confirm original decision markers. Endpoint update validates
destination first and preserves profile ID, references and original session scope.
Wrong identity or storage failure must not replace the old working profile.

**Mobile:** foreground/background/cold reconnect uses the retained key/reference.
Stop the old reconnect loop before endpoint change/navigation; a late dial result
must not revive a disposed connection. Explicit WSS-port replacement verifies
same identity before save. Revocation is a refusal, not an endless retry prompt.

For each native client, inspect actual request methods and effect counters as
well as the displayed result. Simulator evidence does not qualify physical camera
or Secure Enclave behavior.

## Optional ngrok agent restart

Unselected/unqualified in R07. If separately selected, baseline reservation,
agent ownership and registry; restart only the owned agent, preserve reserved
address, and verify same identity/reattachment with no new enrollment or workload.
Do not apply this branch to a direct deployment.

## Optional ngrok service/account outage

Unselected/unqualified. Preserve observed service/account error and original
operations; only the explicitly tunneled deployment is affected. Restore the
selected account/service under its own scope; do not downgrade to insecure direct
transport. Verify original identity/results without resubmission.

## Optional ngrok authtoken revocation

Unselected/unqualified. Token revocation belongs to the tunnel credential owner;
it does not revoke NetClaw enrollment identity. Verify tunnel closure/refusal and
unchanged NetClaw keys/history. Replacement credentials require exact private
configuration and account authority; never include them in evidence or registry.

## Closeout

Correlate all scenario timestamps, original IDs, authority and effect evidence.
Export verified private artifacts before stopping/removing owned disposable
resources. Confirm actual cleanup rather than inferring it from process/VM stop.
Preserve R05/R06 jobs and all unrelated resources. Record limitations and human
timing/acceptance review in verification; no R08 work follows automatically.
