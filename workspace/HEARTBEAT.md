# NetClaw Heartbeat

Periodic silent health checks. Don't dump results unless asked or something is broken.

## Checks (run silently)
- Device reachability (ping all testbed)
- CPU/Memory (flag >80% CPU or >85% memory)
- Interface errors (rising CRC/drops on uplinks)

## Reporting
- **Healthy:** One sentence: "Everything looks good across the fleet."
- **Problem:** Plain language lead, offer to investigate. Don't auto-remediate.
- **Recovered:** Brief note that it's resolved.

Post to all configured channels (Slack, WebEx, Teams).

## Cadence
- Business hours: every 30 min
- Off-hours: every 60 min
- Active incidents: every 10 min

## Rules
- Never spam technical details unprompted
- Never auto-remediate on a heartbeat
- Record in GAIT only on anomaly
