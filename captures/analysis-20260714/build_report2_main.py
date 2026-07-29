#!/usr/bin/env python3
"""Assemble the full engineer-grade report (part 2 — page body)."""
import html as H
from build_report2 import (
    S1, S2, S5, INK, INK2, MUTE, GRID, AXIS, SURF, GOOD, SER, CRIT,
    FRAME_HDR, HANDSHAKE, BGP_KA, HEARTBEAT, topo, seq_diagram,
    chart_traffic, chart_types, chart_latency, hexdump, chips, PAGE_CSS)

# ── exact captured payload hex ──────────────────────────────────────────────
PAYLOADS = {}
cur = None
for line in open("payloads.txt"):
    line = line.strip()
    if line.startswith("FRAME "):
        cur = int(line[6:-1])
    elif line and cur is not None:
        PAYLOADS[cur] = line

# frame 1 full stack (verified against tshark -x)
F1_LINK = "08000000000000020001000 6bc9a8eebf1410000".replace(" ", "")
F1_LINK = "0800000000000002000100066bc9a8eebf14100 00".replace(" ", "")  # 20 B
F1_LINK = "08000000" + "00000002" + "0001" + "0006" + "bc9a8eebf141" + "0000"
F1_IP   = "450000" + "47c9cf4000" + "7306f617" + "0313822b" + "c0a801e3"
F1_IP   = "45000047" + "c9cf4000" + "7306" + "f617" + "0313822b" + "c0a801e3"
F1_TCP  = "4eeba81a" + "06f2e534" + "8c2c33af" + "801800f5" + "839b0000" + "0101080a" + "f8da4cd8" + "5f585e21"
F1_BGP_MARK = "ff"*16
F1_BGP_TAIL = "001304"

DIS_KEEPALIVE = hexdump([
    (F1_LINK, "c-link"), (F1_IP, "c-ip"), (F1_TCP, "c-tcp"),
    (F1_BGP_MARK, "c-hdr"), (F1_BGP_TAIL, "c-pay")])

def ncfed_dissect(frame_no, max_rows=None):
    pl = PAYLOADS[frame_no]
    return hexdump([(pl[:8], "c-hdr"), (pl[8:10], "c-hdr"), (pl[10:], "c-pay")], max_rows=max_rows)

DIS_HB     = ncfed_dissect(5)
DIS_EP     = ncfed_dissect(7)
DIS_DENY   = ncfed_dissect(118)
DIS_RESULT = ncfed_dissect(853, max_rows=6)

CHIP_FULL  = chips(("c-link","linux-sll2 (20 B)"),("c-ip","IPv4 (20 B)"),("c-tcp","TCP + opts (32 B)"),("c-hdr","BGP marker/len"),("c-pay","BGP fields"))
CHIP_NCFED = chips(("c-hdr","NCFED header — length (uint32) + flags"),("c-pay","JSON-RPC 2.0 payload (UTF-8)"))

# ── method table ────────────────────────────────────────────────────────────
METHODS = [
    ("n2n/endpoint_update","both → both",114,"153 B","75 B","34.5 ms","re-announce own public endpoint (ngrok host:port); ran every ~28 s per side"),
    ("n2n/chat/open","John → Nick",3,"110 B","127 B","2.3 ms","create operator chat session (returns session_id)"),
    ("n2n/chat/message","John → Nick",3,"303 B","308 B","18.0 s","chat turn — response carries the full agent reply (latency = LLM turn)"),
    ("n2n/tasks/submit","John → Nick",4,"388 B","137 B","12.4 ms","async skill delegation; authz check → task_id or error −32001"),
    ("n2n/tasks/result","John → Nick",12,"136 B","389 B","0.5 ms","poll task state; final poll returned the 3,114 B completed report"),
    ("n2n/tasks/cancel","John → Nick",1,"137 B","127 B","0.5 ms","cancel request — returned cancelled=false (finding 2)"),
    ("heartbeat (len=0)","both → both",115,"5 B","—","—","liveness proof; 30.0 s server-side, ~27.3 s client-side"),
]

TL = [
 ("14:03:05","—","info","Capture starts","tcpdump -i any 'tcp port 20203'; both channels already established (mid-stream — handshake &amp; inventory pre-date the window)."),
 ("14:03:54","John → Nick","chat","n2n/chat/open + message","“Is your NetClaw a standalone claw or a risk?” — federation topology question."),
 ("14:04:13","Nick → John","chat","chat reply (433 B)","“Standalone claw — 0 members, 2 federated peers.” 19.8 s round-trip (agent turn)."),
 ("14:05:55","John → Nick","deny","n2n/tasks/submit №1 · frame 116","pyats-health-check vs 20-Node v2 lab. <b>DENIED</b> in 21 ms — error −32001, frame 118."),
 ("14:07:10","John → Nick","deny","n2n/tasks/submit №2","Testbed-wide variant. <b>DENIED</b> — −32001 again. Fail-closed authz holds."),
 ("14:08:04","John → Nick","chat","chat ×2 + replies","Traffic-gen pings for this capture demo; both round-trips acknowledged (~18 s each)."),
 ("14:09:05","operator","grant","grant applied (off-wire)","POST /n2n/grants on localhost:8179 → grant id 3, skill pyats-health-check for as65001-4.4.4.4. Correlated from federation.db — not visible on port 20203."),
 ("14:10:18","John → Nick","ok","n2n/tasks/submit №3 · frame 295","<b>ACCEPTED</b> in 6 ms → task 83d1176e… state=submitted (frame 296). First post-grant delegation."),
 ("14:14:18","John → Nick","ok","n2n/tasks/submit №4","20-node lab variant → task 9751b33a… Both tasks now in flight."),
 ("14:10–14:24","John → Nick","info","n2n/tasks/result ×12","Poll loop across both tasks, ~60–170 s apart; every reply state=working; each answered in &lt;1 ms."),
 ("14:24:43","Nick → John","good","task 9751b33a completed · frame 853","3,114 B result in a single NCFED frame (one loopback TCP segment) — full 14-device fleet health report. 10 m 25 s wall-clock."),
 ("14:29:30","John → Nick","warn","n2n/tasks/cancel 83d1176e","Reply: cancelled=false in 0.5 ms. Task №3 never left “working” and refused cancellation."),
 ("14:30:21","—","info","Capture stops","1,059 packets on file."),
]
BADGE = {"deny":("✕ DENIED",CRIT),"ok":("✓ ACCEPTED",GOOD),"good":("✓ COMPLETED",GOOD),
         "warn":("⚠ ANOMALY",SER),"grant":("● GRANT",S5),"chat":("» CHAT",INK2),"info":("· INFO",MUTE)}

def timeline_rows():
    out = []
    for t, dirn, kind, what, note in TL:
        label, color = BADGE[kind]
        out.append(f'<tr><td class="t">{t}</td><td class="t">{H.escape(dirn)}</td>'
                   f'<td><span class="badge" style="color:{color};border-color:{color}55">{label}</span></td>'
                   f'<td><b>{H.escape(what)}</b><br><span class="note">{note}</span></td></tr>')
    return "\n".join(out)

def method_rows():
    out = []
    for m, d, n, rq, rs, lat, desc in METHODS:
        out.append(f'<tr><td class="mono" style="font-size:9px">{H.escape(m)}</td><td class="t">{H.escape(d)}</td>'
                   f'<td class="num">{n}</td><td class="num">{rq}</td><td class="num">{rs}</td>'
                   f'<td class="num">{lat}</td><td class="note">{H.escape(desc)}</td></tr>')
    return "\n".join(out)

legend_traffic = (f'<div class="legend"><span><i style="background:{S2}"></i>stream 0 — BGP mesh session (ens18, cleartext)</span>'
                  f'<span><i style="background:{S1}"></i>stream 1 — NCFED JSON-RPC channel (loopback via ngrok)</span></div>')

page = f"""<meta charset="utf-8">
<title>NCFED on the Wire — N2N Federation Protocol Analysis</title>
<style>{PAGE_CSS}</style>

<h1>NCFED on the Wire</h1>
<div class="sub">A packet-level walkthrough of NetClaw N2N federation — peering <b>as65007-7.7.7.7 (Nick)</b> ⇄ <b>as65001-4.4.4.4 (John / johns-risk)</b>, including a complete skill-delegation lifecycle with live authorization denials.</div>
<div class="meta">captures/n2n-session-20260714.pcap · 2026-07-14 14:03:05 → 14:30:21 EDT · capture filter <span class="mono">tcp port 20203</span> · interface <span class="mono">any</span> (linux-sll2) · decoded with an NCFED frame parser implementing the <span class="mono">bgp/federation/channel.py</span> wire format · frame numbers reference the pcap</div>

<div class="kpis">
 <div class="kpi"><div class="v">1,059</div><div class="l">packets</div></div>
 <div class="kpi"><div class="v">27 m 15 s</div><div class="l">duration</div></div>
 <div class="kpi"><div class="v">115 kB</div><div class="l">wire data</div></div>
 <div class="kpi"><div class="v">446</div><div class="l">protocol messages decoded</div></div>
 <div class="kpi"><div class="v">137</div><div class="l">JSON-RPC req/resp pairs</div></div>
 <div class="kpi"><div class="v">0</div><div class="l">retransmits / dup ACKs</div></div>
</div>

<h2>Executive summary</h2>
<p>This capture records a complete <b>eN2N skill-delegation lifecycle</b> between two federated NetClaw agents. John's agent opened chat sessions, attempted to delegate the <span class="mono">pyats-health-check</span> skill twice and was <b style="color:{CRIT}">denied both times</b> (JSON-RPC error −32001 in ~20 ms), the authorization layer failing closed exactly as designed. After the operator granted the skill at 14:09:05 — a local API action, deliberately invisible on the wire — identical re-submissions were <b style="color:{GOOD}">accepted in 6 ms</b>. One task completed in 10 m 25 s and returned a 3,114-byte fleet health report; the other <b style="color:{SER}">stalled in “working”</b> and refused a cancel — the one genuine anomaly. Transport was flawless: zero retransmissions, zero duplicate ACKs, heartbeats never missed.</p>

<h2>Topology — what the two TCP streams actually are</h2>
{topo()}
<p class="flow">Both streams are the <b>same peering</b> seen from different sides. Stream 0 is Nick's daemon dialing John's published ngrok TCP endpoint — a genuine RFC 4271 BGP session used for mesh liveness (KEEPALIVEs only in this window; no UPDATEs). Stream 1 is John dialing <i>Nick's</i> ngrok endpoint; the local ngrok agent terminates the tunnel and delivers it from loopback, which is why the NCFED channel appears as <span class="mono">127.0.0.1 ⇄ 127.0.0.1</span>. Peer Byrn (as65099) has no direct endpoint and generated no traffic in the window.</p>

<h2>Wire formats observed</h2>
<div class="layouts">{FRAME_HDR}{HANDSHAKE}{HEARTBEAT}{BGP_KA}</div>
<p class="flow">NCFED is length-prefixed JSON-RPC 2.0 over TCP: every message is a 5-byte <span class="mono">!IB</span> header followed by a UTF-8 JSON body. A zero-length frame is a heartbeat. Payloads over 64 kB are chunked with the continuation flag (none needed in this session — largest frame was 3,114 B). The 13-byte handshake exchanges AS number and router-id before any frames flow; this session's handshakes pre-date the capture (see <span class="mono">ncfed-session.pcap</span> from 2026-07-13 for a captured handshake, <span class="mono">n2n/hello</span>, and the 46 kB inventory exchange).</p>

<div class="pagebreak"></div>
<h2>JSON-RPC method inventory — everything seen on stream 1</h2>
<table>
<tr><th>Method</th><th>Direction</th><th class="num">Count</th><th class="num">Avg req</th><th class="num">Avg resp</th><th class="num">Median RTT</th><th>Purpose (as observed)</th></tr>
{method_rows()}
</table>
<p class="flow">Request IDs are namespaced by sender identity (<span class="mono">"as65001-4.4.4.4:35"</span>) — both sides can issue requests on one connection without ID collisions. Every request got exactly one response; no orphans, no duplicates, no reordering.</p>

<h2>Response latency by method — three timing regimes</h2>
{chart_latency()}
<p class="flow">The spread is diagnostic: <b>sub-millisecond</b> methods are pure SQLite reads/writes in the daemon; <b>tens of milliseconds</b> involve authz checks or endpoint upserts; <b>~18 seconds</b> is a full LLM agent turn — <span class="mono">chat/message</span> blocks synchronously on the reply, which is exactly why <span class="mono">tasks/submit</span> is async (submit → poll → result) for long-running skills.</p>

<h2>Session sequence — the delegation lifecycle</h2>
{seq_diagram()}

<h2>Traffic over time — bytes per minute</h2>
{legend_traffic}
{chart_traffic()}
<p class="flow">The ≈3.4 kB/min floor is pure control plane: heartbeats, BGP keepalives, and the endpoint re-announce loop (finding 3). The 14:24 spike is the completed health-check result.</p>

<h2>Message-type breakdown — all 446 decoded messages</h2>
{chart_types()}
<p class="flow">Substantive agent work — chat, submits, polls, one result, one cancel — is 25 messages (5.6%). Everything else is liveness and endpoint chatter.</p>

<h2>Liveness cadence &amp; transport health</h2>
<div class="two">
<div><table>
<tr><th>Timer</th><th class="num">Observed</th><th class="num">Jitter (min–max)</th></tr>
<tr><td>NCFED heartbeat — Nick's daemon</td><td class="num">30.0 s</td><td class="num">30.0 – 30.0 s</td></tr>
<tr><td>NCFED heartbeat — John's client</td><td class="num">27.3 s</td><td class="num">27.2 – 29.8 s</td></tr>
<tr><td>BGP KEEPALIVE — Nick (local)</td><td class="num">60.0 s</td><td class="num">60.0 – 60.0 s</td></tr>
<tr><td>BGP KEEPALIVE — John (remote)</td><td class="num">54.5 s</td><td class="num">54.5 – 58.4 s</td></tr>
</table></div>
<div><table>
<tr><th>TCP pathology check (tshark analysis flags)</th><th class="num">Count</th></tr>
<tr><td>Retransmissions</td><td class="num">0</td></tr>
<tr><td>Duplicate ACKs</td><td class="num">0</td></tr>
<tr><td>Zero-window events</td><td class="num">0</td></tr>
<tr><td>Out-of-order segments</td><td class="num">0</td></tr>
</table></div>
</div>
<p class="flow">The daemon's timers are metronomic (jitter only on the remote/client sides, where event-loop scheduling shows). The 3,114 B result crossed loopback in a <b>single TCP segment</b> (64 kB loopback MSS); on the internet path the same frame would span ~3 segments at a 1,460 B MSS — still one NCFED frame after reassembly.</p>

<h2>Session timeline — the conversation, diagnosed</h2>
<table>
<tr><th style="width:60px">Time (EDT)</th><th style="width:74px">Direction</th><th style="width:76px">Verdict</th><th>Event</th></tr>
{timeline_rows()}
</table>

<h2>Packet dissections — real captured bytes, annotated</h2>

<div class="dissect"><h3>Frame 1 — BGP KEEPALIVE from John's endpoint (full stack)</h3>
{CHIP_FULL}
{DIS_KEEPALIVE}
<div class="cap"><span class="mono">14:03:05.610276 · 3.19.130.43:20203 → 192.168.1.227:43034 · [PSH,ACK]</span> — RFC 4271 §4.4: 16-byte all-ones marker, length 0x0013 (19), type 0x04 (KEEPALIVE). TTL 0x73 (115) — the path transits ngrok's edge. This is the entire mesh-liveness message; no BGP UPDATE appeared all session.</div></div>

<div class="dissect"><h3>Frame 5 — NCFED heartbeat (the whole message is 5 bytes)</h3>
{CHIP_NCFED}
{DIS_HB}
<div class="cap"><span class="mono">14:03:12.588192 · 127.0.0.1:33466 → 127.0.0.1:20203</span> — length=0, flags=0. Any inbound frame proves liveness; <span class="mono">NCFED_HEARTBEAT_MISS_LIMIT</span> consecutive silent intervals close the channel.</div></div>

<div class="dissect"><h3>Frame 7 — n2n/endpoint_update (the re-announce loop, finding 3)</h3>
{CHIP_NCFED}
{DIS_EP}
<div class="cap"><span class="mono">14:03:12.762144 · Nick → John</span> — header <span class="mono">00 00 00 94 00</span>: length 0x94 = 148 bytes, flags 0. Nick re-announces his own tunnel endpoint (<span class="mono">8.tcp.ngrok.io:XXXXX</span>). This exact message repeated 57× per side with an unchanged endpoint value.</div></div>

<div class="dissect"><h3>Frame 118 — authorization denial (the −32001 error, complete)</h3>
{CHIP_NCFED}
{DIS_DENY}
<div class="cap"><span class="mono">14:05:55.987033 · Nick → John · 21 ms after submit frame 116</span> — header length 0x8e = 142 bytes. JSON-RPC error object; the request ID <span class="mono">as65001-4.4.4.4:35</span> ties it to the denied submit. Note what's absent: no capability leak — the error names only the skill and peer, not what <i>is</i> granted.</div></div>

<div class="dissect"><h3>Frame 853 — the delivered result (3,114 B frame, first 96 bytes)</h3>
{CHIP_NCFED}
{DIS_RESULT}
<div class="cap"><span class="mono">14:24:43.593893 · Nick → John</span> — header <span class="mono">00 00 0c 25 00</span>: length 0x0c25 = 3,109 bytes, flags 0 (no chunking needed). Carries <span class="mono">state:"completed"</span> plus the full markdown fleet-health report as <span class="mono">output_text</span>. Readable in cleartext — see finding 4.</div></div>

<h2>Findings</h2>

<div class="finding good"><h3>1 · Authorization enforcement verified on the wire — fail-closed, then open after grant</h3>
Two <span class="mono">n2n/tasks/submit</span> requests (14:05:55 frame 116, 14:07:10) were rejected with <span class="mono">−32001 “skill 'pyats-health-check' not allowlisted for as65001-4.4.4.4”</span> in ~20 ms while ungranted. Identical submissions at 14:10:18 (frame 295) and 14:14:18 — after grant id 3 landed at 14:09:05 — were accepted in 6 ms. The deny → grant → allow transition is fully visible in the trace, with no bypass path and no capability enumeration leaked in the error.</div>

<div class="finding warn"><h3>2 · Task 83d1176e stalled for 19 minutes and refused cancellation</h3>
The first accepted task (14:10:18, testbed-wide health check) was polled 7 times over 19 minutes and never left <span class="mono">state=working</span>, while its near-duplicate submitted 4 minutes later completed in 10 m 25 s. John's <span class="mono">n2n/tasks/cancel</span> at 14:29:30 returned <span class="mono">cancelled=false</span> in 0.5 ms — the daemon answered from local state without attempting runner termination. Two issues: (a) why the first runner never finished — likely both tasks contending for the same testbed; (b) cancel should terminate a working task or say why it can't. Check <span class="mono">delegated_task</span> for 83d1176e… and the runner logs.</div>

<div class="finding warn"><h3>3 · endpoint_update re-announce loop is 64% of all NCFED JSON-RPC traffic</h3>
114 <span class="mono">n2n/endpoint_update</span> requests (57 per side, one every ~28 s) plus 114 responses — ~26 kB of the channel's 94 kB — re-announced tunnel endpoints that <b>never changed</b> (frame 7's <span class="mono">8.tcp.ngrok.io:XXXXX</span> is byte-identical all session). Re-announce should be event-driven (on tunnel change) with a slow refresh, not a sub-30-second loop; at fleet scale this dominates channel cost.</div>

<div class="finding crit"><h3>4 · The federation channel is cleartext — chat and task results readable on the wire</h3>
Every chat message, task input, and the complete 3,114-byte health report (device names, IGP/BGP topology detail) were recovered from this capture by parsing 5-byte headers. The BGP mesh session to <span class="mono">3.19.130.43:20203</span> is cleartext on the actual internet path; the NCFED channel's privacy rests entirely on ngrok's tunnel transport. Feature 056 already ships per-peer pinned keys under <span class="mono">~/.openclaw/n2n/keys/</span> — wiring TLS onto the eN2N channel would close this.</div>

<div class="finding info"><h3>5 · Protocol correctness &amp; transport health: excellent</h3>
137 request/response pairs, every ID matched, no orphans or duplicates. Heartbeats metronomic at 30.0 s (zero misses in 27 min); BGP keepalives steady. Zero TCP retransmissions, duplicate ACKs, zero-window or out-of-order events across 1,059 packets. Async task design confirmed on the wire: submits return in ms while the 18 s agent turns ride <span class="mono">chat/message</span> only.</div>

<h2>Delivered payload — what the delegation produced</h2>
<div class="card">
<b>Fleet Health Check — “NetClaw True CCIE Enterprise 20-Node v2”</b> (task 9751b33a…, completed 14:24:43, frame 853)
<ul>
<li><b>14/14 devices reachable</b>, all protocols converged: 50/50 BGP sessions UP, 26/26 OSPF FULL adjacencies, both EIGRP AS10/AS20 neighbors UP.</li>
<li>Zero CRC / input / output errors fleet-wide; CPU 0–1%, memory uniform at 17.3–17.6%.</li>
<li>Overall <b>⚠ WARNING from a single cause</b>: every device's uptime ≈ 37 min (&lt; 24 h threshold) — lab freshly started; expected.</li>
<li>R1/R2 correctly show 9 BGP sessions each (iBGP route reflectors); R7/R8/R12/R13 OSPF=0 by design (EIGRP branch LANs, eBGP-only ISP nodes).</li>
</ul>
</div>

<h2>Reproducing this analysis</h2>
<div class="card"><span class="mono" style="font-size:9px">
sudo tcpdump -i any -nn -s 0 'tcp port 20203' -w n2n-session.pcap&nbsp;&nbsp;# capture both mesh + federation channels<br>
tshark -r n2n-session.pcap -q -z conv,tcp&nbsp;&nbsp;# find the streams<br>
tshark -r n2n-session.pcap -Y 'tcp.len&gt;0' -T fields -e frame.time_epoch -e tcp.stream -e tcp.payload&nbsp;&nbsp;# extract payloads<br>
# then parse: 13 B handshake (magic "NCFED" + !I AS + router-id), else 5 B !IB header + JSON-RPC body; len=0 ⇒ heartbeat
</span></div>
"""

open("report2.html", "w").write(page)
print("report2.html written,", len(page), "chars")
