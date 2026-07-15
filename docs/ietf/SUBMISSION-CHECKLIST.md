# Submission Checklist — `draft-capobianco-ncfed-00`

Gate list for a clean IETF Datatracker submission (spec SC-001/002/006, FR-021).

## Tooling (record versions)

| Tool | Purpose | Status in authoring env (2026-07-14) |
|------|---------|--------------------------------------|
| `kramdown-rfc` / `kdrfc` 1.7.39 | Markdown → RFCXML + text | **installed + working** (Ruby 3.0.2) |
| `xml2rfc` 3.34.0 | RFCXML render + v2→v3 upgrade | **installed + working** (`~/.local/bin`) |
| `idnits` | I-D nits checker | not installable locally (PyPI unreachable) → **Datatracker runs it server-side (authoritative)** |

> **The draft compiles and renders CLEAN.** Working recipe (reproduces the artifacts):
>
> ```bash
> # one-time: Ruby's OpenSSL expects a cert bundle where Ubuntu doesn't put it
> sudo ln -sf /etc/ssl/certs/ca-certificates.crt /usr/lib/ssl/cert.pem
> gem install kramdown-rfc          # provides kdrfc + kramdown-rfc2629
>
> cd docs/ietf && mkdir -p rendered
> kdrfc draft-capobianco-ncfed-00.md                         # -> .xml (v2) + .txt, clean
> xml2rfc --v2v3 draft-capobianco-ncfed-00.xml \
>         -o rendered/draft-capobianco-ncfed-00.xml          # upgrade to RFCXML v3
> xml2rfc rendered/draft-capobianco-ncfed-00.xml --text \
>         -o rendered/draft-capobianco-ncfed-00.txt          # v3 -> text (0 lines >72)
> xml2rfc rendered/draft-capobianco-ncfed-00.xml --html \
>         -o rendered/draft-capobianco-ncfed-00.html         # v3 -> HTML (nice to read)
> rm -f draft-capobianco-ncfed-00.xml draft-capobianco-ncfed-00.txt  # keep rendered/ copies
> ```
>
> Rendered artifacts live in **`docs/ietf/rendered/`** (tracked): the `.xml` is what you
> upload to Datatracker; the `.html`/`.txt` are for reading. The source of truth is the
> `.md` — always rebuild from it.
>
> **Compile result:** RFCXML **v3** (`version="3"`), `.txt` renders with **0 lines
> over 72 columns**, correct Experimental boilerplate + computed expiry, only benign
> "auto-reduced indentation" notes (no errors). `idnits` is not installed here; the
> **Datatracker submit tool runs `xml2rfc`+`idnits` server-side** on upload and is
> authoritative (plan A1).

## Pre-submission gates

- [X] `kdrfc` + `xml2rfc --v2v3` produce RFCXML **v3** + text with **zero errors** (SC-001) — verified locally 2026-07-14.
- [~] `idnits` **zero errors** (SC-002) — `idnits` not installable locally; the rendered `.txt` has 0 over-length lines and valid boilerplate, and **Datatracker runs idnits server-side on upload** (authoritative). Expected/acceptable warnings:
  - "no date" — intentional; the Datatracker fills the date on submission.
  - "no RFC number / obsolete boilerplate date" style — pre-publication placeholders.
- [X] **Author email** filled in the front matter (`ptcapo@gmail.com`, URI `https://automateyournetwork.ca`) — done 2026-07-14.
- [ ] `submissiontype: IETF` (individual submission to the IETF stream; ISE is the fallback only).
- [ ] Upload the **`.xml`** (RFCXML v3) at <https://datatracker.ietf.org/submit/>; verify the confirmation email (unless logged in as the listed author).
- [ ] Acknowledge the rights granted to the IETF Trust under **BCP 78 / BCP 79** at submission.
- [ ] Mind the **meeting submission window** — new I-Ds freeze for ~2 weeks around each IETF meeting.

## Manual structure + fidelity validation (done at authoring time)

- [x] All mandatory I-D sections present in order (Abstract; §1 Intro + Motivation/Applicability + status note; §2 Conventions & Terminology; §3 Stack; §4 Discrimination; §5 Handshake; §6 Framing; §7 Heartbeat; §8 Semantic Payload + errors; §9 Negotiation; §10 Cards; §11 Trust; §12 Operational; §13 Security; §14 IANA; back: Prior Art, Acknowledgments; References). (SC-006)
- [x] Three figures present as ASCII artwork, ≤72 cols, anchored/titled: `fig-stack`, `fig-handshake`, `fig-frame` (+ `fig-in2n-preamble`). (SC-005)
- [x] Both error registries present verbatim (eN2N −32001..−32010, −32601; iN2N −32021..−32031).
- [x] RFC 2119/8174 boilerplate via `{::boilerplate bcp14-tagged}`; keywords used normatively.
- [x] **Wire-fact fidelity re-verified against source 2026-07-14** (SC-003) after an external
      review pass. The review found several fidelity gaps in the earlier draft; all were
      corrected against `bgp/federation/*` (not by changing code — the wire is frozen):
      - eN2N handshake is **request/reply** (acceptor replies with its own 13-octet handshake),
        not one-way — `service.py:263-265,298-309`. **Fixed.**
      - Deterministic initiator: numerically **lower AS** dials; higher/equal accepts —
        `service.py:284`. **Added.**
      - Discrimination **consumes-and-replays** the first octet (BGP marker re-injected), not a
        peek — `bgp/agent.py:278,338,352`. **Clarified.**
      - Consent is a **two-bit lattice** (local × remote grant), not linear; re-consent after
        sever exists — `manager.py:270-284`. **Redrawn.**
      - Auto-quarantine triggers on **failed pinned-key auth only**, not health checks —
        `risk.py:485`, `service.py:553`. **Corrected.**
      - `-32022` is **defined but not emitted**; member-id-taken is reported as `-32021` —
        `service.py:507`, `risk.py:281`. **Disclosed honestly.**
      - "Version negotiation" performs **no version comparison**; feature-gated graceful degrade —
        `negotiate.py`. **Rewritten.**
      Confirmed accurate as-is: magics, frame format (BE len + flags, bit0 CONTINUATION, 64 KiB,
      oversize→close), reserved-bits rule, heartbeat (0-len, 30/3/90), iN2N IN2N1+32B nonce /
      ECDSA-P256 / TOFU / single-use token / outbound-only, capability card (posture+llm).
- [x] **Real code weaknesses disclosed, not hidden** (SC-004): no eN2N crypto peer-auth; iN2N
      Border-not-authenticated + TLS `CERT_NONE`; unbounded reassembly; quarantine-DoS; no hop-count;
      task bearer-capability; card metadata. All in Security Considerations + `NCFED-HARDENING-BACKLOG.md`.
      Decision 2026-07-14: keep freeze, ship honest Experimental `-00`; fix in a follow-up spec.
- [x] **JSON-RPC method reference appendix** (Appendix C) added — params/results/encodings for
      n2n/hello, n2n/tools/call, the task family, n2n/inventory, in2n/enroll, in2n/hello — derived
      from the handlers (`invocation.py`, `tasks.py`, `service.py`).
- [x] All 5 Security Considerations parts present (port-sharing, TOFU, confidentiality, agent-delegation, DoS). (SC-004)
- [x] Differentiation from `draft-yan-a2a-device-agent-applicability` + MCP/A2A restatable in one sentence. (SC-007)
- [x] No secrets / no per-member topology in the capability-card spec.
- [x] No claim of a wire behavior the code does not implement (freeze / FR-023/024) — recommendations are marked SHOULD/RECOMMEND (version octet, reassembly bound, delegation-depth, TLS).
- [x] **RFC 7942 Implementation Status** appendix present (`{:removeinrfc="true"}`, `RFC7942` informative ref), citing `captures/ncfed-johns-risk-nick-20260714.pcap`; figures match `capinfos`/`tshark` (24 pkts / 3141 octets; conv `192.168.2.61:45722`↔`13.58.157.220:10416`, 13in/1567 + 11out/1574; 0 SYN/FIN/RST; 0 retransmits/dup-acks; segments 5/75/110/127/153/274/352 + 12 pure-ACK) and the honest scope (TLS-tunnel/ciphertext = channel evidence, not plaintext frames; plaintext = future work). **0 overclaims** (SC-008).
