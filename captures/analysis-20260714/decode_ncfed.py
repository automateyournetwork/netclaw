#!/usr/bin/env python3
"""Decode NCFED (N2N federation) frames from the session pcap.

Wire format (bgp/federation/channel.py):
  handshake: b"NCFED" + !I peer_as + 4-byte router-id  (13 bytes each way)
  frame:     !IB header (length, flags) + JSON-RPC payload; len=0 => heartbeat
Capture may start mid-stream, so we resync by scanning for a plausible frame
boundary (header length sane + payload starts with '{' or is a heartbeat).
"""
import json, struct, subprocess, sys
from collections import defaultdict

PCAP = sys.argv[1]
MAGIC = b"NCFED"
MAX_PAYLOAD = 2 * 1024 * 1024

out = subprocess.run(
    ["tshark", "-r", PCAP, "-Y", "tcp.len>0",
     "-T", "fields", "-e", "frame.number", "-e", "frame.time_epoch",
     "-e", "tcp.stream", "-e", "ip.src", "-e", "tcp.srcport",
     "-e", "ip.dst", "-e", "tcp.dstport", "-e", "tcp.seq", "-e", "tcp.payload"],
    capture_output=True, text=True, check=True).stdout

# gather segments per (stream, direction), dedupe retransmits by seq
segs = defaultdict(dict)   # (stream, src:port) -> {seq: (ts, frameno, bytes)}
meta = {}
for line in out.strip().splitlines():
    f = line.split("\t")
    if len(f) < 9 or not f[8]:
        continue
    fno, ts, st, src, sp, dst, dp, seq, payload = f[:9]
    key = (int(st), f"{src}:{sp}")
    meta[key] = (f"{src}:{sp}", f"{dst}:{dp}")
    segs[key].setdefault(int(seq), (float(ts), int(fno), bytes.fromhex(payload)))

def resync(buf):
    """Return offset of first plausible frame/handshake boundary."""
    i = buf.find(MAGIC)
    for off in range(0, max(0, len(buf) - 5)):
        if i != -1 and off >= i:
            return i, "handshake"
        if off + 5 > len(buf):
            break
        ln, fl = struct.unpack("!IB", buf[off:off+5])
        if ln == 0 and fl == 0:
            # heartbeat — plausible only if what follows also parses; accept
            return off, "frame"
        if 0 < ln <= MAX_PAYLOAD and fl in (0, 1) and off + 5 < len(buf) and buf[off+5:off+6] == b"{":
            return off, "frame"
    return (i, "handshake") if i != -1 else (None, None)

events = []
for key, seqmap in segs.items():
    src, dst = meta[key]
    buf = b""
    times = []           # (buf_end_offset, ts, frameno)
    for seq in sorted(seqmap):
        ts, fno, data = seqmap[seq]
        buf += data
        times.append((len(buf), ts, fno))

    def ts_at(off):
        for end, ts, fno in times:
            if off < end:
                return ts, fno
        return times[-1][1], times[-1][2]

    off, kind = resync(buf)
    if off is None:
        continue
    skipped = off
    pos = off
    asm = b""  # continuation reassembly
    while pos < len(buf):
        if buf[pos:pos+5] == MAGIC and len(buf) - pos >= 13:
            peer_as = struct.unpack("!I", buf[pos+5:pos+9])[0]
            rid = ".".join(str(b) for b in buf[pos+9:pos+13])
            ts, fno = ts_at(pos)
            events.append(dict(ts=ts, frame=fno, src=src, dst=dst, kind="handshake",
                               summary=f"NCFED handshake AS{peer_as} router-id {rid}",
                               size=13))
            pos += 13
            continue
        if len(buf) - pos < 5:
            break
        ln, fl = struct.unpack("!IB", buf[pos:pos+5])
        if ln > MAX_PAYLOAD:
            pos += 1  # lost sync; slide
            continue
        if len(buf) - pos - 5 < ln:
            break  # truncated tail (capture ended mid-frame)
        payload = buf[pos+5:pos+5+ln]
        ts, fno = ts_at(pos)
        if ln == 0:
            events.append(dict(ts=ts, frame=fno, src=src, dst=dst, kind="heartbeat",
                               summary="heartbeat (empty frame)", size=5))
        else:
            asm += payload
            if fl & 1:  # continuation
                events.append(dict(ts=ts, frame=fno, src=src, dst=dst, kind="chunk",
                                   summary=f"continuation chunk ({ln} B)", size=ln+5))
            else:
                try:
                    msg = json.loads(asm.decode("utf-8", "replace"))
                except Exception:
                    msg = None
                events.append(dict(ts=ts, frame=fno, src=src, dst=dst, kind="jsonrpc",
                                   size=len(asm)+5, msg=msg))
                asm = b""
        pos += 5 + ln
    if skipped:
        events.append(dict(ts=times[0][1], frame=times[0][2], src=src, dst=dst,
                           kind="note", size=skipped,
                           summary=f"{skipped} B of pre-capture mid-stream data skipped before first frame boundary"))

events.sort(key=lambda e: e["ts"])
json.dump(events, open(sys.argv[2], "w"), indent=1, default=str)
print(f"{len(events)} events decoded")
for e in events:
    if e["kind"] == "jsonrpc" and e.get("msg"):
        m = e["msg"]
        tag = m.get("method") or ("response id=" + str(m.get("id")))
        print(f'{e["ts"]:.1f} {e["src"]} -> {tag} ({e["size"]} B)')
