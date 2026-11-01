"""Controlled official-FastMCP Terminal peer. Synthetic data only; never contacts NetConverter."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from fastmcp import FastMCP

parser=argparse.ArgumentParser()
parser.add_argument('--workspace',required=True);parser.add_argument('--server')
parser.add_argument('operation');parser.add_argument('--auth');parser.add_argument('--mcp-url');parser.add_argument('--strict',action='store_true')
args=parser.parse_args();root=Path(args.workspace)
fixture=json.loads((root/'fixture.json').read_text())
caps={'job_types':['convert','validate','optimize'], 'vendors':[{'code':'cisco_asa','roles':['source'],'device_type':'firewall','input':'text'},
      {'code':'palo_alto_set','roles':['target'],'device_type':'firewall','input':'text'}],
      'paths':[{'source':'cisco_asa','target':'palo_alto_set','device_type':'firewall'}],
      'limits':{'max_config_bytes':1048576}}
if args.operation=='capabilities':
    print(json.dumps(caps));raise SystemExit(0)
mcp=FastMCP('synthetic-netconverter-peer')

@mcp.tool()
def account()->dict:
    if os.environ.get('NETCONVERTER_AUTH')!='key' or os.environ.get('NETCONVERTER_API_KEY')!='synthetic-key':
        raise ValueError('wrong auth binding')
    if os.environ.get('NETCONVERTER_PROVIDER') or os.environ.get('HTTP_PROXY'):
        raise ValueError('ambient environment leaked')
    return {'auth_kind':'api_key','credential_source':'api_key_environment','job_types':['convert','validate','optimize'],
            'exposure_level':fixture.get('exposure','masked'),'profile':'terminal_quick','client_version':'synthetic-1'}

@mcp.tool()
def submit_file(path:str,source_vendor:str,target_vendor:str='',job_type:str='convert',options:dict|None=None)->dict:
    # Record every invocation before simulating a lost receipt.
    with (root/'attempts.jsonl').open('a') as f: f.write(json.dumps({'path':path,'job_type':job_type})+'\n')
    data=Path(path).read_bytes()
    if fixture.get('delay_after_accept'): time.sleep(10)
    if fixture.get('fail_after_accept'): raise RuntimeError('PRIVATE_CONFIG_CANARY synthetic-key')
    return {'job_id':'tra_synthetic123','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'status':'queued'}

@mcp.tool()
def job_status(job_id:str)->dict:
    return {'job_id':job_id,'status':'completed','verdict':'NEEDS REVIEW','review_reason_count':1,
            'unsafe_content':'PRIVATE_CONFIG_CANARY synthetic-key'}

@mcp.tool()
def wait_for_job(job_id:str,timeout_s:int=30)->dict:
    return {'job_id':job_id,'status':'running','timed_out':True,'waited_s':timeout_s}

@mcp.tool()
def get_evidence(job_id:str,section:str='summary')->dict:
    return {'status':'completed','verdict':'NEEDS REVIEW','partial':True,'truncated':True,
            'unsafe_content':'PRIVATE_CONFIG_CANARY synthetic-key'}

@mcp.tool()
def get_job_brief(job_id:str)->dict:
    return {'job_id':job_id,'status':'completed','verdict':'NEEDS REVIEW'}

@mcp.tool()
def download(job_id:str,dest_dir:str='.')->dict:
    destination=Path(dest_dir);destination.mkdir(parents=True,exist_ok=True)
    data=b'SYNTHETIC_CANDIDATE_CANARY\n';path=destination/'candidate.txt';path.write_bytes(data)
    return {'job_id':job_id,'files':[{'name':str(path.relative_to(root)),
             'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}]}

@mcp.tool()
def apply_mapping_answers(answers:dict)->dict:
    raise RuntimeError('must never be called')

@mcp.tool()
def get_target_config(job_id:str)->dict:
    raise RuntimeError('must never be called')

if fixture.get('transport')=='http':
    mcp.run(transport='streamable-http',host='127.0.0.1',port=fixture['port'],stateless_http=True,json_response=True)
else: mcp.run(transport='stdio')
