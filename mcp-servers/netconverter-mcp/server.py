#!/usr/bin/env python3
"""NetClaw's optional guarded NetConverter integration. Stdio only."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parent))
from artifacts import Refused, directory, read_file
from core import Config, Ledger
from transport import Upstream, READS, qualified_read, private_report, verify_download

ENV_KEYS=frozenset({'NETCONVERTER_MODE','NETCONVERTER_DATA_DIR','NETCONVERTER_INSTALLATION_ID',
                    'NETCONVERTER_WORKSPACE','NETCONVERTER_EXECUTABLE','NETCONVERTER_ACCOUNT_REF',
                    'NETCONVERTER_API_KEY'})


def load_config(env_file=None):
    env={k:v for k,v in os.environ.items() if k in ENV_KEYS}
    if env_file:
        data,_=read_file(Path(env_file).expanduser(),limit=2_000_000)
        path=Path(__file__).resolve().parents[2]/'scripts/write-env.py'
        spec=importlib.util.spec_from_file_location('netconverter_literal_env',path)
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        env.update({k:v for k,v in helper.values(data.decode()).items() if k in ENV_KEYS})
    return Config.from_env(env)


class Guard:
    def __init__(self,config,upstream=None):
        self.config=config; self.ledger=Ledger(config); self.upstream=upstream or Upstream(config)

    async def status(self,discover=False):
        result={'mode':self.config.mode,'installed':True,'discovered':False,'authenticated':False,
                'capable':False,'approval':'per_request','account_reference':self.config.account,
                'account_identity_verified':False,'terminal':'not_required' if self.config.mode=='hosted-readonly' else 'unverified',
                'license':'operator_managed','hosted_submission':False,'read_content':'private_local_artifacts'}
        if discover:
            async with self.upstream.session() as session:
                catalog=await session.discover();result['discovered']=True
                result['available_reads']=sorted(set(catalog)&READS)
                if self.config.mode=='local-terminal':
                    caps=await self.upstream.capabilities(session)
                    result.update(authenticated=True,terminal='discovered',capable=bool(caps['paths']),
                                  capabilities=caps,hosted_submission='exact_file_approval_required')
                else:
                    account=await session.call('get_account',{})
                    result['account_evidence']=private_report(self.config,account)
                    result['authenticated']=(account.get('signed_in') is True or account.get('auth_kind')=='api_key') and account.get('status') not in ('signed_out','not_signed_in','unauthorized')
                    result['authentication_evidence']='confirmed' if result['authenticated'] else 'not_established'
                    result['capable']=result['authenticated'] and bool(result['available_reads'])
        return result

    async def prepare(self,path,source_vendor,target_vendor=None,job_type='convert',options=None):
        self.ledger.artifacts()  # reject read-only mode before any connection
        async with self.upstream.session() as session:
            await session.discover();caps=await self.upstream.capabilities(session)
            return self.ledger.prepare(path,source_vendor,target_vendor,job_type,options or {},caps)

    async def submit(self,request_id):
        # Local check before discovery; missing approval never sends source data.
        status=self.ledger.status(request_id)
        if status['state']!='approved': raise Refused('approval_required_or_consumed')
        async with self.upstream.session() as session:
            await session.discover();caps=await self.upstream.capabilities(session)
            attempt=self.ledger.claim(request_id,caps)
            args={'path':str(self.config.workspace/attempt['frozen']['relative_path']),
                  'source_vendor':attempt['source_vendor'],
                  'job_type':attempt['job_type'],'options':attempt['options']}
            if attempt['target_vendor'] is not None: args['target_vendor']=attempt['target_vendor']
            try:
                receipt=await session.call('submit_file',args)
            except Exception:
                # An upstream error can follow a successful upload. Do not call it
                # a safe-to-retry failure. Cancellation leaves the durable attempt.
                return self.ledger.finish(request_id,attempt['attempt_id'],None)
            return self.ledger.finish(request_id,attempt['attempt_id'],receipt)

    async def read(self,name,arguments):
        qualified_read(name,arguments)
        async with self.upstream.session() as session:
            await session.discover()
            result=private_report(self.config,await session.call(name,arguments))
            if name=='get_job_brief' and arguments.get('job_id'):
                result['job_ref']=self.ledger.associate(arguments['job_id'])
            return result

    async def job_status(self,job_ref,timeout_s=0):
        if type(timeout_s) is not int or not 0<=timeout_s<=45: raise Refused('polling_budget_exceeded')
        job=self.ledger.job(job_ref)
        if timeout_s: self.ledger.reserve_poll(job_ref,timeout_s)
        async with self.upstream.session() as session:
            await session.discover()
            name='wait_for_job' if timeout_s else 'job_status'
            args={'job_id':job['job_id']}
            if timeout_s: args['timeout_s']=timeout_s
            if self.config.mode=='hosted-readonly':
                name='get_job_brief';args={'job_id':job['job_id']}
            receipt=await session.call(name,args)
            return {'job_ref':job_ref,**private_report(self.config,receipt)}

    async def download(self,job_ref):
        artifacts=self.ledger.artifacts();job=self.ledger.job(job_ref)
        destination=artifacts.root/('download-'+uuid.uuid4().hex)
        with directory(destination,create=True,private=True): pass
        async with self.upstream.session() as session:
            await session.discover()
            receipt=await session.call('download',{'job_id':job['job_id'],'dest_dir':str(destination)})
        outputs=verify_download(self.config,receipt,job['job_id'],destination,artifacts)
        return {'job_ref':job_ref,'artifacts':outputs,'verified':'bytes_and_hashes',
                'semantic_acceptance':'not_tested','deployment_approval':False}


async def safe(call,*args,**kwargs):
    try: return await call(*args,**kwargs)
    except Refused as exc: return {'status':'unavailable','code':str(exc)}
    except Exception: return {'status':'unavailable','code':'integration_failed_private_details_not_exposed'}


def serve(config):
    from fastmcp import FastMCP
    mcp=FastMCP('netconverter-mcp');guard=Guard(config)

    @mcp.tool()
    async def netconverter_status(discover:bool=False)->dict:
        """Report distinct readiness stages. Optional discovery sends no configuration file."""
        return await safe(guard.status,discover)

    @mcp.tool()
    async def netconverter_prepare_submission(path:str,source_vendor:str,target_vendor:str|None=None,
                                             job_type:str='convert',options:dict|None=None)->dict:
        """Freeze an existing local file and prepare exact operator review metadata; no upload.

        Never paste source configuration into arguments. Approval must be made by
        the human in scripts/netconverter-settings.py; do not invoke approval yourself.
        """
        return await safe(guard.prepare,path,source_vendor,target_vendor,job_type,options)

    @mcp.tool()
    async def netconverter_submit_approved(request_id:str)->dict:
        """Attempt the exact natively approved request once. Unknown outcomes must never be replayed."""
        return await safe(guard.submit,request_id)

    @mcp.tool()
    def netconverter_request_status(request_id:str)->dict:
        """Local metadata, approval and durable attempt state; no provider call."""
        try: return guard.ledger.status(request_id)
        except Refused as exc: return {'status':'unavailable','code':str(exc)}
        except Exception: return {'status':'unavailable','code':'local_state_unavailable'}

    @mcp.tool()
    async def netconverter_read(name:str,arguments:dict)->dict:
        """Schema-qualified strict read allowlist. Reports stay private; metadata and known verdicts return."""
        return await safe(guard.read,name,arguments)

    @mcp.tool()
    async def netconverter_job_status(job_ref:str)->dict:
        """Read an opaque connection-bound job reference; no implicit account/route switch."""
        return await safe(guard.job_status,job_ref)

    @mcp.tool()
    async def netconverter_wait_for_job(job_ref:str,timeout_s:int=30)->dict:
        """Poll a bound job for at most 45 seconds. Budget unattended sequences to five minutes."""
        return await safe(guard.job_status,job_ref,timeout_s)

    @mcp.tool()
    async def netconverter_download(job_ref:str)->dict:
        """Download into a new private directory, verify every item and return frozen artifact references."""
        return await safe(guard.download,job_ref)

    return mcp


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file');parser.add_argument('--status',action='store_true')
    args=parser.parse_args()
    try:
        config=load_config(args.env_file)
        if args.status: print(json.dumps(asyncio.run(Guard(config).status())))
        else: serve(config).run(transport='stdio')
    except Exception:
        print('NetConverter guard unavailable; check selected installation settings.',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__': raise SystemExit(main())
