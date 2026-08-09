# nsm-mcp — offline NSM analysis (Zeek + Suricata)

Roadmap **R13**, spec [091](../../specs/091-nsm-zeek-suricata/spec.md). NetClaw-authored,
**read-only**: the input is a packet capture already on disk, and nothing here sniffs an
interface or touches a device.

| | |
|---|---|
| Tools | **6** — `nsm_status`, `nsm_update_rules`, `nsm_analyze`, `nsm_sessions`, `nsm_protocol_log`, `nsm_alerts` |
| Manifest cost | **~934 tokens** of the 5,000 ceiling |
| Zeek | 8.2.1, `zeek/zeek@sha256:eca2b391…` |
| Suricata | 8.0.6, `jasonish/suricata@sha256:81468a22…` |
| State | `~/.openclaw/nsm` (`NSM_HOME`) — rules and analysis output |

## Why containers

Not a preference. `zeek` has **no apt candidate** on Ubuntu 26.04, and `suricata` needs root
to install. Both images are pinned **by digest**: a floating tag would let a security tool's
analysis change under the operator with no signal, which is worse than being out of date.

## The two silent wrong answers this server exists to prevent

Both were reproduced live against `tests/nsm/fixtures/checksum-offload.pcap` before the
server was written. In both cases the tool exits 0 and looks like it worked.

### 1. Suricata with no ruleset alerts on nothing

| Config | Signatures | Alerts |
|---|---|---|
| Stock | **0** | **0** |
| After `nsm_update_rules` | **52,205** | 4 on the fixture |

Two *non-fatal* warnings are the only signal. So `nsm_alerts` attaches
`suricata_posture` to every response, and when the state is `INERT` it **replaces an empty
alert list with an object carrying `NOT_A_CLEAN_RESULT`** — a caller reading only the alerts
field cannot mistake it for a clean verdict.

### 2. Zeek discards invalid-checksum packets by default

| Mode | `http.log` | `conn.log` rows |
|---|---|---|
| Zeek default (validating) | **absent** | 3 — *wrong* |
| `ignore_checksums=true` (this server's default) | present | 2 — correct |

The HTTP request was **completely invisible** in the default run, and the connection count was
also wrong because discarded packets fragment the flow. Captures from NICs with checksum
offloading routinely trigger this — **including the ones NetClaw's own `cml-packet-capture`
and `gns3-packet-capture` skills produce** — which is why this server inverts Zeek's default
and always reports which mode it used.

## The chokepoint

`envelope.emit()` raises `PostureError` if a response would carry an alert verdict without
Suricata posture, or Zeek findings without checksum posture. There is no code path that
returns a finding without the qualifier that makes it readable, so a skill author cannot
forget. Same shape as `document-mcp`'s `emit()` (spec 082) and `catc-mcp`'s `_envelope()`
(spec 087).

## Scope

**In:** offline PCAP analysis — session metadata, protocol logs, signature alerts, session
pivot by Zeek `uid`.

**Out:** live sensors, any write, and **Arkime** — it requires a mandatory
OpenSearch/Elasticsearch cluster and ~12–16 GB, which is a platform to operate rather than a
tool to call.

## Tests

`bash tests/nsm/run-tests.sh` — 19 assertions. The posture and pinning assertions need no
containers; the two live analysis assertions skip themselves when docker is unreachable.
