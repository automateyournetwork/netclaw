"""Real local TLS sockets. No ngrok, cloud, model, or device qualification."""
import asyncio
import ssl

import pytest

from bgp.federation import certs
from bgp.federation import exporter_tls as tls


@pytest.fixture
def material(tmp_path):
    ca, key = certs.create_risk_ca('r01-local')
    crt, private = certs.issue_cert(ca, key, 'border.example.test', san='border.example.test')
    other, _ = certs.create_risk_ca('wrong-ca')
    paths = {}
    for name, value in [('ca', ca), ('cert', crt), ('key', private), ('other', other)]:
        path = tmp_path / (name + '.pem')
        path.write_text(value)
        path.chmod(0o600)
        paths[name] = str(path)
    return paths


async def listen(material, callback, **kw):
    return await tls.start_server(callback, '127.0.0.1', 0,
                                  cert_file=material['cert'], key_file=material['key'], **kw)


async def connect(material, server, **kw):
    return await tls.open_connection('127.0.0.1', server.sockets[0].getsockname()[1],
                                     ca_file=kw.pop('ca_file', material['ca']),
                                     server_hostname=kw.pop('server_hostname', 'border.example.test'), **kw)


@pytest.mark.asyncio
async def test_bidirectional_fragmented_exporter_and_freshness(material):
    accepted = asyncio.Queue()
    server = await listen(material, lambda r, w: accepted.put_nowait((r, w)))
    writers = []
    bindings = []
    try:
        for _ in range(2):
            cr, cw = await connect(material, server)
            sr, sw = await asyncio.wait_for(accepted.get(), 2)
            writers += [cw, sw]
            binding = cw.get_extra_info('tls_exporter')
            assert len(binding) == 32 and binding == sw.get_extra_info('tls_exporter')
            assert cw.get_extra_info('tls_version') == 'TLSv1.3'
            bindings.append(binding)
            async def send(writer, byte):
                for _ in range(128):
                    writer.write(byte * 32768)
                    await writer.drain()
            async def receive(reader, byte):
                for _ in range(128):
                    assert await reader.readexactly(32768) == byte * 32768
            await asyncio.wait_for(asyncio.gather(send(cw, b'a'), send(sw, b'b'),
                                                 receive(sr, b'a'), receive(cr, b'b')), 10)
            for byte in b'fragmented':
                cw.write(bytes([byte]))
                await cw.drain()
            assert await sr.readexactly(10) == b'fragmented'
            cw.close()
            assert await asyncio.wait_for(sr.read(), 2) == b''
            await asyncio.wait_for(cw.wait_closed(), 3)
            await asyncio.wait_for(sw.wait_closed(), 3)
        assert bindings[0] != bindings[1]
    finally:
        for writer in writers:
            writer.close()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['name', 'ca', 'tls12', 'cleartext', 'proxy'])
async def test_refusals_before_callback(material, failure):
    admitted = []
    server = await listen(material, lambda r, w: admitted.append(w), handshake_timeout=.2)
    try:
        if failure in ('name', 'ca'):
            kwargs = {'server_hostname': 'wrong.example.test'} if failure == 'name' else {'ca_file': material['other']}
            with pytest.raises((ssl.SSLError, ConnectionError, ValueError)):
                await connect(material, server, **kwargs)
        elif failure == 'tls12':
            ctx = ssl.create_default_context(cafile=material['ca'])
            ctx.maximum_version = ssl.TLSVersion.TLSv1_2
            with pytest.raises((ssl.SSLError, ConnectionError)):
                await asyncio.open_connection('127.0.0.1', server.sockets[0].getsockname()[1],
                                              ssl=ctx, server_hostname='border.example.test')
        else:
            reader, writer = await asyncio.open_connection('127.0.0.1', server.sockets[0].getsockname()[1])
            writer.write(b'PROXY TCP4 1.2.3.4 5.6.7.8 1 2\r\n' if failure == 'proxy' else b'IN2N cleartext')
            await writer.drain()
            assert await asyncio.wait_for(reader.read(), 1) == b''
            writer.close()
            await writer.wait_closed()
        await asyncio.sleep(.05)
        assert not admitted
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_stalled_handshake_timeout_and_cancel(material):
    peers = []
    server = await asyncio.start_server(lambda r, w: peers.append(w), '127.0.0.1', 0)
    try:
        with pytest.raises((TimeoutError, ConnectionError)):
            await connect(material, server, handshake_timeout=.05)
        task = asyncio.create_task(connect(material, server))
        await asyncio.sleep(.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(.05)
        assert len(peers) == 2
    finally:
        for writer in peers:
            writer.close()
            await writer.wait_closed()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_abrupt_eof_and_bounded_pending_output(material):
    accepted = asyncio.Queue()
    server = await listen(material, lambda r, w: accepted.put_nowait((r, w)))
    writers = []
    try:
        cr, cw = await connect(material, server)
        sr, sw = await accepted.get()
        writers += [cw, sw]
        # A real TCP abort must not look like authenticated TLS close_notify.
        sw.abort()
        with pytest.raises((ConnectionError, ssl.SSLError)):
            await asyncio.wait_for(cr.readexactly(1), 2)
        await cw.wait_closed()
        cr, cw = await connect(material, server)
        sr, sw = await accepted.get()
        writers += [cw, sw]
        with pytest.raises(BufferError):
            cw.write(b'x' * (tls.MAX_PENDING + 1))
        await asyncio.wait_for(cw.wait_closed(), 2)
    finally:
        for writer in writers:
            writer.close()
        server.close()
        await server.wait_closed()
