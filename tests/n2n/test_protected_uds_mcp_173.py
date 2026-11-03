"""Exercise the real outer MCP SDK over UDS through the actual relay."""
import asyncio
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import threading

import pytest


@pytest.mark.asyncio
async def test_native_mcp_discovery_over_uds_preserves_rebinding_defense():
    from mcp.server.mcpserver import MCPServer
    import uvicorn

    source = Path(__file__).resolve().parents[2] / 'scripts/protected-inference.py'
    spec = importlib.util.spec_from_file_location('uds_mcp_relay', source)
    relay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(relay)
    mcp = MCPServer('Protected native discovery', version='173')
    tool_calls = []

    async def netbox_get_object_by_id(object_type: str, object_id: int,
                                     fields: list[str], brief: bool) -> dict:
        tool_calls.append(True)
        raise AssertionError('Discovery must not execute a tool')

    mcp.add_tool(netbox_get_object_by_id)
    application = mcp.streamable_http_app(json_response=True, stateless_http=True,
                                         max_request_body_size=1048576)
    observed = []

    async def app(scope, receive, send):
        observed.append(dict(scope['headers']).get(b'host'))
        return await application(scope, receive, send)

    with tempfile.TemporaryDirectory(prefix='ncr04-', dir='/tmp') as directory:
        path = str(Path(directory).resolve() / 'broker.sock')
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(path)
        listener.listen(16)
        relay.SOCKET = path
        server = uvicorn.Server(uvicorn.Config(app, log_level='error',
                                              access_log=False, lifespan='off'))
        proxy = relay.ThreadingHTTPServer(('127.0.0.1', 0), relay.Relay)
        thread = threading.Thread(target=proxy.serve_forever, daemon=True)

        def request(method, *, direct=False, host='attacker.invalid:443'):
            body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                               'params': ({'protocolVersion': '2025-11-25',
                                           'capabilities': {},
                                           'clientInfo': {'name': 'test', 'version': '1'}}
                                          if method == 'initialize' else {})}).encode()
            connection = (relay.UnixHTTPConnection(path) if direct else
                          http.client.HTTPConnection('127.0.0.1', proxy.server_port, timeout=5))
            try:
                connection.request('POST', '/mcp', body, {'Host': host,
                    'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})
                response = connection.getresponse()
                return response.status, response.read()
            finally:
                connection.close()

        async with mcp.session_manager.run():
            task = asyncio.create_task(server.serve(sockets=[listener]))
            while not server.started:
                await asyncio.sleep(.01)
            thread.start()
            try:
                # The old authority reproduces the actual 421 startup failure.
                assert (await asyncio.to_thread(request, 'initialize', direct=True,
                                                host='localhost'))[0] == 421
                assert (await asyncio.to_thread(request, 'initialize'))[0] == 200
                status, body = await asyncio.to_thread(request, 'tools/list')
                assert status == 200
                assert [tool['name'] for tool in json.loads(body)['result']['tools']] == ['netbox_get_object_by_id']
                # Caller Host is replaced by the fixed virtual authority; direct
                # unapproved authorities remain refused by the default SDK.
                assert observed[-1] == b'localhost:80'
                assert (await asyncio.to_thread(request, 'tools/list', direct=True))[0] == 421
                assert not tool_calls
            finally:
                await asyncio.to_thread(proxy.shutdown)
                proxy.server_close()
                thread.join(timeout=5)
                server.should_exit = True
                await task
