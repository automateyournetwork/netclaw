# Hermes federation and NetClaw Mobile — 1.8.0

Spec149 adds Hermes execution to the existing NCFED transports, including Border
and member roles. Spec148's HUD companion remains separate: federation owns its
own private ledger and processes under the selected home's `netclaw-federation/`.
A capability card describes a peer; it never authorizes execution or selects a
local runtime. Missing harness/version metadata is **unknown**.

## Install and select

Complete `hermes setup`, then use the same selected home for installation and
launch. For a custom home, export its absolute `HERMES_HOME` before these commands:

```sh
./scripts/install.sh --runtime hermes --add "subnet-calc n2n"
export NETCLAW_RUNTIME=hermes
./scripts/peering-setup.sh
./scripts/peering-setup.sh start
./scripts/peering-setup.sh status
```

The n2n component installs the isolated protocol/bridge dependencies and pinned
Hermes companion without requiring OpenClaw or installing the browser UI. Add
`hermes-hud` separately for HUD Chat/Canvas/local Avatar. CLI and HUD selection
share the installation identity. `status` is read-only; `stop` only addresses the
selected installation's owned daemon. Use different local ports for concurrently
running installations. Do not copy ownership manifests between homes.

Configure iN2N/eN2N and enrollment through the existing Risk and peering commands.
Existing consent, possession proof, member scope, grants, approvals, rate/token
budgets and revocation checks still apply. Remote chat has no tools. A remote
skill receiver has only its qualified skill tools; it cannot promote itself to
an operator, manage grants, launch a shell or orchestrate another Risk.

## Qualified execution

The initial protected profile is the registered, reviewed IPv4 subnet calculator
(`/24` through `/30`) and installed `subnet-calculator` skill. Local HUD/mobile
operator requests may observe federation, perform bounded subnet calls, open
owned peer chats and delegate/poll permitted subnet work through n2n MCP. Installed
or advertised tools outside this profile are **not execution-qualified**.

Hermes members use private homes, a minimal skill/configuration slice and their
own state. To prepare an inspectable member from a configured Hermes Border:

```sh
python3 scripts/in2n-member-home.py --runtime hermes --risk lab --member subnet
python3 scripts/in2n-migrate.py --risk lab --border-endpoint 127.0.0.1:11790 --staging ./hermes-migration
```

These are separate alternatives: each preserves an existing member config rather
than overwriting it. Add the endpoint and one-use enrollment token to the generated
private `.env`, and launch with `N2N_MEMBER_ENV_FILE` using the recorded n2n Python.
Never source credentials into a shared shell or copy Border communications keys.
Mixed runtime deployments keep each member's own selected configuration/runtime.
Generating a systemd file does not prove a service is active or confined.

Hermes production model-guard/confinement qualification is pending and fails
closed. The Mac acceptance uses explicitly isolated **testing** mode and read-only
subnet work. Do not treat it as production configuration-change authorization.

## Mobile compatibility

Use **NetClaw Mobile 1.0.3 (build 6) or later** for full uncertainty-aware Hermes
behavior. This candidate was signed and uploaded to App Store Connect; it is not
an App Store public-release announcement. Existing enrollment and NCFED method
names remain unchanged. Older clients can still send text; unknown/interrupted
outcomes project to a failed state with an explanation instead of silent pending,
but cannot provide the new durable lost-receipt recovery or harness summary.

Authenticated `n2n/edge/ask` requests receive explicit operator execution scope,
bound to installation, enrolled device/key generation and conversation. The client
persists a request ID before sending; reconnect looks up that admission instead of
resubmitting it. Progress, results and cancellation use the existing task methods.
Siri preserves `origin: voice`; transcribed speech is text input. Siri, Watch and
Live Activity show uncertain/interrupted/cancellation-requested outcomes explicitly.
A requested stop is not a confirmed stop. **Check status; do not replay uncertain work.**

The Summary page displays Border type, version, model and advertised capabilities.
Metadata absent from older Borders remains unknown. Disconnected information is
labeled as last received rather than current state.

**Photo, video and audio-file attachments are unavailable with the protected
Hermes Border.** They are rejected before execution; the app explains the limit
and preserves the draft. Text produced by voice transcription is supported.
Existing OpenClaw attachment paths remain, with regression tests; this does not
claim new physical-camera/microphone qualification.

## Evidence and recovery

See [spec149 verification](../specs/149-hermes-ncfed-federation/verification.md) for
actual host/runtime coverage and [handoff](../specs/149-hermes-ncfed-federation/validation-handoff.md)
for unrun platforms. Controlled-provider tests run the real pinned Hermes agent
and real MCP subnet tool over authenticated local NCFED transports; they are not
hosted-model or physical-device tests.

After a crash, a pre-dispatch request becomes interrupted; work that may have
executed becomes outcome_unknown. Owned late results can reconcile it. Retain
unresolved ledgers and task records. For source rollback, stop the selected
installation, preserve its complete home/databases and restore the matching source
and isolated runtime. Do not downgrade a migrated database in place or erase
uncertain work. Existing owner config, identity, skills and histories are preserved.
