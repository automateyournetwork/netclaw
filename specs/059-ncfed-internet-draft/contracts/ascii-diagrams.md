# Contract: RFC ASCII-art figures (draft-ready)

Three figures the draft MUST contain, drawn to RFC conventions (fixed-width, ≤ 72
columns, bit-ruler for packet diagrams). These are **pre-drawn from ground truth**
so the implement phase drops them in verbatim (inside kramdown-rfc `~~~` artwork
blocks with `{: #fig-… title="…"}`).

## Fig 1 — Protocol stack (`fig-stack`)

```
+---------------------------------------------------------------+
| Application semantics (NCFED payload)                         |
|   MCP:  n2n/tools/call                                        |
|   A2A:  capability card, n2n/tasks/{submit,status,result,...} |
+---------------------------------------------------------------+
| Encoding: UTF-8 JSON-RPC 2.0                                  |
+---------------------------------------------------------------+
| Framing:  [4-octet BE length][1-octet flags][payload]        |
|           flags bit0 = CONTINUATION (chunk); len 0 = heartbeat|
+---------------------------------------------------------------+
| Federation handshake (13 octets):                            |
|   "NCFED" + <4-octet AS> + <4-octet router-id (IPv4)>        |
+---------------------------------------------------------------+
| Discrimination on the shared listen port:                    |
|   0xFF          -> BGP-4        (RFC 4271 marker)             |
|   'N' + "CFED"  -> NCFED (this document)                     |
|   'N' + "CTUN"  -> NCTUN data plane (out of scope)           |
+---------------------------------------------------------------+
| TCP  /  IP                                                    |
+---------------------------------------------------------------+
```

*(iN2N runs the same framing/JSON-RPC over a SEPARATE Border listener with the
`IN2N1`+nonce preamble instead of discrimination — shown in Fig 2b / §11, not here.)*

## Fig 2 — NCFED federation handshake, 13 octets (`fig-handshake`)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      'N'      |      'C'      |      'F'      |      'E'      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      'D'      |     Autonomous System Number (bits 0..23)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  AS (24..31)  |        Router-ID (IPv4) (bits 0..23)         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Router-ID(24..31)|
+-+-+-+-+-+-+-+-+
```

Octets 0–4 = the 5-octet magic `NCFED`. Octets 5–8 = 4-octet AS, **network byte
order**. Octets 9–12 = 4-octet router-id = a packed IPv4 address. Sent once by the
**initiator**; the acceptor does not echo a binary handshake (mutual identity +
version follow at `n2n/hello`).

## Fig 2b — iN2N transport preamble (`fig-in2n-preamble`) — for §11

```
Border  --> Member :  "IN2N1" (5 octets)  ||  nonce (32 octets, random)
Member  --> Border :  JSON-RPC  in2n/hello | in2n/enroll
                      (params carry an ECDSA-P256/SHA-256 signature over the nonce,
                       proving possession of the member's pinned self-signed key)
  ... then the standard NCFED framing/JSON-RPC channel runs ...
```

The trailing `1` in `IN2N1` is a preamble version digit. iN2N uses a **separate
listener** (operator-configured port), not the shared discrimination port.

## Fig 3 — NCFED frame (`fig-frame`)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|              Length (payload octets, unsigned, BE)            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Flags     |            Payload (Length octets) ...        |
+-+-+-+-+-+-+-+-+                                               +
|                              ...                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Flags (1 octet):
  bit 0 (0x01)  CONTINUATION  payload is a chunk; concatenate frames
                              until a frame with this bit clear
  bits 1..7                   RESERVED; MUST be 0 on send, ignored on receipt

Length == 0 with Flags == 0  ==>  HEARTBEAT (not delivered to the application)
Length  > 65536              ==>  receiver MUST close the connection
```

## Drawing rules (for the author)

- Keep every figure ≤ 72 columns; use only ASCII (no box-drawing Unicode) so `idnits`
  and the text renderer are happy.
- Wrap each in kramdown-rfc artwork: ` ~~~ ` … ` ~~~ ` then `{: #fig-… title="…"}`.
- Bit-rulers (`0 1 2 …`) only on true packet diagrams (Fig 2, 3); Fig 1/2b are
  layered/sequence art and don't need a ruler.
