# Quickstart — Fortinet Coverage (spec 080 / R3)

Operator guide: build the verification lab, obtain credentials, run the server.

> **Read the licence-clock rule before booting anything.** FortiGate's evaluation licence is
> **permanent**. FortiManager's and FortiAnalyzer's are **15 days from first boot**, and there is no way
> to pause them. Boot the trial VMs **only when the server is ready to be verified** — Stage 7 of the
> plan, not Stage 1. Booting all three at the start spends the verification window on implementation.

---

## 0. What you need

- A free **FortiCloud / FortiCare** account — <https://support.fortinet.com>. One account covers all
  three products. Registration is free; no purchase, no sales contact.
- **Hyper-V** — all three appliances. **containerlab is not used.** It has exactly one Fortinet kind
  (`fortinet_fortigate`, verified against the binary) and none for FortiManager or FortiAnalyzer, so it
  could only ever have covered one plane of three.

**There is no hosted alternative.** Fortinet's Demo Center is GUI-only with no API; FNDN requires
sponsorship by two Fortinet employees. This was researched, not assumed — see the spec's Clarifications.

**Nothing in this section is committed.** No image, licence or credential enters the repository (FR-036a).

---

## 1. FortiGate — Hyper-V, permanent licence, boot freely

Download the **Hyper-V** FGVM64 image from support.fortinet.com and import it. The reference lab runs
**FortiOS v8.0.0** (build 0167, GA).

### Networking — get this right first, it cost an afternoon

**Do not leave the VM on the Hyper-V "Default Switch".** Two reasons, the second being the serious one:

1. It is an internal NAT network reachable only from the Windows host. WSL2 — where NetClaw runs — sits on
   the external adapter and cannot route to it. Every port looks closed.
2. **Its subnet re-randomises on host reboot.** A lab pinned to a Default Switch address breaks silently
   later, which defeats FR-036a's reproducibility requirement.

Attach the VM to an **External** vSwitch and give `port1` a static address on your LAN:

```
config system interface
    edit port1
        set mode static
        set ip 192.168.2.130 255.255.255.0
        set allowaccess ping https ssh
    next
end
config router static
    edit 1
        set gateway 192.168.2.1
        set device port1
    next
end
```

`allowaccess` is not optional — FortiGate drops everything not listed, so a failed ping there says nothing
about reachability.

### Licence

Boot, then register the serial to your FortiCloud account (Dashboard → Licenses, or *support.fortinet.com
→ Asset Management → Register*). Confirm with `get system status`:

```
License Status: Valid     ← must say Valid; "Invalid" means unregistered
Model: EVAL (1)
```

**The free permanent eval is one licence per FortiCloud account.** If that account already has an eval VM
registered, a second one will not license.

**Caps, which shape what can be verified**: 1 vCPU, 2 GB RAM, **3 interfaces, 3 routes, 3 firewall
policies**. Set the VM to 1 vCPU — the licence allows no more, and extra vCPUs are wasted.

### API token

Create a least-privilege REST API admin (*System → Administrators → REST API Admin*), restricted by
trusthost to the NetClaw host. Do **not** use the `admin` password for the integration — the spec requires
token auth (FR-028).

---

## 2. FortiManager + FortiAnalyzer — Hyper-V, 15-day clocks

**Do not boot these until the server is ready to verify.**

Download the Hyper-V VM images from support.fortinet.com. *(Confirm FortiAnalyzer ships a Hyper-V image —
only the trial terms were verified in research, not the hypervisor matrix. This is an open task.)*

| | Trial | Cap |
|---|---|---|
| FortiManager-VM | 15 days, full-featured | **3 managed devices** |
| FortiAnalyzer-VM | 15 days, full-featured | **6 GB/day** of logs |

Neither needs activation — the trial is built in and starts at first boot.

Ensure WSL2 can reach both over the Hyper-V network, then:

1. Register the FortiGate to FortiManager (uses 1 of 3 device slots).
2. Point the FortiGate's logging at FortiAnalyzer.
3. Generate a read-only API token on each (FortiAnalyzer needs **7.2.2+** for token auth).

**The device cap is on devices, not rules.** FortiManager places no limit on rules per policy package, so
policy-audit and `fwrule-analyzer` verification run at realistic rule counts. Only the FortiGate's own
installed policy count is capped at 3.

---

## 3. Configure NetClaw

```bash
FORTIMANAGER_HOST=https://<fmg-ip>
FORTIMANAGER_API_TOKEN=<token>
FORTIGATE_HOST=https://<fgt-ip>
FORTIGATE_API_TOKEN=<token>
FORTIANALYZER_HOST=https://<faz-ip>
FORTIANALYZER_API_TOKEN=<token>

FORTINET_VERIFY_SSL=true     # keep true — see below
FORTINET_ALLOW_WRITES=false  # default; leave false unless testing US3
```

### Certificates

Lab appliances present **self-signed** certificates. Import each appliance's CA into the trust store
rather than setting `FORTINET_VERIFY_SSL=false`. Disabling verification exposes the API token to
interception — the same warning both community servers give.

If you must disable it for a lab, do so knowingly: it is opt-in and never the default (FR-030).

---

## 4. Verify

```bash
python3 scripts/reconcile-mcp.py            # must exit 0
python3 scripts/verify-inventory-counts.py  # 206 skills
python3 scripts/trace-skill.py fortimanager-ops
python3 scripts/trace-skill.py fortigate-ops
python3 scripts/trace-skill.py fortianalyzer-ops
```

`trace-skill.py` is the check that would have caught this feature's premise years ago — the
`fortimanager-ops` skill has always pointed at a server that was never installed.

Smoke tests, one per plane:

```bash
python3 $MCP_CALL "$FORTINET_MCP_CMD" fgt_system_status '{}'
python3 $MCP_CALL "$FORTINET_MCP_CMD" fmg_list_adoms '{}'
python3 $MCP_CALL "$FORTINET_MCP_CMD" faz_query_logs '{"adom":"root","filter":"policyid=1"}'
```

Every response must carry `plane` and `scope`. **A response missing either is a bug, not a quirk** —
that guarantee is the point of the feature.

---

## 5. Which skill answers what

| Question | Skill | Plane |
|---|---|---|
| "What policy governs this site?" | `fortimanager-ops` | manager (intent) |
| "Is the tunnel up?" | `fortigate-ops` | device (state) |
| "Has anything matched this rule?" | `fortianalyzer-ops` | analyzer (traffic) |
| "Does the device match the intent?" | `fortigate-ops` → `fgt_compare_with_manager` | both |
| "Run a command on the FortiGate CLI" | `multivendor-raw-cli` (spec 076) | CLI — **not this feature** |
| "Does this new rule overlap an existing one?" | `fwrule-analyzer`, fed from `fortimanager-ops` | analysis |

**Two traps worth internalising:**

- *No logs in a window is not an unused rule.* Retention is finite; a window is not history.
- *Manager intent is not device state.* They legitimately diverge between installs, and that gap is where
  out-of-band change lives. `fgt_compare_with_manager` reports it; it never silently picks a side.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `License Status: Invalid` | Serial not registered to a FortiCloud account | Register the serial; verify FortiGuard is reachable (`execute ping update.fortiguard.net`). Remember: **one free eval per account** |
| Appliance unreachable, all ports "closed" | VM on the Hyper-V **Default Switch** (internal NAT), or `allowaccess` omits https/ping | Move to an External vSwitch; set `allowaccess` on `port1` |
| Lab worked, breaks after a host reboot | Default Switch re-randomised its subnet | Use an External vSwitch with a static address |
| `grep -E` / `\| head` fail on the FortiGate CLI | FortiOS `grep` is a limited builtin | Use plain patterns; `config system console` → `set output standard` to stop paging |
| `auth_expired` on FortiManager | Session expired | Expected — re-establish. **Never** read this as "no policies exist" |
| Only 3 policies installable | Free-licence cap, working as intended | Not a bug; FortiManager packages are uncapped |
| `refused_no_change_record` | Gate 2 — no approved CR | Supply one, or classify the device as lab (exempts **only** this gate) |
| `refused_no_approval` | Gate 1 — no human approval | Supply `approved_by`. A CR does **not** substitute |
| Trial expired mid-work | 15-day clock ran out | Booted too early — see the rule at the top |
