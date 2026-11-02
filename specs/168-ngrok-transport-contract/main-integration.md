# R01 source integration — 2026-11-02

The owner authorized moving completed R01 source into main while withholding
release, version increments and rollout documentation until the full issue310
roadmap is complete. R01 remains transport/lab qualification, not a general
cloud Border product with users, SSO or RBAC.

Preserve upstream OpenClaw compatibility fixes and version1.18.1; extension
version1.5.0 remains unchanged. The parallel upstream168-openclaw-2026-10-compat
spec retains its name; R01 keeps168-ngrok-transport-contract and its existing
receipts. Existing duplicate-number conventions allow these independent paths.

Public-facing R01 additions were withdrawn from README, general HUD/installation
guides, extension README/wizard, default environment examples and shipped agent
instructions. The new deployment guides are retained as deferred engineering
drafts in deferred-docs/. Setup keeps private-routing corrections and does not
advertise moving a Border to cloud. Transport implementation, opt-in registry,
security tests, pilot review artifacts and exact evidence remain preserved.

The full original working diff and untracked files were backed up privately
before reconciliation. The supplied issue310 ZIP remains local and is excluded
from the integration. No credentials, runtime homes, Terraform state or saved
plans are committed. No running pilot or existing owner runtime is upgraded.

Next is R02 — execution parity on NetClaw production mode, expected spec169
(subject to the next available number at kickoff). It maps current controls,
adds exact one-use principal-bound approvals, guarded member execution, broker-
held credentials, signed durable results and lost-reply reconciliation. Its gate
is a reviewed parity matrix plus actual local approved-read/refusal evidence.
R02 has not been started. R15–R17 user/SSO/RBAC work remains part of the release gate.

Integration verification and final merge receipt are recorded below.
