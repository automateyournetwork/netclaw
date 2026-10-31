# Verification

Run border-implementation-20261031: start16:40:10UTC, deadline17:25:10UTC.
Checkout /home/ubuntu/netclaw-convergence-linux, branch164-convergence-border,
starting commit6822be58. User authorized continuing the owner-directed integration.
Default3attempts/task; T001/T002/T003 attempt1/3. T004 starts after integration.
Initial gaps: no Convergence Investigate callback, no dedicated member profile,
source-only no-bypass wording can be misread as whole-investigation restriction.
Acceptance and file ownership are in spec.md/plan.md. Existing spec163 T002 is still
failed/exhausted5/5. No new model calls or runtime/production changes this run.

Source inspection expanded T002's prerequisite work: shared ExecutionScope/service
hardcodes subnet even for OpenClaw. Owner's approved outcome requires an explicit
Convergence OpenClaw receiver profile, not profile advertisement alone. Plan updated
before adapter edits; worker owns execution/service/gateway plus focused regression
tests as needed. Existing connector configuration validation is extracted unchanged
into a stdlib-only settings module for profile readiness reuse. Generic member profiles
and Hermes restrictions must remain unchanged.

T003 attempt1: skill and public guides now distinguish retrieval from investigation;
native selected-window requests preserve the recorded interval. Generated catalog
updated with OpenClaw member metadata. Canonical schema/metadata and six-surface
reconciliation PASS; setup eligibility fixtures PASS(2), including retained Mac/WSL
component blocks and rejection of Hermes membership. T004 attempt1 started with
the full offline setup-installer regression suite; private logs are under
~/.local/state/convergence-border-164/. Pre-adapter federation baseline:11 tests pass,
with an existing unawaited-task/closed-database warning in test_scope_enforcement;
new execution tests must wait for terminal status and cannot use submission as proof.

Full offline installer first run failed:274 tests,35 errors/1 failure/32 skips;
errors trace to unsafe_parent because this isolated checkout's source directories
were group-writable. Removed group/other write permission from tracked-source parent
directories only (no production checkout changes), then reran with the private-source
log. This is a test prerequisite correction, not a waived code failure.

Correction to the earlier dispatch hypothesis: an actual route/receiver fixture
showed execution_context returns None for OpenClaw before constructing ExecutionScope.
The subnet-only profile restriction applies to Hermes. Unnecessary dispatcher/broker
extensions are removed; native member configuration/tool policy is the OpenClaw
boundary. Existing routing is exercised to terminal completion rather than inferred
from a shared function's body. Plan and user update corrected accordingly.

The second installer run had15 remaining unsafe_parent errors in fixture-created
directories. The host's group-writable umask affected those temporary directories;
rerunning with umask077 preserves the suite's existing private-file assumptions.

T001 source and fixture browser checks PASS; browser delivered11,073 characters
through Dashboard/Canvas/owned draft intact (100 returned,26 included,74 omitted),
with zero model requests and stale refresh blocked. Production build/bundle PASS.
T002 connector suite PASS(18 existing+7 member fixtures);17 focused federation checks
PASS, including actual loopback routing to terminal result with fake model. Installed
OpenClaw2026.10.9 config validation/native matcher PASS(3 allowed,9 denied).

T004 attempt1 default HUD tests failed in untouched Pal fixed-delay fixtures (25ms/
35ms); bounded-concurrency run passed401/401, baseline default passed393/393. Do not
label these failures proven inherited: they occur under the current parallel load.
T004 attempt2/3: replace only those fixture sleeps with bounded readiness predicates,
retain every assertion and rerun default suite. HUD worker owns the two test-only
changes; independent verifier is notified. No production Pal changes.

Offline installer regression now PASS:274 tests,32 explicitly skipped live/platform
checks,85.801s with private source permissions and umask077. No fixture assertions
were weakened. Canonical configuration provenance follows the Settings extraction.

Independent review found a valid-provider compatibility gap: native installer emits
apiKey={source:'env',provider:'default',id:<key>}; new member setup initially handled
only strings. T002 attempt2/3: support that exact environment reference, copy only
its referenced key to member env, retain refusal of file/exec/vault/custom references,
and add a regression using the real installer shape. No auth-store inspection.
T004 default HUD suite now PASS401/401,0skips after readiness-only test corrections.

## Source milestone result

T001/T003 COMPLETE at attempt1; T002/T004 COMPLETE at attempt2. Independent final
review PASS after provider compatibility and metadata attribution fixes. Both member
builders share the restricted native policy; explicit local loopback providers can
omit authentication, remote providers cannot. Default model comes from the selected
runtime or an explicit override, with no invented provider/model limits. Existing
homes are preserved and risk mode is retained (absent mode defaults production).

Final commands/results:

- `python3 scripts/run-contract-tests.py --suite convergence-read --prepare`:
  PASS18 connector +13 member tests. No endpoint/provider/device calls beyond fixtures.
- `npm --prefix ui/netclaw-visual test`: PASS401 tests,0skips,6.61s.
- `npm --prefix ui/netclaw-visual run build` and Canvas bundle check: PASS;
  initial JavaScript151,622 bytes below400,000 budget.
- `node ui/netclaw-visual/integration/convergence-handoff.mjs <private-output>`:
  PASS in Playwright1.58.2 container/Chromium145 with network disabled and source
  read-only. Context11,073 characters preserved;100 returned/26 included/74 omitted;
  zero model requests/browser errors; stale handoff refused. CI runs the same fixture
  on native Linux amd64/arm64 using its existing browser dependencies.
- `umask 077; bash tests/setup-installer/run-tests.sh`: final PASS274 tests,
  32 live/platform skips,78.341s after the shared setup policy hook.
- Catalog metadata, skill descriptor/generated parity, catalog coverage, six-surface
  reconciliation, spec artifacts147/4legacy exceptions and `git diff --check`: PASS.

Private evidence: ~/.local/state/convergence-border-164/ and
~/.local/state/convergence-linux-qualification/border-handoff/ (plus HUD readiness log).
No production runtime changes, provider calls or source release bump. T005 remains
open: actual Border/member and standalone cross-source model interpretation must be
qualified separately. Spec163 failures and attempt exhaustion remain unchanged.
This follow-up is a draft source milestone, stacked on spec162; it does not replace
or claim completion of upstream PR311 or Hermes/production confinement qualification.

Publication: source commitdde78b44 is in draft
[fork PR6](https://github.com/byrn-baker/netclaw-convergence/pull/6), based on
162-convergence-read. Hosted CI started; final hosted results are reported on that PR.

Additional reproducibility details from the worker:

```bash
python3 -m pytest tests/n2n/test_convergence_member_164.py \
  tests/n2n/test_execution_context_149.py tests/n2n/test_hermes_members_149.py \
  tests/n2n/test_internal_transport.py tests/n2n/test_routing.py -q
```

Result:17 passed,13 existing datetime.utcnow deprecation warnings,2.59s.
`openclaw config validate --json` against isolated temporary member homes returned
valid=true with no warnings for declared Ollama and native built-in Anthropic env
SecretRef configurations on2026.10.9. Native `isToolAllowedByPolicyName` matcher
accepted read/summary/evidence and rejected9 other tools. These native checks were
recorded in tool output; temporary fixtures were cleaned and no persistent native
check artifact was saved. They made no provider requests.
