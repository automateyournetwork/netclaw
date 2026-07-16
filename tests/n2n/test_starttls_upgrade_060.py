"""Proves the in-place STARTTLS upgrade of an NCFED stream works over a real
asyncio loopback connection — the mechanism US1's channel wiring depends on.

Flow mirrors secured NCFED: the server sends a cleartext preamble (stands in for
the NCFED magic + AS/router-id handshake), then BOTH sides upgrade the SAME
connection to TLS and exchange encrypted data plus a channel-bound signed-nonce
proof. Uses asyncio.run (repo convention — no pytest-asyncio).
"""

import asyncio
import os

from bgp.federation import tls, certs


def _send_blob(writer, data: bytes):
    writer.write(len(data).to_bytes(4, "big") + data)


async def _recv_blob(reader) -> bytes:
    n = int.from_bytes(await reader.readexactly(4), "big")
    return await reader.readexactly(n)


async def _scenario():
    scert, skey = certs.create_self_signed("as65001-4.4.4.4")
    dcert, dkey = certs.create_self_signed("as65007-7.7.7.7")
    expected_pin = certs.key_fingerprint(scert)
    result = {}

    async def handle(reader, writer):
        try:
            writer.write(b"NCFED-PREAMBLE\n")          # cleartext discrimination
            await writer.drain()
            r, w = await tls.upgrade_to_tls(reader, writer,
                                            tls.server_context(scert, skey),
                                            server_side=True)
            nonce = os.urandom(32)                     # listener issues nonce
            _send_blob(w, nonce)
            await w.drain()
            dialer_cert = (await _recv_blob(r)).decode()   # dialer proof
            sig = await _recv_blob(r)
            binding = tls.binding_from_own_cert(scert)
            result["auth_ok"] = tls.verify_auth(dialer_cert, sig, nonce, binding)
            _send_blob(w, b"ok" if result["auth_ok"] else b"no")
            await w.drain()
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    assert await reader.readline() == b"NCFED-PREAMBLE\n"
    cctx, _ = tls.client_context("pinned")
    r, w = await tls.upgrade_to_tls(reader, writer, cctx, server_side=False)

    sslobj = w.get_extra_info("ssl_object")
    result["pin_ok"] = tls.leaf_key_fingerprint(sslobj) == expected_pin

    nonce = await _recv_blob(r)
    binding = tls.binding_from_peer(sslobj)
    sig = tls.sign_auth(dkey, nonce, binding)
    _send_blob(w, dcert.encode())
    _send_blob(w, sig)
    await w.drain()
    result["verdict"] = await _recv_blob(r)

    w.close()
    server.close()
    await server.wait_closed()
    return result


def test_starttls_upgrade_and_channel_bound_auth():
    res = asyncio.run(_scenario())
    assert res["pin_ok"] is True          # dialer pinned the listener's key over TLS
    assert res["auth_ok"] is True         # listener verified the channel-bound proof
    assert res["verdict"] == b"ok"
