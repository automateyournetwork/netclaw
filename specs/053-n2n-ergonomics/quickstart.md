# Quickstart: N2N Ergonomics & Reliability (053)

**Feature**: 053-n2n-ergonomics
**Cast**: John (AS65001), Nick (AS65007), Byrn (AS65099) — the live mesh.
Prereq: all three on 053, `N2N_ENABLED=true`, daemons running.

## 1. Async delegation — clone a CML lab over N2N (US1, the headline)

John: *"Have Nick's claw recreate my NetClaw-Full-Topo lab in his CML."*
- `n2n_delegate(peer="as65007-7.7.7.7", target_type="skill",
  target_name="cml-lab-lifecycle", input_text="<build spec>")` → returns
  `task_id` in ~2 s.
- Nick's claw builds in the background; John's claw polls `n2n_task_status` and
  shows progress ("nodes 4/10 … links 12/12 … configs pushed … OSPF up").
- `n2n_task_result(task_id)` → the finished lab summary.
- The channel can drop and reconnect mid-build; the task keeps running and the
  result is still retrievable (FR-004).

**Verify**: total build time ≫ any single-call timeout, yet it completes with
zero "Connection lost" (SC-001).

## 2. Self-heal across a peer restart (US2)

Nick restarts his daemon (deploy/crash). Do nothing.
- John's reconnect supervisor detects the dead channel (missed heartbeats),
  re-dials with backoff, re-runs `hello`, and federation is restored from
  persisted consent — **no manual re-dial**.
- **Verify**: within 60 s of Nick's daemon coming back, a query to Nick succeeds
  again (SC-002).

## 3. Endpoint moves, nobody swaps host:port (US3)

Nick's restart gave him a new ngrok endpoint.
- Nick's claw sends `n2n/endpoint_update` to John over the live session; John
  updates Nick's endpoint record and the supervisor re-dials the new address.
- **Verify**: federation re-establishes with zero manual endpoint exchange
  (SC-003). No more "send me your new host:port" in Slack.

## 4. Different builds just work (US4)

John's build has `--session-key`+`--session-id`; Nick's has only `--session-id`;
replies differ (`payloads` vs `finalAssistantVisibleText`).
- At `hello`, each learns the other's capability descriptor; each responder uses
  its own probed agent flag + tolerant reply parsing.
- **Verify**: delegated chat/skill succeed both directions with no flag/shape
  error (SC-004). A pre-053 peer still federates at 052 behavior (FR-016).

## 5. Health at a glance (US6)

- `n2n_health()` or the HUD claw node shows, per peer: channel up/reconnecting/
  unreachable, last-seen, endpoint freshness, and any in-flight tasks with
  progress.
- New peer setup: `n2n_connect(peer, host, port)` then `n2n_trust(peer,
  tools=[...], chat=true)` — two calls instead of five.
- **Verify**: federate a fresh peer in < 2 min and see accurate live health
  (SC-006).

## 6. Robustness (US5) — mostly invisible, always tested

- A long op never lost to a client giving up early (client 610 s > server
  300/600 s).
- A reply with a trailing `[agent] run … stop` log line still parses clean.
- A segmented request body is read whole; missing fields → clear typed error.
- **Verify**: `pytest tests/n2n/test_robustness.py` — each asserts the fix and
  fails against pre-053 behavior (SC-008).

## Soak (SC-007)

Run the 3-claw mesh 24 h with ≥3 peer restarts / endpoint changes; federation
self-heals every time with no manual re-dial and no lost task results.
