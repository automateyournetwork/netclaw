# Fixtures — synthetic and captured `/api/n2n` payloads

Research R4. These make SC-006 (product generality) and FR-029 (100-member
ceiling) falsifiable — neither can be evidenced against a single 29-member
Border.

| File | Members | Peers | Exercises |
|---|---:|---:|---|
| `empty.json` | 0 | 0 | FR-033 first-run: bands, boundary and CTAs with no data |
| `single.json` | 1 | 0 | Degenerate single-member chart |
| `live-29.json` | 29 | 5 | Captured real Border — regression baseline |
| `scale-100.json` | 102 | 5 | FR-029 ceiling + FR-029b frame rate; all four health states |
| `uncategorised.json` | 29 | 5 | FR-006a: every member matches no integration prefix |

## Notes

**`live-29.json` is a point-in-time capture (2026-07-27) and will drift from the
live Border.** It is committed deliberately as a fixed regression baseline; do
not refresh it casually, or the tests asserting against it lose their meaning.

Its 5 `live` members are **not** a contradiction of the spec's "4 live
(`cml`, `ipfabric`, `pyats`, `viz`)". Those 4 are agent members. The 5th is an
**edge node that reconnected between the spec measurement and the capture** —
and it is a useful accident: its `display_name` is `null`, so it renders as the
`member_id` tail (`1785078347014`). That is exactly the case FR-015 exists for,
now present in the baseline fixture rather than only in prose.

**`scale-100.json` has 102 members**: 100 generated plus the 2 real edge nodes,
so the edge lane is exercised at the ceiling too. Health states are seeded
(`random.seed(72)`) for reproducibility — roughly 10% HOT, 10% WARM, 10% FAULT,
70% COLD, which approximates a real fleet where most claws are cold by design.

**No credentials are present.** The `/api/n2n` payload carries topology and state
only. Peer `endpoint` fields were nulled during capture regardless.
