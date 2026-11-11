# Research

Sources: the installed OpenClaw 2026.10.9 (docs under `.../lib/node_modules/openclaw/docs`), this
branch, and a live test Border (VM, NetClaw at this branch, Border role, production posture with
DefenseClaw).

## Provider entries and key references

A provider in `models.providers` is an object with `api`, `baseUrl`, optional `apiKey` and a
`models` list. OpenClaw resolves `${NAME}` in config values from the process environment, which a
member loads from its own `.env` (`in2n-member.py`, `write-env.py values`). Spec 184 already
relies on this for `apiKey: "${ANTHROPIC_API_KEY}"`. A copied entry with only `${VAR}`
references therefore needs only those variables in the member slice; `literal_secrets` (spec 184
round 3) finds literal keys, userinfo and secret headers by path.

The test Border's provider: `ollama-cloud` with `api: ollama`, `baseUrl: https://ollama.com`,
`apiKey: ${OLLAMA_API_KEY}` and models `minimax-m3`, `minimax-m2.7`. A production Border also
has `llama-cpp` with `localService` (OpenClaw starts `llama-server`): a member must not start it,
so such providers are refused.

## Subscription logins

`docs/concepts/oauth.md`: OpenClaw supports ChatGPT/Codex OAuth under the canonical `openai`
provider (`openclaw models auth login --provider openai`; "OpenAI explicitly allows subscription
OAuth usage in external tools/workflows like OpenClaw") and Anthropic Claude CLI reuse or
`claude setup-token` under `anthropic` (allowed per Anthropic staff, "API key auth is still the
safer recommended path" for production). Credentials live in OpenClaw's state database, and
"the database and migration sources respect `$OPENCLAW_STATE_DIR`". A login run with the
member's `OPENCLAW_STATE_DIR` is therefore stored in the member's home only and never reaches the
Border or other members. Built-in providers need no `models.providers` entry; the primary model
`openai/<id>` or `anthropic/<id>` with the model in `agents.defaults.models` is enough
(`openclaw config validate` accepts it; test below).

## Member model and --model

`gateway.py` runs `openclaw agent --local --model <N2N_MEMBER_MODEL>`; the comment in
`in2n-member-home.py` notes that the agent rejects a `--model` not in `agents.defaults.models`.
So the staged `N2N_MEMBER_MODEL` must be exactly the configured primary (spec 184 fix 3afbb44a
for `model: null`); this spec stages the full `<provider>/<model>` binding.

## Member interpreter

Live: a cold-started member (`netclaw-coldmember@`, confined system instance) logged
`enroll failed ('...Certificate' object has no attribute 'not_valid_before_utc')` and then
`Task ... failed: No module named 'websockets'`. `run.sh` was `exec python3 .../in2n-member.py`;
the system Python had `cryptography` 41.0.7 and no `websockets`. `federation-control.py` starts
the daemon with the interpreter recorded in `<home>/python-runtimes/records/n2n`
(`n2n-component-bounds/bin/python` on that host). Staging that interpreter fixed both.

## Guard routes

`controls.guarded_model_route` (production posture): the DefenseClaw plugin route accepts any
model whose provider domain DefenseClaw knows and refuses models on loopback/private/local
providers, because a fetch interceptor need not send local traffic through the proxy. A member
on a LAN Ollama therefore runs only in testing posture or behind a provider-route guard; a cloud
provider (`ollama.com`) works in production posture (verified live).
