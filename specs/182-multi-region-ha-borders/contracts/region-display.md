# Contract: region display (clients)

Input: a manifest node endpoint host from the signed manifest. Output: display label only.
- Parse `^(nne1|ew1|ase1)-[0-9a-f]{6}\.automateyournetwork\.com$` -> label (Montreal, Belgium, Singapore). Anything else -> "Unknown region" (still usable).
- The label never selects, trusts or pins an endpoint. Only the signed manifest does.
- Clients show per-endpoint state: leader / follower / no_quorum / fenced / retired (existing states) plus failover notices.
