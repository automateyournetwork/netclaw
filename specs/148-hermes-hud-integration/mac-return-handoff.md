# Spec 148 — return from WSL to Mac

## State and transfer

Continue **148-hermes-hud-integration**, never main. The WSL worktree is
`/home/johncapobianco/netclaw-148`. WSL fixes start at `9f26dfa`, descending from
`28cbc67` and `db5a1b0`. Later branch commits contain browser checks, sanitized evidence
and this handoff. Run `git log -4 --oneline` after importing to record the exact tip.
No push, merge or publication was performed. No spec 149 work was started.

A portable local bundle is written after the final commit to
`/home/johncapobianco/netclaw-spec148-wsl.bundle`. It contains Git history only; provider
keys, profiles, dependencies and private test logs are excluded. Transfer that file to
Mac. Preserve the existing checkout and all uncommitted changes/stashes. A new checkout
is the simplest way to avoid touching existing work:

```sh
git clone --branch 148-hermes-hud-integration /path/to/netclaw-spec148-wsl.bundle "$HOME/src/netclaw-148-wsl-return"
cd "$HOME/src/netclaw-148-wsl-return"
git status --short --branch
git merge-base --is-ancestor 9f26dfa HEAD
```

Do not use the old Mac `28cbc67` tip alone: it lacks the stable Python/Anthropic dependency,
plugin/lazy-install protection and upgrade-preflight fixes discovered in WSL.

## What passed, and what remains

Read [validation.md](validation.md) and the JSON/log summaries in [evidence/](evidence/).
Actual WSL Anthropic (`claude-sonnet-4-6`) completed all five turns with a reviewed
subnet tool result, remembered context, 14 usable hosts and actual usage. The controlled
real agent passed an actual companion restart between turns. Windows Edge exercised
loopback, contextual Chat, local Avatar, owned history and refusal paths. Two Canvas branches preserve their distinct quote-point contexts, graph and draft on
refresh; the truthful Hermes readiness badge also passes. Automated HUD, Canvas, installer and compatibility checks
passed. The actual isolated HUD upgrade preserved the selected profile; owner service
PIDs and credential/configuration hashes remained unchanged.

**This is a clean source handoff, not full Windows/WSL acceptance or spec closure.**
Unchecked tasks must stay unchecked until their entire criteria are observed:

1. **T053, Mac-only:** live five-turn context/tool/skill on a qualified Mac Hermes home;
   real upgrade/preservation and existing OpenClaw Chat/Canvas/Avatar/models/panels/
   Terminal Intent regression. WSL success cannot satisfy this gate.
2. **T052:** finish selected-runtime panel/no-inference checks, UI attachment draft retention,
   actual installation switching/storage separation, pending-request progress, exact
   approval/deny and stop/late/unknown/fresh-conversation browser workflows. Inspect the
   committed Windows browser report rather than extrapolating beyond its assertions.
3. **T029/T055:** full real-process fault matrix while a request is pending, including
   HUD/bridge/companion restart, uncertain admission persisted across restart, status-only
   recovery, rejected provider credentials, missing config and intentionally changed
   fixture source. Automated contracts cover many paths, but are not full host evidence.
   If the qualified read-only policy cannot produce an eligible approval pause, explicitly
   record that limitation and leave the acceptance item unresolved.
4. **T034/T039:** repeated component installation on populated synthetic Hermes/OpenClaw
   homes; retained bindings and browser graph/drafts/quotes across upgrade; supported
   rollback and no v2 downgrade writes. HUD check/apply hash preservation alone is partial.
5. **Windows-specific remainder:** supported native OpenClaw launch/regression has not
   been run. Native Windows Node was 24.11.1, insufficient to qualify that launch.
   The installed WSL OS is Ubuntu 26.04, not the originally requested 24.04. Preserve
   this distinction; Mac cannot prove these Windows/Linux gates. Arrange the required
   host checks or obtain an explicit owner revision of the platform criterion.
6. Only after all required acceptance passes: reconcile current main **into the feature
   branch without updating main**, inspect CONTRIBUTING/release conventions, choose the
   correct minor version from current release state, update VERSION/CHANGELOG and actual
   linked manifests, finish T056/spec closure, audit and leave Git clean. No push, merge
   to main, publication or federation without separate instructions.

The isolated WSL Claude profile remains private on WSL. Configure Mac credentials locally;
do not transfer `.env` through Git or paste keys into chat. Only an Anthropic API key was
needed for the successful Claude provider run. No OpenClaw credential import is needed.

## Prompt to use on Mac

> Continue spec 148 on branch 148-hermes-hud-integration from the WSL return bundle,
> including commits 9f26dfa, a45225a and all later handoff commits. Preserve my existing work,
> credentials, configuration and services. Do not work on main. Read AGENTS.md, SOUL.md,
> USER.md, TOOLS.md, the constitution, and specs/148-hermes-hud-integration/{spec.md,
> tasks.md,validation.md,validation-handoff.md,mac-return-handoff.md}, including committed
> evidence. Start the required audit session. Finish the explicitly outstanding Mac live
> provider, real-browser, restart/permissions, populated upgrade/rollback and existing
> OpenClaw acceptance checks. Fix failures and rerun affected tests autonomously. Keep
> Windows-only and Ubuntu-version gaps explicit; do not claim Mac tests close those gates.
> Record actual evidence and update checkboxes only when fully verified. Once all required
> acceptance passes, reconcile current release metadata and complete release preparation
> and spec closure on branch 148, leaving Git clean. Do not push, merge to main or publish.
> Federation is spec 149; do not begin it. Tell me precisely what remains if any gate
> cannot be completed on this host.
