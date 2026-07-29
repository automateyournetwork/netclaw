# N2N Federation Packet Captures & Analysis

Packet captures and analysis reports documenting the NCFED / N2N federation
protocol on the wire, before and after channel security (specs 060/063).

## Bundles

| Date | Capture | Analysis | What it shows |
|------|---------|----------|---------------|
| 2026-07-14 | `n2n-session-20260714.pcap` | `analysis-20260714/`, `N2N-Capture-Analysis-20260714.pdf` | Pre-060 **cleartext** NCFED session (BGP mesh + JSON-RPC channel). Chat, task I/O, and a full health report recovered from raw payloads — the motivation for spec 060. |
| 2026-07-17 | `n2n-encrypted-20260717.pcap` | `analysis-20260717/` | Post-060 **encrypted** channel to a domain-verified peer. Review guide for confirming payloads are dark. |
| 2026-07-18 | `n2n-cml-health-20260718.pcap` | `analysis-20260718/` | CML lab-health chat exchange over secured channels (060/063). Bundle includes transcript, daemon log for the window, and SHA256SUMS. |
| — | `ncfed-session.pcap`, `NCFED-Wireshark-Analysis.pdf`, `ncfed-decode.log` | — | Earlier NCFED wire analysis supporting the Internet-Draft work (spec 059). |

## Redaction policy

These artifacts were scanned before publication for anything usable against the
live mesh:

- **No credentials are present** — no ngrok authtokens, API keys, private keys,
  or enrollment/grant tokens appear in any pcap or report.
- **Live tunnel endpoints are redacted.** ngrok TCP ports that were still
  active at publication time (including one reserved, non-rotating address)
  were replaced with `XXXXX` in all text, PDF (true redaction, text layer
  removed), and pcap files (same-length byte substitution in pcapng metadata;
  TLS payloads untouched).
- **Stale endpoints are left as captured** (e.g. `8.tcp.ngrok.io:20203`,
  `0.tcp.ngrok.io:15091`) — those tunnels are long gone and ngrok reassigns
  the ports to other customers.
- Device names, lab topology, and lab credentials visible in the 2026-07-14
  cleartext capture are intentional demo-lab content.

`analysis-20260718/SHA256SUMS` was regenerated after redaction and verifies
clean with `sha256sum -c`.
