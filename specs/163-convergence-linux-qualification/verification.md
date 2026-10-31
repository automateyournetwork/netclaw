# Verification and bounded run ledger

Run: linux-qualification-20261031
Start UTC: 2026-10-31 02:31:24; deadline UTC: 2026-10-31 03:16:24.
Checkout: /home/ubuntu/netclaw-convergence-linux
Branch: 163-convergence-linux-qualification; base c954845c.
Task attempts: T001=1/3; T002=3/3; T003=1/3; T004=1/3.

Baseline: dedicated clean Ubuntu24.04 amd64 guest, cloud-init done, no Node,
Docker or OpenClaw. Offline clean-OS snapshot available. Production unchanged.
Private evidence root: ~/.local/state/convergence-linux-qualification/.
Research delegate: linux_install_path (read-only installation/CLI evidence).
Coordinator owns spec, docs, installation, integration and publication.
Acceptance is defined in spec.md; applicable gates: spec-artifacts, reconciliation,
catalog coverage and changed-component tests if code changes.
Outcome: IN PROGRESS. No installation or model qualification claimed yet.

T001 progress: official Docker apt repository installed Engine29.9.2 and Compose5.6.1;
Node24.22.1 official amd64 archive matched published SHA256. Two coordinator apt
operations initially overlapped (cache rename error); serialized apt update/install
and Python venv creation then passed. This was execution coordination, not a product
failure. Initial service start hit Docker Hub HTTP502 on an OTEL image layer; retry
uses the same bundle and retained downloaded layers. Private viewer configured before
first successful start. No secret values are included in evidence.

T001: core verifier passed all 10 checks, including scoped authentication and
Grafana datasource. Synthetic exporter built and exported two records; waiting
for archive check. Full optional reader installation completed with isolated
FastMCP4.0.11/MCP2.3.0 and OpenClaw2026.10.9 (8b18b55), Node24.22.1/npm11.19.1.
Preconfigured minimal custom provider uses environment-reference auth; no channels
or production credentials imported. Core installer projected native MCP as expected.
Repository spec, catalog and all six reconciliation surfaces pass.

T001 COMPLETE: published demo export and retained same-window evidence passed.
T002 attempt1: native doctor/probe discovered both tools; actual gateway turn reached
provider but failed with Abacus HTTP402 billing. No model execution claim. Initial
config validation env warnings no longer reproduce; researcher confirmed standard
private dotenv loading and a warning-free fresh CLI validation. Attempt2 uses the
existing Ollama provider; no billing/account changes.

T003 attempt1: actual installed stdio connector against the running demo returned
unauthorized for both a wrong key and a wrong site, and unavailable for a closed
loopback port. Valid summary preserved explicit synthetic coverage. These checks
used process-only overrides, leaving installed credentials unchanged.

T002 attempt2: Ollama Cloud/minimax-m2.7 gateway run completed; native nested tool
records prove summary and evidence success with identical start/end/exporter. Model
first guessed unsupported `window`, recovered with `range`, and then overclaimed
sampling_rate0 meant unsampled and suggested traffic purpose from byte asymmetry.
Do not count semantic qualification complete. Attempt3 clarifies tool descriptions
without relaxing strict input validation; repeat a fresh chat against final source.

Verification correction: directly running tests/convergence-read/run-tests.sh used
the coordinator's unpinned system SDK and failed annotation attribute compatibility
(17/18 passed). Required rerun uses run-contract-tests.py --suite convergence-read
--prepare, which creates the declared isolated dependency environment. Do not report
the incompatible direct invocation as a product regression or passing check.

Pinned `python3 scripts/run-contract-tests.py --suite convergence-read --prepare`
PASS (18 tests, 9.08s runner). The direct-shell SDK mismatch is isolated to the
coordinator's system environment; the declared runtime and contract suite pass.

T004 review starts after code/docs writers finished. Coordinator is collecting
remaining runtime evidence and owns ledger/release integration. Independent reviewer
may inspect readonly VM state and private sanitized evidence; no credential values.

T002 attempt3: final gateway turn completed with valid summary/evidence and exact
window; sampling uncertainty was now preserved. Independent review found remaining
unsupported request/reply wording ("larger reply") despite the explicit guidance.
Outcome: BUDGET_EXHAUSTED for T002 (3/3 attempts), not a complete semantic pass.
Native execution is qualified for this provider/runtime; trustworthy interpretation
remains open. No additional model attempts in this run. T001/T003/T004 continue
within the original deadline. Interactive onboarding wizard was not exercised;
this fresh VM used official scripted onboarding before the real NetClaw installer.

Final native transcript independently verified: two successful calls, `range=1h`,
start2026-10-31T01:45:18.711Z/end02:45:18.711Z, same absent exporter filter,
site demo, coverage demo, 2,148 bytes/15 packets/2 records, evidence limit100.
Complete54-event export retained privately. T003 disabled check passed with the
external stack stopped: connector returned disabled, not unavailable. Restart/data
retention checks underway. A request for two additional T002 attempts is pending;
no extra provider calls are authorized by elapsed time alone.

T003 COMPLETE: stop/start retained exactly2 records,2,148 bytes,15 packets and
original receipt timestamp. Core verification and flow archive checks passed after
restart. Disabled reader returned disabled while backend was stopped. Re-enabled
reader returned the unchanged synthetic data. Native gateway restarted and doctor
connected successfully; its literal-sensitive-value warning is a resolved-config
false positive here: raw saved token remains an environment reference (not a secret).
Unused failed-provider credential was removed from the dedicated guest; only the
selected Ollama reference credential remains for subsequent authorized tests.

T004 independent final verdict: code/docs PASS; T003 PASS; T002 semantic FAIL.
Reviewer independently repeated all18 pinned tests, inspected final54-event native
trajectory, retained totals, loopback listeners and private env permissions. Corrected
native reload command (`openclaw mcp reload`, no positional server) succeeded; probe
has no diagnostics and config validation has no warnings. All findings disclosed.
Qualification report is qualification.md. Spec remains incomplete, so no source
version bump/tag/release is prepared. Preserve existing spec162 release metadata.

## Authorized continuation: grounding-20261031

User approved two additional model-validation attempts after the prior wall-clock
window expired. Linked continuation starts 2026-10-31 03:47:35 UTC; deadline
2026-10-31 04:32:35 UTC. T002 total limit is now5 attempts (prior3 preserved).
Attempt4/5 begins: use available Ollama Cloud kimi-k3, clarify the observation skill
with an evidence audit and explicit unknown request/reply semantics. Same dedicated
VM and private provider reference; no production changes. Coordinator owns edits
and installation; independent verifier receives final outputs without model calls.
Acceptance unchanged: both native tools, exact scope/window, correct counters,
synthetic coverage, bounded evidence and no unsupported semantic/sampling claims.
Re-generate fresh demo records because the prior one-hour window has elapsed.

Attempt4 setup: deployed identical skill v1.0.1 into the guest checkout and runtime;
selected catalog-available ollama-cloud/kimi-k3; regenerated synthetic records.
Canonical catalog metadata/parity/spec checks pass. Generic Codex skill validator
rejects the repository's pre-existing `version`/`tags` frontmatter; those fields are
supported by NetClaw's canonical metadata checker, which passes. Initial catalog
build needed extension dependencies and non-group-writable owned config directories;
after npm ci and narrowing permissions on this dedicated checkout, parity passed.
These setup corrections did not alter runtime policy or tool contracts.

Attempt4 FAIL: kimi-k3 loaded the skill, followed a setup-guide pointer outside
normal observation, and used shell/source inspection, a new local dependency venv
and an alternate client instead of discovering native MCP tools. It claimed to
override a disabled setting in that process. Gateway was stopped; no production
state changed. Reject this result even though parts of its prose were cautious.
Independent verifier confirmed native-tool absence and scope violations.

Attempt5/5 begins: return to minimax-m2.7 (previously demonstrated native tools),
require native discovery, and stop on missing tools rather than read credentials,
install dependencies or call alternate APIs. Make the setup link conditional on
operator setup requests. Preserve exact acceptance; no further model attempts after5.

Attempt5 prerequisite correction: systemctl start returned before the gateway
listener was ready. CLI dispatch failed before any model run; no extra model turn
was consumed. Wait for the supported gateway restart readiness check before the
single attempt5 model turn. Final skill/catalog review passed independently.

Continuation checks: all18 pinned connector contracts pass (7.14s); skill/catalog
metadata and generation parity pass. Reviewer independently approved final skill
scope. Attempt4 complete trajectory retained privately (132 events). Redacted export
contains no literal matching sensitive runtime values; this is not proof of what
an external provider observed. The test-only viewer credential will be refreshed
and the extra venv quarantined after attempt5 finishes. No source/provider credentials
will be printed or committed. T004 continuation review is attempt2/3.

Attempt5 complete: 42-event trajectory independently confirms final skill loaded,
only read/tool_search/tool_call/tool_call, both native results ok, same explicit
exporter127.0.0.1/site demo/synthetic coverage and 15m interval
03:40:04.306Z–03:55:04.306Z. Structured results:2 records/2148bytes/15packets/limit100.
Interpretation FAIL:100-record bound omitted; sampling0 asserted to mean missing
metadata; distinct nanosecond receipt times described as same instant. T002 remains
BUDGET_EXHAUSTED at5/5. No more model calls. Independent code/skill/scope review PASS;
semantic acceptance remains open. Do not mark spec complete or bump its release.

Cleanup: test viewer refreshed; new key HTTP200, old key HTTP401. Extra model-created
venv quarantined outside source; no production changes. Native gateway/reader
recovery check follows this credential change. Provider/model defaults remain scoped
to the dedicated guest. Full evidence retained in private attempt4/attempt5 artifacts.

Recovery PASS: supported gateway restart, native MCP doctor and authenticated
installed-reader summary succeeded after viewer refresh. Same synthetic counters
remain available. Final independent verdict: skill/code and native execution PASS;
T002 answer acceptance FAIL. Both additional authorized model attempts are consumed.
The follow-up preserves this finding and the prior model failures; no model-runtime
sandbox or universal correctness is claimed. Local canonical metadata/parity,
reconciliation across six surfaces, spec artifacts and release checks pass.
