# NetClaw 1.7.0 — Hermes HUD integration

Spec 148 connects Hermes deployments to the shared NetClaw HUD through a private MCP
bridge and protected, pinned Hermes companion. OpenClaw remains the default when no
runtime is selected. Chat, Canvas, local Avatar, owned history, Settings and recorded
usage follow the selected installation.

## Changes

- Add persistent runtime selection and custom-home launch without an OpenClaw dependency
  for Hermes. The dedicated companion uses authenticated loopback and isolated Python
  environments; it does not attach to or restart the owner's ordinary Hermes gateway.
- Qualify the real read-only subnet MCP and installed skill, with request-correlated tool
  evidence. Isolate conversations, browser storage and private runtime databases.
- Preserve independent Canvas branch context, saved drafts/quotes/files and Chat/Avatar
  state. Surface unsupported controls before dispatch.
- Persist admission before submission, honor configured deadlines, retain unknown
  outcomes across restarts, recover late results and provide cooperative stop without
  automatically replaying work.
- Preserve existing OpenClaw behavior and populated homes through installation/upgrade.
  Fix truthful readiness, runtime Settings rows and known pre-admission failure reporting.

## Upgrade and compatibility

Follow the [Hermes HUD guide](https://github.com/automateyournetwork/netclaw/blob/v1.7.0/docs/HERMES-HUD.md).
Use Node 24.19–24.x or 26.1+, private bridge/tool Python 3.12 and companion Python 3.14.
The installer pins Hermes v0.21.6 revision 818c13be1dc4fd28987e1e881a9408224afd4535 and
explicit dependencies. Keep credentials in the selected home's private `.env`; they are
not automatically imported from OpenClaw or the repository.

Start with `netclaw hud select hermes /absolute/home` and `netclaw hud`. Preserve existing
configuration and browser work before switching roots. Keep the same browser origin;
legacy OpenClaw originals and binding backups remain available for rollback.

## Validation

Mac and Windows/WSL live Anthropic five-turn/context/skill/subnet acceptance passed.
Mac validation passed 369 HUD tests, 27 Canvas suites, 238 installer tests plus 25
subtests, six real-process integration/fault tests, controlled real-browser acceptance,
repeated install/build and saved-work rollback checks. Live existing OpenClaw Chat,
model selection, Canvas, Avatar and structured read-only Terminal Intent passed.

See the [acceptance record](https://github.com/automateyournetwork/netclaw/blob/v1.7.0/specs/148-hermes-hud-integration/closure.md)
for exact versions, commits, evidence types and qualification limits.

## Known limits

The initial qualified Hermes tool is IPv4 subnet calculation for /24 through /30.
General network MCP/CML parity, writes/APPLY, attachments, per-conversation model/effort
overrides, hosted Avatar, shared memory and automatic context compression are unavailable.
Background auxiliary model clients are disabled outside the protected inference path.
The read-only subnet tool has no eligible paused approval; positive approval protocol/UI
cases use controlled fixtures. Federation is separate spec 149.

Qualified hosts are macOS 26.5.2 arm64 and Ubuntu 26.04 x86_64 under Windows WSL2.
Native Windows Hermes is unsupported and its early refusal was tested. Ubuntu 24.04
and native Windows OpenClaw are unverified; final matrix approval is pending.
