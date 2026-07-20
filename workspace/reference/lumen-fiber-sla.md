# Quantum Fiber SLA — Byrn's Home Network

## Service Details
- **Provider:** Quantum Fiber (formerly CenturyLink/Lumen, now AT&T subsidiary)
- **Service:** Residential Fiber (940 Mbps / 1 Gig)
- **Account Username:** ${ISP_ACCOUNT_USERNAME}
- **Service Address:** ${ISP_SERVICE_ADDRESS}
- **Support Email:** ${ISP_SUPPORT_EMAIL}
- **Account Portal:** https://login.quantumfiber.com/QuantumFiber/s/login/
- **Subscriber Agreement:** https://quantumfiber.com/on/demandware.static/Sites-QFCC-Site/Sites-QFCC-Library/-/legal/internet-subscriber-agreement.pdf
- **Legal/Terms page:** https://www.quantumfiber.com/legal/
- **Outage info:** https://quantumfiber.com/support/speed-performance/outages.html

## SLA Context (Residential Fiber)

Quantum Fiber residential service does NOT have a formal enterprise-style SLA
with guaranteed uptime percentages and automatic credits like Lumen DIA. However:

- The subscriber agreement defines service expectations
- Credits/compensation for extended outages are available by REQUEST
- The key is documenting the outage with evidence and requesting a billing credit

## Credit Eligibility (based on subscriber agreement terms)

| Situation | What you can claim |
|-----------|-------------------|
| Extended outage (>4 hours) | Prorated daily credit for days without service |
| Repeated outages in a billing cycle | Credit for affected days |
| Service not meeting advertised speed | Speed adjustment or credit |
| Missed repair appointment | Possible credit |

**Important:** Quantum Fiber FAQ states "Partial (prorated) refunds are not
granted if you cancel in the middle of your billing period" — but this is about
cancellation, NOT outage credits. Outage credits are a separate process.

## How to File a Claim

### Option 1: Email (RECOMMENDED — creates a paper trail)
**To:** fibersuccess@quantumfiber.com
**Subject:** Service Credit Request — Extended Outage [DATE]

### Option 2: Chat
- Via https://www.quantumfiber.com/support/contact.html
- Or via the Quantum Fiber app

### Option 3: Phone
- Support line accessible via the app or website contact page

## What to Include in a Claim

NetClaw can auto-generate this evidence package from observability data:

```
TO: ${ISP_SUPPORT_EMAIL}
SUBJECT: Service Credit Request — Internet Outage [DATE]

BODY:
Account: ${ISP_ACCOUNT_USERNAME}
Service Address: ${ISP_SERVICE_ADDRESS}

I am requesting a service credit for the following internet outage:

OUTAGE DETAILS:
- Start time: [FROM InternetDown alert firing timestamp]
- End time: [FROM InternetDown alert resolved timestamp]
- Duration: [CALCULATED]
- Service affected: Fiber internet (complete loss of connectivity)

EVIDENCE OF OUTAGE (not caused by my equipment):
- My router/firewall (pfSense) remained operational throughout the outage
  (CPU, memory, all LAN interfaces healthy — logs attached)
- All internal network devices continued functioning normally
- The failure was isolated to WAN connectivity — your gateway IP was
  unreachable from my premises equipment
- Monitoring system (Prometheus) confirms probe failures to external
  targets starting at [START] and recovering at [END]
- Gateway health monitor (dpinger) logged "alarm" state at [START],
  confirmed my CPE was actively trying to reach your network

This was not caused by:
- My equipment (firewall remained operational, all LAN services healthy)
- Power outage (UPS maintained systems throughout)
- Any changes on my side (no config changes in the 24h prior)

I am requesting a prorated credit for [X] hours / [Y] days of service
I paid for but could not use due to this outage on your network.

Please confirm receipt and expected timeline for the credit.

Thank you,
Byrn Baker
```

## NetClaw Automation — What It Can Do

When a WAN outage resolves (InternetDown alert → resolved), NetClaw can:

1. **Calculate outage duration** — from Alertmanager firing/resolved timestamps
2. **Gather evidence** — Prometheus probe data, dpinger logs, pfSense system health
3. **Prove CPE was healthy** — pfSense system_status shows UP during the outage
4. **Draft the claim email** — auto-populate the template above with real data
5. **Post to Discord for review** — you review, then forward to fibersuccess@quantumfiber.com
6. **Log to Network Guardian** — record the claim as an event for tracking

### What NetClaw CANNOT do (yet):
- Send email directly (no SMTP MCP configured)
- Submit via the Quantum Fiber portal (no API)
- Know your circuit/account ID beyond the username (check your bill for account #)

## Monitoring That Maps to Claims

| What we measure | Prometheus metric | Claim evidence |
|-----------------|-------------------|----------------|
| Complete outage | `probe_success == 0` sustained | "Internet was down from X to Y" |
| High latency | `guardian:wan_latency_ms:avg > 80` | "Service degraded, not meeting advertised performance" |
| Packet loss | `guardian:wan_loss_ratio:5m > 0.01` | "Experiencing packet loss affecting service quality" |
| Speed below advertised | `speedtest_download_bits_per_second < 700000000` sustained | "Not receiving advertised 940 Mbps speeds" |
| Gateway unreachable | pfSense dpinger alarm state | "Your gateway was unreachable from my equipment" |

## Alert Rule for Claim-Worthy Outages

```yaml
- alert: QuantumFiberOutageCreditEligible
  expr: |
    (time() - max(max_over_time(probe_success{job="blackbox_wan_icmp"}[5m])) * time())
    > 14400
  for: 0m
  labels:
    severity: critical
    service: network-guardian
    action: sla-claim
  annotations:
    summary: "WAN outage exceeds 4 hours — eligible for Quantum Fiber service credit"
    description: >
      Internet has been down for over 4 hours. Draft a credit request email
      to fibersuccess@quantumfiber.com with outage timestamps and CPE health
      evidence. Post draft to Discord for operator review before sending.
```

## Exclusions (claim will be rejected if any apply)

- Outage caused by YOUR equipment (router, power failure on your side)
- Scheduled maintenance (they notify via app/email)
- Force majeure
- Non-payment / account suspension

## Future: Full Automation

To make this fully hands-off, you'd need:
1. **SMTP MCP** — so NetClaw can send the email to fibersuccess@quantumfiber.com
2. **Human approval gate** — Draft → Discord → you reply "send" → email goes out
3. **Claim tracker** — log all claims in Network Guardian with status (filed/pending/credited/denied)

## References
- Subscriber Agreement PDF: https://quantumfiber.com/on/demandware.static/Sites-QFCC-Site/Sites-QFCC-Library/-/legal/internet-subscriber-agreement.pdf
- Internet Service Disclosure: https://www.quantumfiber.com/internet-service-disclosure.html
- Account FAQ: https://www.quantumfiber.com/support/account/account-faq.html
- Outage Support: https://quantumfiber.com/support/speed-performance/outages.html
