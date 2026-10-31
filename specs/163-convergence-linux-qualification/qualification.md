# Fresh Linux qualification, 2026-10-31

## Tested environment

Dedicated Ubuntu 24.04.5 amd64 guest; kernel 6.8.0-147-generic; 4 vCPU / 8 GiB RAM,
48 GiB disk. Started with no Docker, Node, OpenClaw or NetClaw state. A clean
OS snapshot precedes application installation. Hypervisor choice is incidental;
no Proxmox APIs or managed network equipment are used by the software.

- Docker Engine 29.9.2; Compose 5.6.1, official Docker apt repository.
- Node 24.22.1, official amd64 archive verified against published SHA256;
  npm 11.19.1; Python 3.12; isolated FastMCP 4.0.11 / MCP 2.3.0.
- External service f54bafca82f339d8573c55c53795fa05bd9dd843.
- NetClaw reader base c954845c, with this spec's tool-description clarification.
- OpenClaw 2026.10.9 (8b18b55), selected by the installer runtime policy.
- Ollama Cloud/minimax-m2.7 with private environment-reference authentication.

## Executed path

Followed the external home-lab prepare/validate/start/verify/demo/check commands,
with site demo and API port 3080. Added a dedicated site-scoped viewer before
startup. Node and Docker were installed separately. Preinstalled OpenClaw using
the npm arguments from runtime-policy.py, then used official noninteractive
onboarding with loopback/token gateway, reference credentials, no channels and
no hooks. Ran the real NetClaw installer with --runtime openclaw --components
convergence-read, including preflight. Projected native MCP and restarted gateway.
The interactive onboarding wizard and fresh optional HUD installation were not
exercised; earlier connector/browser evidence is in spec 162.

The first provider rejected the chat with HTTP 402. Ollama Cloud onboarding then
selected minimax-m2.7; the unused provider credential was removed from the guest.
No production credentials other than the selected model authentication were copied.
No production runtime, device, capture interface or network configuration changed.

## Results

| Check | Result |
|---|---|
| Core service, scoped authentication, Grafana datasource | PASS, all 10 checks |
| Synthetic exporter through collector/archive/API | PASS, 2 records / 2,148 bytes / 15 packets |
| Optional isolated reader installation | PASS |
| Native OpenClaw MCP doctor/probe | PASS, both Convergence tools discovered |
| Actual gateway/model tool execution | PASS, both tools with exact same window/filter/site |
| Model interpretation | FAIL, unsupported request/reply wording remains |
| Wrong key / ungranted site | PASS, explicit unauthorized |
| Closed endpoint | PASS, unavailable; no invented zero traffic |
| Disabled with backend stopped | PASS, explicit disabled |
| Stop/start and re-enable | PASS, exact retained totals/receipt timestamp unchanged |
| Pinned connector contract suite | PASS, 18 tests; independently repeated |
| Independent code/docs/security review | PASS; semantic finding remains open |

Final model execution used `range=1h`, window 2026-10-31T01:45:18.711Z through
02:45:18.711Z. Summary and evidence both omitted exporter filtering, preserving
scope; the configured exporter allowlist contained loopback only. Both results
identified site demo and synthetic coverage. Evidence contained two records with
limit 100. The final complete trajectory has 54 events, retained privately.

The tested model initially guessed an invalid argument and inferred unsampled
traffic from zero sampling metadata. Clearer tool descriptions corrected those
observed mistakes in the final turn, but the answer still called a flow a
“larger reply.” Metadata establishes record direction, not request/reply meaning.
This is an open acceptance finding, not a qualified end-to-end investigation.
The structured reader results remain available independently of a model.

Transient Docker Hub 502 was resolved by retrying the same bundle. An initial
OpenClaw env warning did not recur on fresh validation; raw saved registration
uses environment references. Direct shell tests accidentally used the coordinator's
unqualified system SDK; the declared isolated suite passed. These are recorded
separately from product defects in verification.md.

## Limits and next acceptance

No macOS, Windows/WSL2, Hermes, physical capture, packet IDS, fresh K3s installation
or interactive onboarding claim. No performance/capacity minimum inferred from
this small demo. Finish model grounding acceptance before marking spec 163 complete.
All scope, counters and uncertainty must survive the generated explanation;
request/reply, application, initiator and unsampled claims require supporting evidence.

See [verification.md](verification.md) for commands, attempts and review dispositions.
