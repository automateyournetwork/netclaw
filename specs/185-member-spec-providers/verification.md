# Verification

## Tests

`tests/n2n/test_member_spec_providers_185.py` (44 tests):

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

## Review round 1 (read-only Claude reviewer)

Eight findings, no critical one; all fixed in e053de56 with tests
(`test_provider_entry_is_built_from_allowed_fields_only`,
`test_provider_entry_keeps_references_env_secretref_and_whitelisted_model_keys`,
`test_border_providers_named_like_built_ins`, `test_member_home_refuses_model_override_for_every_spec`,
`test_member_record_names_provider_and_auth_and_export_lines_count`):

1. The provider entry was copied whole, so a file/exec SecretRef or an unknown field reached the
   member: it is now built from `PROVIDER_FIELDS`; `apiKey` is a `${NAME}` or a default env
   SecretRef; other fields are refused by name.
2. A key in a `baseUrl` query or in an unusual header name passed: `baseUrl` may carry no
   credentials, query or fragment; every header value must be reference-only.
3. Provider references skipped the deny lists and store keys: denied names are refused and
   filtered from the slice.
4. `--model` on an Anthropic spec desynced the staged model: refused for every spec run.
5. The chosen model object was copied unscanned: only `PROVIDER_MODEL_FIELDS` are kept.
6. The member record lacked `provider` and `auth`: recorded.
7. Model ids with `/` were refused: accepted for Border providers (`PROVIDER_MODEL_ID`); the
   production Border's `ollama` provider lists `voytas26/openclaw-qwen3vl-8b-opt`, and a spec
   naming it validates.
8. `export NAME=` lines were reported MISSING: the report uses write-env.py's assignment form.

## Review round 2 (confirmation pass)

All eight round 1 fixes confirmed. New: (1) a `${NAME}` `baseUrl` hid the provider's host from
the production guard (`controls._local_model_provider`), so a LAN model server passed as
non-local: in2n-member-home.py now writes the literal URL from the member's own env and refuses
an unresolved or unclean one (`test_referenced_base_url_is_written_literally_so_the_guard_sees_its_host`,
`test_referenced_base_url_must_resolve_to_a_clean_url`); (2) the present/MISSING report now
names env SecretRef ids; (3) N2N-RISK.md and the release notes describe the round 1 rules;
(4) `api` must be a plain adapter name (`test_provider_api_must_be_a_plain_adapter_name`).

The live alert loop was re-run on the hardened code (case resolved by the member; Border agent
calls: `case_get`, `n2n_route`, `n2n_task_wait` ×2).

Results: `test_member_spec_providers_185.py` 44 passed, `test_member_spec_184.py` 146 passed,
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
