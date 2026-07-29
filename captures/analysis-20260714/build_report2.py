#!/usr/bin/env python3
"""N2N capture — engineer-grade protocol analysis report (weasyprint, print/light)."""
import html as H
import math

# ── palette (dataviz reference, light) ──────────────────────────────────────
S1, S2, S5 = "#2a78d6", "#1baf7a", "#4a3aa7"
INK, INK2, MUTE = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURF = "#e1e0d9", "#c3c2b7", "#fcfcfb"
GOOD, SER, CRIT = "#0ca30c", "#ec835a", "#d03b3b"
# hex-dissection tints (light washes of the palette)
T_LINK, T_IP, T_TCP, T_HDR, T_PAY = "#efefec", "#fdf3d9", "#e2f6ee", "#eceafa", "#e3eefc"

ncfed = [3890,3530,3500,3176,4487,4252,2948,4090,3154,3670,3514,4119,3303,3226,4164,3226,2660,2809,3154,3176,2660,6126,2809,2662,3182,2664,3216,816]
bgp   = [921,758,758,614,758,758,758,758,758,758,921,758,758,758,758,758,758,758,758,758,921,758,758,758,758,758,758,144]
msg_types = [
    ("JSON-RPC responses", 135), ("NCFED heartbeats", 115), ("n2n/endpoint_update", 114),
    ("BGP KEEPALIVE", 57), ("n2n/tasks/result (polls)", 12), ("n2n/tasks/submit", 4),
    ("n2n/chat/open", 3), ("n2n/chat/message", 3), ("errors (-32001)", 2), ("n2n/tasks/cancel", 1),
]

# ═══════════════════ SVG helpers ═══════════════════
def svg(w, h, body, cls=""):
    return f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="system-ui,sans-serif" class="{cls}">{body}</svg>'

# ── byte-layout (RFC-style) diagrams ────────────────────────────────────────
def byte_layout(title, total_label, fields, W=330):
    """fields: (n_units, label, sub, tint) drawn proportional to n_units."""
    rowh, ruler = 34, 14
    total = sum(f[0] for f in fields)
    x0, x1 = 4, W-4
    pw = x1-x0
    p = [f'<text x="{x0}" y="10" font-size="9.5" font-weight="700" fill="{INK}">{H.escape(title)}</text>',
         f'<text x="{x1}" y="10" text-anchor="end" font-size="8.5" fill="{MUTE}">{H.escape(total_label)}</text>']
    y = 16
    x = x0; acc = 0
    for n, label, sub, tint in fields:
        w_ = n/total*pw
        p.append(f'<rect x="{x:.1f}" y="{y}" width="{w_:.1f}" height="{rowh}" fill="{tint}" stroke="{AXIS}" stroke-width="0.8"/>')
        p.append(f'<text x="{x+w_/2:.1f}" y="{y+14}" text-anchor="middle" font-size="8.5" font-weight="600" fill="{INK}">{H.escape(label)}</text>')
        if sub:
            p.append(f'<text x="{x+w_/2:.1f}" y="{y+25}" text-anchor="middle" font-size="7.5" fill="{INK2}">{H.escape(sub)}</text>')
        # byte-offset ruler tick
        p.append(f'<text x="{x:.1f}" y="{y+rowh+ruler-4}" font-size="7" fill="{MUTE}" font-family="ui-monospace,monospace">{acc}</text>')
        x += w_; acc += n
    p.append(f'<text x="{x1}" y="{y+rowh+ruler-4}" text-anchor="end" font-size="7" fill="{MUTE}" font-family="ui-monospace,monospace">{acc}</text>')
    return svg(W, y+rowh+ruler, "".join(p))

FRAME_HDR = byte_layout("NCFED frame header — every message", "5 bytes, big-endian",
    [(4,"length","uint32 !I payload bytes",T_HDR),(1,"flags","bit0=cont",T_HDR)])
HANDSHAKE = byte_layout("NCFED handshake — once per connection", "13 bytes",
    [(5,'magic "NCFED"',"4e 43 46 45 44",T_HDR),(4,"AS number","uint32 !I",T_PAY),(4,"router-id","IPv4 packed",T_PAY)])
BGP_KA = byte_layout("BGP KEEPALIVE (RFC 4271) — mesh session", "19 bytes",
    [(16,"marker","16 × 0xFF",T_HDR),(2,"length","0x0013 = 19",T_PAY),(1,"type","4",T_PAY)])
HEARTBEAT = byte_layout("NCFED heartbeat — 30 s liveness", "5 bytes",
    [(4,"length = 0","00 00 00 00",T_HDR),(1,"flags 0","00",T_HDR)])

# ── protocol stack / topology diagram ───────────────────────────────────────
def topo():
    W, HH = 680, 132
    p = []
    def box(x,y,w,h,fill,stroke,label,sub=None,mono=False):
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        fam = 'ui-monospace,monospace' if mono else 'system-ui,sans-serif'
        p.append(f'<text x="{x+w/2}" y="{y+(16 if sub else h/2+3.5)}" text-anchor="middle" font-size="9.5" font-weight="650" fill="{INK}" font-family="{fam}">{H.escape(label)}</text>')
        if sub: p.append(f'<text x="{x+w/2}" y="{y+29}" text-anchor="middle" font-size="8" fill="{INK2}">{H.escape(sub)}</text>')
    # endpoints
    box(4, 30, 150, 72, SURF, AXIS, "", None)
    p.append(f'<text x="79" y="48" text-anchor="middle" font-size="10" font-weight="700" fill="{INK}">Nick — as65007</text>')
    p.append(f'<text x="79" y="62" text-anchor="middle" font-size="8" fill="{INK2}">bgp-daemon-v2.py</text>')
    p.append(f'<text x="79" y="74" text-anchor="middle" font-size="8" fill="{INK2}" font-family="ui-monospace,monospace">0.0.0.0:20203 · rid 7.7.7.7</text>')
    p.append(f'<text x="79" y="88" text-anchor="middle" font-size="8" fill="{MUTE}">192.168.1.227</text>')
    box(526, 30, 150, 72, SURF, AXIS, "", None)
    p.append(f'<text x="601" y="48" text-anchor="middle" font-size="10" font-weight="700" fill="{INK}">John — as65001</text>')
    p.append(f'<text x="601" y="62" text-anchor="middle" font-size="8" fill="{INK2}">johns-risk (Border)</text>')
    p.append(f'<text x="601" y="74" text-anchor="middle" font-size="8" fill="{INK2}" font-family="ui-monospace,monospace">rid 4.4.4.4</text>')
    p.append(f'<text x="601" y="88" text-anchor="middle" font-size="8" fill="{MUTE}">behind ngrok</text>')
    # ngrok cloud
    box(285, 8, 110, 30, "#f4f4f1", AXIS, "ngrok cloud", "8.tcp.ngrok.io")
    # stream 0: BGP outbound (through ngrok to John)
    p.append(f'<path d="M 154 52 C 240 52 240 23 285 23" fill="none" stroke="{S2}" stroke-width="2"/>')
    p.append(f'<path d="M 395 23 C 460 23 470 52 526 52" fill="none" stroke="{S2}" stroke-width="2"/>')
    p.append(f'<text x="340" y="56" text-anchor="middle" font-size="8.5" fill="{S2}" font-weight="650">stream 0 · BGP KEEPALIVE / TCP</text>')
    p.append(f'<text x="340" y="67" text-anchor="middle" font-size="7.5" fill="{INK2}" font-family="ui-monospace,monospace">:43034 → 3.19.130.43:20203 · cleartext</text>')
    # stream 1: NCFED inbound via own tunnel
    p.append(f'<path d="M 526 88 C 420 88 400 96 285 96" fill="none" stroke="{S1}" stroke-width="2"/>')
    box(230, 84, 55, 24, "#f4f4f1", AXIS, "tunnel", None)
    p.append(f'<path d="M 230 96 C 200 96 185 88 154 88" fill="none" stroke="{S1}" stroke-width="2"/>')
    p.append(f'<text x="405" y="112" text-anchor="middle" font-size="8.5" fill="{S1}" font-weight="650">stream 1 · NCFED JSON-RPC / TCP (John dials Nick\'s ngrok endpoint :XXXXX)</text>')
    p.append(f'<text x="405" y="123" text-anchor="middle" font-size="7.5" fill="{INK2}" font-family="ui-monospace,monospace">delivered from loopback: 127.0.0.1:33466 → 127.0.0.1:20203</text>')
    return svg(W, HH, "".join(p))

# ── sequence ladder diagram ─────────────────────────────────────────────────
def seq_diagram():
    W = 680
    XL, XR = 195, 545          # lifelines: John (left), Nick (right)
    rows = [
        # (time, dir, style, label, sub)  dir: '>' John→Nick req, '<' Nick→John resp, 'B' box, 'G' grant, 'GAP' elision
        ("14:03:54", ">", "chat", "n2n/chat/open + n2n/chat/message (345 B)", "“standalone claw or a risk?”"),
        ("14:04:13", "<", "chat", "response (433 B) — chat reply", "“Standalone claw — 0 members, 2 peers” · 19.8 s agent turn"),
        ("14:05:55", ">", "req",  "n2n/tasks/submit №1 (405 B) — pyats-health-check", None),
        ("+21 ms",   "<", "deny", "error −32001 (147 B)", "“skill not allowlisted for as65001-4.4.4.4”"),
        ("14:07:10", ">", "req",  "n2n/tasks/submit №2 (371 B) — testbed variant", None),
        ("+18 ms",   "<", "deny", "error −32001 (147 B) — denied again", None),
        ("14:08:04", ">", "chat", "chat ×2 — traffic-gen pings for this capture", "both acknowledged in ~18 s"),
        ("14:09:05", "G", "",     "OPERATOR GRANT — id 3 · skill pyats-health-check", "POST /n2n/grants on localhost:8179 (off-wire)"),
        ("14:10:18", ">", "req",  "n2n/tasks/submit №3 (371 B)", None),
        ("+6 ms",    "<", "ok",   "result: task 83d1176e… state=submitted (128 B)", None),
        ("14:14:18", ">", "req",  "n2n/tasks/submit №4 (405 B) — 20-node lab", None),
        ("+5 ms",    "<", "ok",   "result: task 9751b33a… state=submitted (128 B)", None),
        ("14:10–24", "GAP","",    "n2n/tasks/result poll ×12 (~60–170 s apart) — every reply state=working · sub-ms", None),
        ("14:24:43", ">", "req",  "n2n/tasks/result (136 B)", None),
        ("+4 ms",    "<", "big",  "result: 9751b33a state=completed — 3,114 B single frame", "full 14-device fleet health report"),
        ("14:29:30", ">", "req",  "n2n/tasks/cancel 83d1176e… (137 B)", None),
        ("+0.5 ms",  "<", "warn", "result: cancelled=false (127 B)", "stalled task refuses cancel"),
    ]
    y0, dy_lab, dy = 40, 0, 0
    ys, y = [], y0
    for r in rows:
        y += 36 if r[4] else 30
        ys.append(y)
    HH = y + 24
    p = []
    # lifeline headers
    for x, name, sub in ((XL,"John · as65001-4.4.4.4","requester (client side of stream 1)"),(XR,"Nick · as65007-7.7.7.7","responder (bgp-daemon-v2.py)")):
        p.append(f'<rect x="{x-92}" y="4" width="184" height="26" rx="5" fill="{SURF}" stroke="{AXIS}"/>')
        p.append(f'<text x="{x}" y="15" text-anchor="middle" font-size="9" font-weight="700" fill="{INK}">{name}</text>')
        p.append(f'<text x="{x}" y="25" text-anchor="middle" font-size="7" fill="{MUTE}">{sub}</text>')
        p.append(f'<line x1="{x}" y1="30" x2="{x}" y2="{HH-6}" stroke="{AXIS}" stroke-width="1"/>')
    CLR = {"chat": INK2, "req": S1, "deny": CRIT, "ok": GOOD, "big": GOOD, "warn": SER}
    for (t, d, style, label, sub), y in zip(rows, ys):
        if d == "G":
            p.append(f'<rect x="{XR-150}" y="{y-11}" width="300" height="{30 if sub else 18}" rx="4" fill="#f0eefb" stroke="{S5}" stroke-width="1"/>')
            p.append(f'<text x="{XR}" y="{y+1}" text-anchor="middle" font-size="8.5" font-weight="700" fill="{S5}">{H.escape(label)}</text>')
            if sub: p.append(f'<text x="{XR}" y="{y+12}" text-anchor="middle" font-size="7.5" fill="{INK2}">{H.escape(sub)}</text>')
            p.append(f'<text x="{XL-98}" y="{y+2}" font-size="8" fill="{MUTE}" font-family="ui-monospace,monospace">{t}</text>')
            continue
        if d == "GAP":
            p.append(f'<rect x="{XL+20}" y="{y-10}" width="{XR-XL-40}" height="18" rx="4" fill="#f7f7f4" stroke="{GRID}"/>')
            p.append(f'<text x="{(XL+XR)/2}" y="{y+2}" text-anchor="middle" font-size="7.8" fill="{INK2}">{H.escape(label)}</text>')
            p.append(f'<text x="{XL-98}" y="{y+2}" font-size="8" fill="{MUTE}" font-family="ui-monospace,monospace">{t}</text>')
            continue
        c = CLR[style]
        x1, x2 = (XL, XR) if d == ">" else (XR, XL)
        dash = ' stroke-dasharray="5,3"' if d == "<" else ""
        wid = 2.4 if style == "big" else 1.6
        p.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{c}" stroke-width="{wid}"{dash}/>')
        ah = 5 if d == ">" else -5
        p.append(f'<path d="M {x2} {y} l {ah*-1.6} -4 l 0 8 z" fill="{c}"/>')
        p.append(f'<text x="{(XL+XR)/2}" y="{y-5}" text-anchor="middle" font-size="8.2" font-weight="600" fill="{c}">{H.escape(label)}</text>')
        if sub:
            p.append(f'<text x="{(XL+XR)/2}" y="{y+11}" text-anchor="middle" font-size="7.4" fill="{INK2}">{H.escape(sub)}</text>')
        p.append(f'<text x="{XL-98}" y="{y+2}" font-size="8" fill="{MUTE}" font-family="ui-monospace,monospace">{t}</text>')
    p.append(f'<text x="{XL-98}" y="{HH-8}" font-size="7.5" fill="{MUTE}">solid = request · dashed = response · NCFED heartbeats (30 s) and endpoint_update loop (~28 s) omitted</text>')
    return svg(W, HH, "".join(p))

# ── traffic chart ───────────────────────────────────────────────────────────
def chart_traffic():
    W, HH = 680, 210
    ml, mr, mt, mb = 46, 8, 8, 30
    pw, ph = W-ml-mr, HH-mt-mb
    ymax, n = 7000, len(ncfed)
    slot = pw/n; bw = slot-4
    p = []
    for kb in range(0, 8, 2):
        y = mt+ph-(kb*1000/ymax)*ph
        p.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W-mr}" y2="{y:.1f}" stroke="{GRID}"/>')
        p.append(f'<text x="{ml-6}" y="{y+3.5:.1f}" text-anchor="end" font-size="10" fill="{MUTE}">{kb} kB</text>')
    for i,(nv,bv) in enumerate(zip(ncfed,bgp)):
        x = ml+i*slot+2
        hN, hB = nv/ymax*ph, bv/ymax*ph
        yN = mt+ph-hN
        p.append(f'<rect x="{x:.1f}" y="{yN:.1f}" width="{bw:.1f}" height="{hN:.1f}" rx="2" fill="{S1}"/>')
        p.append(f'<rect x="{x:.1f}" y="{yN-2-hB:.1f}" width="{bw:.1f}" height="{hB:.1f}" rx="2" fill="{S2}"/>')
    px_ = ml+21*slot+2+bw/2
    py_ = mt+ph-(ncfed[21]+bgp[21]+2)/ymax*ph
    p.append(f'<text x="{px_:.1f}" y="{py_-16:.1f}" text-anchor="middle" font-size="10" fill="{INK2}">14:24 — task result</text>')
    p.append(f'<text x="{px_:.1f}" y="{py_-5:.1f}" text-anchor="middle" font-size="10" font-weight="600" fill="{INK}">6.9 kB</text>')
    p.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{W-mr}" y2="{mt+ph}" stroke="{AXIS}"/>')
    for m in range(0, n+1, 5):
        p.append(f'<text x="{ml+m*slot+slot/2:.1f}" y="{mt+ph+15}" text-anchor="middle" font-size="10" fill="{MUTE}">14:{3+m:02d}</text>')
    return svg(W, HH, "".join(p))

def chart_types():
    W = 680; rowh = 21; ml, mr = 178, 56; mt, mb2 = 6, 20
    HH = mt+rowh*len(msg_types)+mb2
    pw = W-ml-mr; vmax = 140
    p = []
    for v in range(0, 141, 35):
        x = ml+v/vmax*pw
        p.append(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+rowh*len(msg_types)}" stroke="{GRID}"/>')
        p.append(f'<text x="{x:.1f}" y="{mt+rowh*len(msg_types)+13}" text-anchor="middle" font-size="9.5" fill="{MUTE}">{v}</text>')
    for i,(name,v) in enumerate(msg_types):
        y = mt+i*rowh
        bw_ = max(v/vmax*pw, 2)
        p.append(f'<text x="{ml-8}" y="{y+rowh/2+3.5}" text-anchor="end" font-size="10" fill="{INK2}">{H.escape(name)}</text>')
        p.append(f'<rect x="{ml}" y="{y+4}" width="{bw_:.1f}" height="{rowh-8}" rx="2" fill="{S1}"/>')
        p.append(f'<text x="{ml+bw_+6:.1f}" y="{y+rowh/2+3.5}" font-size="10" font-weight="600" fill="{INK}">{v}</text>')
    p.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+rowh*len(msg_types)}" stroke="{AXIS}"/>')
    return svg(W, HH, "".join(p))

# ── latency dot plot (log scale) ────────────────────────────────────────────
LAT = [  # (method, n, min_s, med_s, max_s, note)
    ("n2n/tasks/result", 12, 0.00042, 0.00053, 0.0043, "local DB read"),
    ("n2n/tasks/cancel", 1, 0.00052, 0.00052, 0.00052, "local DB write"),
    ("n2n/chat/open", 3, 0.0023, 0.0023, 0.0024, "session create"),
    ("n2n/tasks/submit", 4, 0.0025, 0.0124, 0.0204, "authz check + task row"),
    ("n2n/endpoint_update", 114, 0.0033, 0.0345, 0.390, "endpoint upsert"),
    ("n2n/chat/message", 3, 17.7, 17.97, 19.8, "full agent turn (LLM)"),
]
def chart_latency():
    W = 680; rowh = 26; ml, mr = 178, 130; mt, mb2 = 6, 30
    HH = mt+rowh*len(LAT)+mb2
    pw = W-ml-mr
    lo, hi = math.log10(0.0003), math.log10(30)
    def X(v): return ml + (math.log10(v)-lo)/(hi-lo)*pw
    p = []
    for tick, lab in [(0.001,"1 ms"),(0.01,"10 ms"),(0.1,"100 ms"),(1,"1 s"),(10,"10 s")]:
        x = X(tick)
        p.append(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+rowh*len(LAT)}" stroke="{GRID}"/>')
        p.append(f'<text x="{x:.1f}" y="{mt+rowh*len(LAT)+13}" text-anchor="middle" font-size="9.5" fill="{MUTE}">{lab}</text>')
    for i,(name,n,mn,md,mx,note) in enumerate(LAT):
        y = mt+i*rowh+rowh/2
        p.append(f'<text x="{ml-8}" y="{y+3.5}" text-anchor="end" font-size="10" fill="{INK2}">{H.escape(name)}</text>')
        p.append(f'<line x1="{X(mn):.1f}" y1="{y}" x2="{X(mx):.1f}" y2="{y}" stroke="{S1}" stroke-width="2" opacity="0.45"/>')
        for cap in (mn, mx):
            p.append(f'<line x1="{X(cap):.1f}" y1="{y-4}" x2="{X(cap):.1f}" y2="{y+4}" stroke="{S1}" stroke-width="1.5" opacity="0.6"/>')
        p.append(f'<circle cx="{X(md):.1f}" cy="{y}" r="4.5" fill="{S1}" stroke="#fff" stroke-width="1.5"/>')
        medlab = f"{md*1000:.1f} ms" if md < 1 else f"{md:.1f} s"
        p.append(f'<text x="{X(mx)+8:.1f}" y="{y+3.5}" font-size="9" fill="{INK}"><tspan font-weight="600">{medlab}</tspan> <tspan fill="{MUTE}">· n={n} · {H.escape(note)}</tspan></text>')
    p.append(f'<text x="{ml}" y="{mt+rowh*len(LAT)+26}" font-size="8.5" fill="{MUTE}">median dot, min–max whisker · log scale · measured request→response on stream 1 (responder-side turnaround)</text>')
    return svg(W, HH, "".join(p))

# ── hex dissection helper ───────────────────────────────────────────────────
def hexdump(segments, per_row=16, max_rows=None):
    """segments: list of (hexstr_nospace, css_class). Renders hex+ascii grid."""
    data = [(b, cls) for hx, cls in segments for b in bytes.fromhex(hx)]
    rows = []
    for off in range(0, len(data), per_row):
        chunk = data[off:off+per_row]
        hx = "".join(f'<span class="{cls}">{b:02x}</span>{" " if (j+1)%8 or j==len(chunk)-1 else "&nbsp; "}'
                     for j,(b,cls) in enumerate(chunk))
        asc = "".join(f'<span class="{cls}">{H.escape(chr(b)) if 32<=b<127 else "·"}</span>' for b,cls in chunk)
        rows.append(f'<div class="hxrow"><span class="off">{off:04x}</span>  {hx.rstrip()}  <span class="asc">{asc}</span></div>')
        if max_rows and len(rows) >= max_rows:
            rows.append(f'<div class="hxrow"><span class="off">····</span>  <span style="color:{MUTE}">… {len(data)-off-per_row} more bytes …</span></div>')
            break
    return '<div class="hx">' + "".join(rows) + '</div>'

def chips(*pairs):
    return '<div class="chips">' + "".join(f'<span><i class="{c}"></i>{H.escape(t)}</span>' for c,t in pairs) + '</div>'

PAGE_CSS = f"""
@page {{ size: A4; margin: 12mm 13mm 14mm 13mm;
  @bottom-left  {{ content: "netclaw · N2N wire analysis · captures/n2n-session-20260714.pcap"; font: 8px system-ui; color:{MUTE}; }}
  @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font: 8px system-ui; color:{MUTE}; }} }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color:{INK}; background:#fff; font-size:10.5px; line-height:1.45; }}
h1 {{ font-size:22px; letter-spacing:-0.02em; }}
h2 {{ font-size:13.5px; margin:16px 0 7px; padding-bottom:4px; border-bottom:1px solid {GRID}; }}
h3 {{ font-size:11px; margin:9px 0 4px; }}
.sub {{ color:{INK2}; margin-top:3px; }}
.meta {{ color:{MUTE}; font-size:9px; margin-top:5px; }}
.kpis {{ display:flex; gap:7px; margin:12px 0 4px; }}
.kpi {{ flex:1; border:1px solid {GRID}; border-radius:6px; padding:7px 9px; background:{SURF}; }}
.kpi .v {{ font-size:18px; font-weight:600; }}
.kpi .l {{ color:{INK2}; font-size:8.5px; margin-top:1px; }}
.card {{ border:1px solid {GRID}; border-radius:6px; padding:9px 11px; background:{SURF}; margin:7px 0; }}
.legend {{ display:flex; gap:16px; margin:2px 0 5px; font-size:9.5px; color:{INK2}; }}
.legend i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }}
table {{ border-collapse:collapse; width:100%; font-size:9.5px; }}
th {{ text-align:left; color:{INK2}; font-weight:600; padding:4px 7px; border-bottom:1px solid {AXIS}; }}
td {{ padding:4px 7px; border-bottom:1px solid {GRID}; vertical-align:top; }}
td.t, td.num {{ font-variant-numeric:tabular-nums; white-space:nowrap; color:{INK2}; }}
td.num {{ text-align:right; }} th.num {{ text-align:right; }}
.badge {{ font-size:8px; font-weight:700; border:1px solid; border-radius:3px; padding:1px 5px; white-space:nowrap; }}
.note {{ color:{INK2}; }}
.mono {{ font-family:ui-monospace,Menlo,monospace; font-size:8.5px; }}
.finding {{ margin:8px 0; padding:8px 10px 8px 12px; border:1px solid {GRID}; border-left:3px solid {MUTE}; border-radius:4px; background:{SURF}; }}
.finding.good {{ border-left-color:{GOOD}; }} .finding.warn {{ border-left-color:{SER}; }}
.finding.crit {{ border-left-color:{CRIT}; }} .finding.info {{ border-left-color:{S1}; }}
.finding h3 {{ margin:0 0 3px; }}
.pagebreak {{ break-before:page; }}
.two {{ display:flex; gap:12px; }} .two > div {{ flex:1; }}
.layouts {{ display:flex; flex-wrap:wrap; gap:6px 14px; }}
ul {{ margin:4px 0 4px 16px; }} li {{ margin:2px 0; }}
.flow {{ font-size:9.5px; color:{INK2}; margin:4px 0; }}
.hx {{ font-family:ui-monospace,Menlo,monospace; font-size:8.4px; line-height:1.6; background:#fdfdfc; border:1px solid {GRID}; border-radius:4px; padding:7px 9px; margin:4px 0; }}
.hx .off {{ color:{MUTE}; }} .hx .asc {{ letter-spacing:0.5px; }}
.c-link {{ background:{T_LINK}; }} .c-ip {{ background:{T_IP}; }} .c-tcp {{ background:{T_TCP}; }}
.c-hdr {{ background:{T_HDR}; font-weight:700; }} .c-pay {{ background:{T_PAY}; }}
.chips {{ display:flex; gap:12px; font-size:8.5px; color:{INK2}; margin:2px 0 8px; flex-wrap:wrap; }}
.chips i {{ display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:4px; vertical-align:-1px; border:1px solid {AXIS}; }}
.chips i.c-link {{ background:{T_LINK}; }} .chips i.c-ip {{ background:{T_IP}; }} .chips i.c-tcp {{ background:{T_TCP}; }}
.chips i.c-hdr {{ background:{T_HDR}; }} .chips i.c-pay {{ background:{T_PAY}; }}
.dissect {{ margin:10px 0; break-inside:avoid; }}
.finding, .card {{ break-inside:avoid; }}
.dissect .cap {{ font-size:9px; color:{INK2}; margin-top:2px; }}
"""

if __name__ == "__main__":
    print("module ok — assembled in build step 2")
