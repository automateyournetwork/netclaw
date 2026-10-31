# From a converted configuration to a migration you can test

*Spec162 development update, refreshed 2026-10-31. Two real synthetic
conversions completed with review findings. Live appliance acceptance remains open.*

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

Actual CML discovery found IOS-XE 17.18.2 images and an active evaluation license,
but no installed Junos image. Capacity, isolated management, the real protected
apply runtime and actual commit/readback still need qualification. Four existing
lab devices supplied identity observations and remain unchanged.

The remaining appliance demonstration is concrete: preserve the actual returned
candidate and every reviewed interface adaptation, boot a compatible target,
then test FULL adjacency, route/next hop, positive traffic, a negative control
and management continuity. A reverse-converted IOS-XE rehearsal would test the
round trip; it would not establish Junos runtime acceptance.

This is where the value grows: conversion, simulation, validation and change
review can share the same artifacts and evidence. Faster migration work becomes
more useful when the engineer can explain exactly what was submitted, what was
applied, what passed and what still needs attention.

## Short community note

NetClaw has now used NetConverter for real synthetic IOS-XE OSPF → Junos SET →
IOS-XE conversions, with separate exact-file approvals and verified downloads.
The integration carries review findings and private artifacts into the existing
lab, pyATS, Batfish and change-review workflows. Both real jobs remain needs
review; live target application and forwarding tests are still open. This is a
concrete step toward turning migration candidates into testable engineering
work, with the remaining gaps visible. [Spec162 guide](../NETCONVERTER.md).
