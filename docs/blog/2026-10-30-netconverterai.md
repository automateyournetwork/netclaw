# From a converted configuration to a migration you can test

*Staged Spec162 article. The integration is in development; real NetConverter
account conversion and Junos-target acceptance remain pending. Not published.*

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

Four local lab devices have returned actual identity/version observations. That
does not establish an OSPF source configuration or a successful migration. My
NetConverter account is awaiting enablement, and the licensed Junos image,
management path and live commit/readback still need qualification.

The planned live demonstration is concrete: collect a synthetic IOS-XE OSPF
source, run the approved NetConverter conversion, preserve the original and any
interface adaptations, boot a Junos target, and test FULL adjacency, route/next
hop, positive traffic, a negative control and management continuity. Its results
will be added only after those operations actually run.

This is where the value grows: conversion, simulation, validation and change
review can share the same artifacts and evidence. Faster migration work becomes
more useful when the engineer can explain exactly what was submitted, what was
applied, what passed and what still needs attention.

## Short community note

We're building NetConverter integration into NetClaw: supported conversion workflows,
exact-file approval, private artifacts, and a path to create and test real virtual
migration targets with the existing lab and validation tools. The controlled MCP,
installer and governance tests are passing. Our planned IOS-XE→Junos OSPF demo is
waiting on account activation and target-image qualification; we won't label it
tested until it runs. The goal is to carry a migration from source configuration
through a reviewed candidate to observed behavior and an evidence-backed change
proposal. [Spec162 guide](../NETCONVERTER.md).
