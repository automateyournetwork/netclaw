"""Isolated service process for the real runtime matrix. Test-only stdin control."""
import asyncio,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'mcp-servers/protocol-mcp'))
from bgp.federation.service import FederationService
from bgp.federation.manager import FederationManager
from bgp.federation.channel import read_handshake
from bgp.constants import NCFED_MAGIC

async def main():
    home=Path(os.environ['TEST_PEER_HOME']);index=int(os.environ['TEST_PEER_INDEX'])
    svc=FederationService(local_as=65001+index,router_id=f'{index+1}.{index+1}.{index+1}.{index+1}',manager=FederationManager(base_dir=str(home/'n2n')))
    await svc.start_runtime()
    svc.risk.set_role('border',risk_name='risk',enabled_stacks='both')
    async def accept(reader,writer):
        assert await reader.readexactly(5)==NCFED_MAGIC
        asn,rid=await read_handshake(reader);await svc.accept_channel(asn,rid,reader,writer)
    internal=await asyncio.start_server(svc.accept_internal,'127.0.0.1',0)
    external=await asyncio.start_server(accept,'127.0.0.1',0)
    print(json.dumps({'internal':internal.sockets[0].getsockname()[1],'external':external.sockets[0].getsockname()[1],'identity':svc.local_identity,'asn':svc.local_as,'rid':svc.router_id}),flush=True)
    try:
        while line:=await asyncio.to_thread(sys.stdin.readline):
            try:
                cmd=json.loads(line);op=cmd.pop('op');result={}
                if op=='stop':break
                if op=='token':result=svc.risk.issue_token()
                elif op=='member':
                    svc.risk.set_role('member',risk_name='risk',self_member_id=cmd['name']);svc.member_scope={'subnet-calculator'}
                    await svc.dial_border('127.0.0.1',cmd['port'],enrollment_token=cmd['token'])
                elif op=='scope':
                    svc.manager._conn.execute('UPDATE member SET scope=? WHERE member_id=?',(json.dumps([{'name':'subnet-calculator','type':'skill','tier':'specialty'}]),cmd['name']));svc.manager._conn.commit()
                elif op=='consent':svc.manager.local_consent(cmd['asn'],cmd['rid'])
                elif op=='connect':await svc.open_channel(cmd['asn'],cmd['rid'],'127.0.0.1',cmd['port']);await asyncio.sleep(.3)
                elif op=='grant':
                    svc.authz.grant(cmd['peer'],'skill','subnet-calculator');svc.authz.grant(cmd['peer'],'tool','subnet-calc-mcp/subnet_calculator');svc.manager.set_chat_enabled(cmd['peer'],True)
                elif op=='delegate':
                    result=await svc.delegate_to_member(cmd['peer'],'subnet-calculator','SUBNET') if cmd.get('internal') else await svc.invoker.submit_remote_skill(cmd['peer'],'subnet-calculator','SUBNET')
                elif op=='result':result=await svc.poll_member_task(cmd['peer'],cmd['task'],'result') if cmd.get('internal') else await svc.invoker.poll_remote_task(cmd['peer'],cmd['task'],'result')
                elif op=='tool':result=await svc.invoker.invoke_remote_tool(cmd['peer'],'subnet-calc-mcp/subnet_calculator',{'cidr':'192.0.2.0/28'})
                elif op=='chat':result=await svc.chat.open_and_send(cmd['peer'],cmd['text'],cmd.get('session'))
                elif op=='card':result=svc.inventory.load_remote(cmd['peer']) or {}
                else:raise ValueError('unknown test operation')
                print(json.dumps({'ok':result}),flush=True)
            except Exception as e:print(json.dumps({'error':type(e).__name__+': '+str(e)}),flush=True)
    finally:
        for c in list(svc.channels.values())+list(svc.member_channels.values()):await c.close()
        if svc.border_channel:await svc.border_channel.close()
        internal.close();external.close();await svc.stop_runtime();svc.manager.close()
        from bgp.federation import gateway_ws
        if gateway_ws._singleton:await gateway_ws._singleton.close()

if __name__=='__main__':asyncio.run(main())
