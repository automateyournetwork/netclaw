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
- [ ] **Token Usage** — Session token count, cost, TOON savings percentage
- [ ] **Top 5 Token-Expensive Operations** — Ranked by total tokens consumed

## How to Check In

Send heartbeat check-ins to **all configured channels** — Slack, WebEx, and Teams (if enabled). Use the same message content adapted to each channel's formatting:

### Slack
- Use the `message` tool to post to the configured heartbeat channel
- Keep it one sentence when healthy; use Slack Block Kit for problem summaries

### WebEx
- If `WEBEX_BOT_TOKEN` and `WEBEX_ALERTS_ROOM_ID` are set, also check in to WebEx
- Use the WebEx Messages API to post to the configured room
- Use Adaptive Cards for problem summaries (attention style for failures, good style for all-clear)
- Plain text is fine for healthy check-ins

### Teams
- If Microsoft Graph is configured, also post to the designated Teams channel

### Message Format

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
- **ALWAYS include token usage summary in heartbeat check-ins**:
  - Session token count and estimated cost
  - TOON savings percentage (tokens saved vs JSON equivalent)
  - Top 5 most token-expensive operations this session
  - Example: "Session so far: 45,231 tokens ($0.42). TOON saved 38% (27,890 tokens). Top consumer: pyats_show_interfaces (12,450 tokens)."
