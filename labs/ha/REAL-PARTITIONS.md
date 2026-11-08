# REAL partition rows: topology and procedure (spec 179, R08)

Rows: **Minority partition**, **Asymmetric partition**, **Three-way partition**
(`specs/179-border-ha-authority/real-closure-plan.md`). Coordinator-operated source;
nothing here starts anything by itself. A fixture or unit result (`tests/n2n/test_ha_real_proxies_179.py`)
is not REAL evidence. Authority decisions are made from etcd, so the isolation that
matters is the Border's etcd client path.

## 1. What can and cannot be interposed (read first)

| Path | Interposable with the unmodified production node? | Reason |
|---|---|---|
| Border i -> etcd voter k (client, `ha-config.json` `etcd.endpoints`) | **Yes**, per Border | Endpoints are in the *unsigned* per-Border config; each Border gets its own listener set |
| Border -> Border NCFED cluster channel | **No** | `ha/node.py` binds `manifest.node(self)['endpoints']['cluster']` and every peer dials that **same signed** host/port (`_dial`, `start`). A proxy would need the real listener on a different port than the signed one, and per-source separation would need a per-source dial address. Neither is expressible in a manifest. |
| Border -> member / attachments (iN2N) | Not planned | same signed-endpoint property |

Consequences. Isolating Border i means cutting its three `b<i>-v*` forwarders: it can no
longer read or renew authority, so it is an isolated old leader by the same
mechanism the production code uses. The cluster/NCFED channels stay direct and are
**not** claimed as cut; every evidence packet must say `ncfed_cluster_channel_cut:false`.
Directed (asymmetric) behavior is obtained on the etcd client link (`--direction request|response`),
not per Border pair. If a literal NCFED-channel cut is later required, the minimal
production prerequisite is two optional unsigned `ha-config.json` fields (a bind override for the
cluster listener and a per-peer dial override); that is a production change and is out of scope here.

## 2. Plan and materialization (default off)

Optional plan fields (absent = `direct`, byte-for-byte unchanged behavior):

```json
"topology": "proxied",
"proxy_ports": {"etcd": [[p00,p01,p02],[p10,p11,p12],[p20,p21,p22]]}
```

`proxy_ports.etcd[i][k]` is Border i's loopback listener for voter k. Nine distinct
1024-65535 ports, distinct from every other plan port and (checked at `prepare`) from the voters' ports.
No other keys are accepted. `topology:"direct"` with `proxy_ports` is refused.

Because only the unsigned `ha-config.json` changes, the signed manifest and offline
anchor/identity preparation are untouched; **no ordering constraint against `prepare_identity`**
(`endpoints.cluster` stays as `prepare_identity` writes it).

`materialize` with `proxied`:
1. Creates `$R/proxies/` (0700, one-shot, `write_new`/`mkdir exist_ok=False`) via
   `real_proxies.init_control`: `spec.json` (owner = plan name, forwarders `b<i>-v<k>`:
   listen `127.0.0.1:proxy_ports.etcd[i][k]` -> target `127.0.0.1:voters.owned.json ports[k]`)
   and an all-pass generation-1 `policy.json`.
2. Writes each Border's `ha-config.json` `etcd.endpoints` as
   `https://127.0.0.1:<proxy_ports.etcd[i][k]>` (k = voter order). TLS is end to end: voters'
   server certs already carry the `127.0.0.1` SAN, the Border client cert/credentials are
   unchanged, and the proxy never sees keys. `profile.ha.config_sha256` binds the final config as usual.

`coordination-start` still uses the lab's direct admin store (provisioning only).

`labs/ha/real_proxies.py` must be in the frozen source map (it is a new file, so a new source map,
fixture gate and source packet are required before `prepare`).

## 3. Proxy controls

Run from the frozen source with the reviewed Python; `C=$R/proxies`, `P="$PY -I -B $S/labs/ha/real_proxies.py"`.

| Action | Command |
|---|---|
| start owned process (after `materialize`, before `start-role`) | `$P start --control $C` |
| cut Border i from etcd (block: new refused, existing severed) | `$P cut --control $C --border i` |
| one-way cut | `$P cut --control $C --border i --direction request` (Border->voter bytes dropped) or `--direction response` (voter->Border dropped); sockets stay open |
| partial (one voter) | add `--voter k` |
| heal | `$P heal --control $C --border i` / `--all` |
| delay (ms per chunk, <= 2000) | `$P delay --control $C --border i --ms N` |
| prove the cut was applied | `$P wait-applied --control $C --generation G` (G printed by cut/heal) |
| counters / observed policy | `$P status --control $C` |
| stop (pid + start time + argv bound) | `$P stop --control $C` |

Files in `$C`: `spec.json`, `policy.json` (monotone generation, atomic replace), `metrics.json`
(every 50 ms: observed rule per forwarder, active connections, `connections_accepted|refused|severed|failed_upstream`,
per direction `received|forwarded|dropped_bytes`), `events.jsonl` (append-only, one line per applied policy with
sha256 and severed counts), `owner.json` (pid, process start time, argv, source/spec sha256, ports),
`final-metrics.json` and `stopped.json` (written at stop). A cut is **observed** only when `wait-applied`
returns the generation and `events.jsonl` shows it; only changed forwarders are severed.
The proxy never interprets bytes (no TLS termination, keys never enter it).

## 4. Common preconditions (all three rows)

`prepare` (proxied plan) -> `model-start` -> `materialize` -> `coordination-start` -> `proxies start`
-> `start-role` border0/1/2/member -> `attachments` (three authenticated iN2N). Before each row:
write `counter-observations/{guard,model,native}.json` (before) and a `$P status` snapshot; confirm
`budget` shows no active slot; confirm all rules `pass` and `active_connections` > 0 (live pre-cut positive control:
`review` succeeds on every Border).

Identify the leader: `review --node borderN` returns `review.cluster.issuer_node_id`/`authority_epoch`
(`review` reserves nothing). Call the leader `L`, the others `M1`, `M2` (majority side).

Create the review that will later be approved through `L` **before** the cut and keep its file:
`review --node L > review-L.json`.

Timing: leader lease 12 s, renewal 3 s, clock uncertainty 250 ms, admission 3 s. After a cut,
wait at least `lease + clock uncertainty` (use 15 s) and re-observe rather than assuming.

## 5. Minority partition

1. Baseline as in section 4; `review --node L` -> `review-L.json`.
2. `cut --border L` (both directions); `wait-applied`; record `status`.
3. Majority elects: poll `review --node M1` until `issuer_node_id != L` and `authority_epoch` increased
   (this is a read-only review, no budget). Export M1's/M2's observation.
4. `approve --review-file review-L.json --node L`: expected refusal before dispatch
   (`authority_unavailable`/`no_quorum`, or `stale_review`). `approve_once` reserves + claims send, then
   on `operator_refused` with a status read showing `review_pending`, `attempt_count 0`,
   `may_have_executed false`, calls `Budget.refused` (slot released, **reservation still counted**).
   Anything else becomes `unknown` and holds the slot. Use `Budget.refused` only; do not hand-edit.
5. Counters unchanged: re-save `counter-observations/{guard,model,native}.json` and diff with the
   baseline (model access log request count, guard, native). Also `$P status`: etcd forwarders of `L`
   show no new forwarded bytes while cut; M1/M2 unchanged except their own traffic.
6. Positive control after step 3 (optional, budgeted): fresh `review` + `approve` through `M1`
   (this is a normal successful operation; export with `export-operation`).
7. `heal --border L`; `wait-applied`; `observe`/`status` shows L is not leader or re-attached under the
   new epoch; stale review stays refused.
8. Export before cleanup (section 8). Budget: 1 reservation (refused, slot released) (+1 for step 6).

## 6. Asymmetric partition

Directed cuts on the etcd client link of the old leader; both orientations are exercised.

A. `request` cut (`--direction request`, L's writes never reach etcd, so renewals fail and the lease lapses):
1. baseline; `review --node L` -> `review-L.json`.
2. `cut --border L --direction request`; `wait-applied`.
3. After >= 15 s: M1/M2 `review` shows a new issuer/epoch (election observed).
4. `approve --review-file review-L.json --node L` -> refused pre-dispatch (slot released via `Budget.refused`);
   model/guard/native counters unchanged.
5. **Majority distinct work exactly once**: fresh `review --node M1` (new operation id and nonce),
   `approve --node M1 --review-file ...`; do not retry; `export-operation`. Exactly-once evidence: member
   ledger, model access log delta of exactly the reviewed work, GAIT commits, budget `settled`.
6. `heal --border L`.

B. `response` cut (`--direction response`, L's writes reach etcd but L never sees the answer). This is
an observation, not an assertion: if L's renewal writes still commit, the lease may **not** lapse and no
election occurs; L's own view then expires and it refuses. Record whichever happens (epoch, issuer,
`events.jsonl`, voter logs). Approve through L (a second budget unit, owner-approved since the cap is lifted)
and require either refusal with counters unchanged, or, if L stays authoritative per etcd, stop and export
as `unknown` rather than claim a result. Never retry.

Budget: A = 2 reservations (1 refused/released, 1 majority); B = 1 more. Order inside the plan: A then B.

## 7. Three-way partition

1. baseline; create `review-0/1/2.json` (one per Border; reviews only).
2. `cut --all`; `wait-applied`. Optional heartbeat observation: all `review` calls now fail.
3. Wait >= 15 s (L's lease lapses; no one can campaign).
4. `approve` through **one** Border (reviews are leader-issued; use the leader's `review-L.json`; this is the single
   budgeted approval). Expected refusal pre-dispatch -> `Budget.refused`. For `M1/M2`, assert refusal at the
   read-only level (`status` returns retained/unavailable), **without** approving, to keep zero calls.
5. Counters (guard/model/native) unchanged across the whole window; proxy counters show only dropped/refused bytes.
6. `heal --all`; `wait-applied`; poll `review` until one Border is leader again; verify the pre-cut review is not executable
   (stale). Export. Budget: 1 reservation (refused).

## 8. Evidence to export (before any container removal)

Per row, into a fresh private directory: `$C/{spec,policy}.json`, `events.jsonl`, `metrics.json` (before cut,
during cut, after heal), `final-metrics.json`; `$P status` snapshots with timestamps; the three
`counter-observations/*.json` (before/after, retained verbatim, still marked unverified by the exporter); the
budget snapshot; `docker logs` of each owned voter `v0..v2` (election/leader-change lines) and of the owned
model container (**access/request log**, the independent model counter: `docker logs` must be copied before
`docker rm`); the original `review-*.json`, claim file, refusal output, `export-unknown` for any `unknown`;
`approve` stderr, role daemon logs (`border*-daemon.log`), `*-spawn.json`; `$P stop` then `stopped.json`.
The packet states `topology:"proxied"`, `ncfed_cluster_channel_cut:false`, the exact generations and cut directions.

## 9. Design risks

* **Admission window 3 s / etcd timeout 2 s.** `block` fails fast; one-way cut hangs until the client
  timeout (~2 s) so a refusal arrives near the 3 s admission bound. `delay` (per chunk, both directions) multiplies
  across a TLS handshake plus several etcd calls. Do not delay `M1/M2` during their approval.
* **Retained status.** `Border._route` answers `status` from a cached DTO when quorum is lost; the
  `Budget.refused` evidence therefore rests on cached review-time state, so confirm "no dispatch" independently from the
  model access log and member ledger before treating the slot as released.
* **Unknown holds the slot.** Any refusal that is not a clean pre-dispatch refusal makes the claim `unknown`
  and blocks later rows until `export-unknown` / owner decision.
* **Response-cut is not a clean partition.** It can leave authority with the old leader (section 6B).
* **No NCFED cut.** Isolated Border keeps its direct cluster/iN2N channels (section 1), so forwarded
  traffic can still reach it; authority is not derived from them.
* **Macro etcd behavior:** etcd's own client keep-alives/auth tokens survive; the heal path relies on severed
  connections and fresh TLS, tested at unit level only.
* **Ports on a shared host** are bound at start; a port taken in between fails `start` (`proxy_start_unknown`).
