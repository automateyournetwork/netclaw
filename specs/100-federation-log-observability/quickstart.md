# Phase 1 Quickstart: Verifying Federation Inbound-Call Observability

**Feature**: 100-federation-log-observability
**Date**: 2026-08-06
**Input**: [spec.md](./spec.md) Success Criteria · [contracts/interfaces.md](./contracts/interfaces.md)

How to verify each fix against the running system. Follows Constitution VIII —
**observe → baseline → apply → verify** — so every claim is measured, not asserted.

> **Interpreter**: use `/usr/bin/python3` (3.14.4) explicitly for anything asserting
> asyncio behavior. The repo `.venv/` is Python 3.13.0b1 with a different `asyncio`,
> and two defects here are asyncio-behavior-dependent (research R1). Activating the
> venv is the default in a dev shell — this is a real trap.

> **Exit codes**: never read one through a pipe. `cmd | tail` reports `tail`'s status.
> Use `cmd >/dev/null 2>&1; echo $?` (CLAUDE.md — this mistake misdiagnosed spec 075).

---

## 0. Baseline — capture before changing anything

```bash
# Dead-peer noise, per 10 minutes (SC-003 needs a before/after ratio)
journalctl --user -u netclaw-mesh.service --since "10 minutes ago" --no-pager \
  | grep -cE 'open_channel to .* failed'

# Benign-disconnect tracebacks (SC-004)
journalctl --user -u netclaw-mesh.service --since "1 hour ago" --no-pager \
  | grep -c 'Error in _handle_incoming_connection'

# The stdlib TLS warning (SC-011)
journalctl --user -u netclaw-mesh.service --since "1 hour ago" --no-pager \
  | grep -c 'eof_received'

# Peers and endpoint freshness
sqlite3 -header -column ~/.openclaw/n2n/federation.db \
  "SELECT identity, state, endpoint_host, endpoint_port, endpoint_updated_at
     FROM federation_peer ORDER BY identity;"
```

Record these numbers. SC-003 (≥90% reduction) is meaningless without them.

**Back up the database before any test that writes to it:**

```bash
cp ~/.openclaw/n2n/federation.db ~/.openclaw/n2n/federation.db.bak-$(date +%Y%m%d-%H%M%S)
```

---

## 1. Apply and restart

The daemon must restart to load code changes, **and restarting drops every live
federation channel** — including any channel being watched for an inbound call. This
is an explicit, confirmed step, never incidental (plan.md "Restart sensitivity").

```bash
systemctl --user restart netclaw-mesh.service
systemctl --user is-active netclaw-mesh.service     # expect: active
journalctl --user -u netclaw-mesh.service --since "1 minute ago" --no-pager | tail -20
```

Confirm the supervisor came up and no import error was introduced:

```bash
journalctl --user -u netclaw-mesh.service --since "2 minutes ago" --no-pager \
  | grep -E 'reconnect supervisor started|Traceback'
```

---

## 2. US1 — inbound call is unmistakable (SC-001, SC-002, SC-008)

**Watch the right logger.** The 2026-08-06 observation session missed the existing
audit line because its filter matched `n2n.invocation` but not `n2n.audit` (research
R2). Watch both:

```bash
journalctl --user -u netclaw-mesh.service -f | grep -E 'n2n\.(audit|invocation)'
```

Trigger an inbound call from a peer, then verify:

- [ ] An **arrival** line appears at handler entry carrying `req=` (FR-033).
- [ ] Exactly **one** audit line follows — not two (FR-032).
- [ ] The audit line carries `req=` matching the arrival line (FR-005).
- [ ] Field order and the `AUDIT[` prefix are unchanged (§5.2 compatibility).

Join a log line to its audit row without guesswork (SC-001/002):

```bash
sqlite3 -header -column ~/.openclaw/n2n/federation.db \
  "SELECT id, direction, peer_identity, target_name, decision, outcome, request_id
     FROM remote_invocation_record ORDER BY id DESC LIMIT 5;"
```

The `req=` value must prefix-match a `request_id` above.

### Denial severity (FR-003)

Force a refusal — call a target that is not allowlisted — and confirm it is isolable
by severity alone:

```bash
journalctl --user -u netclaw-mesh.service --since "5 minutes ago" -p warning --no-pager \
  | grep 'AUDIT\['
```

- [ ] The denial appears at `WARNING` in a `-p warning` view.
- [ ] A successful call does **not** appear in that view.

### Secrets (FR-007)

```bash
journalctl --user -u netclaw-mesh.service --since "10 minutes ago" --no-pager \
  | grep -iE 'token|secret|password|BEGIN (RSA |EC )?PRIVATE KEY' | grep 'AUDIT\['
```

- [ ] Returns nothing.

---

## 3. US2 — dead peer stops drowning the log (SC-003, SC-005, SC-006, SC-012)

### Noise reduction (SC-003, ≥90%)

Let the daemon run long enough to span several retry intervals — at least 30 minutes
with a dead peer configured — then compare against §0:

```bash
journalctl --user -u netclaw-mesh.service --since "30 minutes ago" --no-pager \
  | grep -cE 'open_channel to .* failed|unreachable:'
```

- [ ] At least 90% below the §0 rate, normalized to the same window length.
- [ ] Each summary states attempt count and period (FR-009), e.g.
      `14 failures in 5m0s`.
- [ ] With N dead peers, at most N summary lines per interval (FR-016).

### Transient failure is not penalized (SC-005, FR-012)

Stop a healthy peer's listener briefly, then restore it within one backoff interval:

- [ ] Reconnects no later than it does today — the first few failures keep the 5 s→60 s
      ramp and are logged per-attempt.
- [ ] The peer never reaches `dampened` on a single transient blip.

### Flapping does not defeat dampening (SC-012, FR-031)

The critical case — research R3 found the current wholesale reset makes flapping
bypass dampening entirely. Drive a peer to connect and drop repeatedly:

- [ ] `attempts` does **not** return to `0` on each brief connect.
- [ ] The peer stays `dampened` and summarized; log volume stays bounded.
- [ ] Dampening clears only after the channel stays up ≥ `STABLE_AFTER_S` (120 s).

### Re-registration resets immediately (SC-006, FR-013)

With a peer dampened at the 900 s ceiling, have it re-register an endpoint:

```bash
watch -n2 'sqlite3 ~/.openclaw/n2n/federation.db \
  "SELECT identity, endpoint_updated_at FROM federation_peer WHERE identity=\"<ident>\";"'
```

- [ ] Reconnects within **seconds** of `endpoint_updated_at` changing, not after 15 min.
- [ ] A peer that becomes reachable *without* re-registering resumes within ~15 min.

### Health stays observable while dampened (FR-014)

```bash
curl -s localhost:8179/n2n/health | python3 -m json.tool
```

- [ ] The dampened peer still reports `state`, `attempts`, `next_retry_at`, `last_seen`.
- [ ] `dampened` is present and additive — no existing field renamed or retyped.

### Master disable restores verbose reporting (SC-010, FR-028)

```bash
# in ~/.openclaw/mesh.systemd.env
N2N_RECONNECT_DAMPEN=0
systemctl --user restart netclaw-mesh.service
```

- [ ] Per-attempt `WARNING` returns, ceiling back to 60 s, no summaries — byte-for-byte
      today's behavior.

---

## 4. US3 + FR-030/038 — benign disconnects (SC-004, SC-011)

### Zero-byte connect (SC-004, FR-017)

```bash
# connect and immediately close, sending nothing
python3 -c "import socket; socket.create_connection(('127.0.0.1', 1179)).close()"
journalctl --user -u netclaw-mesh.service --since "1 minute ago" --no-pager | tail -5
```

- [ ] **Exactly one** log line.
- [ ] **No** stack trace.
- [ ] Names the source and the reason.

### Truncated preamble (FR-017)

```bash
python3 -c "
import socket
s = socket.create_connection(('127.0.0.1', 1179)); s.sendall(b'N'); s.close()"
```

- [ ] One low-severity line, no traceback.

### Complete-but-invalid magic still errors (FR-018)

```bash
python3 -c "
import socket
s = socket.create_connection(('127.0.0.1', 1179)); s.sendall(b'NXXXX'); s.close()"
```

- [ ] Still a one-line `WARNING` (`Invalid N-magic`) — the existing convention at
      `agent.py:307` is preserved, not swallowed.

### Unexpected faults still produce tracebacks (FR-019)

This is the regression that matters most — the narrow catch must not widen the
catch-all and start hiding real bugs.

- [ ] `Error in _handle_incoming_connection` with `exc_info` still fires for a genuine
      internal fault. Verify by unit test rather than by breaking the daemon.

### HTTP probe against the edge listener (FR-038)

```bash
curl -s -m 3 http://localhost:<edge-port>/ >/dev/null 2>&1; echo $?
```

- [ ] No error-level traceback.
- [ ] Repeated probes collapse into a periodic summary.
- [ ] A genuine enrolled-device connection failure is still visible and distinguishable.

### TLS `eof_received` warning (SC-011, FR-030)

Open and close a secure channel, then:

```bash
journalctl --user -u netclaw-mesh.service --since "5 minutes ago" --no-pager \
  | grep -c 'eof_received'          # expect 0
journalctl --user -u netclaw-mesh.service --since "1 hour ago" --no-pager \
  | grep -c '\[asyncio\]'           # other asyncio warnings must still pass
```

- [ ] Zero `eof_received` lines.
- [ ] The filter did **not** silence the `asyncio` logger wholesale (FR-030).

---

## 5. US4 — endpoint retirement (SC-007, FR-021..026)

**Back up the database first** (§0).

```bash
# Via the MCP tool (the supported path — zero SQL, FR-026)
#   n2n_forget_endpoint(peer="as65099-10.255.255.1")

# Or the route directly:
curl -s -X POST localhost:8179/n2n/peers/forget-endpoint \
  -H 'Content-Type: application/json' \
  -d '{"peer":"as65099-10.255.255.1","actor":"operator"}' | python3 -m json.tool
```

- [ ] Returns the prior endpoint in `previous` (reversible by hand).
- [ ] Calling it twice succeeds — idempotent, `forgotten: false` the second time.
- [ ] Unknown peer → `404`.

Confirm the peer is otherwise untouched (FR-022):

```bash
sqlite3 -header -column ~/.openclaw/n2n/federation.db \
  "SELECT identity, state, chat_enabled, trust_model, pinned_fp, endpoint_host,
          endpoint_port, endpoint_updated_at
     FROM federation_peer WHERE identity='as65099-10.255.255.1';"
```

- [ ] `endpoint_host`, `endpoint_port`, `endpoint_updated_at` all cleared **together**.
- [ ] `state`, `chat_enabled`, `trust_model`, `pinned_fp` unchanged.
- [ ] Audit history for the peer still present.

Dialling and recovery:

- [ ] Supervisor stops dialling within seconds, no restart needed (FR-023) — the
      supervisor re-reads `list_peers()` every 2 s.
- [ ] A live channel to that peer, if any, keeps running (research R7 resolution).
- [ ] Re-registration restores dialling with no operator action (FR-024).

Attribution (FR-025):

```bash
sqlite3 -header -column ~/.openclaw/n2n/federation.db \
  "SELECT peer_identity, decision, outcome, gait_ref FROM remote_invocation_record
     ORDER BY id DESC LIMIT 3;"
git -C ~/.openclaw/n2n/gait log --oneline -3
```

- [ ] The retirement is recorded and attributable, with a GAIT commit.

---

## 6. Regression guards (FR-001/002/004/006, SC-009)

These four were **already satisfied** before this feature (research R2). Their only
risk is being lost while enriching the same line.

- [ ] Every inbound call still logs peer identity and requested target (FR-001).
- [ ] Authorization decision still distinguishes granted from denied (FR-002).
- [ ] Terminal outcome still recorded, including failures and cancellations (FR-004).
- [ ] A newly created pending approval is still visible at creation (FR-006).
- [ ] Audit completeness unchanged (SC-009): for a given call, every column populated
      before is populated now.

```bash
/usr/bin/python3 -m pytest tests/n2n/ -q
```

---

## 7. Constitution XI artifact check

```bash
python3 scripts/reconcile-mcp.py >/dev/null 2>&1; echo $?     # must be 0
grep -c 'N2N_RECONNECT_' .env.example                         # must be >= 9 (3 existing + 6 new)
grep -c 'n2n_forget_endpoint' TOOLS.md                        # must be >= 1
grep -c '@mcp.tool' mcp-servers/n2n-mcp/server.py             # must be 39
```

CI runs `reconcile-mcp.py` and fails the merge on non-zero (CLAUDE.md).
