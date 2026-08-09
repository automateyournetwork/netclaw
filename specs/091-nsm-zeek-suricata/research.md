# Phase 0 Research — NSM: Zeek + Suricata (reconstruction)

**Date of work**: 2026-08-04 | **Reconstructed**: 2026-08-05 | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Assembled after merge from `spec.md`, the delivered server and its tests. The
> two silent wrong answers below were reproduced live **before** the server was written; only this
> write-up is retrospective.

---

## R1 — What is actually missing?

**Decision**: The NSM layer, not packet decode.

`packet-buddy-mcp` already covers packet-level decode (12 tools: summary, protocol hierarchy,
conversations, endpoints, display filters, packet detail, expert info). It is *skill-bundled*,
invoked via `MCP_CALL` from `packet-analysis`, not a registered server.

What was absent: **session reconstruction, protocol metadata, signature alerting**. `nsm-mcp`
composes with `packet-buddy-mcp` rather than replacing it, and the latter was audited and left
alone.

---

## R2 — Which engines, and adopt or build?

**Decision**: Zeek + Suricata, **built**.

| Candidate | Verdict |
|---|---|
| **Zeek 8.2.1** | adopted as an engine — session/protocol metadata |
| **Suricata 8.0.6** | adopted as an engine — signature alerting |
| **Arkime** | **rejected** — mandatory OpenSearch/Elasticsearch cluster, ~12–16 GB. A platform to operate, not a tool to call |
| A thin community wrapper | **rejected** — none carries provenance, and a thin wrapper passes both traps through unqualified |

---

## R3 — Silent wrong answer #1: Suricata with no ruleset alerts on nothing

Measured on a five-packet fixture built byte by byte:

```
W: detect: No rule files match the pattern /var/lib/suricata/rules/suricata.rules
W: detect: 1 rule files specified, but no rules were loaded!
0 signatures processed
```

| Config | Signatures | Alerts |
|---|---|---|
| Stock | **0** | **0** |
| After `suricata-update` | **52,205** | 4 on the fixture |

Two **non-fatal** warnings, **exit 0**, and an `eve.json` full of dns/flow events so the output
looks healthy. An analyst reads "0 alerts" as "clean traffic". The detector inspected nothing.

**Consequences**: FR-004 (an empty alert list from a 0-signature detector is wrapped with
`NOT_A_CLEAN_RESULT`) and FR-008 (the installer fetches a ruleset and warns explicitly if it cannot).

---

## R4 — Silent wrong answer #2: Zeek discards invalid-checksum packets by default

| Mode | `http.log` | `conn.log` rows |
|---|---|---|
| Zeek default (validating) | **absent** | 3 — *wrong* |
| `-C` / `ignore_checksums=true` | present | 2 — correct |

The HTTP GET was **completely invisible** in the default run. Worse, `conn.log` was also *wrong* —
3 rows rather than 2, because discarded packets fragment the flow. **The default output is not
merely incomplete; it misreports what it does show.** The only signal is a warning on stderr.

**This is not exotic.** NICs with checksum offloading routinely produce such captures — **including
the ones NetClaw's own `cml-packet-capture` and `gns3-packet-capture` skills produce.** NetClaw
would have been analysing its own captures wrongly by default.

**Independent corroboration**: with ET Open loaded, Suricata fires `SURICATA TCPv4 invalid checksum`
(sid 2200074) on the same packets Zeek silently dropped — two tools agreeing about the fixture from
opposite directions.

**Consequence**: FR-005 — `ignore_checksums` defaults to `true`, opposite to Zeek's own default, and
the mode used is reported on every response.

---

## R5 — How do you stop a hazard being forgotten?

**Decision**: A chokepoint that raises, not a documented convention.

`envelope.emit()` raises `PostureError` when a response would carry an alert verdict without
Suricata's signature count, or Zeek findings without the checksum posture. No code path omits it.

The guard must also **not cry wolf**: an `ARMED` detector reporting no alerts is *not* wrapped. A
guard that fires on correct results trains people to ignore it.

---

## R6 — Containers or host packages?

**Decision**: Containers, digest-pinned — and it was not a preference.

`zeek` has **no apt candidate** on Ubuntu 26.04; `suricata` needs root to install. Digest pinning
additionally prevents a security tool's analysis changing under the operator silently, which is
worse than being stale.

---

## R7 — Session pivot: exact or heuristic?

**Decision**: Exact, by Zeek `uid`. Every protocol log shares `uid` with `conn.log`, so the pivot is
a join rather than a guess (FR-007).

---

## R8 — Input validation

**Decision**: An absent, empty, or directory input **raises**. Returning an empty analysis would be
indistinguishable from a capture containing nothing — the same absence-versus-evidence confusion the
rest of the feature exists to prevent (FR-006).
