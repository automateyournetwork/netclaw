# Implementation Plan: Fix the dead servers, promote `startup` to a hard gate

**Branch**: `090-fix-dead-servers` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)
**Follows**: [088](../088-server-startup-check/spec.md) (found them), [089](../089-meraki-official/spec.md) (retired one)

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05** after merge, from `spec.md`, the delivered change and the git history. No
> `plan.md` existed during the build — a breach of Principle XVI, part of the 087–096 drift.

## Summary

Spec 088 found **7 registered servers that could not start** and shipped its check warn-only,
because two were believed to need SDKs that were not publicly distributable.

**Six are fixed and one is excepted with a written reason**, so `startup` is promoted from advisory
to a **hard gate**: a registered server that cannot start now fails the build. That was 088's stated
exit condition, and this meets it.

## Technical Context

**Language/Version**: Bash (`scripts/lib/pip-helper.sh`, `install-steps.sh`), Python 3.10+ (checker)
**Primary Dependencies**: None new to NetClaw. Installs three third-party SDKs — `pygnmi` 0.8.15,
`junos-eznc` 2.8.2, `prisma-sase` 6.8.1b1
**Storage**: None
**Testing**: The `startup` surface itself, run against the live config; shared-pin verification
before and after
**Target Platform**: Linux — specifically a **PEP 668 externally-managed** host, which is the whole
problem
**Project Type**: Repository remediation + installer correction
**Constraints**: Must not move a shared dependency pin (spec 076's cryptography incident is the
standing warning)
**Scale/Scope**: 7 servers, 1 install helper, 53 collapsed call sites

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **VIII. Verify After Every Change** | Breakage must be detectable | **PASS** — this is what promoting the gate achieves |
| **XI. Artifact Coherence** | A registration must correspond to something real | **PASS** — every registered server now starts, or is excepted with a reason |
| **XII. Documentation-as-Code** | Corrections recorded where the error was made | **PASS** — 088's wrong `prisma_sase` conclusion corrected **in 088's own text**, not quietly here |
| **XV. Backwards Compatibility** | Installer changes must not break existing components | **PASS** — 94 `component_install_*` functions unchanged |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## Root cause

`netclaw_pip_install` — the single install path spec 077 mandates — was a bare
`"$py" -m pip install "$@"` with **no PEP 668 handling**. On this externally-managed host it could
not install *any* new package.

Meanwhile **56 call sites** each papered over that independently:

```bash
netclaw_pip_install X 2>/dev/null || \
    netclaw_pip_install --break-system-packages X 2>/dev/null || \
    log_warn "… install failed"
```

Both calls discarded stderr, so a **total** install failure produced one warning line in a long log
and **exit 0**. That is why three servers sat dead while the installer reported success.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a recurrence gate |
| **Changing the repo's single install helper** — explicitly deferred by 088 as "its own change with its own blast radius" | The helper *is* the root cause; fixing servers without it would leave the next new package equally uninstallable | Per-server workarounds were what created the 56 papered-over call sites in the first place |
| **Patching vendored upstream at install time** (`arista-cvp-mcp`) | The clone is gitignored, so a working-copy edit is lost on the next fresh install | Committing the edit is impossible (gitignored); an idempotent install-time patch, re-applied after every `git pull`, is the shape the Slack `fetch-interceptor` problem taught. Verified against a **pristine upstream download**, because the committed artifact is the patch, not the edit |
