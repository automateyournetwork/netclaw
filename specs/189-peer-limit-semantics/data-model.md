# Data Model (additive SQLite, federation.db)

```sql
CREATE TABLE IF NOT EXISTS peer_limit_policy (
  peer_identity   TEXT PRIMARY KEY,      -- '*' = node-wide defaults + global aggregate caps
  rate_per_min    INTEGER,               -- NULL = inherit
  daily_requests  INTEGER,
  daily_tokens    INTEGER,
  action          TEXT,                  -- refuse|warn|teardown, NULL = inherit
  warn_threshold  REAL,                  -- (0,1], NULL = inherit
  restart_timer_s INTEGER,               -- >=0, NULL = inherit
  updated_at      TEXT NOT NULL
);
-- For '*': daily_requests/daily_tokens are the GLOBAL aggregate caps (NULL = off);
-- they are NOT inherited as per-peer defaults. Per-peer defaults for '*' rows come only from
-- action, warn_threshold, restart_timer_s.
CREATE TABLE IF NOT EXISTS limit_hold_down (
  peer_identity TEXT PRIMARY KEY,
  until_epoch   REAL NOT NULL,
  reason        TEXT NOT NULL,
  started_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS limit_warning (
  peer_identity TEXT NOT NULL,
  day           TEXT NOT NULL,
  limit_name    TEXT NOT NULL,           -- requests|tokens|global_requests|global_tokens
  warned_at     TEXT NOT NULL,
  PRIMARY KEY (peer_identity, day, limit_name)
);
```
Global usage: `budget_counter` row with `peer_identity='*'` (existing table).

Validation: ints >= 0 (0 = deny all), threshold in (0,1], action in set, restart >= 0. Invalid -> ValueError, no change.

Audit decisions (remote_invocation_record.decision): `limit_warning`, `limit_exceeded_warned`, `limit_exceeded_refused`, `limit_teardown`, `limit_hold_down_refused`, `limit_reset`, `limit_config`; `target_type='limit'`, `target_name=<limit name>:<scope peer|global>`.

State: peer is `normal` -> `warned` (latch, per day) ; `exceeded` ; `held-down` (teardown until timer/clear) -> `normal`.
