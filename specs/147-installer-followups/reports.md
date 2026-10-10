# Report triage — 2026-10-10

Baseline: main `b4334bf`, merged into the spec branch as `cf12ec1`. Reports are user-supplied evidence, not a claim that all issues still exist in this revision. Private home paths and device data are omitted.

## macOS / Homebrew / Hermes report

The pasted run selected 108 components. It first found Apple's Python 3.9.6 and no uv; Homebrew installed Python 3.14, but the same process retained an earlier component interpreter. Later errors named missing Go 1.25+ and Zabbix's unresolved relative vendor requirement. Its final summary reported eight failed components; only two component failures and prerequisite excerpts are available. The referenced archive was not attached.

| Report | Current disposition | Evidence / next action |
| --- | --- | --- |
| uv absent | Missing prerequisite; early detection now merged | PR #287 checks uv/uvx before mutation. pyATS/GAIT setup uses uv to create isolated runtimes; inspected code does not pin a uv version. Keep actionable installation guidance. |
| Python 3.9 retained after Homebrew repair | Historical retry path; new preflight changes the flow | Current full installer stops at preflight before legacy repair offers. Existing 3.12 selection and explicit override preservation are tested. Any future repair must re-resolve both interpreters; do not reinstall generic latest Python blindly. |
| Python 3.14 allegedly unsupported on Apple Silicon | Incorrect general explanation | CPython 3.14 supports Apple Silicon. Individual packages/native wheels impose their own bounds; PR #287 models known limits (for example Panorama and Zoom). |
| Forward requires Go >=1.25 | Addressed by merged preflight | Go, CGO, compiler and Apple command-line-tool checks now precede component installation. This is not proof of a real Forward deployment. |
| Zabbix `./vendor/zabbix-mcp-server` missing | Fixed by Nick's merged PR #287 | Installation now changes into the Zabbix component directory before pip evaluates the requirement; focused regression passes. |
| Eight failed components | Partially evidenced | Do not invent the six unnamed failures. Add them when sanitized logs become available. |

## Linux / OpenClaw report dated 2026-09-13

The report describes Debian/Ubuntu, Node 20.20.2, 23 selected components, remote self-hosted Ollama and an unspecified checkout revision. It names OpenClaw 2026.9.4 in npm output. Its local workarounds are evidence about that host; none were applied to this workstation.

| ID | Report | Current disposition |
| --- | --- | --- |
| L1 | REPO_ROOT unset without Claw Certification | Fixed by earlier installer changes. Five affected path tests pass with REPO_ROOT unset. |
| L2 | Node prerequisite too low | **Confirmed remaining defect.** Current preflight and core checks accept >=18. Fixture checks accept Node 18/20/22/24.15/25 even though current OpenClaw's published engine range excludes them. |
| L3 | npm EACCES guidance favors sudo | **Remaining installer behavior.** Generic helper assumes failed npm installation usually needs root and offers sudo. Provide targeted, rootless guidance and truthful failure propagation. Running one package command with sudo is distinct from running the entire installer as root; do not conflate them. |
| L4 | npm allowScripts warnings prove skipped builds | **Version-dependent claim; install compatibility gap remains.** Current command omits the flag. Official docs say npm 11.16 warns but still runs scripts; npm 12 blocks unapproved scripts. Use version-aware first-party approval, not the report's unconditional five-package list. |
| L5 | Ollama CLI absent after selecting remote provider | **Not proof of failure.** A remote provider needs its configured host/model, not a local binary. Add endpoint/model readiness verification. Current upstream onboarding has evolved; exact historical behavior is unverified. |
| L6 | Packet Buddy downgrades shared dependencies | Installer isolation addressed by spec 133 and framework migration. Current component installs select isolated targets and record launchers. Regression tests pass; this does not repair old global packages or prove every live integration. Skill-based launch bindings still need attention (L9). |
| L7 | Deploy ignores existing OpenClaw config | Fixed by current unconditional selected-registration merge. Preservation tests pass for both supported config shapes. |
| L8 | Twelve selected components missing native entries | **Confirmed.** Running the actual generator for those twelve yields zero native registrations with exit 0. Some have MCP_CALL-based skills, so absence from the native registry is not proof of no invocation mechanism. Current pyATS already has a private loopback HTTP bridge behind stdio. |
| L9 | Interpreter mismatch at runtime | Fixed for generated native Python/console registrations with runtime records. **Residual skill path:** e.g. NetBox examples spawn bare python3; MCP_CALL splits/spawns that command without consulting component runtime records. |
| L10 | OpenClaw MCP client fails both transports | **Narrow reproduction obtained; broad blame unproven.** Installed 2026.7.1-2 discovers synthetic stdio and explicit streamable-http correctly. URL-only HTTP sends GET, discovers no tool, but CLI returns 0. This is a candidate explanation for part of the HTTP report, not proof about 2026.9.4 or CML. |
| L11 | Persona overwritten on rerun | Current deploy preserves existing persona/testbed paths; regression passes. |
| L12 | Agent invents CML capacity after tool failure | Serious reported first-use failure, not independently reproduced here. Add deterministic readiness and an evidence-backed canary; do not claim installer prompts alone prevent all hallucinations. |
| L13 | Installation summary implies usable tools | **Remaining gap.** Artifact checks still print OK based on a file/directory/runner, and remote entries can be OK without connectivity. Separate install, registration, discovery and endpoint readiness. |

## Verified corrections to suggested fixes

- Do not add a mandatory persistent 0.0.0.0:8080 pyATS daemon: the owned bridge already starts a private temporary loopback server with the correct managed interpreter.
- Do not use a public/general Python 3.14 ban. Compatibility belongs to the selected packages and architectures.
- Do not require a local Ollama binary merely because a remote Ollama provider is selected.
- Do not infer lifecycle-script blocking from npm 11 warning text alone.
- Do not treat direct MCP success as proof that the runtime's command, env, cwd, credentials and transport match.
- Do not treat `openclaw mcp probe` exit 0 as proof of tool discovery.

See [research](research.md) for sources and [verification](verification.md) for measured checks.

## Shipped disposition after spec 147 implementation

- L2/L3/L4: one Node target contract; npm-version-aware first-party script approval; user-owned prefix on permission conflicts; install/executable failure propagation.
- L8/L9: all twelve components have thirteen selected native registrations and a shared native/skill launch contract. Module paths and recorded interpreters are used. Existing pyATS bridge is retained.
- L5/L13: structured discovery and configured Ollama endpoint/model checks, truthful failure exits and explicit configuration-required/unverified stages.
- L10: synthetic transports and four actual component catalogs verified through installed OpenClaw; original CML/runtime combination remains unreproduced, not labelled fixed upstream.
- L12: failed-tool exits, deterministic readiness, SOUL guidance and a real local calculator canary added. Arbitrary Ollama answer grounding is not certified.
- L1/L6/L7/L11 and macOS preflight/Zabbix fixes: retained and regression-tested. No need to reimplement merged fixes.
- Six unnamed macOS failures and real network/lab acceptance still need the missing evidence; no blanket all-components installation claim is made.
