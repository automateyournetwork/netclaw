#!/usr/bin/env python3
"""Pinned external disposable flow fixture -> this connector and real HUD browser.

The external project's fixture owns its generated traffic, storage and cleanup.
Replace only its consumer callbacks: no external service source is copied here.
"""
import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import secrets
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE_REVISION = 'f54bafca82f339d8573c55c53795fa05bd9dd843'


def execute(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service-checkout', required=True)
    parser.add_argument('--evidence-dir', required=True)
    parser.add_argument('--mode', choices=('demo','host','both'), default='both')
    args = parser.parse_args()
    external = Path(args.service_checkout).resolve()
    actual = subprocess.check_output(['git','rev-parse','HEAD'],cwd=external,text=True).strip()
    if actual != SERVICE_REVISION:
        raise ValueError('Use the exact documented external service revision')
    execute(['git','diff','--quiet',SERVICE_REVISION,'--','tests/convergence-home',
             'workspace/skills/convergence-setup','deploy/convergence','ui/convergence-api'],cwd=external)
    output = Path(args.evidence_dir).resolve();output.mkdir(parents=True,mode=0o700,exist_ok=True)
    fixture = load(external/'tests/convergence-home/run-tests.py','external_home_fixture')
    writer = fixture.setup.env_writer(external)
    def write_env(path, values):
        for key,value in values.items(): writer.update(path,key,value)
    prepare = fixture.setup.prepare
    # Each fixture bundle receives a separate site-scoped VIEWER key, never the
    # default operator key. The producer/collector credentials remain unchanged.
    def prepare_viewer(repo, bundle, options):
        result = prepare(repo,bundle,options)
        if result['status'] != 'preserved':
            values = writer.values((bundle/'compose.env').read_text())
            keys = json.loads(values['API_KEYS'])
            token = secrets.token_hex(32)
            keys.append({'id':'upstream-reader','name':'Disposable reader','key':token,
                         'role':'viewer','sites':[options['site']]})
            write_env(bundle/'compose.env', {'API_KEYS':json.dumps(keys)})
            write_env(bundle/'hud.env', {'CONVERGENCE_API_TOKEN':token})
        return result
    fixture.setup.prepare = prepare_viewer
    with tempfile.TemporaryDirectory(prefix='convergence-reader-runtime-') as private:
        state = Path(private)
        env = {**os.environ, 'NETCLAW_RUNTIME':'openclaw','OPENCLAW_STATE_DIR':str(state),
               'NETCLAW_RUNTIME_ROOT':str(state/'python-runtimes'),
               'NETCLAW_RUNTIME_ENV':str(state/'.env'), 'NETCLAW_INSTALL_COMPONENT':'convergence-read',
               'NETCLAW_DIR':str(ROOT), 'NETCLAW_PY':sys.executable}
        # Execute the same fixed installer function/pip-helper as --add, with an
        # isolated runtime and no top-level launcher/global registration writes.
        install = ['bash','-c','source "$NETCLAW_DIR/scripts/lib/common.sh"; source "$NETCLAW_DIR/scripts/lib/pip-helper.sh"; source "$NETCLAW_DIR/scripts/lib/install-steps.sh"; component_install_convergence_read']
        write_env(state/'.env', {'UNRELATED_RUNTIME_SETTING':'preserved-fixture'})
        execute(install,cwd=ROOT,env=env,stdout=subprocess.DEVNULL)
        before = (state/'.env').read_bytes()
        execute(install,cwd=ROOT,env=env,stdout=subprocess.DEVNULL)
        assert (state/'.env').read_bytes()==before, 'Repeat install changed unrelated settings'
        record=state/'python-runtimes/records/convergence-read'
        assert record.is_file()
        connection = state/'connection.json'
        native_config = state/'openclaw.json'
        writer.write_private(native_config,json.dumps({'model':'preserved-fixture','mcpServers':{'unrelated':{'command':'fixture-only'}}}))
        registration = ['python3',str(ROOT/'scripts/install-mcp-config.py'),'--repo',str(ROOT),
            '--runtime-root',str(state/'python-runtimes'),'--components','convergence-read',
            '--output',str(state/'registered.json'),'--config',str(native_config)]
        execute(registration,env=env,cwd=ROOT)
        initial=json.loads((state/'registered.json').read_text())['mcpServers']['convergence-read-mcp']
        assert initial['env']['CONVERGENCE_ENABLED']=='false'
        assert '${' not in json.dumps(initial)
        async def disabled_native(entry):
            from fastmcp import Client
            values=writer.values((state/'.env').read_text())
            bound={key:re.sub(r'\$\{([A-Z_][A-Z0-9_]*)\}',lambda m:values.get(m[1],''),value)
                   for key,value in entry['env'].items()}
            async with Client({'mcpServers':{'convergence':{**entry,'env':{**env,**bound}}}}) as mcp:
                result=await mcp.call_tool('convergence_flow_summary',{})
                assert result.data['error']['code']=='disabled',result.data
        asyncio.run(disabled_native(initial))
        async def consumer(bundle, mode):
            from fastmcp import Client
            settings = writer.values((bundle/'hud.env').read_text())
            current = {**env, 'CONVERGENCE_ENABLED':'true','CONVERGENCE_SITE':mode,
                       'CONVERGENCE_API_URL':settings['CONVERGENCE_API_URL'],
                       'CONVERGENCE_API_TOKEN':settings['CONVERGENCE_API_TOKEN'],
                       'CONVERGENCE_ALLOW_LOOPBACK_HTTP':'true','CONVERGENCE_EXPORTERS':'127.0.0.1'}
            write_env(state/'.env',{k:v for k,v in current.items() if k.startswith('CONVERGENCE_')})
            execute(registration,env=current,cwd=ROOT)
            installed=json.loads(native_config.read_text())
            assert installed['model']=='preserved-fixture'
            assert installed['mcpServers']['unrelated']=={'command':'fixture-only'}
            entry=installed['mcpServers']['convergence-read-mcp']
            assert entry['env']['CONVERGENCE_ENABLED']=='${CONVERGENCE_ENABLED}'
            assert current['CONVERGENCE_API_TOKEN'] not in json.dumps(installed)
            def config(overrides=None):
                supplied={**current,**(overrides or {})}
                # Native references are resolved from the selected private env,
                # without claiming an OpenClaw gateway/model process was exercised.
                bound={key:re.sub(r'\$\{([A-Z_][A-Z0-9_]*)\}',lambda m:supplied.get(m[1],''),value)
                       for key,value in entry['env'].items()}
                return {'mcpServers':{'convergence':{**entry,'env':{**supplied,**bound}}}}

            async with Client(config()) as mcp:
                tools=await mcp.list_tools()
                assert {t.name for t in tools}=={'convergence_flow_summary','convergence_flow_evidence'}
                result=await mcp.call_tool('convergence_flow_summary',{'range':'15m'})
                assert result.data['ok'],result.data
                summary=result.data['data'];assert summary['coverage']['mode']==mode
                assert summary['total']['records']>0
                evidence=await mcp.call_tool('convergence_flow_evidence',{'address':summary['sources'][0]['src_addr'],
                    'start':summary['start'],'end':summary['end'],'exporter':'127.0.0.1'})
                if not evidence.data['ok']:
                    import httpx
                    raw=httpx.get(current['CONVERGENCE_API_URL']+'/api/flows/records',
                        params={'site':mode,'address':summary['sources'][0]['src_addr'],
                                'start':summary['start'],'end':summary['end'],'exporter':'127.0.0.1'},
                        headers={'Authorization':'Bearer '+current['CONVERGENCE_API_TOKEN']},timeout=20).json()
                    diagnostic=output/(mode+'-private-contract-diagnostic.json')
                    diagnostic.write_text(json.dumps(raw));diagnostic.chmod(0o600)
                assert evidence.data['ok'] and evidence.data['data']['records'],evidence.data
            for changed,code in [({'CONVERGENCE_API_TOKEN':'wrong-fixture-token'},'unauthorized'),
                ({'CONVERGENCE_SITE':'other'},'unauthorized'),({'CONVERGENCE_ENABLED':'false'},'disabled')]:
                async with Client(config(changed)) as mcp:
                    result=await mcp.call_tool('convergence_flow_summary',{})
                    assert result.data['error']['code']==code,result.data
            connection.write_text(json.dumps(current));connection.chmod(0o600)
        fixture.mcp_check = consumer
        original_execute = fixture.execute
        def execute_consumer(command, **kwargs):
            if command[0]=='node' and command[1].endswith('/integration/convergence-home.mjs'):
                return execute(['node',str(ROOT/'ui/netclaw-visual/integration/convergence-read.mjs'),
                                str(connection),str(output)],env=env,cwd=ROOT)
            return original_execute(command,**kwargs)
        fixture.execute=execute_consumer
        for mode in (('demo','host') if args.mode=='both' else (args.mode,)):
            fixture.qualify(mode,output)
        write_env(state/'.env',{'CONVERGENCE_ENABLED':'false'})
        execute(registration,env=env,cwd=ROOT)
        final=json.loads(native_config.read_text())
        assert final['model']=='preserved-fixture' and 'unrelated' in final['mcpServers']
        asyncio.run(disabled_native(final['mcpServers']['convergence-read-mcp']))
        assert writer.values((state/'.env').read_text())['UNRELATED_RUNTIME_SETTING']=='preserved-fixture'
        print(json.dumps({'result':'PASS','serviceRevision':SERVICE_REVISION,
                          'scope':'isolated repeat install, viewer scope, real export/store/MCP/HUD/browser and persistence'}))

if __name__=='__main__':
    main()
