# REAL qualification-only instrumentation (spec 179, lane B)

Status: SOURCE ONLY. Nothing here was run against a cluster, Docker, model or native tool. Unit tests:
`tests/n2n/test_ha_real_instrument_179.py` (local, fakes plus the real production classes' signatures).

Purpose: four REAL rows need a controlled fault *inside* the real production member or Border process.
The wire fixture did this with a test-only worker; REAL must use the actual `FederationService` role. These
files perturb one **input** or **delivery boundary**, once, for one armed operation. They never relax a
product check and never live in product paths (no file under `mcp-servers/` is modified or names them).

| File | Role |
|---|---|
| `labs/ha/real_instrument.py` | scenario table, strict config validation, one-shot claim, arm/release, evidence, class-attribute wrappers, `arm` / `release` / `create-config` CLI |
| `labs/ha/real_role_launcher.py` | used INSTEAD of `scripts/protected-role.py` for exactly the role that carries a fault |

## How it reaches the real process without a product seam

`MemberAdmission(state/'ha-member', manifest, identity)` in `ha/factory.py` passes no clocks, so a clock
cannot be injected from outside the process. Production also replaces the process (`os.execve`) twice
(`protected-role.py` -> `federation-control.py run` -> `bgp-daemon-v2.py`), so a patch made early would be lost.
The launcher therefore:

1. Stage 1 (`run`): production `protected_role.validate()` (unchanged) plus `check_qualification`, then
   `execve` the pinned contract Python `-I -B real_role_launcher.py ... stage2 <daemon path>` with the exact
   validated environment (same as `protected-role.py`; `chdir(home)`, `umask 077`).
2. Stage 2: re-validates, requires `os.environ == validated environment`, then runs `federation-control.py run`
   via `runpy`. Its final `os.execve(sys.executable, [-I,-B,bgp-daemon-v2.py], env)` is intercepted and must
   match **exactly** (executable, flags, daemon path, environment) or the process refuses. Only then are the
   scenario's wrappers installed on the already-imported frozen production classes and the same daemon file is
   run in-process (`runpy`, `__main__`). PID, daemon lock, `daemon.json` start time and nonce are unchanged.
3. The daemon path is passed as a trailing argument so production `federation-control.py stop` (`ps command`
   must contain `.../bgp-daemon-v2.py`) still owns and stops the process. `stop-role` is unchanged.

Patched surfaces (all class attributes, restored by `uninstall()` in tests):

| Row | Class attribute | Effect |
|---|---|---|
| clock | `MemberAdmission.__init__` (supply `monotonic`/`wall` only if absent; production passes none), `.begin`, `.fresh` | after the armed `begin` returns, an offset is added to ONE of the two clocks read by the admission gate only. No process-wide clock, no OS clock. `fresh` is wrapped only to record the first product refusal code. |
| stale | `MemberAttachments.send_admission` | after the real Border returns the committed claim, the member holds it, unchanged, until `release.json` or `hold_ms`, then returns it |
| result/ACK | `ClusterMemberOperations.member_result`, `.acknowledge` | result: production lookup runs, then the authenticated channel is closed and the reply is not written. ACK: channel closed before production `acknowledge` persists |
| commit | `EtcdStore._request` | for the armed operation's `admit_<kind>` txn: the real request is sent and committed, then `HAError('commit_unknown',503)` is raised; the unresolved variant also refuses the recovery read of that decision key once |

## Safety contract (what the tests prove)

- **Default off**: importing patches nothing; a process without the config is the production chain; an
  installed but un-armed instrument only writes an `installed` record.
- **Scenario-exact**: one scenario per process from a closed list; its role is fixed (member scenarios
  refuse a Border config and vice versa); parameter set and bounds are exact (`delta_ms` 400..2000, `hold_ms`
  4000..45000, `kind` model|tool, `ordinal` 1..2). Wrong operation, kind or ordinal is untouched.
- **Armed**: a second new-only 0600 file `instrument/<scenario>/arm.json` names the exact operation UUID.
  Written by the coordinator after `review` (operation ID known) and before `approve`.
- **One-shot**: `claim-<fault>.json` is created with `O_EXCL` before any fault; it survives a restart and is
  shared across Borders (all three Borders may carry the same commit config; only one fires). There is no
  retry path.
- **Evidenced**: every phase writes a new-only private file `instrument/<scenario>/<role>-<pid>-<seq>-<phase>.json`
  (class `REAL-INSTRUMENT`, run, role, operation, pid, wall/monotonic time, config hash, hashes of the affected
  envelope). If the pre-fault record cannot be written the fault is suppressed.
- **Refuses outside the REAL profile**: contract must be `<run>/contracts/<role>.json` with
  `schemaVersion 3`, `openclaw`, matching role/installation/`control_only`, home `<run>/homes/<role>`, source
  `<run>/source`; `reviewed-plan.json` run ID/name `netclaw-r08-*`; `materialized.json` launch schema 3 / profile 2;
  config and contract hashes; the launcher and `real_instrument.py` must be the plan's frozen, hash-listed
  source files; any production `validate()` refusal propagates. Config files must be private (0600, same uid).

## Common REAL procedure

Preconditions per run: fresh `prepare`; the plan `source_files` map MUST include `labs/ha/real_instrument.py`
and `labs/ha/real_role_launcher.py` (new packet, new fixture gate; both are checked against the plan hash at
launch). Unknown-producing rows each get a fresh run. Idle host during approval.

```
PY=<reviewed python>; S=<run>/source; R=<run>
$PY -I -B $S/labs/ha/real_runtime.py ... model-start | materialize | coordination-start     # as today
# 1. one config per process that carries a fault (writes <R>/instrument/<role>-<scenario>.json, new-only)
$PY -I -B $S/labs/ha/real_instrument.py create-config --root $R --role-name <member|borderN> --scenario <name> [--param k=v]
# 2. start that role through the instrumented launcher; every other role starts normally
$PY -I -B $S/labs/ha/real_runtime.py start-role --root $R --role <role> --instrument-config <config file>   # PROPOSED, see below
# 3. attachments; review; arm AFTER review, BEFORE approve
$PY -I -B $S/labs/ha/real_instrument.py arm --config <config file> --operation-id <UUID from review file>
# 4. approve / observe / export-operation or export-unknown, then stop-role (unchanged)
```

Proposed runner change (NOT applied; the runner is frozen for the running cluster agent). In `Rehearsal.start_role`
add an optional `instrument_config`; when given, require `Path(cfg).parent == root/'instrument'` and the config's
`role_name == name`, record it in `<name>-start.claim.json`/`<name>-spawn.json`, and use
`argv = [python, '-I', '-B', source/'labs/ha/real_role_launcher.py', '--contract', contract, '--instrument-config', cfg, 'run']`
instead of `scripts/protected-role.py ... run`. Add `--instrument-config` only to the `start-role` subparser. The
runner must also copy `<run>/instrument/<scenario>/` into the packet (hash each file); today's exports do not
include it. The launcher cannot start without that flag, so a default run never loads instrumentation.

Independent observations required for every row (instrument evidence is NOT sufficient alone): coordinator
counter snapshots `counter-observations/{guard,model,native}.json` immediately before approve and after settle,
including the independent model access-log counter exported before any container removal; read-only etcd
snapshot (claim/decision/operation keys, leader key and epoch); member `ha-admission.sqlite3`, inference/runner
and native journals (read through `export-unknown`); owned-process observations from the production
`daemon.json` PID/start-time.

## Row 1: Clock uncertainty (`clock-wall-step`, optionally a second run `clock-monotonic-step`)

Config: role `member`, scenario `clock-wall-step`, defaults `kind=model ordinal=1 delta_ms=1500` (any 400..2000;
the step must exceed the manifest `clock_uncertainty_ms` (250) by 100 and, for monotonic, stay 1 s under
`admission_ms` (3000) so the product returns `clock_uncertain`, not `admission_expired`; otherwise nothing is
injected and no claim is consumed).

Injected: right after the first inference admission challenge is journaled (`begin`), +1.5 s is added to the
wall input of that member's admission gate only.
Expected product behaviour: the Border still commits the claim (real etcd decision exists), the member's
`consume` -> `fresh` refuses `clock_uncertain` (409) BEFORE verifying/consuming the proof, before
`forward`/`invoke`; the admission row becomes `unknown`; the inference is `RuntimeUnknown`; no model request.
Instrument evidence: `installed`, `clock-step` (started clock readings, limits), `gate-refusal`
(`code: clock_uncertain`).
Independent: model/guard counters unchanged (zero added calls) while the etcd `admit_model` decision exists;
`ha-admission.sqlite3` row `state=unknown`, `proof_hash` NULL; native counter unchanged.
Latch: **leaves the member runner latch `uncertain`** (`ExactModelBroker` marks any inference-path exception
uncertain). One per run; use a fresh run for `clock-monotonic-step` if the owner wants both.
Approvals: 1 (wall). Settle with `export-unknown` (never releases the slot).

## Row 2: Lost result / ACK (`result-and-ack-loss`, or `result-reply-loss` / `ack-delivery-loss` separately)

Config: role `member`, no parameters. `result-and-ack-loss` injects both on one operation (two independent
claims) so one approval covers the row; the two single scenarios exist if the owner funds two approvals.
Injected: (result) after `member_result` finds the receipt, the authenticated Border channel is closed
and the reply never written; (ACK) the later `execution/ack` is delivered on a re-established attachment and
dropped before production `acknowledge` persists, channel closed. The Border's attachment loop reconnects (1 s).
Expected: no new forward/execute (the member's receipt already exists); the Border retains the operation as
`dispatch_claimed`/awaiting result, then recovers the ORIGINAL signed result (digest equals the instrument's
`envelope_sha256`) and the original ACK via the surviving attachment or another Border (`reconcile`/`observe`);
the member ends `acknowledged`. A second drop never happens (claims spent).
Evidence: `result-reply-dropped` (envelope hash, peer, interception point), `ack-delivery-dropped` (ack hash).
Independent: receipt digest in the Border authority record equals the member's; `ack_delivered` true in etcd;
model/native counters equal exactly the original 2-inference/1-effect set (nothing repeated).
Latch: does **not** leave it `uncertain` (the member finished); this row recovers, so it needs no unknown slot.
Run it with the non-unknown rows; before the stale/clock/commit runs.

## Row 3: Unknown consensus commit (`unknown-commit-recovered` first, `unknown-commit-unresolved` second)

Config: role `border` on all three Borders (same scenario, `kind=model`); the shared claim ensures only the
Border that leads when the admission arrives fires.
Injected: in the leader Border, the `admit_model` etcd transaction for the armed operation is sent and committed
for real; its reply is then dropped (`commit_unknown`). `unknown-commit-unresolved` additionally refuses the
product's recovery read of the decision key once (`no_quorum`).
Expected (recovered): `Authority.mutate` re-reads the decision key, finds its exact `decision`, treats it as
committed and returns the proof; the member proceeds; inference completes; no second claim, no re-forward.
Expected (unresolved): `commit_unknown` (503) to the member's admission RPC; the member refuses before
forward/invoke; the claim is committed but never consumed (`unknown`); no new claim or dispatch is created.
Evidence: `commit-reply-drop-armed` (decision ID, action, writes hash), `commit-reply-dropped` (real
`succeeded`, etcd revision), and for unresolved `recovery-read-refused`.
Independent: etcd snapshot shows exactly one decision with that ID and one claim key; the `decisions/<id>`
revision equals the recorded etcd revision; counters show only the original attempts.
Latch: recovered does **not** leave `uncertain` (completes). Unresolved **does** (one per run; fresh run). The owner's
closure table lists this row as unknown-producing: use the unresolved variant for that, run recovered
earlier/with the recoverable rows.
Note: this is a client-side reply drop after a real commit, not a network-level drop; a byte-level reply drop
belongs to the proxy lane (A).

## Row 4: Stale leader at the guard (`stale-leader-held-claim`)

Config: role `member`, defaults `kind=model ordinal=1 hold_ms=30000` (4000..45000; keep it above the 12 s lease
plus election and below the 60 s inference bound and 180 s operation bound).
Injected: the member receives the real committed claim from leader L (epoch E) and holds it. During the
hold the coordinator, not the instrument, moves authority.
Coordinator steps (all read-only except the one owned signal):
1. wait for `claim-held` evidence; read `details.leader_node_id`, `claim_epoch`, `commit_revision`;
2. confirm the production `daemon.json` PID/start-time for L, then `kill -STOP` that PID (owned-process only);
3. poll a read-only etcd snapshot until another node holds `leader` at epoch E' > E (lease 12 s + election);
4. `real_instrument.py release --config ...` (or let `hold_ms` expire).
Expected product behaviour: the late claim reaches the real member gate; `consume` -> `fresh` refuses
`admission_expired` (409) because elapsed > `admission_ms`; the stale proof is never consumed; no forward/invoke.
Observation that matters: the gate has no explicit epoch comparison; the defence demonstrated is the bounded
freshness window, with E < E' proven by etcd. Do not describe the refusal as epoch-based.
After refusal, `kill -CONT` L only if the packet needs L's later stale-mutation refusal (`stale_authority`); record
either way. Evidence: `claim-held` (proof hash, epoch, leader), `claim-released` (reason, held ms, same proof hash).
Independent: unchanged counters; admission row `unknown`; etcd claim exists with epoch E and leader key now E'.
Latch: **leaves the member runner latch `uncertain`**; one per run; fresh run. Approvals: 1.

## Risks

1. **In-process daemon, not the exec'd chain.** Instrumented roles run `bgp-daemon-v2.py` under `runpy` inside the
   launcher process (needed to keep wrappers). Behaviour should be identical (same interpreter flags, env, PID,
   lock) but it is a different process image: `sys.argv[0]`, `__main__` module identity and the launcher frames
   differ. A packet must state that the faulted role used the qualification launcher. Not evidence of an unmodified
   process for that role; mitigated by exact exec-chain and environment equality checks.
2. **Early import of production modules** (`bgp.federation.ha.*`) before the daemon imports them. Import-order side
   effects are believed nil, but only a real start proves it.
3. **Clock row is an input perturbation, not an OS clock step.** It proves the admission gate's two-clock
   disagreement logic, not NTP/kernel behaviour. The offset applies to this member's gate only.
4. **Stale-leader row proves the freshness bound**, not epoch checking at the guard (none exists there).
   A hold above 5 s cannot be done at the Border (the member RPC timeout is 5 s), hence the member-side hold.
5. **Commit drop is client-side** and the recovered variant is the product's designed recovery; whether the
   closure table row requires the unresolved (unknown) outcome is an owner/coordinator call.
6. **Frozen-source and gate cost.** Two new source files change `source_sha256`: new packet, new fixture gate,
   re-freeze. The runner patch (start-role flag, export of the instrument directory) is also source.
7. **Restart-one-shot**: the member `start-role` claim is one-shot per run, so a combined multi-scenario run needs
   the member started once with a scenario that covers all intended faults (`result-and-ack-loss` exists for
   that); unknown-producing scenarios remain one per run.
8. **Runner-owned Border selection**: the commit config must be created for all three Borders; a Border started
   without it cannot fire, so a leader without the config silently leaves the row un-injected (the evidence
   directory then has no `commit-reply-dropped`; the packet must treat that as a not-run row, not a pass).
9. **Evidence is self-reported by the process under test**; it is corroborated only by the independent
   observations listed above. Do not promote instrument evidence alone.

## Production seam

None is unavoidable and none was applied. A default-off clock parameter on `from_service`/`MemberAdmission` would
be cleaner than the `__init__` wrapper but would put a qualification input into product code, which
`real-runtime.md` forbids; it is not recommended.
