"""Synchronous protected-worker boundary to the private NCFED broker."""
import json
import os
from pathlib import Path
import time
import httpx
from ledger import HudError, digest

ROOT=Path(__file__).resolve().parents[2]


def validate_operator(name,args):
    import sys
    sys.path.insert(0,str(ROOT/'mcp-servers/protocol-mcp'))
    from bgp.federation.operator_policy import wire_operation
    try:return wire_operation(name.removeprefix('mcp__n2n_mcp__'),args)
    except (ValueError,TypeError,KeyError):raise HudError('capability_unsupported') from None


def invoke_operator(home,ledger,request,call_id,name,args,execution_permit=None):
    """Use the official isolated MCP client with a fresh per-effect environment."""
    import asyncio
    import sys
    validate_operator(name,args)
    with ledger.db() as db:row=db.execute('SELECT conversation FROM requests WHERE id=?',(request,)).fetchone()
    if not row:raise HudError('owner_invalid')
    record=broker_record(home,ledger.installation)
    with httpx.Client(timeout=5,trust_env=False,follow_redirects=False) as client:
        route='/operator/scoped' if execution_permit else '/operator'
        response=client.post(f"http://127.0.0.1:{record['port']}"+route,headers={'Authorization':'Bearer '+(execution_permit or record['key'])},
            json={'request':request,'conversation':row['conversation'],'call_id':call_id,'tool':name.removeprefix('mcp__n2n_mcp__'),'arguments':args})
        if response.status_code!=200:raise HudError('authorization_revoked')
        permit=response.json()
    sys.path.insert(0,str(ROOT/'mcp-servers/protocol-mcp'))
    from bgp.federation.hermes_runtime import call_stdio
    bridge_python=(Path(home)/'python-runtimes/records/hermes-hud').read_text().strip()
    env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','SYSTEMROOT','TMPDIR')}
    env.update(NETCLAW_FEDERATION_SCOPED='1',NETCLAW_FEDERATION_BROKER_URL=permit['url'],NETCLAW_FEDERATION_EFFECT_PERMIT=permit['permit'])
    result=asyncio.run(call_stdio(bridge_python,['-u',str(ROOT/'mcp-servers/n2n-mcp/server.py')],env,
                       name.removeprefix('mcp__n2n_mcp__'),args,timeout=610))
    return json.dumps(result)


def broker_record(home, installation):
    file=Path(home)/'netclaw-federation/broker.json'
    fd=os.open(file,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno())
        if info.st_mode&0o077 or info.st_uid!=os.getuid() or info.st_size>8192:raise HudError('owner_invalid')
        value=json.load(stream)
    if value.get('installationId')!=installation or not isinstance(value.get('port'),int) or not 1024<=value['port']<=65535:raise HudError('owner_invalid')
    return value


def check_receiver(home, installation, permit, request, tool=None, arguments=None):
    record=broker_record(home,installation)
    with httpx.Client(timeout=5,trust_env=False,follow_redirects=False) as client:
        try:
            response=client.post(f"http://127.0.0.1:{record['port']}/check",headers={'Authorization':'Bearer '+permit},
                                 json={'request':request,'tool':tool,'arguments':arguments})
            if response.status_code!=200:raise HudError('authorization_revoked')
            result=response.json()
        except httpx.HTTPError:raise HudError('authorization_unavailable') from None
    if not result.get('allowed') or result.get('installationId')!=installation:raise HudError('owner_invalid')
    return result['scope']
