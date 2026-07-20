---
name: isp-sla-claim
description: "Draft ISP service credit claims after WAN outages. Gathers evidence from Prometheus, pfSense, and dpinger logs to prove the outage was ISP-side (not CPE). Produces a ready-to-send email for human approval before filing. Tracks claim eligibility windows."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PROMETHEUS_URL"] } } }
---

# ISP SLA Claim — Outage Credit Request

Draft and track service credit claims against the ISP (Quantum Fiber) after WAN
outages. Produces evidence-backed claim emails for human review before sending.

## When to Use

- WAN outage resolves after >1 hour of downtime
- Alert fires: `QuantumFiberOutageCreditEligible` (>4h outage)
- User asks "should I file a claim for that outage?"
- User asks "how long was the internet down last week?"
- Periodic check: "any unclaimed outages this month?"

## ISP Details

| Field | Value |
|-------|-------|
| Provider | Quantum Fiber (AT&T) |
| Support email | ${ISP_SUPPORT_EMAIL} |
| Account | ${ISP_ACCOUNT_USERNAME} |
| Service address | ${ISP_SERVICE_ADDRESS} |
| Portal | https://login.quantumfiber.com/QuantumFiber/s/login/ |
| Service tier | Residential Fiber (940 Mbps / 1 Gig) |

## Procedure

### Step 1: Confirm a Claim-Worthy Outage Occurred

Query Prometheus for recent WAN outages:

```promql
# Find sustained outage windows (probe_success == 0 for extended periods)
min_over_time(probe_success{job="blackbox_wan_icmp"}[1h])

# Check the InternetDown alert history (Alertmanager)
# GET http://192.168.3.250:9093/api/v2/alerts?filter=alertname="InternetDown"
```

**Claim-worthy thresholds:**
- **>1 hour:** Worth filing (prorated daily credit)
- **>4 hours:** Strong case (significant portion of a day's service)
- **>24 hours:** Escalate — request full day credit

If no outage >1h occurred, inform the user and stop.

### Step 2: Calculate Outage Duration

Use Alertmanager alert history or Prometheus probe data:

```promql
# When did probes start failing?
min_over_time(probe_success{job="blackbox_wan_icmp"}[7d]) == 0

# Get exact timestamps from the InternetDown alert
# firing time = outage start, resolved time = outage end
```

Record:
- **Outage start:** (UTC and local time)
- **Outage end:** (UTC and local time)
- **Duration:** (hours and minutes)

### Step 3: Gather Evidence (prove it's not CPE)

Query these to build the evidence package:

| Evidence | Source | Query |
|----------|--------|-------|
| WAN probe failures | Prometheus | `probe_success{job="blackbox_wan_icmp"}` range during outage |
| pfSense was healthy | pfSense MCP | `system_status` — confirm CPU, memory, uptime normal |
| Gateway unreachable | pfSense MCP / Loki | dpinger logs showing gateway alarm state |
| LAN was operational | Prometheus | `up{instance=~"HomeSwitch.*"}` stayed 1 during outage |
| No config changes | GAIT / pfSense | `get_config_history` — no changes in 24h prior |
| Speedtest before/after | Prometheus | `speedtest_download_bits_per_second` — normal before, normal after |

**Critical evidence points:**
1. pfSense `system_status` shows UP during the entire outage window
2. dpinger logs show the ISP gateway IP went unreachable
3. All LAN devices remained reachable (proves power/CPE was fine)
4. No pfSense config changes in the 24h before the outage

### Step 4: Draft the Claim Email

Compose the email using this template, populated with real data:

```
TO: ${ISP_SUPPORT_EMAIL}
SUBJECT: Service Credit Request — Internet Outage [DATE in local time]

Account: ${ISP_ACCOUNT_USERNAME}
Service Address: ${ISP_SERVICE_ADDRESS}

I am requesting a service credit for an internet outage:

OUTAGE:
- Start: [DATE TIME Mountain Time]
- End: [DATE TIME Mountain Time]
- Duration: [X hours Y minutes]
- Impact: Complete loss of internet connectivity

MY EQUIPMENT WAS NOT THE CAUSE:
- Router/firewall (pfSense) remained fully operational (system healthy,
  all interfaces up, CPU/memory normal throughout)
- All internal network devices stayed online
- No configuration changes were made in the 24 hours prior
- Gateway health monitor confirms your upstream gateway was unreachable
  from my premises equipment

I am requesting a prorated credit for the [X] hours of service I paid
for but was unable to use due to this network outage.

Please confirm receipt and the timeline for processing this credit.

Thank you,
Byrn Baker
```

### Step 5: Post Draft for Human Approval

Post the completed email draft to Discord:

```
openclaw message send --channel discord --target ${DISCORD_ALERT_CHANNEL_ID} \
  --message "📧 **ISP Credit Claim Draft** — [X]h outage on [DATE]\n\n[full email text]\n\n✅ Reply 'send' to email to ${ISP_SUPPORT_EMAIL}\n❌ Reply 'skip' to discard"
```

**DO NOT send the email without human approval.**

### Step 6: Log to Network Guardian

Post an event to the Network Guardian dashboard:

```bash
curl -X POST "${NETWORK_GUARDIAN_URL}/api/events?site=home" \
  -H "Authorization: Bearer ${NETWORK_GUARDIAN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"message":"ISP credit claim drafted: [X]h outage on [DATE], awaiting approval","severity":"info","source":"netclaw"}'
```

### Step 7: Track the Claim (after approval)

Once the user approves and the email is sent:
- Record in memory: "Filed ISP credit claim on [DATE] for [X]h outage. Expect response in 1-2 billing cycles."
- Set a follow-up reminder: if no credit appears on the next bill, remind the user to follow up

## Autonomous Mode (triggered by alert)

When `QuantumFiberOutageCreditEligible` fires or `InternetDown` resolves after >4h:

1. Execute Steps 1-6 automatically
2. Always post the draft to Discord for approval (Step 5)
3. NEVER send the email without explicit human "send" reply
4. If outage was <1 hour, post a brief note: "WAN was down [X]min — too short for a credit claim"

## Interactive Mode

User asks "should I file a claim?" or "draft a credit request":

1. Check recent outage history (last 30 days)
2. Identify any claim-worthy outages not yet filed
3. Draft the claim for the longest/most impactful one
4. Present for approval

## What This Skill Does NOT Do

- Send emails (no SMTP MCP — drafts only, human sends)
- Access the Quantum Fiber portal
- Guarantee a credit will be granted (ISP discretion)
- File claims for outages caused by local equipment/power

## References

- Full SLA details: `workspace/reference/lumen-fiber-sla.md`
- Subscriber agreement (ingest to RAG): https://quantumfiber.com/on/demandware.static/Sites-QFCC-Site/Sites-QFCC-Library/-/legal/internet-subscriber-agreement.pdf
- Quantum Fiber support: https://www.quantumfiber.com/support/contact.html
