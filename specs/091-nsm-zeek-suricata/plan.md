# Implementation Plan: NSM — Zeek + Suricata offline PCAP analysis (R13)

**Branch**: `091-nsm-zeek-suricata` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)
**Roadmap**: R13 — NSM / IDS

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05** after merge, from `spec.md`, the delivered server and tests, and the git
> history. No `plan.md` existed during the build — a breach of Principle XVI, part of the 087–096
> drift.

## Summary

NetClaw could decode packets (`packet-buddy-mcp`, 12 tools) but had **no network-security-monitoring
layer**: no session reconstruction, no protocol metadata, no signature alerting.

`nsm-mcp` adds both, read-only, over a capture file already on disk — Zeek 8.2.1 for session and
protocol metadata, Suricata 8.0.6 for signature alerting. **6 tools, ~934 tokens.**

**The substance is not the wiring.** Both engines have a failure mode where they run successfully,
exit 0, and tell you nothing while looking like they told you everything. Both were reproduced live
*before a line of the server was written*, and the server is built so neither can reach an operator
unqualified.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: Zeek 8.2.1 and Suricata 8.0.6 as **digest-pinned containers**; ET Open
ruleset fetched at install
**Storage**: None persistent — analysis output is per-call, from a file the operator supplies
**Testing**: `bash tests/nsm/run-tests.sh` — **19 assertions**, using a five-packet fixture built
byte by byte (`tests/nsm/fixtures/checksum-offload.pcap`) so results are deterministic and need no
network
**Target Platform**: Linux with Docker
**Project Type**: MCP integration — **built**, not adopted
**Performance Goals**: Manifest ≤ 5,000 (achieved ~934)
**Constraints**: Read-only — a capture file on disk; nothing sniffs an interface
**Scale/Scope**: 6 tools, 2 skills, 2 container engines

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **I. Safety-First** | No device access, no live capture | **PASS** — input is a file |
| **II. Read-Before-Write** | No writes | **PASS** |
| **VIII. Verify After Every Change** | Findings must be trustworthy | **PASS** — this is the whole feature: posture travels with every verdict |
| **IX. Security by Default** | A security tool must not be silently inert | **PASS** — FR-004/FR-008 |
| **XI. Artifact Coherence** | All touchpoints | **PASS** — counts 158→159 MCP, 216→218 skills, caught by the `docs` surface |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## Project Structure

```text
mcp-servers/nsm-mcp/            # the server, incl. envelope.emit() chokepoint
tests/nsm/run-tests.sh          # 19 assertions
tests/nsm/fixtures/checksum-offload.pcap   # 5 packets, built byte by byte
workspace/skills/nsm-ids-triage/
workspace/skills/nsm-session-pivot/
```

**Structure Decision**: Built rather than adopted. No candidate wraps offline Zeek + Suricata with
provenance, and **a thin wrapper would pass both traps through unqualified** — which is precisely
what the feature exists to prevent.

## The design centre: a chokepoint, not a convention

`envelope.emit()` raises `PostureError` if a response would carry an alert verdict without
Suricata's signature count, or Zeek findings without the checksum posture. **There is no code path
that omits it**, so a skill author cannot forget. An empty alert list from a detector that loaded
**0 signatures** is replaced with an object carrying `NOT_A_CLEAN_RESULT` — a caller reading only
the alerts field cannot mistake it for clean.

This is the difference between documenting a hazard and removing it.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a recurrence gate |
| **Two container engines rather than host packages** | `zeek` has **no apt candidate** on Ubuntu 26.04 and `suricata` needs root to install | Host packages were not available; digest pinning additionally prevents a security tool's analysis changing under the operator silently, which is worse than being stale |
| **Defaulting `ignore_checksums` to `true` — the opposite of Zeek's own default** | Zeek's default silently loses `http.log` entirely and **miscounts `conn.log`** (3 rows vs the correct 2) on checksum-offloaded captures | Matching upstream's default would make NetClaw analyse **its own** `cml-packet-capture` and `gns3-packet-capture` output wrongly. The mode used is reported on every response |
| **Rejecting Arkime** | Mandatory OpenSearch/Elasticsearch cluster, ~12–16 GB | That is a platform to operate, not a tool to call. Indexed full-packet retrospective search is unreachable without it and is declared out of scope |
