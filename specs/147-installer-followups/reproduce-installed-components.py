"""Disposable component/native discovery and calculator canary; no real credentials."""
from pathlib import Path
import argparse
import json, os, subprocess, sys, tempfile, shutil
parser=argparse.ArgumentParser(description='Prepare a disposable test venv and probe four installed components; downloads declared test dependencies with uv.')
parser.add_argument('--node-bin', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
node_bin=args.node_bin.resolve()
components=['packet-buddy','subnet-calc','tts','netbox']
results={}
with tempfile.TemporaryDirectory(prefix='netclaw147-owned-probe-') as directory:
    home=Path(directory); runtime=home/'python-runtimes'; records=runtime/'records';records.mkdir(parents=True)
    stage=home/'source'; (stage/'mcp-servers').mkdir(parents=True)
    shutil.copytree(root/'mcp-servers/subnet-calculator-mcp',stage/'mcp-servers/subnet-calculator-mcp',ignore=shutil.ignore_patterns('.git','.venv'))
    subprocess.run([sys.executable,str(root/'scripts/apply-fastmcp-patches.py'),'--root',str(stage),'--component','subnet-calc'],check=True)
    subprocess.run(['uv','venv','--python','3.12',str(home/'test-venv')],check=True)
    python=home/'test-venv/bin/python'
    subprocess.run(['uv','pip','install','--python',str(python),'-r',str(root/'mcp-servers/tts-mcp/requirements.txt'),
        'python-dotenv','pydantic-settings','requests'],check=True)
    for component in components: (records/component).write_text(str(python))
    env={'HOME':str(home),'PATH':str(node_bin)+':/usr/bin:/bin','NETCLAW_RUNTIME_ROOT':str(runtime),
        'NETCLAW_RUNTIME_ENV':str(home/'.env'),'OPENCLAW_STATE_DIR':str(home),'PYTHON_DOTENV_DISABLED':'1',
        'SUBNET_MCP_SCRIPT':str(stage/'mcp-servers/subnet-calculator-mcp/servers/subnetcalculator_mcp.py'),
        'NETBOX_URL':'http://127.0.0.1:9','NETBOX_TOKEN':'fixture','FASTMCP_CHECK_FOR_UPDATES':'off','TTS_OUTPUT_DIR':str(home/'tts'),'PACKET_BUDDY_PCAP_DIR':str(home/'pcaps')}
    for component in components:
        r=subprocess.run([sys.executable,str(root/'scripts/mcp-call.py'),'--component',component,'--list-tools'],env=env,cwd=home,capture_output=True,text=True,timeout=35)
        assert r.returncode==0,(component,r.stderr)
    (home/'.env').write_text(''.join(key+'='+json.dumps(value)+'\n' for key,value in env.items()))
    config=home/'openclaw.json'
    r=subprocess.run([sys.executable,str(root/'scripts/install-mcp-config.py'),'--repo',str(root),
        '--runtime-root',str(runtime),'--components',' '.join(components),'--output',str(home/'generated.json'),
        '--config',str(config)],env=env,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    r=subprocess.run([sys.executable,str(root/'scripts/installer-readiness.py'),'--runtime-root',str(runtime),
        '--config',str(config),'--components',' '.join(components),'--probe','--output',str(home/'readiness.json')],
        env=env,capture_output=True,text=True,timeout=110)
    print(r.stdout,r.stderr)
    results['native']=json.loads((home/'readiness.json').read_text())
    r=subprocess.run([sys.executable,str(root/'scripts/mcp-call.py'),'--component','subnet-calc','subnet_calculator',
        '{"cidr":"192.0.2.0/30"}'],env=env,cwd=home,capture_output=True,text=True,timeout=45)
    assert not r.stderr,r.stderr
    results['subnet_canary']={'exit':r.returncode,'result':json.loads(r.stdout) if r.stdout else {},
        'stderr_present':bool(r.stderr)}
    # Actual response must contain the requested TEST-NET CIDR, never model prose.
    results['subnet_canary']['requested_cidr_returned']='192.0.2.0' in r.stdout and '255.255.255.252' in r.stdout
print(json.dumps(results,indent=2))
args.output.write_text(json.dumps(results,indent=2)+'\n')
