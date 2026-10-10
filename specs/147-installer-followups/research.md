# Research: Installer follow-ups

## Baseline

Start from main after merging [PR #288](https://github.com/automateyournetwork/netclaw/pull/288), spec 146. That patch imports checkout dotenv settings before onboarding/setup, preserves runtime assignments, and propagates onboarding failures. Its release metadata is 1.6.1.

The prior reporter's exact init command and host were unknown. Do not reuse that uncertainty as evidence of a different installer bug.

## Existing related work

[PR #287](https://github.com/automateyournetwork/netclaw/pull/287), `codex/fix-installer-preflight`, was open and draft when inspected on 2026-10-10. Its author describes host/component preflight, interpreter compatibility, per-run logs and Zabbix installation working-directory repair under spec 049. These are PR claims pending review here, not newly reproduced findings. Recheck the PR before selecting overlapping work.

## Pending evidence

The owner will provide new reports. For each, capture what is available:

- Install command and selected runtime/profile/components.
- OS/version/architecture and relevant Python/Node/runtime versions.
- Fresh installation or retry; repository revision if known.
- First relevant error and failing stage, with credentials and private addresses removed.
- Expected result, actual result and reproducibility.

Do not request a complete dotenv file or unredacted logs. No new root cause, solution, dependency or platform guarantee is selected yet.

Merged baseline: `aecf438ee56ad28337b3f5d715c8d8afa62605ae`, PR #288 merged 2026-10-10T11:19:33Z after all 31 checks passed for `813a6dc3174922b84ad185769cd3aff4f094b33d`.
