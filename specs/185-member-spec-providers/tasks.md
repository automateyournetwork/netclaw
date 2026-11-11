# Tasks

- [x] T001 Research provider entries, key references, subscription login storage, `--model` matching, guard routes (research.md).
- [x] T002 `model: <provider>/<model>` from the Border's `models.providers`, with `provider_problem` refusals.
- [x] T003 `auth: subscription` for `anthropic/<id>` and `openai/<id>`; error for every other combination.
- [x] T004 Member config: one copied provider entry with only its model, none for a subscription, spec 184 Anthropic unchanged.
- [x] T005 Env slice from the provider entry's references; none for a subscription.
- [x] T006 Staged `N2N_MEMBER_MODEL` is the full binding; `--model` cannot override a provider spec.
- [x] T007 Member-home output: provider variables present/MISSING by name; exact subscription login command.
- [x] T008 `run.sh` execs the recorded n2n interpreter (found live), quoted.
- [x] T009 Tests, including `openclaw config validate` on provider and subscription homes.
- [x] T010 Live: Convergence investigator on `ollama-cloud/minimax-m3` on a test Border, alert loop end to end.
- [x] T011 Docs (N2N-RISK.md) and release metadata (1.22.0).
- [ ] T012 Review (Claude reviewer, read-only).
