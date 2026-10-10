---
title: "Good news for Hermes users!"
date: "2026-10-10"
path: "/netclaw/good-news-for-hermes-users/"
description: "NetClaw 1.8.0 brings protected Hermes federation and Mobile Ask Border together, following the shared HUD work in 1.7.0. Five diagrams explain the design and its tested boundaries."
image: "/images/hermes-1-8/01-netclaw-harness-choice.webp"
topics:
  - NetClaw
  - AI
  - Network automation
  - MCP
draft: false
---

**Good news for Hermes users: NetClaw now connects the Hermes HUD, federation, and mobile conversation into the same engineering story.** 🦞

The source version moves from **1.7.0 to 1.8.0**. Two specifications explain the change: spec148 connected Hermes to the shared NetClaw HUD, and spec149 adds protected Hermes execution to NCFED, our NetClaw-to-NetClaw Federation protocol. Hermes can be a Border or a scoped member, with its own selected home, model and state.

I wanted a Hermes-based Risk—a group of NetClaws—to work without installing OpenClaw just to make its members useful. I also wanted the phone already in my pocket to reach that Hermes Border. That meant working through execution, authorization, ownership and recovery, not stopping when two agents exchanged a capability card.

The 1.8.0 implementation is available for review in PR #291; it has not been merged into `main` at publication. The changes are in [the spec148 HUD PR, #290](https://github.com/automateyournetwork/netclaw/pull/290) and [the spec149 federation/mobile PR](https://github.com/automateyournetwork/netclaw/pull/291). The [1.8.0 release notes](https://github.com/automateyournetwork/netclaw/blob/149-hermes-ncfed-federation/docs/releases/1.8.0.md) and [updated README](https://github.com/automateyournetwork/netclaw/blob/149-hermes-ncfed-federation/README.md) describe the supported setup.

## Choose the harness that fits your deployment

NetClaw already runs on OpenClaw or Hermes. The work in 1.7.0 brought Hermes into shared HUD Chat, Canvas, local Avatar and owned conversation history through an authenticated private MCP bridge and a protected companion.

That companion uses the selected Hermes home and configured model. It keeps its state separate from other installations and from the ordinary Hermes gateway. The first qualified execution path is deliberately concrete: the installed subnet skill and the real, read-only IPv4 subnet calculator.

<figure><img src="/images/hermes-1-8/01-netclaw-harness-choice.webp" alt="OpenClaw and Hermes as alternative NetClaw harnesses, with their own runtime strengths and a shared networking layer" width="1672" height="941"/><figcaption>Harness choice describes the broader runtime ecosystem. Native Hermes memory and tools are not automatically enabled inside NetClaw’s protected federation profile.</figcaption></figure>

## A Border and its members can use different runtimes

A Border coordinates a Risk. Internal NCFED, or iN2N, connects that Border to its members. External NCFED, or eN2N, connects independently operated peers through the existing consent, identity and grant controls.

Spec149 gives Hermes a protected receiver path and a bounded operator path. A remote peer can request permitted work; it cannot turn its message into local operator authority. A local operator can discover capabilities, delegate permitted subnet work and retrieve the owned result. Enrollment and the existing NCFED method names remain in place.

<figure><img src="/images/hermes-1-8/02-mix-and-match-federation.webp" alt="All-OpenClaw, all-Hermes and mixed Border/member arrangements connected by iN2N and eN2N" width="1672" height="941" loading="lazy"/><figcaption>The runtime combinations are the design target. The verification record identifies which journeys actually ran; capabilities still require explicit qualification and authorization.</figcaption></figure>

There is a useful distinction between *installed*, *advertised* and *qualified to execute*. A long MCP catalogue does not make every integration safe to expose to every peer. This release qualifies subnet calculations from `/24` through `/30`, the corresponding skill, isolated peer conversation and the bounded federation operations needed to reach them.

## Carry the harness in the capability card

A NetClaw should be able to tell you which harness it runs alongside its model and capabilities. The optional harness metadata carries a type, a version when known, and its source and observation information.

Older peers can omit it. The UI then says **unknown**. It does not assume OpenClaw, invent a version, or turn a peer’s claim into a local execution choice. The HUD and the mobile Summary page can show the Border’s type alongside the information an operator already uses to understand it.

<figure><img src="/images/hermes-1-8/04-capability-card-harness-identity.webp" alt="A NetClaw capability card with harness identity, model, tools and provenance, with metadata separated from authorization" width="1672" height="941" loading="lazy"/><figcaption>“Runs Hermes” is useful descriptive information. It is not a grant, an approval or proof of an execution result.</figcaption></figure>

## Ask a Hermes Border from NetClaw Mobile

Authenticated mobile requests now enter the protected Hermes runtime with an explicit operator execution scope. That scope retains the installation, enrolled device and key-generation ownership. Text conversations can use permitted internal and external delegation, report progress and return results through the existing task methods.

Voice transcription remains text input. Siri retains its `origin: voice` behavior so the response can be composed for spoken delivery. The app’s Summary page adds the Border type, version, model and advertised capabilities, with unknown and last-received information labeled honestly.

The mobile candidate is **1.0.3 (build 6)**. The signed Apple archive includes the app, Watch app and Live Activity extensions. Apple accepted build 6 for processing on October 10. Final processing completion and tester availability were not observed; this article does not announce a public App Store release.

**Hermes photo, video and audio-file attachments are unavailable in this release.** The app and backend explicitly refuse that path before protected execution. Voice-transcribed text is supported. The existing OpenClaw attachment behavior has regression coverage, but that is not a claim that every camera, microphone or device combination was physically tested today.

## A disconnected phone must not duplicate work

A lost response does not tell us whether an operation happened. The app now saves its request identifier before sending. On reconnect, it asks about the original admission and retrieves the owned result. It does not submit the same uncertain operation again.

That distinction also applies to cancellation. “Cancellation requested” means the stop was requested; “cancelled” means it was confirmed. Interrupted and unknown outcomes are visible in Chat, Siri, Watch and Live Activity instead of remaining silent spinners.

<figure><img src="/images/hermes-1-8/05-request-to-verified-result.webp" alt="An authenticated request passes scope and policy checks, executes through protected tools, records evidence and returns a verified result, with explicit uncertain recovery" width="1672" height="941" loading="lazy"/><figcaption>The acceptance model follows a request through execution and evidence. A companion crash after dispatch remains uncertain until owned evidence resolves it; restart does not replay the request.</figcaption></figure>

The process-fault test was especially useful: it caught an upstream queued receipt surviving after its worker had died. The fix makes that uncertainty explicit. That is the kind of detail I want the tests to catch before a phone tells someone their work is still running.

## Where this could lead for managed services

A Border per customer or operational domain is an interesting direction for managed service providers. Different Risks could use different harnesses and models while sharing a federation protocol.

<figure><img src="/images/hermes-1-8/03-msp-multitenant-architecture.webp" alt="Proposed managed service provider architecture with separate customer Risks, Borders, members and explicit tenant boundaries" width="1672" height="941" loading="lazy"/><figcaption>This is a proposed architecture, not a claim of shipped multi-tenant isolation. eN2N alone does not provide a complete MSP security boundary.</figcaption></figure>

Tenant credentials, storage, grants, operational approvals and failure handling would all need their own isolation and acceptance evidence. The diagram is a way to discuss that work, not permission to skip it.

## What the evidence says

All four internal runtime pairs—Hermes/Hermes, Hermes/OpenClaw, OpenClaw/Hermes and OpenClaw/OpenClaw—returned real subnet results in separate processes. Bidirectional Hermes/OpenClaw external tool, skill and contextual-chat exchanges passed as well.

The acceptance work runs the actual pinned Hermes agent and real subnet MCP tool against a controlled local provider, through authenticated local NCFED connections. It covers mobile admission and ownership, voice origin, permitted delegation, results, reconnect and cancellation. The release also runs the existing shared federation/OpenClaw mobile regressions, Flutter tests and analysis, HUD tests and builds, and installer/preservation checks.

The [spec149 verification record](https://github.com/automateyournetwork/netclaw/blob/149-hermes-ncfed-federation/specs/149-hermes-ncfed-federation/verification.md) is the authority for exact counts, runtime pairs, build/upload receipts and remaining work. Mac protocol execution and a signed iOS build do not establish physical iPhone, iPad, Watch, Siri, Android or fresh Linux/WSL acceptance. Spec148’s earlier Mac/WSL HUD evidence keeps its original scope. Hermes production model-guard/confinement remains unavailable and fails closed.

This was spec-driven work: expand the specification, update the plan and tasks, analyze the contracts, implement, and test the behavior those contracts promise. The result is a much more useful Hermes path through NetClaw—and a clearer account of what it can actually do.

**Explore the work:** [NetClaw](/netclaw/) · [Hermes federation and mobile setup](https://github.com/automateyournetwork/netclaw/blob/149-hermes-ncfed-federation/docs/HERMES-FEDERATION.md) · [1.7.0 HUD history](https://github.com/automateyournetwork/netclaw/blob/main/docs/releases/1.7.0.md) · [Latest](/latest/)
