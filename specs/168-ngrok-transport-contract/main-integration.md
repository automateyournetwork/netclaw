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

## Combined-source verification

PR: https://github.com/automateyournetwork/netclaw/pull/319

Upstream `a57566f8` was merged without dropping its gateway/bootstrap preservation
fixes. The sole conflict was the generated effect-source digest; component and
source hashes were recomputed from the reviewed merged installer. The Bash
catalog digest was regenerated after the canonical skill descriptor projection.
No source/version/release metadata differs from upstream1.18.1; extension stays1.5.0.

Actual combined checkout results:

- Federation:881 passed,5 real-runtime fixture skips;69 existing warnings.
- HUD:408 passed, no skips; build passes with the existing chunk-size advisory.
- Extension:150 passed,3 existing native/runtime skips; typecheck passes.
- Installer/deploy/upstream preservation:57 passed,1 disposable-WSL skip,
  26 subtests passed.
- Public lab ingress:3 passed. Catalog coverage:112 components,239 skills,
  178 integrations, no unexplained gaps. Spec artifacts:153,4 legacy exceptions.
- All six registration/dependency/documentation/portability reconciliation
  surfaces pass in a clean detached checkout. The development checkout also has
  an unrelated ignored HumanRail clone with an old unbounded MCP dependency;
  it was left untouched and is not included in the commit or CI checkout.
- Authored local links, new catalog public-link delta, release metadata and
  whitespace checks pass. The original staged source scan found no credentials.

The n2n CI suite's obsolete cryptography<45 extra conflicted with the strict
transport's pinned cryptography50 requirements. The suite now uses the canonical
protocol pins and explicitly installs/checks its asyncio test plugin and TLS
imports. No dependency or refusal check was disabled. Failed command invocations
and pre-regeneration receipts remain private alongside successful checks.

Private integration receipts: ~/.local/share/netclaw/spec168-main-integration-20261102/.
The maintainer summary is a shareable draft, not an announcement sent to others.
Hosted CI and merge outcomes are retained in that directory and the PR checks.
