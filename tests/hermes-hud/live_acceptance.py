#!/usr/bin/env python3
"""Explicit live-provider acceptance. Default is status only; --run performs five agent turns."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
import httpx
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:3001');parser.add_argument('--run',action='store_true');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if urlparse(args.url).hostname not in ('localhost','127.0.0.1'):raise SystemExit('Use the local HUD or an explicit local SSH tunnel.')
    report={'host':platform.platform(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'evidence':'live-provider' if args.run else 'status-only','checks':[],'toolPolicySha256':hashlib.sha256((ROOT/'config/hermes-hud-tool-policy.json').read_bytes()).hexdigest(),'sourceManifestSha256':hashlib.sha256((ROOT/'config/hermes-hud-compatibility.json').read_bytes()).hexdigest()}
    try:
        with httpx.Client(base_url=args.url,timeout=20,follow_redirects=False,trust_env=False) as client:
            def call(method,route,body=None):
                response=client.request(method,route,json=body);response.raise_for_status();return response.json()
            runtime=call('GET','/api/runtime');report['runtime']=runtime
            if runtime['kind']!='hermes' or not runtime['readiness']['ready']:raise SystemExit('Selected protected Hermes runtime is not ready. No inference performed.')
            if args.run:
                call('POST','/api/hud/session',{})
                thread='acceptance-'+uuid.uuid4().hex
                prompts=['Remember the acceptance colour violet for this conversation. Reply briefly.','What acceptance colour did I ask you to remember?',
                         'Use the installed subnet-calculator skill and qualified subnet_calculator tool to calculate 192.0.2.0/28. Do not answer from memory.',
                         'Using the observed tool result, state the usable host count. Do not invoke another tool.',
                         'Summarize what you verified and state which requested capabilities are unavailable.']
                for index,prompt in enumerate(prompts):
                    value=call('POST','/api/chat/requests',{'hudThread':thread,'clientNonce':uuid.uuid4().hex,'message':prompt})
                    deadline=time.monotonic()+300
                    while time.monotonic()<deadline:
                        value=call('GET','/api/chat/requests/'+value['requestId'])
                        if value.get('state') in ('completed','failed','unknown','cancelled','interrupted'):break
                        time.sleep(.75)
                    ok=value.get('state')=='completed'
                    if index==1:ok=ok and 'violet' in value.get('output','').lower()
                    if index==3:ok=ok and bool(re.search(r'\b14\b',value.get('output','')))
                    events=call('GET','/api/chat/requests/'+value['requestId']+'/events').get('events',[])
                    if index==2:ok=ok and any(e['state']=='completed' and 'subnet_calculator' in e['tool'] for e in events)
                    report['checks'].append({'turn':index+1,'passed':bool(ok),'state':value.get('state'),'runtime':value.get('runtime'),'usage':value.get('usage'),'toolEvidence':[{'tool':e['tool'],'state':e['state'],'digest':e.get('result_digest')} for e in events]})
                    if not ok:break # Never replay a failed/unknown operation.
    except (httpx.HTTPError,KeyError,ValueError) as error:
        report['errorCategory']=type(error).__name__
        report['passed']=False
    finally:
        report['passed']=len(report['checks'])==5 and all(c['passed'] for c in report['checks']) if args.run else None
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS' if report['passed'] else 'STATUS ONLY' if not args.run else 'FAIL: review saved report; no automatic resend')
    if args.run and not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
