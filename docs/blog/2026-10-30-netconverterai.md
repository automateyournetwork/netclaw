# From a converted configuration to a migration you can test

*Spec162 development update, refreshed 2026-11-01. Real synthetic conversion,
protected IOS-XE appliance application and bidirectional packet tests passed.
A fresh Border-plus-one-member installation and real native delegation also
passed, using owner-requested simulated installer review inputs. All 44 scoped
tasks are complete; platform and appliance limits remain explicit.*

Network migrations accumulate work at every handoff. Someone collects the old
configuration. Someone translates it. Someone checks the warnings, builds a lab,
reconciles interfaces, runs tests and assembles the evidence for a change review.
The interesting opportunity is to connect those steps without losing the
engineer's control over what leaves the environment or reaches a device.

That is what I am building with [NetClaw](https://github.com/automateyournetwork/netclaw)
and [NetConverter.ai](https://netconverter.ai/).

## Part one: what NetConverter contributes

NetConverter provides conversion, validation and optimization workflows, with
an [MCP interface and official Terminal](https://netconverter.ai/mcp.html) that
let an assistant work with files and saved job evidence. Its capabilities depend
on the account, platform and conversion direction. A local Terminal reads a local
file, but submitting that file still sends it to the hosted conversion service.

The [supported-vendor matrix](https://netconverter.ai/docs/supported-vendors.html)
includes IOS-XE and Junos router paths. That makes OSPF a useful reference
migration: interfaces, routing intent, adjacency and forwarding can all be tested.
EIGRP is not translated to Junos; moving from EIGRP to OSPF needs an explicit
protocol redesign. Router output remains subject to engineer review.

That distinction matters. A generated configuration is a candidate whose warnings,
manual work and supported features need to travel with it.

## Part two: what NetClaw adds

Spec162 connects conversion to the surrounding engineering work. The optional
integration appears in both the VS Code and terminal installers, with a choice
between hosted read-only access and an operator-installed licensed Terminal.

Before a file submission, NetClaw freezes the source and presents its hash, size,
destination, account reference, operation, direction and options. The human
approves that exact request in a native terminal. A changed file or connection
invalidates the review. A lost response becomes an unknown outcome that cannot
quietly create a second conversion job.

The next handoff also deserves care. A downloaded candidate can stay private while
the model receives an artifact reference. Terminal Intent lets the engineer review
that file for one designated lab endpoint. The API issues a short-lived, one-use
capability only after baseline and rollback preparation. Application uses the
existing pyATS configuration tool and keeps its permission checks.

The result is a more useful engineering question:

> Can we create the proposed target virtually, load the reviewed candidate, and
> demonstrate the behavior we expect before requesting a production change?

The workflow discovers actual images, capacity and management paths for CML,
containerlab, EVE-NG or GNS3. It records resource ownership before creation,
reconciles uncertain outcomes and retains the lab for inspection. FRR can supply
a routing peer or traffic experiment; it does not stand in for a target firewall
or establish an unsupported converter direction.

Sources of truth and assurance systems make this more powerful. NetBox, Nautobot,
Infrahub, Catalyst Center and ServiceNow can help select the estate. IP Fabric and
Forward can contribute scoped observations. Dynamic [pyATS MCP](https://github.com/automateyournetwork/pyATS_MCP)
testbeds can bring the selected endpoints together for observation and verification.
Batfish contributes modeled checks, and Jev can provide an optional advisory review.
Diagrams, documents and a draft ticket can then point to the same evidence.

## What has actually been tested

The controlled integration tests exercise real MCP transports, exact approval,
concurrent and interrupted attempts, private collection, candidate application,
download integrity and failure reporting. The CML-shaped test peer receives real
create, boot and inspect calls; it is a fixture, not a real vendor appliance.
Installer tests cover cancellation and preservation of unrelated settings.

We also corrected a Batfish interpretation problem: partial parsing or a failed
differential query must remain inconclusive. An empty difference list cannot
stand in for a query that never succeeded. The composed review-package test
deliberately includes a failed traffic assertion and retains that failure.

The real account has now completed IOS-XE OSPF → Junos SET and a separately
approved Junos SET → IOS-XE reverse conversion. The first input was an authored
477-byte synthetic fixture; the reverse input was the actual returned 857-byte
Junos artifact. Both submissions consumed their own exact-file grants, and all
six downloaded files passed byte/hash verification.

Both jobs say **needs review**. The forward evidence has six warnings and one
manual-review item; reverse has six warnings and five manual items. Both report
partial coverage. The provider's forward OSPF analysis passed, while several
other behavior categories were inconclusive. That is useful evidence to carry
into a lab, not proof that an appliance accepted the candidate or forwarded packets.

We also ran the original source and both actual candidates through a local
Batfish engine with the same synthetic peer. All files parsed, OSPF sessions
were modeled as established, and nine modeled traffic assertions passed: both
loopback directions and an unadvertised-prefix negative control for each snapshot.
The model still found a meaningful difference: the peer's route to the converted
loopback had metric 10 in Junos versus 11 in IOS-XE. That difference stays in the
review package. Modeled reachability is useful evidence, and it does not replace
a real appliance, commit or packet test.

We then installed a real, separate minimal NetClaw. Claude invoked the guarded
NetConverter MCP and received authenticated capability discovery. Native OpenClaw
also discovers the repaired dynamic pyATS runtime, Batfish and GAIT. That exercise
caught two installer defects that fixtures had missed: the guard's Python runtime
location and a stale native pyATS revision. Both are corrected with regressions.
The original partial installation report and separate repair evidence stay visible.

The next step is now real. CML booted an IOS-XE 17.18.2 target and peer with
separate management VRFs and an isolated test link. NetClaw composed and activated
their dynamic pyATS inventory. The reviewed candidate came from the actual
NetConverter reverse conversion; its only local adaptation mapped the physical
interface name to the virtual target's Ethernet0/2. The target bootstrap contained
management access only, so the converted routing configuration had to prove itself.

Through the actual HUD and Terminal Intent, NetClaw captured a private baseline,
prepared a scoped rollback plan and obtained an API-issued, one-use apply grant.
The existing pyATS configuration tool applied the candidate. Then real device
checks and an independent peer readback established:

- OSPF **FULL** adjacency on both routers.
- Reciprocal loopback routes with the expected IOS-XE metric of **11**.
- **5/5 successful pings in each direction**.
- **0/3 pings to an unadvertised prefix**, the expected negative result.
- Management access preserved in its separate VRF, with fresh private collection.

The live exercise also improved the controls. An initial run exposed an agent
replacing the record's captured baseline with a reference note. We retained the
original configuration and flawed run, added exact-byte checks against the
collector's original artifact, reproduced the failure in a regression, and ran
a clean protected repeat from the management-only bootstrap. That repeat passed.
Native HUD loading, gateway SecretRef handling and cross-turn dynamic inventory
lifetime were also repaired and tested. These are concrete lessons from running
the whole chain through a real NetClaw.

The five-slot CML license required temporary, owner-authorized stop/start of two
existing routers, with captured baselines and restoration checks. The rehearsal
resources and failed trials are retained for inspection. No Junos image was
available, so this qualifies the IOS-XE round trip, not Junos appliance behavior.
Both hosted conversion jobs still carry their original review findings. The
fresh Border-plus-one-member installation also passed: all 26 installer effects,
required verification, an actual rendered HUD and real native delegation. The
owner explicitly requested simulated review inputs; downloads, services,
enrollment and account checks were real. No fresh human approval is implied.

This is where the value grows: conversion, simulation, validation and change
review can share the same artifacts and evidence. Faster migration work becomes
more useful when the engineer can explain exactly what was submitted, what was
applied, what passed and what still needs attention.

## A specialist member behind the Border

We also built a fresh Risk with exactly one NetConverter specialist. The Border
holds routing tools; the member owns its guarded integration, account key and
private workspace. A real Border agent delegated a discovery request, the real
member called the native NetConverter guard, and the answer came back with typed
authentication and approval evidence. The Border never needed the converter key.

That run exposed a stale local routing-port binding which tool discovery alone
had missed. We retained the failed attempt, fixed the registration order, and
repeated from empty homes. The clean run passed. The account exposed 75 qualified
operation paths—47 convert, 14 optimize and 14 validate—plus nine reads, with seven
paths still unqualified. These are discovered options, not 75 tested migrations.
Every hosted file submission still requires its own exact-file approval.

## Short community note

NetClaw + NetConverter has crossed from configuration generation into a real
virtual-router rehearsal: synthetic IOS-XE OSPF → Junos SET → IOS-XE, separately
approved uploads, a reviewed candidate applied through NetClaw's protected pyATS
route, OSPF FULL, 5/5 pings both ways and passing negative controls. Private
baselines, conversion warnings and Batfish's metric difference stay in the
evidence. This is the IOS-XE round trip; Junos appliance behavior remains
unqualified. A fresh Border with one NetConverter member now also passes real
native delegation and authenticated discovery. All 44 scoped Spec162 tasks are
complete; the installer review inputs were explicitly simulated at the owner's
request, with the actual installation and services independently verified.
[Spec162 guide](../NETCONVERTER.md).
