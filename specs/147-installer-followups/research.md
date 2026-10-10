# Research: Installer and first-use reliability

## Current baseline and integration

Fetched origin and confirmed PR #287 merged at 2026-10-10T11:25:31Z, main `b4334bf255cd53aecd2e81f51abe63deea53f1df`. Fast-forwarded local main and merged into spec 147 without conflicts. This supersedes the intake draft's statement that #287 was still open. Dotenv PR #288 is also included.

The reports mix historical defects, dependency/platform requirements and residual first-use gaps. [reports.md](reports.md) preserves every supplied issue without treating the report's overall conclusion as current-main fact.

## Independent evidence

1. **Host checks:** the actual preflight evaluator with otherwise-ready host fixtures accepts all of Node 18.20.8, 20.20.2, 22.0.0, 24.15.0, 24.16.0, 25.9.0 and 26.1.0. Current upstream OpenClaw excludes the first four and Node 25. [Evidence](node-preflight-evidence.json).
2. **Missing native coverage:** the actual selected-registration generator returns zero entries and exit 0 for the reported twelve components. pyATS and NetBox skills do have MCP_CALL invocation examples, so native absence and total unavailability are distinct. [Evidence](registration-evidence.json).
3. **Native binding versus skills:** `install-mcp-config.py` substitutes recorded interpreters for native entries. `netbox-reconcile/SKILL.md` still invokes a child `python3 -u $NETBOX_MCP_SCRIPT`; `mcp-call.py` splits and spawns without looking up runtime records.
4. **Readiness:** `verify_file`, `verify_dir`, `verify_runner` and `verify_remote` verify artifacts or declared transport, not actual runtime discovery/endpoint operation. CI catalog coverage includes externally invoked integrations and cannot prove runtime readiness.
5. **Transport:** isolated real OpenClaw 2026.7.1-2, Node 24.19.0, synthetic servers only. Stdio receives initialize/initialized/tools-list and discovers the fixture tool. Explicit streamable-http POSTs initialize and discovers it. URL-only HTTP sends GET without discovery and exits 0. [Evidence](transport-evidence.json), [portable reproduction](reproduce-transports.py). This is not the reporter's exact runtime or server implementation.
6. **Existing regressions:** 113 focused tests pass across preflight, independent component paths, isolated runtime selection, native configuration merging/binding, preservation and dotenv onboarding.

## Primary sources checked 2026-10-10

- [OpenClaw Node compatibility](https://docs.openclaw.ai/install/node-compatibility): published engines `>=24.16.0 <25 || >=26.1.0`; installed older runtimes can have different ranges. Match the installation target rather than a moving general minimum.
- [OpenClaw installation](https://docs.openclaw.ai/install): npm 12 / 11.16+ use `--allow-scripts=openclaw`; <=11.15 omit it. npm 11.16 warning-only behavior is distinct from npm 12 blocking.
- [npm install-script policy](https://docs.npmjs.com/cli/v11/commands/npm-install-scripts/): global installs use per-install allow-scripts rather than a project approval command. Do not broaden policy to every dependency.
- [Python 3.14 on macOS](https://docs.python.org/3.14/using/mac.html): universal2 supports Apple Silicon and Intel; package wheel support is a separate issue.
- [OpenClaw Ollama setup](https://docs.openclaw.ai/providers/ollama/setup): configured local/LAN/remote hosts are supported and setup includes host/model checks in current upstream. A local executable is not a necessary condition for a remote provider.
- [OpenClaw MCP connections](https://docs.openclaw.ai/tools/mcp): explicit streamable-http transport and runtime discovery probes are documented.

## Design decisions

Build on merged preflight, isolation, deployment and dotenv helpers. First fix runtime compatibility/bootstrap, then close explicit tool access and launcher gaps, then add trustworthy readiness/first-use verification. Preserve transport boundaries and existing approvals. Diagnose original CML failures with matched command/env/cwd/version and a minimal protocol fixture before proposing an upstream patch.

No real credentials, package installation, model/provider request, daemon restart or device operation was performed for this investigation.

## Implementation decisions

Owner explicitly requested fixes followed by commit/PR/merge. Added thirteen native
registrations for all twelve reported components; moved the same thirteen names
out of the external inventory so integration totals remain unchanged. Both native
registrations and recognized legacy skill invocations share a stdlib exec launcher.
The launcher reads literal runtime dotenv settings and recorded interpreter paths;
NetBox/ServiceNow/NVD use module invocation with their source roots. ServiceNow's
low-level SDK1 remains isolated from MCP2. No approval policy or write gate is changed.

Readiness uses actual OpenClaw discovery and its structured server/tool results.
Hermes has a direct stdio probe with agent discovery explicitly unverified. Endpoint
operations are always a separate unverified stage. Ollama checks only native model
catalog/capabilities, not model generation or tool-call correctness. This bounds the
claim we can substantiate instead of treating a successful install as live acceptance.

Initial four-component smoke preparation exposed test-environment gaps: an
unpatched legacy calculator copy, an absent edge-tts dependency, and settings not
persisted into the temporary runtime dotenv. Applying the existing reviewed patch,
installing declared dependencies in a disposable venv and writing fixture settings
reproduced a fresh install's layout. All four then passed native discovery.
No operator component environment was rebuilt or altered by that smoke test.
