# Verification

## Tests

`tests/n2n/test_member_spec_providers_185.py` (21 tests):

- a Border provider model is accepted by reference; the copied entry keeps only the chosen model
  and the Border's entry is unchanged;
- Anthropic models (`null`, `claude-…`, `anthropic/claude-…`) keep spec 184's built-in provider;
- each refusal: unknown provider, unlisted model, `localService`, literal secret (named by path,
  value never in the message), bad model id, bad `auth`, `subscription` without a model, with a
  non-built-in provider or with a bare model id; a provider model when the Border has no
  providers;
- subscription models for `openai` and `anthropic`;
- env slice: the provider entry's references (`OLLAMA_API_KEY`), not `ANTHROPIC_API_KEY` or
  another provider's key; none for a subscription; server variables unchanged;
- end to end (in2n-migrate.py then the printed in2n-member-home.py command) for a provider member
  and a subscription member: staged `N2N_MEMBER_MODEL` equals the configured primary and is
  allowed; exactly one provider entry (or none); the exact login command with the member home;
  no key value in the output;
- `--model` cannot override a provider spec, and nothing is written;
- `run.sh` execs `python3` when no n2n runtime is recorded and the recorded interpreter when one
  is (a path with a space, quoted);
- with the installed OpenClaw 2026.10.9, `openclaw config validate` accepts the provider member
  home and both subscription member homes.

Spec 184's three model error cases now expect the new messages; all other 183/184 tests are
unchanged.

Results: `test_member_spec_providers_185.py` 21 passed, `test_member_spec_184.py` 146 passed,
`test_member_mcp_mappings_183.py` 50 passed (`NETCLAW_TEST_OPENCLAW_DIST` set to the installed
OpenClaw). Full `tests/n2n` (fastmcp4 runtime): 32 failed, 2192 passed, 16 skipped, 179 errors;
the failing and erroring test ids are identical to upstream main e21d867c's on this host (modules
not installed here, such as `service_identity` and `qrcode`, and protected-runtime setup
refusals). `verify-spec-artifacts.py` and `prepare-release.py --check` pass.

## Live

Test Border (VM, Border of a testing Risk in production posture with DefenseClaw), NetClaw at
this branch, Convergence's alert investigator spec with `--model ollama-cloud/minimax-m3`:

1. The member was provisioned with `convergence-case-mcp` and `prometheus-mcp`, the four-entry
   allowlist, its skills, `models.providers` = the copied `ollama-cloud` entry with only
   `minimax-m3`, and `OLLAMA_API_KEY` but no `ANTHROPIC_API_KEY` in its slice.
2. First routed task: the cold-started member failed with `No module named 'websockets'` after an
   enrolment error from an old `cryptography`. `run.sh` ran the system `python3` (FR-007);
   after re-staging, `run.sh` execs `python-runtimes/n2n-component-bounds/bin/python`.
3. Routed task "list scrape jobs that are down": the member answered from Prometheus
   (`output_text`: "No scrape jobs are currently down …", 17 021 tokens).
4. Alert loop: a case opened on the Convergence API for the test site and the receiver's hook
   payload posted to the Border's `alert` agent (tools: `read`, the case tools, `n2n_route`,
   `n2n_task_wait`). The agent called `case_get`, `n2n_route` and `n2n_task_wait` twice; the
   member investigated with `prometheus-mcp` and recorded the case `resolved` with cited facts
   and a root cause. The Border agent made no evidence or `case_update` call.

Not live-tested: subscription logins (configuration validated by OpenClaw only).
