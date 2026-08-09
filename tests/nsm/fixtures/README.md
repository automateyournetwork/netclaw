# NSM test fixtures

## `checksum-offload.pcap`

Five packets, hand-built byte by byte so the test suite is deterministic and needs no network:

| # | Traffic |
|---|---|
| 1 | DNS A query for `example.com` (UDP 53) |
| 2-4 | TCP handshake to 93.184.216.34:80 |
| 5 | `GET /index.html` with `User-Agent: netclaw-r13-fixture` |

**The TCP checksums are deliberately zero**, which is what a NIC with checksum offloading
produces. That is the whole point of the fixture: it reproduces spec 091's central finding.

Run Zeek against it two ways and the results differ in a way that is invisible unless you
look for it:

| | `http.log` | `conn.log` rows |
|---|---|---|
| Zeek default (validating) | **absent** | 3 — *wrong* |
| `-C` / `ignore_checksums=true` | present | 2 — correct |

Zeek marks this with a **non-fatal warning on stderr** and exits 0. An analyst concludes
"there was no HTTP traffic" when there was.

Suricata independently corroborates the fixture property: with the ET Open ruleset loaded it
fires `SURICATA TCPv4 invalid checksum` (sid 2200074) on the same packets.

Do not "fix" the checksums. The invalid ones are the test.
