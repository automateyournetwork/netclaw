"""T014: NCFED framing, chunking, handshake encode/decode."""

import struct

from bgp.federation.channel import encode_frames, build_handshake
from bgp.federation.channel import read_handshake
from bgp.constants import NCFED_MAGIC, NCFED_MAX_PAYLOAD, NCFED_FLAG_CONTINUATION


def test_small_message_single_frame():
    frames = encode_frames({"jsonrpc": "2.0", "method": "n2n/hello", "params": {}})
    assert len(frames) == 1
    length, flags = struct.unpack("!IB", frames[0][:5])
    assert flags == 0
    assert length == len(frames[0]) - 5


def test_large_message_chunks_with_continuation():
    big = {"jsonrpc": "2.0", "id": "x", "result": {"blob": "A" * (NCFED_MAX_PAYLOAD * 2 + 100)}}
    frames = encode_frames(big)
    assert len(frames) >= 3
    # All but the last carry the continuation flag
    for f in frames[:-1]:
        _, flags = struct.unpack("!IB", f[:5])
        assert flags & NCFED_FLAG_CONTINUATION
    _, last_flags = struct.unpack("!IB", frames[-1][:5])
    assert not (last_flags & NCFED_FLAG_CONTINUATION)


def test_handshake_roundtrip():
    import asyncio

    hs = build_handshake(65001, "4.4.4.4")
    assert hs.startswith(NCFED_MAGIC)
    assert len(hs) == 13  # 5 magic + 4 AS + 4 router-id

    async def go():
        r = asyncio.StreamReader()
        r.feed_data(hs[5:])  # magic already consumed by discrimination
        r.feed_eof()
        return await read_handshake(r)

    peer_as, router_id = asyncio.run(go())
    assert peer_as == 65001
    assert router_id == "4.4.4.4"
