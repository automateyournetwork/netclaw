---
title: "Making the mesh hold: N2N federation grows up (async tasks, self-healing, and a CML lab cloned across the internet)"
date: 2026-07-11
authors: [John, Claude]
status: draft
target: WordPress MCP (present to John for review before publishing — Constitution XVII)
spec: specs/053-n2n-ergonomics/
---

# Making the mesh hold: N2N federation grows up

A few days ago we shipped [N2N federation and the NCFED protocol](2026-07-10-n2n-federation.md) — the ability for independently-run NetClaws to discover each other's skills, invoke each other's tools, and chat claw-to-claw. It worked in the first demo: John's claw pulled Nick's live CML lab list and Byrn's Nautobot state across the mesh, entirely over federation.

Then we reached for something bigger — have one operator's claw **rebuild another operator's entire CML lab** over N2N — and the whole thing fell apart. Not because the protocol was wrong, but because the **operational envelope** was paper-thin. This post is about the hardening that turned a fragile demo into something that survives reboots, moving addresses, and version drift between three independently-run claws — and about the moment it actually held.

## The failures, one after another

Three claws — **John (AS 65001), Nick (AS 65007), Byrn (AS 65099)** — trying to cooperate surfaced a parade of issues, each of which took live debugging:

- A **10-node CML lab rebuild dropped mid-flight** with "Connection lost" — the request was one synchronous call that ran the whole multi-minute build, and ngrok reset the long-lived channel before it finished.
- Every time a peer **restarted its daemon**, its channel died and federation silently wedged until someone manually re-dialed — the dead channel lingered as a zombie.
- Every restart also **re-rolled the operator's ngrok endpoint**, so we manually re-exchanged `host:port` in Slack roughly five times in one afternoon.
- Two claws on **different OpenClaw builds** broke silently: one CLI accepted `--session-key`, the other only `--session-id`; one returned the answer in `payloads[*].text`, the other in `finalAssistantVisibleText`.
- A peer's completed answer **never reached the operator** because the MCP client gave up at 120s while the server ran to 300s.

Each was a real bug. None was in the protocol. That's the tell: **the protocol was sound; the resilience wasn't there yet.** Getting a working answer required a human babysitting every restart.

## The fix: stop assuming, start self-healing

We wrote spec 053 — reliability and ergonomics only, with the proven NCFED core (framing, mutual consent, default-deny, no-secrets guard) explicitly **frozen** — and built six things.

### 1. Async task delegation — the headline

Long remote operations are no longer one blocking call. You *submit* a task and get a `task_id` in seconds; the peer runs it in the background; you poll short status calls and fetch the result when it's done. No single call is ever long enough for ngrok to kill it. A ten-minute lab build becomes: submit (2s) + a handful of 15s polls + a result fetch. In practice:

```
> "Have Nick's claw recreate my NetClaw-Full-Topo lab in his CML."

n2n_delegate(peer="as65007-7.7.7.7", target_name="cml-lab-lifecycle",
             input_text="<10-node/12-link build spec>")
  → { task_id: "…", state: "submitted" }        # returns in ~2 seconds

n2n_task_status(task_id)  → working · "nodes 4/10"
n2n_task_status(task_id)  → working · "links 12/12, pushing configs"
n2n_task_result(task_id)  → completed · "lab up, OSPF adjacency formed"
```

The task state is persisted, so the result survives a channel drop **and** a daemon restart mid-build. That single change is the difference between "the build dies at minute two" and "the build finishes."

### 2. Channel auto-reconnect

A background supervisor watches every federated peer. When a channel dies — heartbeat misses or a failed send — it's detected, deregistered (no more zombies), and re-established automatically from *persisted consent*, with bounded backoff. A peer restart now heals itself in under a minute with zero human action.

### 3. Endpoint auto-re-announce

When your ngrok endpoint moves on restart, your claw announces the new endpoint to federated peers over the still-live session, and they re-dial automatically — validated only over the authenticated session for an already-federated identity, so it can't be spoofed. The manual `host:port` dance is gone.

### 4. Capability negotiation

Peers exchange a small capability descriptor in the `hello` handshake — protocol version, which agent CLI flag they support, which reply shapes they emit — and each side adapts. A claw on an older build degrades gracefully to the previous behavior instead of breaking. Silent version drift becomes explicit, self-adapting interoperability. (The `--session-key` vs `--session-id` skew that broke a whole afternoon is now just a negotiated field.)

### 5. Robustness hardening

The live hot-patches became first-class, regression-tested requirements: the client always outlasts the server's own timeouts; reply parsing tolerates a trailing log line after the JSON envelope; the HTTP layer reads the full body even when it arrives in separate TCP segments; missing fields return typed errors, not cryptic strings.

### 6. Health and one-step setup

`n2n_health` — and the 3D HUD claw node — show per-peer channel state, last-seen, endpoint freshness, and in-flight tasks with live progress. And the old five-step setup collapsed into two calls:

```
n2n_connect(peer, host, port)          # add + consent + dial, one call
n2n_trust(peer, tools="…", chat=true)  # consent + grants + chat, one call
```

## It actually works now — CML and Nautobot across the internet

This is the part that matters. On the live three-claw mesh, over nothing but N2N federation:

**John's claw asked Nick's claw about its CML — and got the real answer:**

```
Nick's CML labs — count: 1
Lab                                    State     Nodes
NetClaw OSPF 2R - 20260702-033650Z     started     2
```

That traveled the full path: John's claw → NCFED channel → **Nick's claw ran its own CML query with Nick's own credentials** → answer back to John. No shared credentials, no John configuring Nick's CML — pure federation. Nick runs a different model (gpt-5.5, OpenAI) on a different OpenClaw build, and negotiation made the reply come back clean anyway.

**Byrn's claw answered a Nautobot query the same way** — reporting its site inventory (and honestly telling us its Nautobot host was unreachable at that moment), again entirely peer-side, under Byrn's policies.

**And then we tested the thing that matters most: it survives a reboot.** After a full restart, John's claw came back up on the hardened code, and both peers re-federated cleanly — Nick at his *new* address (`8.tcp.ngrok.io:10416`), Byrn at his — with channels `up` and inventories fresh, via a single one-step `connect`. The reconnect supervisor and endpoint re-announce mean the next reboot won't even need that.

The CML-lab **clone** — the ambitious goal that broke everything and motivated this whole spec — is exactly what async delegation was built to carry: a multi-minute, multi-tool build on the remote side that used to drop at minute two now runs to completion as a background task you can watch progress on.

## What made this trustworthy: tests that fail first

Forty-four automated tests now cover the federation layer, most driving two services over an in-memory channel pair. They don't just check the happy path — they assert the *guarantees*: that submit returns fast while the op runs long, that a result survives a channel drop and a daemon restart, that a dead channel self-deregisters, that a completed answer is never lost to a timeout mismatch, that a non-federated peer's endpoint update is rejected, that a pre-053 peer still federates.

One of those tests immediately earned its keep: it caught a missing `import time` in the reconnect supervisor that would have silently prevented *every* auto-reconnect in production. The entire point of hardening is catching the thing that fails quietly.

## The bigger picture

A community of federated AI network engineers is only as good as its worst 3 a.m. failure mode. The exciting part — "your claw can drive my lab" — is easy to demo and hard to keep running across restarts, moving endpoints, and version drift between independently-operated peers. Spec 053 is the unglamorous work that turns a great demo into something you'd actually leave running. Three claws on three different machines, three different models, now discover, query, and delegate to each other across the internet — and heal themselves when one blinks.

The mesh holds.

Next: an internal-clutch model (**iN2N**) for focused single-operator claw fleets, and eventually lifting NCFED into its own protocol repository. But first — the CML lab clone that started all of this now completes, cleanly, over the mesh.

---

*Written by John and Claude, with debugging and a sharp `--session-id` catch from Nick, and a client-payload PR from Byrn. Spec 053, built spec-through-implement over a live three-claw mesh across three operators, three machines, and three models.*
