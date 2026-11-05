# Verification: R05 / Spec176

## Current state — 2026-11-05

Source implementation integrated on `176-ollama-members`: **21/33 tasks complete**.
Fresh NetClaw model/guard images and private native bindings are prepared.
Actual native MCP boundary tests ran; no model inference, cloud apply, existing
runtime upgrade, client installation, release or R06/R07 work has occurred yet.

NetClaw baseline `db0c9682d4997d51a15f75cbf2df83b97d3c3f45`, source1.18.6,
extension1.6.1, Mobile1.0.4+7. Existing usable pilot/member and December1 lifetime
remain preserved. Thermidor final historical qualification informs the design;
its exact inspected source hashes and limitations are retained separately.

## Acceptance matrix

| Group | Required current NetClaw evidence | Status |
|---|---|---|
| Local ARM64 | Real guarded IPv4 native MCP, verified arithmetic,2 turns/1 call | NOT RUN |
| GCP AMD64 | Real guarded IPv6 native MCP, verified arithmetic,2 turns/1 call | NOT RUN |
| Combined browser | One durable parent,two distinct approvals,both results | NOT RUN |
| Isolation | Guard positive control and agent/broker/sibling/Border/public denials | NOT RUN |
| Resource/accounting | Actual swap/cgroup/OOM, CPU/memory,tokens,time,zero provider charges,unload | NOT RUN |
| Recovery | One-child failure,lost reply/ACK,process/client restart,no repeat | NOT RUN |
| G12 VS Code | AFFECTED: combined references/reviews/results/recovery; actual Mac editor | SOURCE TESTED / LIVE NOT RUN |
| G13 Mobile | AFFECTED: combined WSS contract/UI; native simulator/device-key recovery | SOURCE TESTED / LIVE NOT RUN |
| Regression/portfolio | Existing protected pyATS/NetBox/subnet/hosted models, Chat/Canvas,clients | SOURCE TESTED; live portfolio pending |
| Preservation/lifecycle | Baseline/rollback/export,usable intended delivery,disposable residue inventory | NOT RUN |
| Human acceptance | Owner reviews current R05 evidence before R06/R07 | PENDING |

Existing capabilities have source regression coverage, not new live qualification. Hermes Ollama, Windows/WSL, physical iPhone camera/SecureEnclave, GPU,
other models, HA and external delegation are unqualified. No new transport claim.

## Preparation checks

- Clean `main` at kickoff; Spec Kit created `176-ollama-members` and selected the
  new feature via `.specify/feature.json`; setup-plan/prerequisite discovery used.
- Read actual sibling Thermidor docs, final evidence, implementation and tests;
  preserved source hash manifest; no writes or tests in that checkout.
- Requirements/checklist,15 functional requirements,6 success criteria and33 tasks
  map to contracts and verification. Artifact checks passed: sequential33 unchecked tasks,100% requirement/success-criteria
  mapping, local links, no unresolved template markers,23 Thermidor hashes plus the
  native MCP source hash, Spec Kit prerequisites and `git diff --check`. Independent
  review found two gaps, both addressed: actual native source capability/reproducibility
  and the member/runner-wide uncertainty latch. No functional tests ran for this
  documentation-only preparation.
- GAIT branch+checkout `r05-spec176-thermidor-sdd-20261105`; kickoff `59ef60a6`.
  Existing `/Users/john.capobianco/gait_mcp/venv/bin/python` works; no install needed.
- Startup `pyats_list_devices` attempted: configured HTTP runtime missing, no device
  contacted. MemPalace server source unavailable at checked local locations; no
  successful search/journal claimed. Daily memory retains this preparation.

## Evidence recording rules

Record exact source/artifact/profile identities, actual commands, timestamps,
platform, observed counts, success/failure/unknown results and private receipt hashes.
Separate unit/fixture/native/container/browser/editor/simulator evidence. Retain all
failed attempts and original approval/result/ACK IDs. A later pass does not erase
earlier unknown outcomes. Never store secrets or raw private topology in source.


The full local GAIT trail is retained at
`~/.local/share/netclaw/roadmap-r05-sdd-20261105/gait-final.json`.
Planning checkpoint is `9394ea82`; integrated source commits are `aa263c70`,
`a8566e43`, `c9a46e8e`, and `201841c6`. Optional Spec Kit auto-commit hooks remain
disabled. No push/PR/publication occurred.

## Integrated source checks — 2026-11-05

- Root: isolated Python3.12 `python -m pytest -q tests/n2n/test_protected*.py`: **665 passed**,21 existing datetime deprecation warnings,15.18s. Private log `roadmap-r05-20261105/integrated-python-tests-all.log`. The first explicit file-list command named a nonexistent enrollment test and ran zero tests; its original log remains.
- Native calculator: actual MCP subprocess tested eight IPv4/IPv6 boundary cases, including /0, /31, /32, /127, /128 and decimal counts. This is actual native arithmetic; provider execution in authority tests is explicitly synthetic. Exact native source before `bfb8bb548aa7096c0b2324a3798c581ce917a26388aa6193ae66eb0708e7dd45`, after `582f3203269612fcf949c5875e41ac557bb096d6476c846e1ac921ba559a6364`. Main ignored native clone is unchanged.
- Client lane, qualified Node24.19: HUD47/47 and Vite build; extension200 passed,3 existing live skips, TypeScript and build; Mobile491 full tests, focused combined/device recovery regressions and analyzer clean. Source-only counts do not close browser/editor/native simulator acceptance. Logs retained by coordinator under private evidence.
- Current actual official DefenseClaw reports1.0.4, commit `be69263d5f1fc5d5a9cc2f61769f82056d3b67fe`. The first `version` subcommand was rejected; `--version` succeeded. Native guard routing/readiness remains a live acceptance item.
- Public CPU/model closure was verified before copying from the sibling cache into fresh private NetClaw artifacts. Fresh ARM64 model image `sha256:43fd0705aa3cc01ac6d7b1a72a2eba75558f78771941db62a57383e7eecdb277`; fresh guard `sha256:415ad07d3924f0b1d5bf2c56d9409ace5f9c06a8e3d004747f0694c66a86d1a1`. No Thermidor runtime/image is deployed. Initial guard build treated a bare local image ID as a registry name and failed before build; the exact local base was tagged, rechecked and the offline build passed.
- Cloud preflight was read-only. Existing Border has2GiB total/about1GiB free and no Docker. A separate8GiB member plan is being prepared; no resize, apply, DNS, IAM, budget or authority mutation occurred.

Artifact dispositions are in `labs/ollama/README.md`. Native MCP, official guard
version, source tests, image builds and live model execution remain separate
evidence classes. Actual R05 inference and signed durable delivery are still open.

### Required local qualification corrections

The initial local preparation used assumed guardUID501; actual `id -u` is503.
The UID gate refused before creating resources. A native profile draft also
refused an incorrectly named skill path; the corrected fresh profile uses the
required `skills/subnet-calculator/SKILL.md` and actual discovered MCP schema.
Both original failures remain recorded.

The first model image's Bookworm base lacks glibc2.38 required by the pinned CPU
libstdc++; its owned model exited before inference (exit1, noOOM). The corrected
image uses the final reference's pinned upstream Python3.13.16/Trixie base; it
started actual Ollama0.40.11 on loopback with CPU-only detection and cloud disabled.
No Thermidor product or transport was imported. The second preparation then
found Docker29.9 does not publish the guard port on an internal bridge: actual
`NetworkSettings.Ports` was empty despite the requested binding. Its model API
positive read passed under the guard UID. The owned model was stopped with its
original evidence retained, zero inference. The required correction keeps the
internal network and uses the trusted host's private Docker execution path to
the guard, with no published model/guard TCP port; hosted profiles stay unchanged.
This is a local topology correction, not a new transport or model qualification.

### Current namespace and cloud foundation

Actual local v3 preparation passes: model0.40.11 before/after positive API read,
guard UID503 nonce control, agent/broker/Border/sibling stand-in UID denials,
modelUID21006 API denial and a fresh peer-container positive guard/negative model
probe. No ports are published. This is namespace/UID evidence; actual external
vantage and application roles are still separate open T026 checks. Private
`local-model-v3/qualification-evidence.json` explicitly records this limitation.
Actual model image is `sha256:257ed45084d79372ab2b18d67e9121ffa76e73338869fe918ae7fbb35e20565d`.

Root integrated private-guard tests: **685passed**,21 existing warnings,15.00s.
The subsequent strict JSON history-normalization correction passed138 scoped
checks. Model/guard native positive inference remains open. The first local
strict-wire driver stopped at a snapshot assertion before any protected operation:
member-side production code derives the exporter binding rather than retaining
an `auth_binding` field. Corrected qualification reads the production binding
and compares both endpoints; original homes/keys/enrollment and failure report
are preserved, and an explicit same-home continuation is prepared.

The owner selected48hours instead of the proposedDec1 new-member retention.
The exact revised plan SHA256
`ca32d0d28314d3f90cd5aa0cf0ef5d923524d46e69b5cc3a141c54b2e14dba30`
was independently checked and applied once:8resources created,0changed,0destroyed.
Actual VM is RUNNING, e2-standard-2, no service-account scopes, STOP deadline
2026-11-07T19:41:25Z. Native Ubuntu24.04.5 reports8124712KiB total/7605368KiB
available. Serial-API ED25519 fingerprint was verified before first strict IAP SSH;
existing owner key worked, with no OS Login key mutation. Initial egress remains
denied; no model deployment or cloud inference has occurred. Baselines, current
state, plan claim and apply log are private under `cloud-plan-48h/` and
`cloud-current/`. The oldDec1plan remains unapplied evidence-only.
