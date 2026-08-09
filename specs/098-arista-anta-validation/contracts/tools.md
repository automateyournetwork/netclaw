# Contract — Tool surface

**Server**: `anta-mcp` · NetClaw-authored over `anta` 1.9.0 (Apache-2.0), own virtualenv
**Shape**: dispatcher + discovery — **4 tools for 208 tests**

208 tools would cost ~58,000 tokens (11.6× ceiling). The 087 pattern applies: describe on demand,
never enumerate.

---

## Tools

| Tool | Contacts a device? | Purpose |
|---|---|---|
| `anta_list_tests` | **no** | Search the 208-test catalogue by category or keyword |
| `anta_describe_test` | **no** | One test's description and input schema, so inputs are known before running |
| `anta_run_tests` | yes | Run selected tests against one device, return per-test verdicts and a five-way summary |
| `anta_status` | no | Server health: ANTA version, catalogue size, whether credentials are configured |

Discovery works with **no device configured at all** (FR-008, SC-005) — an operator can explore what
is testable before connecting anything.

---

## `anta_run_tests`

**Inputs**: `host` (per-call, FR-013), `tests` (names) or `category`, optional per-test `inputs`,
optional `verify_tls`.

**Credentials come from the environment only** (`ANTA_USERNAME`, `ANTA_PASSWORD`) — never as
arguments, never echoed (FR-009).

**Returns**: per-test results plus a summary with **five separate counts**.

```json
{
  "device": "172.20.20.4", "observed_at": "2026-08-05T18:22:04Z", "tls_verified": false,
  "summary": {"passed": 3, "failed": 1, "not_applicable": 1, "skipped": 0, "errored": 0, "total": 5},
  "results": [
    {"test": "VerifyEOSVersion", "category": "software", "verdict": "pass"},
    {"test": "VerifyNTP", "category": "system", "verdict": "fail",
     "messages": ["NTP status mismatch - Expected: synchronised Actual: ..."]},
    {"test": "VerifyBGPPeerCount", "category": "routing.bgp", "verdict": "not_applicable",
     "messages": ["'show bgp summary vrf all' failed on veos1: BGP inactive"],
     "note": "feature not configured on this device - nothing was tested"}
  ]
}
```

### The three responses that are not what they look like

| Situation | Response | Why it matters |
|---|---|---|
| Device unreachable | `error` for the device, **no test results** | An unreachable device is not a broken one (R15's distinction) |
| Feature not configured | `not_applicable`, **not** `fail` | ANTA natively returns `failure` here; NetClaw reclassifies. Counting it would report a BGP fault on a device with no BGP |
| No tests matched | `"no tests selected"`, **not** an all-pass run | An empty run is not a healthy device |

**No health percentage is ever emitted.** `passed / total` is meaningless with `not_applicable` and
`skipped` in the denominator, and `summary.emit()` raises rather than computing one.

---

## Read-only guarantee

The manifest contains no configuration verb. ANTA itself only reads. NetClaw adds **no** write path
(FR-003), asserted by a test that scans the source for configuration-session calls.

---

## Configuration

| Variable | Meaning |
|---|---|
| `ANTA_USERNAME` / `ANTA_PASSWORD` | device credentials — environment only |
| `ANTA_ENABLE_PASSWORD` | optional, if tests need enable mode |
| `ANTA_VERIFY_TLS` | default `false` (lab devices ship self-signed certs) — and **always disclosed** in output as `tls_verified`, never silently downgraded |
| `ANTA_TIMEOUT` | per-device timeout |
