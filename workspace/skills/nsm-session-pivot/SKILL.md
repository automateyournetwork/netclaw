---
name: nsm-session-pivot
description: "Pivot through Zeek session and protocol metadata from a packet capture (read-only) — connection listing, service filtering, and following a connection uid into dns/http/ssl logs. Use when reconstructing what sessions occurred in a capture, following a connection across protocols, or investigating retrospectively"
version: 1.0.0
license: Apache-2.0
tags: [security, nsm, zeek, pcap, sessions, forensics, read-only]
---

# NSM Session Pivot (read-only)

## MCP Server

- **Server**: `nsm-mcp` (NetClaw-authored, spec 091)
- **Tools**: `nsm_status`, `nsm_analyze`, `nsm_sessions`, `nsm_protocol_log`
- **Engine**: Zeek 8.2.1, pinned by image digest
- **Input**: a `.pcap`/`.pcapng` file already on disk. Nothing sniffs an interface.

## The rule that matters most here

**A missing protocol log does not mean there was no such traffic.**

Zeek **discards packets with invalid TCP checksums by default**. Measured on a reference
capture: with validation on, Zeek produced **no `http.log` at all** — the HTTP request was
invisible — and a `conn.log` that was also *wrong*, 3 rows instead of the correct 2, because
discarded packets fragment the flow. The only signal is a warning on stderr.

Captures from a NIC with checksum offloading routinely have invalid checksums, **including
the ones NetClaw's own `cml-packet-capture` and `gns3-packet-capture` skills produce.**

So `nsm-mcp` defaults `ignore_checksums=true`, the opposite of Zeek's own default, and
attaches `zeek_posture` to every response:

| `state` | What it means |
|---|---|
| `IGNORING_CHECKSUMS` | all packets analysed — the correct setting for offloaded captures |
| `PACKETS_DISCARDED` | **packets were dropped**; protocol logs may be missing and conn.log may be wrong |
| `VALIDATING` | validation on, nothing flagged |

If you see `PACKETS_DISCARDED`, re-run with `ignore_checksums=true` before drawing any
conclusion. Reporting "no HTTP in this capture" from a discarded run is a wrong answer that
looks like a finding.

## Workflow: reconstruct what happened

1. `nsm_analyze` — which Zeek logs did this capture produce, and how many connections?
2. `nsm_sessions` — the connection table. Note `service`, `conn_state`, byte counts
3. Pick the connection of interest and record its **`uid`**
4. `nsm_protocol_log` with `log="dns"` / `"http"` / `"ssl"` and that `uid` — every Zeek log
   shares `uid` with `conn.log`, which is what makes the pivot exact rather than heuristic
5. `nsm_protocol_log` with `log="weird"` — protocol anomalies Zeek could not classify
6. Report the session narrative, stating the checksum posture you worked under

## Workflow: follow an IDS alert to its session

Given an alert from `nsm-ids-triage`:

1. `nsm_sessions` filtered by the alert's `service`, or scanned for its IP pair
2. Match on `id.orig_h`/`id.resp_h`/`id.resp_p` to find the `uid`
3. `nsm_protocol_log` for the relevant protocol with that `uid`
4. Report the alert **with** its session: duration, bytes each way, `conn_state`
5. `conn_state` is evidence: `S0` (no reply) is a very different story from `SF` (completed)

## Reading results honestly

- **Ask which logs exist before concluding one is empty.** `nsm_protocol_log` returns the
  available log list when you request one Zeek did not write — use it rather than reporting
  absence.
- **`truncated: true` means you are looking at a page**, not the total.
- **Zeek infers `service` from behaviour, not port.** HTTP on 8443 is labelled `http`; trust
  the field over the port number, and say which you used.
- **`weird.log` is not an alert log.** It records protocol oddities, many of them benign.

## Important Rules

- **No writes, no live capture.** This analyses a file.
- **Always state the checksum posture** in any conclusion about absent traffic.
- **Record in GAIT** — log every pivot, including the posture and connection count.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `nsm-ids-triage` | Suricata alerts that this skill puts into session context |
| `packet-analysis` | Individual packet decode (tshark) once a session is identified |
| `cml-packet-capture` / `gns3-packet-capture` | Produce the capture this skill analyses |
| `gait-session-tracking` | Record all pivots |

## Environment Variables

- `NSM_HOME` — analysis and ruleset directory (default `~/.openclaw/nsm`)
- `NSM_TIMEOUT` — per-container timeout in seconds (default 600)
