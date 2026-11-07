"""Strict TLS 1.3 streams using public OpenSSL MemoryBIO/exporter APIs (R01).

All OpenSSL calls belong to the asyncio event loop. No blocking TLS socket,
private CPython attribute, implicit legacy fallback or global loop replacement.
This module is imported only when the strict profile is selected.
"""
import asyncio
from collections import deque
import inspect
import ipaddress
import ssl

from OpenSSL import SSL, crypto
from service_identity.pyopenssl import verify_hostname, verify_ip_address

MAX_PENDING = 17 * 1024 * 1024  # 16 MiB NCFED message plus frame headers.
READ_LIMIT = 128 * 1024
MAX_CIPHERTEXT_CALLBACK = 512 * 1024
CHUNK = 16384


def _context(*, cert_file=None, key_file=None, ca_file=None, require_peer=False):
    ctx = SSL.Context(SSL.TLS_METHOD)
    ctx.set_min_proto_version(SSL.TLS1_3_VERSION)
    ctx.set_max_proto_version(SSL.TLS1_3_VERSION)
    if bool(cert_file) != bool(key_file):
        raise ValueError('certificate and private key must be provided together')
    if cert_file:
        ctx.use_certificate_chain_file(cert_file)
        ctx.use_privatekey_file(key_file)
        ctx.check_privatekey()
    if require_peer:
        if not ca_file:
            raise ValueError('strict peer verification requires an explicit CA')
        ctx.load_verify_locations(ca_file)
        ctx.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
                       lambda conn, cert, errno, depth, ok: bool(ok))
    return ctx


class _TLSStream(asyncio.Protocol):
    def __init__(self, context, *, server_hostname=None, callback=None, handshake_timeout=10,
                 profile='in2n-tls-exporter-v1'):
        self.loop = asyncio.get_running_loop()
        self.connection = SSL.Connection(context, None)
        self.server_hostname = server_hostname
        self.callback = callback
        self.profile = profile
        self.transport = None
        self.ready = self.loop.create_future()
        self.closed = self.loop.create_future()
        # Server ready is not awaited by a caller; consume failures there.
        if callback is not None:
            self.ready.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
            self.connection.set_accept_state()
        else:
            self.connection.set_connect_state()
            if not server_hostname:
                raise ValueError('strict TLS requires an independent server name')
            try:
                ipaddress.ip_address(server_hostname)
            except ValueError:
                self.connection.set_tlsext_host_name(server_hostname.encode('ascii'))
        self.reader = asyncio.StreamReader(limit=READ_LIMIT)
        self.reader.set_transport(self)
        self.pending = deque()
        self.pending_size = 0
        self.write_ready = asyncio.Event()
        self.write_ready.set()
        self.write_paused = False
        self.read_paused = False
        self.pumping = False
        self.handshaken = False
        self.peer_closed = False
        self.closing = False
        self.error = None
        self.exporter = None
        self.handshake_bytes = 0
        self.admission_task = None
        self.deadline = self.loop.call_later(handshake_timeout, self._fail,
                                             TimeoutError('strict TLS handshake timed out'))
        self.shutdown_timer = None

    def connection_made(self, transport):
        self.transport = transport
        transport.set_write_buffer_limits(high=256 * 1024, low=64 * 1024)
        self._pump()

    def data_received(self, data):
        if self.closed.done():
            return
        if len(data) > MAX_CIPHERTEXT_CALLBACK:
            self._fail(BufferError('TLS ciphertext callback limit exceeded'))
            return
        if not self.handshaken:
            self.handshake_bytes += len(data)
            if self.handshake_bytes > MAX_CIPHERTEXT_CALLBACK:
                self._fail(BufferError('TLS pre-authentication input limit exceeded'))
                return
        try:
            self.connection.bio_write(data)
            self._pump()
        except Exception:
            self._fail(ssl.SSLError('strict TLS record processing failed'))

    def eof_received(self):
        if not self.peer_closed and not self.closing:
            self._fail(ssl.SSLError('TLS stream truncated without close_notify'))
        return False

    def connection_lost(self, exc):
        self.deadline.cancel()
        if self.shutdown_timer:
            self.shutdown_timer.cancel()
        if not self.error and (exc or not (self.peer_closed or self.closing)):
            self.error = ConnectionError('strict TLS connection lost')
        if not self.ready.done():
            self.ready.set_exception(self.error or ConnectionError('TLS closed during handshake'))
        if self.error:
            self.reader.set_exception(self.error)
        else:
            self.reader.feed_eof()
        self.pending.clear()
        self.pending_size = 0
        self.write_ready.set()
        if not self.closed.done():
            self.closed.set_result(None)

    def _fail(self, error):
        if self.closed.done():
            return
        self.error = self.error or error
        self.closing = True
        self.reader.set_exception(self.error)
        if not self.ready.done():
            self.ready.set_exception(self.error)
        self.write_ready.set()
        if self.transport:
            self.transport.abort()
        else:
            self.connection_lost(error)

    def _flush(self):
        while not self.write_paused:
            try:
                ciphertext = self.connection.bio_read(CHUNK)
            except SSL.WantReadError:
                return
            if not ciphertext:
                return
            self.transport.write(ciphertext)

    def _verify(self):
        if self.connection.get_protocol_version_name() != 'TLSv1.3':
            raise ValueError('TLS 1.3 required')
        if self.server_hostname:
            try:
                ipaddress.ip_address(self.server_hostname)
            except ValueError:
                verify_hostname(self.connection, self.server_hostname)
            else:
                verify_ip_address(self.connection, self.server_hostname)
        self.exporter = self.connection.export_keying_material(
            b'EXPORTER-Channel-Binding', 32, context=b'')
        if not isinstance(self.exporter, bytes) or len(self.exporter) != 32:
            raise ValueError('TLS exporter unavailable')

    async def _serve(self, awaitable):
        try:
            await awaitable
        except asyncio.CancelledError:
            self.abort()
            raise
        except Exception:
            self._fail(ConnectionError('strict TLS application admission failed'))

    def _pump(self):
        if self.pumping or self.closed.done() or self.error:
            return
        self.pumping = True
        try:
            if not self.handshaken:
                try:
                    self.connection.do_handshake()
                except (SSL.WantReadError, SSL.WantWriteError):
                    self._flush()
                    return
                self._verify()
                self.handshaken = True
                self.deadline.cancel()
                self._flush()
                if not self.ready.done():
                    self.ready.set_result((self.reader, self))
                if self.callback is not None:
                    result = self.callback(self.reader, self)
                    if inspect.isawaitable(result):
                        self.admission_task = self.loop.create_task(self._serve(result))
            while not self.read_paused and not self.peer_closed:
                try:
                    plaintext = self.connection.recv(CHUNK)
                except (SSL.WantReadError, SSL.WantWriteError):
                    break
                except SSL.ZeroReturnError:
                    self.peer_closed = True
                    self.reader.feed_eof()
                    self.close()
                    break
                if not plaintext:
                    break
                self.reader.feed_data(plaintext)
            while self.pending and not self.write_paused:
                chunk = self.pending[0]
                try:
                    sent = self.connection.send(chunk)
                except (SSL.WantReadError, SSL.WantWriteError):
                    break
                if sent <= 0:
                    raise ConnectionError('TLS write made no progress')
                self.pending_size -= sent
                if sent == len(chunk):
                    self.pending.popleft()
                else:
                    self.pending[0] = chunk[sent:]
                self._flush()
            self._flush()
            if self.pending or self.write_paused:
                self.write_ready.clear()
            else:
                self.write_ready.set()
                if self.closing:
                    try:
                        self.connection.shutdown()
                    except (SSL.WantReadError, SSL.WantWriteError):
                        pass
                    self._flush()
                    self.transport.close()
        except Exception:
            self._fail(ssl.SSLError('strict TLS handshake, identity or record failure'))
        finally:
            self.pumping = False

    def write(self, data):
        if not self.handshaken or self.is_closing():
            raise self.error or ConnectionError('TLS stream is not writable')
        if self.pending_size + len(data) > MAX_PENDING:
            error = BufferError('TLS pending output limit exceeded')
            self._fail(error)
            raise error
        value = bytes(data)
        self.pending.extend(value[i:i + CHUNK] for i in range(0, len(value), CHUNK))
        self.pending_size += len(value)
        self._pump()

    async def drain(self):
        await self.write_ready.wait()
        if self.error or self.closed.done():
            raise self.error or ConnectionError('TLS stream closed')

    def pause_writing(self):
        self.write_paused = True
        self.write_ready.clear()

    def resume_writing(self):
        self.write_paused = False
        self._pump()

    def pause_reading(self):
        self.read_paused = True
        self.transport.pause_reading()

    def resume_reading(self):
        self.read_paused = False
        if not self.closed.done():
            self.transport.resume_reading()
            self._pump()

    def is_closing(self):
        return self.closing or self.closed.done()

    def close(self):
        if self.is_closing():
            return
        self.closing = True
        self.shutdown_timer = self.loop.call_later(2, self.abort)
        self._pump()

    def abort(self):
        self._fail(ConnectionError('TLS stream aborted'))

    async def wait_closed(self):
        await asyncio.shield(self.closed)

    def get_extra_info(self, name, default=None):
        if name == 'tls_exporter':
            return self.exporter
        if name == 'tls_version':
            return 'TLSv1.3' if self.handshaken else None
        if name == 'tls_profile':
            return self.profile
        if name == 'tls_peer_certificate':
            certificate = self.connection.get_peer_certificate() if self.handshaken else None
            return crypto.dump_certificate(crypto.FILETYPE_ASN1, certificate) if certificate else None
        if name == 'ssl_object':
            return None
        return self.transport.get_extra_info(name, default) if self.transport else default


async def open_connection(host, port, *, ca_file, server_hostname, handshake_timeout=10,
                          cert_file=None, key_file=None):
    protocol = _TLSStream(_context(ca_file=ca_file, cert_file=cert_file, key_file=key_file,
                                   require_peer=True), server_hostname=server_hostname,
                          handshake_timeout=handshake_timeout,
                          profile='ncfed-cluster-mtls-v1' if cert_file else 'in2n-tls-exporter-v1')
    try:
        await asyncio.wait_for(asyncio.get_running_loop().create_connection(
            lambda: protocol, host, port), handshake_timeout)
        return await protocol.ready
    except BaseException:
        protocol.abort()
        # A cancellation before TCP connect may leave a ready failure unobserved.
        if protocol.ready.done() and not protocol.ready.cancelled():
            protocol.ready.exception()
        raise


class _OwnedServer:
    """Opt-in listener ownership includes authenticated and pending connections."""
    def __init__(self, server, streams):
        self.server, self.streams, self.tasks = server, streams, set()

    def __getattr__(self, name):
        return getattr(self.server, name)

    def close(self):
        self.server.close()
        for stream in list(self.streams):
            task = stream.admission_task
            if task is not None and not task.done():
                self.tasks.add(task); task.cancel()
            stream.abort()

    async def wait_closed(self):
        await self.server.wait_closed()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)


async def start_server(callback, host, port, *, cert_file, key_file, handshake_timeout=10,
                       peer_ca_file=None, close_clients=False):
    context = _context(cert_file=cert_file, key_file=key_file, ca_file=peer_ca_file,
                       require_peer=peer_ca_file is not None)
    streams = set()
    def protocol():
        stream = _TLSStream(context, callback=callback, handshake_timeout=handshake_timeout,
                           profile='ncfed-cluster-mtls-v1' if peer_ca_file else 'in2n-tls-exporter-v1')
        if close_clients:
            streams.add(stream)
            stream.closed.add_done_callback(lambda _: streams.discard(stream))
        return stream
    server = await asyncio.get_running_loop().create_server(protocol, host, port)
    return _OwnedServer(server, streams) if close_clients else server
