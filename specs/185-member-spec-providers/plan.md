# Plan

- `scripts/in2n-profiles.py`: `auth` joins `MEMBER_SPEC_KEYS`; `SUBSCRIPTION_PROVIDERS`;
  `load_member_spec(..., providers=None)` parses `model` into `provider`, `model` and `auth`
  (spec 184 forms unchanged); `provider_problem` (exists, lists the model, no `localService`, no
  literal secrets, safe names); `spec_provider_entry` (deep copy, only the model);
  `spec_model_binding`; `border_template_providers`; `spec_env_slice_keys(..., providers)` takes
  the provider entry's `${VAR}` references, or none for a subscription; the `spec` subcommand
  passes the Border's providers.
- `scripts/in2n-member-home.py`: `spec_member_providers` (built-in Anthropic, copied entry, or
  none); `spec_member_config` uses it and the full binding; refuse `--model` for a provider
  spec; report provider variables by name and print the subscription login command; validate
  with the Border's providers.
- `scripts/in2n-migrate.py`: validate with the Border's providers; stage
  `N2N_MEMBER_MODEL=<binding>` and the slice with providers; `member_python` and a quoted
  `run.sh` exec line.
- Docs: docs/N2N-RISK.md "Member spec" (model and auth rules, providers, subscriptions, guard
  note); release notes 1.22.0.
- Tests: `tests/n2n/test_member_spec_providers_185.py`; spec 184 error cases updated for the new
  messages.
