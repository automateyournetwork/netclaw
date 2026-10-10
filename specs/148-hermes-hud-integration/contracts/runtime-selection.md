# Runtime selection, launch and installation contract

## Resolution

Resolve before dotenv, any runtime filesystem access, module-level path initialization or subprocess:

1. An explicit `NETCLAW_RUNTIME` must be exactly `openclaw` or `hermes`; invalid values stop startup. The selected runtime's explicit home/config overrides apply. Use a matching persisted selection when its kind matches and no home override is supplied; otherwise use that kind's historical default.
2. Without explicit kind, use a valid persisted descriptor. A selected-kind home override may refine it. An environment home variable for an unselected kind does not switch selection.
3. Without kind or descriptor, preserve historical OpenClaw default/home precedence (`OPENCLAW_STATE_DIR`, `OPENCLAW_HOME`, `OPENCLAW_CONFIG_PATH`). Presence of `HERMES_HOME` alone does not silently switch an existing deployment.

Descriptor: `${XDG_CONFIG_HOME:-$HOME/.config}/netclaw/runtime.json`, schema 1, `{schemaVersion,kind,home,configPath?}`. Owner-private atomic writes by installer or explicit `netclaw hud select`; regular startup reads it and must not overwrite selection. Unknown schema, malformed JSON, bad ownership, symlink escape or unreadable paths produce a selection error. Missing descriptor is the only default-fallback case. Canonicalize and reject root/unowned runtime paths; paths with spaces remain valid. Explicit selection never causes reads of the unselected runtime's `.env` or credentials. Shared owner static instructions are an explicit approved exception, not a credential source.

When an explicit home override changes the persisted home, discard the descriptor's old configPath unless `OPENCLAW_CONFIG_PATH` is explicitly supplied; otherwise derive configuration from the new home. An explicit configPath is treated as an intentional selected configuration source and validated, not accidentally inherited across homes. Test descriptor home/config A plus home B, both with and without explicit config override.

This document and shared golden fixtures define the canonical algorithm. `scripts/runtime-selection.py` supports Unix installer bootstrap before Node exists; `scripts/runtime-selection.mjs` supports the HUD and Windows launchers without a new Python prerequisite. Both must pass identical precedence/error/override fixtures. Node's output distinguishes public-safe and private-process metadata, never secrets. PowerShell uses the Node resolver with its existing Node dependency; native Windows Hermes fails before gateway/config mutation. Validate Windows owner ACLs rather than pretending POSIX modes apply there. WSL uses Linux paths/private file modes.

## Command behavior

- `scripts/netclaw hud select --runtime hermes --home /absolute/path`: validates and persists selection; no model/tool request, gateway restart or owner config mutation.
- `scripts/netclaw hud`: resolves selection, explicitly launches fresh owned compatible companion and HUD processes; detects conflicts without killing unrelated processes.
- `scripts/netclaw hud status`: reports stages read-only; never starts services or inference.
- `cd ui/netclaw-visual && npm run dev`: honors the same persisted selection; if the Hermes companion is not running, show the documented launch action rather than bootstrap through a GET route.

Preserve existing `scripts/netclaw` TUI commands. Installer adds selection persistence only after successful selected-runtime setup, not midway through a failed installation. Running `upgrade-hud.sh` builds/upgrades assets and validates prerequisites; it does not silently restart or replace an owner gateway.

## Private component and credentials

Component ID `hermes-hud`; directory `mcp-servers/hermes-hud-mcp`; `access:"hud-private"` in `config/installer-access.json`. Official MCP lifecycle discovery verifies declared tools but does not call an operational tool or provider. Catalog/profile selection installs it for Hermes HUD, not as a dependency of every OpenClaw installation.

Bridge uses its isolated Python manifest. Companion uses the selected, verified Hermes interpreter; no arbitrary browser executable selection and no shell interpolation. Companion binds to literal loopback only, default port 8643 distinct from the owner's API default. Explicit server-side port override must be validated and conflict-safe. HTTP redirects/proxy environment are disabled; remote hosts and profile routing are rejected.

Implementation refinement: install the companion at the fixed private
`<selected-home>/python-runtimes/hermes-hud-agent/{source,venv}` paths. The owner gateway
and its interpreter remain unchanged. On explicit launch, verify the full source manifest
and record private `<selected-home>/netclaw-hud/launch.json`: schema version, absolute
interpreter/source paths, source revision, installation identity and selected configuration
digest. These are provenance records, not trusted process handles. Every launch verifies
source again, and execution guards revalidate source/configuration. Explicit server-side
`NETCLAW_HERMES_SOURCE` / `NETCLAW_HERMES_PYTHON` overrides remain subject to the same
source qualification; no browser-supplied executable or path. Occupied UI/API/companion
ports refuse before spawning or creating companion credentials. No stale PID reuse or
unrelated-process termination.

The companion's response store, run-idempotency store and session store must be injected before their upstream constructors/lazy getters choose default paths. Use process-local fixed-path factories for `ResponseStore`/`RunIdempotencyStore` and explicit `_session_db` injection; all reside in `<selected-home>/netclaw-hud/hermes/`. Replace the companion's memory checkout manager with a no-op before use in addition to protected-agent constructor overrides. Qualification tests must prove zero writes to the owner's `state.db`, `response_store.db`, `runs_idempotency.db` and shared memory files.

Provider secrets remain in the selected owner `.env`; generated companion credentials are stored in private `<selected-home>/netclaw-hud/companion-auth.json`. `NETCLAW_HERMES_HUD_API_KEY` stays server-side and never enters argv. Public configuration documents only variable names (`NETCLAW_RUNTIME`, runtime home variables, `NETCLAW_HERMES_HUD_PORT`, API key name, existing `HUD_CHAT_TIMEOUT_MS`). Runtime descriptor and compatibility/policy files contain no secrets. Server config writes require existing local-access controls and update only an allowlisted supported key in the selected source, preserving unrelated content. Unsupported edits reject before writing.

Agent-native configuration excludes the bridge's conversation interface, including translated Hermes config and blanket registration scripts. Diagnostics documentation explains the private status interface; it does not grant agent recursion. Guard readiness distinguishes missing component, compatibility mismatch, policy mismatch, stopped companion, authentication rejected, missing provider and upstream failure.

## Upgrade/rollback

Do not overwrite owner `.env`, Hermes YAML, persona/static instructions, MCP registrations or skills. New descriptor/installation metadata and binding/browser migration have versioned backups and idempotent markers. Rollback retains pre-migration data and refuses downgrade writes against unknown schemas. No automatic cross-runtime history migration. Record preservation hashes for synthetic upgrade tests, not actual secret contents.

Legacy OpenClaw HUD may currently read repository `.env` as fallback. Preflight reports that dependency without exposing values and offers the documented explicit literal import using `scripts/import-env.py`; selected-home existing keys always win. Keep the old supported startup behavior until that migration has completed or provide the actionable preflight refusal—never silently drop needed values. Hermes does not read/import repository credentials automatically. Test conflict preservation and missing values with populated synthetic dotenv sources.
