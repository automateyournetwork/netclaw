# Research

NetClaw controls.guarded_model_route: models must be `defenseclaw/<model>`; provider
`defenseclaw` baseUrl loopback :DEFENSECLAW_GUARD_PORT (4000); security.mode in
~/.openclaw/config/openclaw.json. defenseclaw-enable.sh pipes unpinned `main`
installers (DefenseClaw, OpenShell) into a shell.
DefenseClaw (cisco-ai-defense/defenseclaw) releases: 1.0.5 (2026-10-30), 1.0.4
(2026-10-27), 1.0.3 (2026-10-21). 1.0.4 source: provider adapters include
adapter_ollama.go (native /api/chat and /api/generate inspection); upstream chosen from
X-DC-Target-URL set by its OpenClaw fetch interceptor; targets must match a provider
domain registry built from embedded providers.json, `llm_providers` in config.yaml,
`llm.base_url`'s host and ~/.defenseclaw/custom-providers.json, or
`guardrail.allow_unknown_llm_domains`. Whether `ollama.com` is in the embedded list,
and how `setup guardrail` rewrites OpenClaw 2026.10.9 provider config, is unverified.
VM: Docker 29.9.2, Node 24.22.1, no Go, no DefenseClaw/OpenShell; 16 GiB.
