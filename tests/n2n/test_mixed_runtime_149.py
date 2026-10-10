"""Real OpenClaw/Hermes processes; controlled provider, never owner gateways."""
import importlib.util,json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
import pytest
from bgp.federation.runtime import ROOT
from test_hermes_external_149 import configure

@pytest.mark.skipif(not os.environ.get('NETCLAW_OPENCLAW_BIN') or not os.environ.get('NETCLAW_HERMES_PYTHON'),reason='real mixed runtime fixture required')
def test_real_four_internal_pairs_and_mixed_external(tmp_path):
    spec=importlib.util.spec_from_file_location('mixed_provider',ROOT/'tests/hermes-hud/fixtures/provider.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    provider=mod.Provider();url=provider.start();children=[];logs=[];peers=[]
    def command(node,**body):
        node['process'].stdin.write(json.dumps(body)+'\n');node['process'].stdin.flush()
        line=node['process'].stdout.readline()
        assert line,'fixture process stopped'
        result=json.loads(line);assert 'error' not in result,result
        return result['ok']
    def result(peer,target,task,internal=False):
        for _ in range(600):
            value=command(peer,op='result',peer=target,task=task,internal=internal)
            if value['state'] not in ('submitted','working'):return value
            time.sleep(.1)
        raise AssertionError('runtime result deadline exceeded')
    try:
        for i,kind in enumerate(['hermes','openclaw','hermes','openclaw','hermes','openclaw']):
            home=tmp_path/f'{kind}-{i}';configure(home,url)
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            if kind=='openclaw':
                config=json.loads((home/'config.yaml').read_text());workspace=home/'workspace';workspace.mkdir();shutil.copytree(home/'skills',workspace/'skills')
                (home/'openclaw.json').write_text(json.dumps({'models':{'providers':{'fixture':{'baseUrl':url,'apiKey':'fixture-only','api':'openai-completions','models':[{'id':'hud-fixture','name':'hud-fixture','contextWindow':64000,'maxTokens':4096}]}}},'agents':{'defaults':{'model':{'primary':'fixture/hud-fixture'},'workspace':str(workspace)}},'tools':{'deny':['exec','read','write','edit','browser']},'mcp':{'servers':{'subnet-calc-mcp':config['mcp_servers']['subnet-calc-mcp']}},'gateway':{'mode':'local','port':port,'auth':{'mode':'token','token':'fixture-token-149-private'}}}))
            env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','TMPDIR','NETCLAW_HERMES_PYTHON','NETCLAW_HERMES_SOURCE','NETCLAW_SUBNET_PYTHON')}
            env.update(HOME=str(home),NETCLAW_RUNTIME=kind,HERMES_HOME=str(home),OPENCLAW_STATE_DIR=str(home),OPENCLAW_CONFIG_PATH=str(home/'openclaw.json'),TEST_PEER_HOME=str(home),TEST_PEER_INDEX=str(i),N2N_CERT_MODE='on',N2N_RISK_MODE='testing',OPENAI_API_KEY='fixture-only',OPENAI_BASE_URL=url,OPENCLAW_BIN=os.environ['NETCLAW_OPENCLAW_BIN'])
            env['PATH']=str(Path(env['OPENCLAW_BIN']).parent)+os.pathsep+env['PATH']
            if i==1:
                log=(tmp_path/'gateway.log').open('w');logs.append(log)
                gateway=subprocess.Popen([env['OPENCLAW_BIN'],'gateway','run','--port',str(port),'--bind','loopback'],env=env,stdout=log,stderr=log);children.append(gateway)
                for _ in range(100):
                    if gateway.poll() is not None:raise AssertionError((tmp_path/'gateway.log').read_text())
                    try:
                        with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                    except OSError:time.sleep(.2)
            log=(tmp_path/f'peer-{i}.log').open('w');logs.append(log)
            child=subprocess.Popen([sys.executable,'-u',str(ROOT/'tests/n2n/mixed_peer_149.py')],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True);children.append(child)
            hello=child.stdout.readline();assert hello,(tmp_path/f'peer-{i}.log').read_text();peers.append({'process':child,**json.loads(hello)})
        # Four distinct member homes: enrollment never crosses Border trust.
        for border_index,member_index in ((0,2),(0,3),(1,4),(1,5)):
            border=peers[border_index];member=peers[member_index]
            name='risk/'+('hermes' if member_index%2==0 else 'openclaw')
            token=command(border,op='token')['token']
            command(member,op='member',name=name,port=border['internal'],token=token)
            command(border,op='scope',name=name)
            task=command(border,op='delegate',peer=name,internal=True)['task_id']
            value=result(border,name,task,True);assert value['state']=='completed' and '192.0.2.' in value.get('output_text',''),value
        h,o=peers[:2]
        for caller,remote in ((h,o),(o,h)):
            command(caller,op='consent',asn=remote['asn'],rid=remote['rid'])
            command(caller,op='grant',peer=remote['identity'])
        command(h,op='connect',asn=o['asn'],rid=o['rid'],port=o['external'])
        for caller,remote in ((h,o),(o,h)):
            tool=command(caller,op='tool',peer=remote['identity']);assert '192.0.2.' in json.dumps(tool),tool
            task=command(caller,op='delegate',peer=remote['identity'])['task_id'];value=result(caller,remote['identity'],task);assert value['state']=='completed' and '192.0.2.' in value.get('output_text',''),value
            chat=command(caller,op='chat',peer=remote['identity'],text='remember violet')
            follow=command(caller,op='chat',peer=remote['identity'],text='what colour?',session=chat['session_id']);assert 'violet' in follow['text'],follow
    finally:
        for peer in peers:
            if peer['process'].poll() is None:
                try:peer['process'].stdin.write('{"op":"stop"}\n');peer['process'].stdin.flush()
                except OSError:pass
        for child in reversed(children):
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10)
        for log in logs:log.close()
        provider.close()
