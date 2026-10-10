# Hermes in the NetClaw HUD

Spec 148 connects the shared HUD to a dedicated, protected Hermes agent. Federation remains spec 149. Mac and WSL live/browser acceptance is recorded in [the Mac return record](../specs/148-hermes-hud-integration/closure.md), including the exact qualified hosts and remaining matrix disposition.

## Install and launch

On macOS or inside Ubuntu on WSL2, configure Hermes with `hermes setup` first. Keep credentials in the selected Hermes home's `.env`; repository or OpenClaw credentials are never imported automatically into Hermes.

```sh
./scripts/install.sh --runtime hermes --add "subnet-calc hermes-hud"
./scripts/netclaw hud select hermes "$HOME/.hermes"
./scripts/netclaw hud status
./scripts/netclaw hud
```

Use `HERMES_HOME` or `hud select hermes /absolute/custom/home` for another installation. The persisted selection survives a fresh shell and a different working directory. Explicit `NETCLAW_RUNTIME` and matching home overrides take precedence. With no selection the default remains OpenClaw. Switch with `netclaw hud select openclaw "$HOME/.openclaw"`. `npm run dev` honors selection but does not start a missing Hermes companion; use `netclaw hud` for the managed lifecycle.

The installer creates a private companion under `<home>/python-runtimes/hermes-hud-agent`, pinned to Hermes **v0.21.6**, commit `818c13be1dc4fd28987e1e881a9408224afd4535`. It uses Python **3.14**, while the bridge and subnet component use separate Python **3.12** environments. HUD Node support is **24.19+ below 25, or 26.1+**; Mac qualification used 24.19.0. The source manifest and dependency constraints are in `config/hermes-hud-*`. An owner gateway can have a different version: it is neither patched nor restarted by this launcher.

Native Windows launchers refuse Hermes with WSL guidance before starting OpenClaw. Run the Linux launcher from the WSL filesystem, then open its localhost HUD from Windows. Do not expose the companion beyond loopback or store its private files in a shared `/mnt/c` directory.

## Supported scope

| Surface | Hermes behavior |
|---|---|
| Standard Chat, Canvas, local Avatar | Real contextual Hermes turns, separate installation storage, owned history |
| Tools and skills | Only source-qualified read-only implementations and reviewed installed skill text |
| Initial qualified tool | `subnet_calculator`, IPv4 `/24` through `/30`, through the actual registered MCP server |
| Terminal Intent | Read-only assistance; no device observation claimed without tool evidence |
| Model and effort | Configured agent model; per-conversation model/effort selection unavailable |
| Usage | Actual per-request provider counters when returned; otherwise unknown |
| Attachments, APPLY/configuration execution | Unavailable in this release |
| Hosted Avatar, n2n/iN2N | Unavailable; local Avatar remains supported, federation is spec 149 |

Installed tools are not automatically safe to execute. The companion excludes shell, code, delegation, shared memory, arbitrary files/history, plugin tools, and unreviewed MCPs. New eligible tools require implementation review, policy qualification and tests. This deliberately narrow first qualification does **not** claim general Hermes network-tool parity. Direct terminal presentation and its existing endpoint/change controls remain separate.

## Ownership, evidence and recovery

Each installation owns a private UUID and browser cookie. Saved Chat and Canvas work is namespaced by that identity. OpenClaw legacy browser data is copied only into the first explicitly associated OpenClaw installation; originals remain as backups. Hermes never imports it. Bindings expire after 30 days; inaccessible native transcripts are not a public lookup interface.

The private stdio MCP bridge has eight conversation/status/control tools. It is not registered with either agent. Submission is persisted in SQLite **before** the upstream POST. A repeated nonce cannot create another run. Unknown outcomes persist across process restarts; status checks never replay work. **Check status** can recover a late reply. **Start fresh conversation** requires an explicit acknowledgment when the previous outcome is unknown. This does not cancel or undo the earlier operation. **Request stop** is cooperative; only observed terminal state confirms cancellation. Approvals accept only the exact pending request, once or deny. The initial read-only subnet tool does not require a paused approval.

Background model-generated titles and automatic context compression are disabled in the protected companion because those auxiliary clients bypass its inference guard. Start another owned conversation when reaching the configured model's context limit; no automatic replay occurs.

Actual tool dispatch/result records carry the owning request identity independently of compressed transcript rows. Assistant prose alone is not execution proof. The bridge strips private reasoning and secret fields; configuration values remain masked. Completed request metadata expires after 30 days; uncertainty records are retained for review.

## Status and troubleshooting

`netclaw hud status` reads selection and the authenticated local companion health endpoint without starting a service, provider request or tool. A ready API is separate from verified execution. `providerConfigured: unverified` means health did not test the provider. Missing tools, authentication failure, incompatible source and policy drift must be repaired before treating the installation as accepted.

- Missing companion: install `hermes-hud`, then use `netclaw hud`.
- No qualified tools: install/register the reviewed `subnet-calc` component in the **selected** Hermes home. A changed source or registration is unqualified.
- Policy/source mismatch: stop these HUD processes, restore or deliberately requalify the pinned implementation, then relaunch. Never disable the guard.
- Busy ports: stop the identified owner process yourself or choose `HUD_PORT`, `HUD_UI_PORT`, and `NETCLAW_HERMES_HUD_PORT` consistently. The launcher never kills an unrelated process.
- Missing provider: finish setup and the selected `.env`, then run the explicit live acceptance harness. Health never spends provider credits to test credentials.
- Unknown request: inspect owned status/history and evidence. Do not resend to find out whether it ran.

OpenClaw retains the historical repository `.env` fallback. To move that dependency explicitly, use `python3 scripts/import-env.py --help` and its literal import mode; selected-home values win. Back up selected configuration and browser work before changing installation roots. Rollback keeps original browser keys/IndexedDB and `.v1-backup` bindings; never copy another installation's identity file or downgrade a v2 binding in place.

See [private server contract](../mcp-servers/hermes-hud-mcp/README.md), [validation](../specs/148-hermes-hud-integration/validation.md), and [WSL handoff](../specs/148-hermes-hud-integration/validation-handoff.md).
