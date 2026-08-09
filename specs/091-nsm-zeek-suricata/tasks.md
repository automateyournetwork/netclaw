# Tasks — NSM: Zeek + Suricata (reconstruction)

**Branch**: `091-nsm-zeek-suricata` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge from the spec, the delivered server and its tests. All
> items `[X]`, ordered by dependency rather than chronology.

---

## Phase 1 — Reproduce the traps BEFORE writing the server (BLOCKING)

- [X] **T001** Build `tests/nsm/fixtures/checksum-offload.pcap` — five packets, byte by byte, so
      results are deterministic and need no network
- [X] **T002** Reproduce Suricata inert: stock config loads **0 signatures**, reports **0 alerts**,
      exits 0, behind two non-fatal warnings
- [X] **T003** Reproduce armed Suricata: **52,205** signatures after `suricata-update`, 4 alerts on
      the fixture
- [X] **T004** Reproduce Zeek's checksum discard: default loses `http.log` entirely and reports
      **3** `conn.log` rows against the correct **2**
- [X] **T005** Corroborate independently — ET Open fires `SURICATA TCPv4 invalid checksum`
      (sid 2200074) on the packets Zeek dropped
- [X] **T006** Establish the blast radius: NetClaw's **own** `cml-packet-capture` and
      `gns3-packet-capture` output is affected

## Phase 2 — Engines and pinning

- [X] **T007** Zeek 8.2.1 and Suricata 8.0.6 from **digest-pinned** containers (FR-002)
- [X] **T008** Confirm containers are not a preference: no apt candidate for `zeek` on Ubuntu 26.04;
      `suricata` needs root
- [X] **T009** Reject Arkime — mandatory OpenSearch, ~12–16 GB

## Phase 3 — The chokepoint (this is the feature)

- [X] **T010** `envelope.emit()` raises `PostureError` if an alert verdict lacks Suricata's signature
      count, or Zeek findings lack the checksum posture (FR-003)
- [X] **T011** Wrap an empty alert list from a 0-signature detector with `NOT_A_CLEAN_RESULT` (FR-004)
- [X] **T012** Wrap integer `0` from an `INERT` detector too — the same lie in a different type
- [X] **T013** Do **not** wrap an `ARMED` detector reporting no alerts — the guard must not cry wolf
- [X] **T014** Default `ignore_checksums=true`, opposite Zeek's own default, and report the mode on
      every response (FR-005)
- [X] **T015** Raise on absent, empty, or directory input (FR-006)

## Phase 4 — Capability

- [X] **T016** Six tools, ~934 tokens, read-only over a file on disk (FR-001)
- [X] **T017** Session pivot by Zeek `uid` — exact, not heuristic (FR-007)
- [X] **T018** Installer fetches ET Open and **warns explicitly** if it cannot (FR-008)
- [X] **T019** Skills `nsm-ids-triage` and `nsm-session-pivot`, both stating the posture rules in
      their own text (FR-009)

## Phase 5 — Tests and coherence

- [X] **T020** `tests/nsm/run-tests.sh` — **19 assertions, 0 failures**
- [X] **T021** Posture and pinning assertions run without containers; the two live-analysis
      assertions skip themselves when docker is unreachable, so the file stays useful in CI
- [X] **T022** Assert no `:latest` anywhere in the runner
- [X] **T023** Artifact coherence — counts 158→159 MCP, 216→218 skills, **caught by the `docs`
      surface rather than by hand**
- [X] **T024** Reconciliation PASS on all six surfaces

---

## Dependencies

```
T001 → T002–T006     (the fixture is what makes the traps reproducible)
T002–T006 → T010–T014 (you cannot block a trap you have not characterised)
T010 → T011 → T012 → T013
T007 → T016
T018 gates a useful T002 outcome in the field
```

## Deliberately not done

Arkime and indexed retrospective search; live sensors (an operational system with its own lifecycle,
not an MCP call); rule authoring or tuning (ET Open is fetched as-is); extending `packet-buddy-mcp`
(audited, left alone).
