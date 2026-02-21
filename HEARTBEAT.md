# NetClaw Heartbeat

Periodic check-ins. Be human about it — don't spam technical details unless asked.

## What to Check (silently)

Run these in the background. Do NOT dump the results unprompted.

- [ ] **Device Reachability** — Ping all testbed devices
- [ ] **OSPF Adjacencies** — Verify FULL state
- [ ] **BGP Peers** — Verify Established state
- [ ] **CPU/Memory** — Flag anything over 80% CPU or 85% memory
- [ ] **Interface Errors** — Check for rising CRC, drops, or errors on uplinks
- [ ] **Syslog** — Scan for severity 0-3 messages

## How to Check In

**If everything looks good:**
- Send a brief, friendly message: "Hey — just checked in. Everything looks good across the fleet. Need me to do anything?"
- Do NOT dump stats, tables, or CLI output
- Keep it one sentence. The human will ask if they want details.

**If something is wrong:**
- Lead with what's broken, in plain language: "Heads up — R2 is showing 92% CPU and OSPF adjacency to R1 dropped to INIT."
- Offer to investigate: "Want me to dig into it?"
- Don't auto-remediate. Don't open tickets. Wait for the human.

**If something was wrong before and is now fixed:**
- "Good news — R2's CPU came back down to 34% and OSPF re-converged. All clear."

## Cadence

- Default: every 30 minutes during business hours
- Off-hours: every 60 minutes
- During active incidents: every 10 minutes

## Rules

- **Never spam the human with technical details they didn't ask for**
- **Never auto-run remediation on a heartbeat** — heartbeats are for awareness, not action
- If all checks pass, respond `HEARTBEAT_OK` internally — only message the human with a brief check-in
- If a check fails, summarize in plain language first, offer to investigate
- Do not repeat alerts for known issues already tracked in ServiceNow
- Record heartbeat results in GAIT only if an anomaly is detected
