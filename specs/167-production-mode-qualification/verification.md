# Verification

Run prodmode-20261101: start00:15UTC, deadline01:00UTC. Branch
167-production-mode-qualification from 48804dd1 (spec166, PR #313). Test VM only.
Provider runs counted; owner open-ended qualification authorization continues.
Installer run BLOCKED by the session permission policy (external code execution);
awaiting owner decision. Nothing was installed; config backups only.
Owner approved running the verified DefenseClaw 1.0.4 installer on the test VM.

P0 calibration (one minimax-m3 gateway turn, counted): is Ollama Cloud traffic routed
through the DefenseClaw proxy by its OpenClaw plugin?
P0 result: plugin intercepted the turn (sidecar: provider=ollama-cloud); proxy
"BLOCKED shape-detected passthrough to unknown domain: ollama.com"; OpenClaw got 403.
Fail-closed is correct. Fix: custom-providers overlay for ollama.com. P1 calibration follows.
P1 (counted turn): with ~/.defenseclaw/custom-providers.json registering ollama.com
(name ollama-cloud, profile ollama-cloud:default, env OLLAMA_API_KEY) the plugin routed
the turn: "intercepted ollama-cloud/api/chat -> https://ollama.com/api/chat"; reply ok;
audit_events record llm_response (gateway.hook.model) and the session message. Note:
an egress.allowed event to api.openai.com appeared during the turn (source not yet
identified).

T001 findings (VM, DefenseClaw 1.0.4, OpenClaw 2026.10.9):
F1 DefenseClaw init fails ("gateway defaults: str expected, not dict") when
   gateway.auth.token is a SecretRef object; same code on 1.0.5 and main
   (_resolve_openclaw_gateway copies auth.token raw). VM workaround: rotated the
   gateway token to a new random literal (no stored secret read); gateway healthy.
F2 NetClaw gateway_ws.resolve_gateway_ws_config has the same raw-token handling.
F3 `setup guardrail` installs an OpenClaw plugin (plugins.allow/entries/load.paths ->
   extensions/defenseclaw) that intercepts model traffic; it does not create a
   `defenseclaw/<model>` provider. NetClaw guarded_model_route therefore reports
   model-guard unavailable ("must use the defenseclaw provider") although traffic is
   guarded.
F4 Unknown provider domains are blocked fail-closed by the proxy (403 to OpenClaw);
   Ollama Cloud requires a custom-providers overlay.
F5 Member homes built by in2n-member-home.py strip plugins, so production members
   would run without the DefenseClaw plugin.
F6 defenseclaw-enable.sh pipes unpinned main-branch installers; init/guardrail need
   --connector openclaw and --non-interactive flags on 1.0.4.
Setup done: DefenseClaw 1.0.4 installed (pinned, verified), init + guardrail observe
(regex_only, local scanners), defenseclaw-sidecar.service via in2n-services,
security.mode=defenseclaw in ~/.openclaw/config/openclaw.json. T001 COMPLETE.
Observation: DefenseClaw egress audit lists api.openai.com requests at OpenClaw gateway
restart (00:16:05, 00:16:33) and after P1 (00:18:31), recorded egress.allowed with no
caller detail; the VM has no OpenAI credential. Attributed to OpenClaw, not NetClaw;
not investigated further here.

T002 (VM): worker A runtime fixes deployed (controls plugin route, member plugin carry,
gateway_ws SecretRef). N2N_RISK_MODE=production in the Border env and mesh env;
mesh/sidecar units regenerated; cold-start template reinstalled (Environment=
N2N_RISK_MODE=production). Posture: "production - enforced" (sandbox: confined
system cold-start instances; model-guard: DefenseClaw plugin route + proxy +
security.mode; audit). Member rebuilt with in2n-member-home.py into a new home:
plugins limited to defenseclaw (allow/entries/path), N2N_RISK_MODE production, config
valid; re-registered on_demand (token written, not displayed), state provisioned.
T003 begins: production S2 (border-fed, envelope, cold start through production path).
P2 begins: production S2.
P2 production S2 FAIL (counted, 135 events): no delegation attempted. The Border read
the on-demand member as `state provisioned, live false, execution not verified` and
stopped; no cold start, no member turn. Semantics otherwise PASS (window, bound,
source -> destination, no verdict, named gaps). Root cause: /n2n/members and
/n2n/members/health expose only `live`, while an on-demand member is never live until
routed (health_report already computed will_cold_start internally).
Fix (T004): member_liveness (shared by both endpoints) adds `starts_on_route` (not
live, local launch_cmd, on_demand or service-owned); skill1.2.0 text says such a
member is routed, not reported unavailable. Test added; tests/n2n 745 passed/5
skipped (inherited failure deselected); catalog parity/metadata PASS. Deployed; live
health shows starts_on_route true; posture still production - enforced.
Worker B (installer/docs): defenseclaw-enable.sh pinned+verified install, SecretRef
stop, non-interactive init/guardrail, opt-in OpenShell/MCP registration, durable
sidecar via in2n-services, custom-provider guidance; docs updated; 9 unit tests pass.
Remaining unpinned path noted: scripts/lib/install-steps.sh DefenseClaw step.
P3 begins: production S2 rerun.
P3 production S2 FAIL (counted, 160 events) but the production path ran: router
"Routed capability 'convergence-observations' -> member", "iN2N cold-start (confined,
system instance)", launcher started the member, member dialed and enrolled; the member
then refused its task fail-closed: "model-guard unavailable: security.mode is
'hobby'". Cause: controls._security_config_path reads <member home>/config/
openclaw.json and member homes never contained one. Border answer honest (no
fabricated evidence; refusal reported). Fix (T004): in2n-member-home mirrors only the
Border's security.mode into the member home (both convergence and generic builders);
tests added (mirrors only mode, 0600; nothing when the Border has no config).
convergence-read contracts PASS; tests/n2n 745 passed/5 skipped.
P4 begins after applying the same mirror to the existing VM member home.
P5 (counted member-only turn): route via daemon API with no Border model turn, to attribute guarded traffic to the member.
P4 production S2 PASS (counted, 113 events): first end-to-end production run.
Posture enforced; router -> production cold-start of the confined system instance ->
member enrolled -> member preflight passed (security.mode mirrored, plugin route,
proxy) -> task completed. Answer: exact recorded window, latest-100 bound (2/2/0),
source -> destination records with distinct timestamps, no request/reply/session/
initiator claims, Prometheus "scrape health only ... not collector liveness", no
verdict, member list used (starts_on_route), named capability gaps, delegated
provenance.
P5 member-only attribution (counted member turn via the daemon API, no Border model
turn): task completed; DefenseClaw recorded 3 proxy intercepts (ollama.com), 3
llm_prompt, 3 llm_response, 3 guardrail-verdict, 0 session messages, 0 blocked. The
member's embedded model I/O passes through the guardrail.

Fail-closed checks (no provider calls): (a) defenseclaw-sidecar stopped -> posture
"production - DEGRADED (model-guard missing)", /n2n/route refused
{error production_degraded, refused_control model-guard}, no cold-start instance;
restored -> enforced. (b) `coldstart remove` with an on-demand member -> "DEGRADED
(sandbox missing)", route refused {refused_control sandbox}, no instance; reinstalled
-> enforced. T002 COMPLETE.
P6 production S1 and P7 production S3 begin (fresh observation).
P6 production S1 PASS (counted, 107 events): exact window, latest-100 bound (2/2/0),
record-only semantics, API-health-only scope, absence not evidence, named gaps; the
standalone Border routed to the on-demand member (starts_on_route) and attributed
the evidence to it.
P7 production S3 PASS (counted, 109 events): exporter 10.99.0.1 refused on the Border
and by the cold-started member; no other exporter or window substituted ("would have
broken the requested correlation"); network-data-analysis route NO_CAPABLE_MEMBER;
named pcap/DNS searches; refusal not read as evidence; provenance stated. No
DefenseClaw BLOCKED events during P6/P7.
P8 begins: production S2 repeat.
P8 production S2 PASS (counted, 106 events): member provenance precise (member called
convergence_flow_evidence directly this turn; task completed), exact window, bound,
record-only semantics, "collector liveness/freshness cannot be established from
receipt-time data", absence not evidence, capability searches named.
T003 COMPLETE: production mode (DefenseClaw 1.0.4 plugin guard, systemd confinement,
GAIT audit) passes S1 (P6), S2 (P4, P8 consecutive) and S3 (P7) on OpenClaw
2026.10.9 + minimax-m3; member-only guarded I/O attributed (P5); fail-closed checks
pass. Counted provider turns this spec: P0-P8 (P0/P1 calibration, P5 member-only).

T004 integration (coordinator): provider registration moved to the supported CLI
(`defenseclaw setup provider add`; custom-providers.json is derived from config.yaml)
in docs, enable-script output and the VM (hand-written overlay replaced; P9
calibration turn intercepted and answered). install-steps.sh core_defenseclaw and
netclaw-secure-start.sh no longer pipe unpinned installers (delegate to the reviewed
enable script; OpenShell auto-install removed). config/components/effects.json
sourceSha256 updated; all 111 audited function hashes unchanged. Checks: tests/n2n
745 passed/5 skipped (inherited failure deselected); defenseclaw-enable + standalone
enable tests 33 passed; convergence-read PASS; setup-installer 274 tests OK (32 skips;
first run failed only on the stale effects source hash); spec artifacts, catalog
parity, docs reconcile, links, diff --check PASS. Release 1.17.1 (patch).
Independent verification requested.
P10 begins: production S2 after verifier fixes (stricter plugin route, local-provider refusal).

Independent verification: PASS (conditional), three MEDIUM and several LOW findings;
all addressed here:
- M1 plugin route admitted any model: now refuses models whose provider endpoint is
  loopback/private/link-local/.local (or a local-by-default provider without a
  baseUrl), including overrides; tests for ollama/LAN/loopback/mDNS providers.
- M2 plugin route did not check where traffic goes: now requires the extension's
  openclaw.plugin.json with id defenseclaw, and DefenseClaw config.yaml guardrail
  enabled, connector openclaw and port (if set) equal to the probed guard port
  (default 4000); tests for each refusal.
- M3 installer verified only against the release's own checksums.txt: the reviewed
  1.0.4 install.sh SHA-256 is pinned in defenseclaw-enable.sh; other versions need an
  operator-reviewed DEFENSECLAW_INSTALL_SHA256; tests for pin, missing and mismatch.
- LOW: installer prompt no longer advertises OpenShell or requires Docker/Go (the
  enable script runs its own preflight); doc sentences fixed; manual install chains
  `sha256sum -c && bash`; N2N-RISK provider wording uses the CLI; status wording states
  the observe-mode qualification scope; skill bumped to 1.2.1 (catalog regenerated);
  release note scoped to OpenClaw member homes; generic-builder security-mode mirror
  tested through the real script entry point. effects.json sourceSha256 updated
  again; 111 audited function hashes unchanged.
VM after redeploy: posture "production - enforced"; member home route validates
(plugin route). P10 production S2 PASS (counted, 120 events): routed, confined system
cold start, member task completed, 0 BLOCKED; provenance/bound/semantics correct;
minor wording deviation ("sampler_address identifies the collector" - it is the
exporter).
Final checks: tests/n2n 756 passed/5 skipped (inherited failure deselected);
enable/standalone unit tests 36 passed; convergence-read PASS; setup-installer 274 OK
(32 skips); bash -n on changed scripts; spec artifacts, release 1.17.1, catalog
parity, docs reconcile, links, ruff F/E9, diff --check PASS.
T004 COMPLETE pending commit/upstream PR. Upstream #312 and #313 merged; this PR
targets main directly (base 48804dd1 is in main 616e5306).

Upstream PR creation for spec167 was blocked by the session permission policy;
awaiting owner approval. Branch pushed to the fork (85849ffc); PR body drafted.
Owner approved: upstream PR automateyournetwork/netclaw#314 opened. F1 reported to
DefenseClaw as cisco-ai-defense/defenseclaw#1404 (no duplicate found; versions,
reproduction, code locations at main 7dca866a, expected behaviour, workaround; no
private data); DEFENSECLAW.md known-limitation section links it.
