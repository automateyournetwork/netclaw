# Spec 091 — NSM: Zeek + Suricata offline PCAP analysis (R13)

**Status**: implemented
**Branch**: `091-nsm-zeek-suricata`
**Date**: 2026-08-04
**Roadmap**: R13 — NSM / IDS

## Summary

NetClaw could decode packets (`packet-buddy-mcp`, tshark, 12 tools) but had **no
network-security-monitoring layer at all**: no session reconstruction, no protocol metadata,
no signature alerting.

`nsm-mcp` adds both, read-only, over a capture file already on disk: **Zeek 8.2.1** for
session and protocol metadata and **Suricata 8.0.6** for signature alerting. **6 tools,
~934 tokens** of the 5,000 ceiling.

The spec's substance is not the wiring — it is that **both tools have a failure mode where
they run successfully, exit 0, and tell you nothing while looking like they told you
everything.** Both were reproduced live before a line of the server was written, and the
server is built so neither can reach an operator unqualified.

## The two silent wrong answers

Measured against `tests/nsm/fixtures/checksum-offload.pcap`, a five-packet capture built byte
by byte so the result is deterministic and needs no network.

### 1. Suricata with no ruleset alerts on nothing

```
W: detect: No rule files match the pattern /var/lib/suricata/rules/suricata.rules
W: detect: 1 rule files specified, but no rules were loaded!
0 signatures processed
```

| Config | Signatures | Alerts |
|---|---|---|
| Stock | **0** | **0** |
| After `suricata-update` | **52,205** | 4 on the fixture |

Two **non-fatal** warnings, exit 0, and `eve.json` full of dns/flow events so the output looks
healthy. An analyst reads "0 alerts" as "clean traffic". The detector inspected nothing.

### 2. Zeek discards invalid-checksum packets by default

| Mode | `http.log` | `conn.log` rows |
|---|---|---|
| Zeek default (validating) | **absent** | 3 — *wrong* |
| `-C` / `ignore_checksums=true` | present | 2 — correct |

The HTTP GET was **completely invisible** in the default run. Worse, `conn.log` was also
*wrong* — 3 rows rather than the correct 2, because discarded packets fragment the flow. So
the default output is not merely incomplete, it misreports what it does show. The only signal
is a warning on stderr.

**This is not an exotic case.** NICs with checksum offloading routinely produce such captures
— **including the ones NetClaw's own `cml-packet-capture` and `gns3-packet-capture` skills
produce.** NetClaw would have been analysing its own captures wrongly by default.

Independent corroboration: with the ET Open ruleset loaded, Suricata fires
`SURICATA TCPv4 invalid checksum` (sid 2200074) on the same packets Zeek silently dropped.
Two tools agreeing about the fixture from opposite directions.

## Requirements

- **FR-001** Run Zeek and Suricata over an existing capture file. Read-only: no live capture,
  no writes, no device access.
- **FR-002** Both engines run from **digest-pinned** containers. A floating tag would let a
  security tool's analysis change under the operator silently, which is worse than being
  stale. (Containers are also the only option: `zeek` has no apt candidate on Ubuntu 26.04 and
  `suricata` needs root.)
- **FR-003 (the chokepoint)** A response MUST NOT carry an alert verdict without Suricata's
  signature count, nor Zeek findings without the checksum posture. Enforced by
  `envelope.emit()` raising `PostureError` — there is no code path that omits it, so a skill
  author cannot forget.
- **FR-004** An empty alert list from a detector that loaded **0 signatures** MUST NOT be
  emittable as a bare empty value. It is replaced with an object carrying
  `NOT_A_CLEAN_RESULT`, so a caller reading only the alerts field cannot mistake it for clean.
- **FR-005** `ignore_checksums` defaults to **true** — the opposite of Zeek's own default —
  and the mode used is reported on every response.
- **FR-006** An absent, empty, or directory input MUST raise rather than return an empty
  analysis, which would be indistinguishable from a capture containing nothing.
- **FR-007** Session pivot by Zeek `uid`: every protocol log shares `uid` with `conn.log`,
  making the pivot exact rather than heuristic.
- **FR-008** The installer MUST fetch a ruleset, and MUST warn explicitly if it cannot —
  shipping an inert detector silently is the failure this spec is about.
- **FR-009** Two skills: `nsm-ids-triage` (alert triage) and `nsm-session-pivot` (session
  reconstruction), both stating the posture rules in their own text.

## R13 checklist, addressed

- **Audit `packet-buddy-mcp` against WireMCP / SharkMCP** — `packet-buddy-mcp` has **12
  tools** and is *skill-bundled* (invoked via `MCP_CALL` from `packet-analysis`), not a
  registered server. It covers packet-level decode: summary, protocol hierarchy,
  conversations, endpoints, display filters, packet detail, expert info. That is a different
  question from NSM and is left as-is; `nsm-mcp` composes with it rather than replacing it.
- **Assess Zeek / Suricata / Arkime** — Zeek and Suricata adopted. **Arkime rejected**: it
  requires a mandatory OpenSearch/Elasticsearch cluster and ~12–16 GB. That is a platform to
  operate, not a tool to call, and indexed full-packet retrospective search is not reachable
  without it.
- **Adopt vs build** — **built**. No candidate wraps offline Zeek + Suricata with provenance,
  and the two traps above are exactly what a thin wrapper would pass through unqualified.
- **Skills** — `nsm-ids-triage` and `nsm-session-pivot` delivered. Retrospective *indexed*
  search is out with Arkime.

## Verification

`bash tests/nsm/run-tests.sh` — **19 assertions, 0 failures**. Posture and pinning assertions
need no containers; the two live-analysis assertions skip themselves when docker is
unreachable, so the file is still useful in CI.

The assertions that matter most:

- an alert verdict without Suricata posture is **refused**
- Zeek findings without checksum posture are **refused**
- an empty alert list from an `INERT` detector is **wrapped** with `NOT_A_CLEAN_RESULT`
- integer `0` from an `INERT` detector is **also** wrapped
- an `ARMED` detector reporting no alerts is **not** wrapped (the guard must not cry wolf)
- `ignore_checksums=true` sees `http.log` and **2** connections
- Zeek's own default **loses `http.log`** and miscounts connections (**3**, not 2)
- both images are digest-pinned; no `:latest` anywhere in the runner
- an empty or missing capture raises rather than returning nothing

Reconciliation: **PASS on all six surfaces.** Counts updated 158→159 MCP integrations and
216→218 skills — both caught by the `docs` surface rather than by me.

## Out of scope

- **Arkime** and therefore indexed full-packet retrospective search.
- **Live sensors.** This analyses files. A live Zeek/Suricata deployment is an operational
  system with its own lifecycle, not an MCP call.
- **Rule authoring or tuning.** ET Open is fetched as-is; writing signatures is not offered.
- **Extending `packet-buddy-mcp`.** Audited and left alone.
