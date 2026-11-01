# NetConverter in NetClaw: what is implemented, what we tested and how to use it

*Draft community update from John Capobianco for NetClaw maintainers and users. November 1, 2026.*

Spec162 is complete: **44 of 44 scoped implementation and qualification tasks**, five implementation review loops and three additional live qualification loops. NetClaw source **1.18.0** now includes a guarded NetConverter integration, an adapted skill, installer support, private migration artifacts and a protected path for rehearsing an approved candidate on a compatible virtual target. The coordinated VS Code extension is **1.5.0**. The release record tracks source and Marketplace publication; existing runtime upgrades remain explicit.

The live work went beyond tool discovery. We completed two separately approved synthetic conversions, tested the returned IOS-XE candidate on a real CML router, and built a fresh Border with exactly one NetConverter member. A real Border agent successfully delegated to the member’s native guarded tool and received authenticated discovery evidence.

For users, the integration joins migration work to the tools you already use to collect, analyze and test a network. [NetConverter’s official MCP model](https://netconverter.ai/mcp.html) separates reviewing saved work from submitting a selected local file. NetClaw preserves that distinction and adds exact-file approval, private artifact references and verification through existing tools. A successful conversion produces a candidate for engineering review.

Both the VS Code wizard and terminal setup expose the integration through the shared catalog. Choose the connection appropriate to the work:

| Mode | Use | Requirements |
|---|---|---|
| `hosted-readonly` | Review supported account and existing-job evidence | Enabled account, API key and account reference |
| `local-terminal` | Prepare approved submissions and retrieve verified artifacts | The same settings, plus the operator-installed official Terminal executable and a workspace |

NetClaw installs its guard’s isolated dependencies. Obtain the separately licensed client from the [official Terminal repository](https://github.com/valeronlabs/netconverter_terminals). Setup does not redistribute that client or automatically accept its license. Put the key in the selected claw’s private settings; plans carry secret references.

For a Risk of Claws, select the OpenClaw NetConverter member profile. The Border keeps `n2n` and `protocol`; the member gets `n2n`, `netconverter` and the `netconverter` skill. Its key, workspace and guard state belong to that member. The clean Mac run passed all 26 installation effects, required verification tiers 1–3 and Risk verification. The HUD showed one active member. Review and credential-entry inputs were explicitly simulated for that automated test; the downloads, services, enrollment and native agent execution were real. Hermes NetConverter member execution remains unqualified.

A practical first workflow is:

1. Ask the selected member to run `netconverter_status(discover=true)` and report actual supported operations and directions.
2. Stage an authorized configuration locally, or use a qualified private collector. Inventory records alone do not provide a running configuration.
3. Have the guard prepare the exact submission. Review its file, hash, size, destination, account reference, operation, direction and options.
4. Run the native approval command yourself. The agent cannot approve its own hosted upload. Each new submission needs its own approval.
5. Review the actual job findings, then retrieve the candidate through the verified download path. Retain warnings, manual actions and incomplete-report flags.
6. If rehearsal is authorized and a compatible image exists, use the existing lab and protected configuration workflow, followed by explicit positive and negative tests.

The [operating guide](../NETCONVERTER.md) contains the exact setup and approval commands. A “local terminal” still sends the approved file to NetConverter’s hosted service. The protected artifact route avoids returning full configurations and reports to the model; it does not sandbox every other tool available to the same OS user. Also, `discover=false` deliberately skips the upstream check: false flags in a new MCP process mean unverified state, not evidence of a bad key.

Our live reference used an authored IOS-XE OSPF fixture. NetConverter returned Junos SET, then converted that returned file back to IOS-XE after a second human approval. Both jobs remained **needs review**. The reverse candidate was adapted only for the target image’s interface name and applied to an IOS-XE 17.18.2 virtual router through NetClaw’s protected pyATS route.

| Evidence | Result |
|---|---|
| Real target and independent peer | OSPF FULL on both ends |
| Reciprocal loopback routing | Present, metric 11 |
| Positive traffic | 5/5 pings each way |
| Unadvertised-prefix control | 0/3 pings each way, as expected |
| Management continuity | Preserved in separate management VRFs |
| Local Batfish comparison | Three snapshots parsed; nine modeled traffic checks passed |
| Difference retained | Junos modeled route metric 10 versus IOS-XE 11 |

No Junos image was available. The Junos output has conversion and modeled evidence; live Junos commit/readback remains unqualified. This was a routing reference, so it does not establish firewall-policy or NAT equivalence, hardware performance or an executed rollback. The owner’s temporarily stopped CML routers were restored and their configurations checked against captured baselines. Rehearsal resources and failed trials remain retained, and the rehearsal’s Local/Lab write authorization was disabled afterward.

Maintainers should pay particular attention to the boundaries that live execution exercised. Exact-file submission uses a durable one-use attempt record; a timeout leaves an unknown outcome and never authorizes an automatic retry. Candidate application retains the existing `pyats_configure_device` identity, requires an API-issued capability and binds the actual candidate, endpoint, active inventory, baseline and rollback evidence. Denial cannot be worked around with another write tool or raw SSH. Production keeps its approved ServiceNow change workflow; the qualified Local/Lab route is an explicit, scoped exception.

The live agent also exposed a real defect by replacing a baseline file with a reference note. The genuine original remained available, but the original gate should have refused the substituted file. We retained that failed acceptance, added exact-byte checks against the collector’s original artifact and receipt, and ran a clean protected repeat that passed. Later, a fresh Risk install exposed MCP endpoint aliases frozen to a default port before the selected Risk ports were applied. Source 1.15.5 fixes that registration order, with a regression covering both Border and member. Tool discovery alone had not established working delegation.

Other fixes from the same qualification covered installed HUD reference files, gateway SecretRef resolution and an explicitly started authenticated pyATS session for clients that close STDIO between turns. Dynamic inventory and subsequent device operations must share the qualified live process. Credentials, authority and inventory are separate concerns throughout.

Recorded checks include 70 NetConverter feature tests, nine deployment tests, eight Risk tests, seven feature-installation tests, nine catalog tests and 18 plan tests, alongside the separately recorded managed-pyATS, HUD and extension checks. The [verification record](../../specs/162-netconverterai/verification.md) distinguishes fixtures, real service calls, modeled behavior and appliance observations. The [task list](../../specs/162-netconverterai/tasks.md) explains what 44/44 covers.

Cross-composition is where contributors can extend this work. NetBox, Nautobot and Infrahub can contribute inventory and intent; ServiceNow and Catalyst Center can add supported context; IP Fabric and Forward Networks can contribute snapshot-bound assurance evidence. CML, containerlab, EVE-NG and GNS3 need separately verified image and management paths. Jev remains an optional adviser, with its own disclosure and budget controls. Diagrams, documents and ticket drafts should preserve the distinction between observed and proposed state. The [composition contract](../../workspace/skills/netconverter/references/composition.md) records those boundaries. FRR remains a separately qualified intent-based alternative where requested; native NetConverter FRR translation is not established.

The most useful next contributions are reproducible cases: a supported direction, synthetic input, exact versions, expected behavior, actual tool results and a clear statement of what failed. A licensed Junos rehearsal, a carefully scoped firewall policy/NAT case, another installer platform, or a private collector adapter would each add concrete coverage. Keep customer configurations, credentials and private topology out of public issues.

Thank you to Marcin Zgola and Steven Robb at NetConverter.ai for the conversation behind this integration. We now have a migration workflow that reaches real software, real virtual routers and inspectable evidence. Users can start with a bounded reference; maintainers can extend it with the same standard of proof.
