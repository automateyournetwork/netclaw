---
name: nsm-ids-triage
description: "Triage Suricata IDS alerts from a packet capture (read-only) — signature alerts with detection posture, severity filtering, and corroboration against Zeek session metadata. Use when triaging IDS alerts, checking whether a capture contains known-bad traffic, or validating that a detector was actually armed"
version: 1.0.0
license: Apache-2.0
tags: [security, ids, suricata, nsm, pcap, alerts, read-only]
---

# NSM IDS Triage (read-only)

## MCP Server

- **Server**: `nsm-mcp` (NetClaw-authored, spec 091)
- **Tools**: `nsm_status`, `nsm_update_rules`, `nsm_alerts`, `nsm_analyze`
- **Engine**: Suricata 8.0.6, pinned by image digest
- **Input**: a `.pcap`/`.pcapng` file already on disk. Nothing sniffs an interface.

## The rule that matters most here

**Zero alerts is not a clean result until you have checked the signature count.**

Stock Suricata loads **0 signatures** and reports **0 alerts**, announcing it with two
*non-fatal* warnings. Measured: **0 signatures** on stock config versus **52,205** after
`nsm_update_rules`. A detector that loaded nothing inspected nothing.

`nsm_alerts` attaches `suricata_posture` to every response for exactly this reason:

| `state` | What it means | What you may say |
|---|---|---|
| `ARMED` | signatures loaded, detector ran | "no alerts matched the loaded ruleset" |
| `INERT` | **0 signatures** | "the detector was off" — **never** "the traffic is clean" |
| `UNKNOWN` | count seen, no ruleset file | treat with suspicion, re-run after `nsm_update_rules` |

When posture is `INERT`, the tool replaces an empty alert list with an object carrying
`NOT_A_CLEAN_RESULT`. That is deliberate: it cannot be read as a clean verdict by a caller
that only looks at the alert field.

## Workflow: triage a capture

1. `nsm_status` — is docker reachable, is a ruleset present, how old is it?
2. If no ruleset: `nsm_update_rules`, then continue. **Do not proceed to conclusions on an
   `INERT` run** — report that the detector was off and stop.
3. `nsm_alerts` with `min_severity=2` — the alerts worth a human's attention first
4. `nsm_alerts` unfiltered — the full picture, noting `truncated` if set
5. For each alert that matters, pivot to the session with `nsm-session-pivot` using the
   `src_ip`/`dest_ip`/`dest_port` — an alert without its session context is a signature
   match, not an incident

## Reading alerts honestly

- **A signature match is not a compromise.** ET Open contains policy and informational rules;
  `category` and `severity` matter. Say what matched, not what it implies.
- **A ruleset age is part of the finding.** A 30-day-old ruleset cannot alert on last week's
  signatures; `nsm_status` reports `ruleset_age_days` and the skill should quote it.
- **Suricata alerts on malformed traffic too.** `SURICATA TCPv4 invalid checksum` means the
  capture has bad checksums — usually NIC offloading, not an attack. It is also a signal that
  Zeek would discard those packets, so cross-check with `nsm-session-pivot`.
- **`truncated: true` means you are looking at a page.** Never present it as the total.

## Important Rules

- **No writes, no live capture.** This analyses a file. Blocking traffic or changing a sensor
  is not available and must not be offered.
- **Never report "0 alerts" without the posture** — the tool will not let you, and neither
  should the summary you write.
- **Record in GAIT** — log every triage, including the signature count and ruleset age.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `nsm-session-pivot` | Turn an alert into its full session and protocol context |
| `packet-analysis` | Drop to individual packet decode (tshark) for a specific alert |
| `cml-packet-capture` / `gns3-packet-capture` | Produce the capture this skill analyses |
| `gait-session-tracking` | Record all triage runs |

## Environment Variables

- `NSM_HOME` — analysis and ruleset directory (default `~/.openclaw/nsm`)
- `NSM_TIMEOUT` — per-container timeout in seconds (default 600)
