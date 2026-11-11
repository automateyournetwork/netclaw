# Spec 185: A member spec's model may use a Border provider or a subscription login

Created 2026-11-11; branch `185-member-spec-providers`, stacked on `183-member-scoping`
(specs 183/184, 1.21.0); status: implementation and verification.

## Problem

Spec 184 lets a member spec choose only an Anthropic model, reached with
`${ANTHROPIC_API_KEY}`. Operators run members on other providers: a Border may have only an
Ollama Cloud key, a local model, or an OpenAI account, and Claude and ChatGPT subscriptions are
supported by OpenClaw as alternatives to API keys. A spec member on such a Border cannot run a
model at all. Found provisioning Convergence's alert investigator on a test Border whose only
provider is `ollama-cloud`.

Provisioning that member live also showed that a staged member's `run.sh` starts it with the
system `python3`, not the federation runtime the mesh daemon uses, so a cold-started member
lacked `websockets` and a current `cryptography` and failed every task.

## Requirements

- FR-001: `model` may be `<provider>/<model>` where `<provider>` is a key of the Border
  template's `models.providers` (other than `anthropic`, which keeps spec 184's behaviour).
  Validation refuses, naming the problem: a provider the Border does not configure; a model the
  provider entry does not list; a provider entry with `localService` (a member does not start
  provider processes); a provider entry holding literal secrets (reported by path, never value);
  an unsafe provider name or model id.
- FR-002: A new optional key `auth`: `"api-key"` (default) or `"subscription"`. With
  `subscription`, `model` must be `anthropic/<id>` or `openai/<id>` (the built-in providers that
  OpenClaw signs in with a Claude or ChatGPT account). Any other combination is an error.
- FR-003: A provider member's `openclaw.json` registers exactly one provider: a copy of the
  Border's entry for its provider with only its model in `models`. Keys stay `${VAR}` references.
  A subscription member registers no provider entry; its primary model is the built-in
  `<provider>/<id>`. An Anthropic API-key member is unchanged (spec 184).
- FR-004: The member's env slice carries the variables the copied provider entry references
  (for example `OLLAMA_API_KEY`) instead of `ANTHROPIC_API_KEY`; a subscription member's slice
  carries no provider key. Server variables and deny lists are unchanged.
- FR-005: `N2N_MEMBER_MODEL` (the member's `--model`) is the full `<provider>/<model>` binding
  the member home configures and allows.
- FR-006: `in2n-member-home.py` reports a provider member's referenced variables as present or
  MISSING in the member env (names only) and prints, for a subscription member, the exact
  login command for the member's own home:
  `OPENCLAW_STATE_DIR=<home> OPENCLAW_CONFIG_PATH=<home>/openclaw.json openclaw models auth login --provider <p>`.
  `--model` cannot override a spec that names a provider.
- FR-007: `in2n-migrate.py` stages `run.sh` to exec the n2n component's recorded interpreter
  (`<runtime home>/python-runtimes/records/n2n`, the one `federation-control.py` starts the
  daemon with), else `python3`. Paths are shell-quoted.
- FR-008: `in2n-profiles.py spec`, `in2n-migrate.py --spec` and `in2n-member-home.py --spec`
  validate against the same Border template's servers and providers.

## Out of scope

- Fallback models and more than one provider per member.
- Providers for profile members (unchanged).
- Running a provider's `localService` for a member, and guarded routes for private-network
  providers: in production posture `controls.guarded_model_route` refuses models on
  loopback/private providers on the DefenseClaw plugin route; this spec does not change that.

## Success criteria

- A spec naming `ollama-cloud/minimax-m3` provisions a member that runs on that provider, with
  `OLLAMA_API_KEY` and no `ANTHROPIC_API_KEY` in its slice; verified live end to end (a
  Convergence alert case delegated by the Border's alert agent, investigated and recorded by the
  member) on a test Border.
- `openclaw config validate` accepts the provider and subscription member homes.
- Spec 184 behaviour for Anthropic models is unchanged; its tests pass.
