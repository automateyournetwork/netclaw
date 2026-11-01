#!/usr/bin/env python3
"""Selected-runtime NetConverter settings; no license action, provider call or file upload."""
import argparse
import getpass
import importlib.util
import json
import re
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/lib'))
from setup_state import guarded_read
spec=importlib.util.spec_from_file_location('netconverter_dotenv',ROOT/'scripts/write-env.py')
dotenv=importlib.util.module_from_spec(spec);spec.loader.exec_module(dotenv)


def configure(path,home,mode,account,workspace=None,executable=None,key=None):
    path=Path(path).absolute();home=Path(home)
    if mode not in ('hosted-readonly','local-terminal') or not home.is_absolute(): raise ValueError('invalid_mode_or_home')
    if not isinstance(account,str) or not account.strip() or len(account)>128: raise ValueError('account_reference_required')
    if re.search(r'nck_(?:live|test)_',account): raise ValueError('credential_in_account_reference')
    try: original=guarded_read(path,1024*1024).decode()
    except FileNotFoundError: original=''
    values=dotenv.values(original)
    changes={'NETCONVERTER_MODE':mode,'NETCONVERTER_ACCOUNT_REF':account,
             'NETCONVERTER_DATA_DIR':str(home/'netconverter'),
             'NETCONVERTER_INSTALLATION_ID':values.get('NETCONVERTER_INSTALLATION_ID') or uuid.uuid4().hex}
    if mode=='local-terminal':
        for name,value in [('NETCONVERTER_WORKSPACE',workspace),('NETCONVERTER_EXECUTABLE',executable)]:
            if not value or not Path(value).is_absolute() or '..' in Path(value).parts: raise ValueError('absolute_path_required')
            changes[name]=value
    if key is not None: changes['NETCONVERTER_API_KEY']=key
    if any(any(c in v for c in '\0\r\n') for v in changes.values()): raise ValueError('single_line_values_required')
    lines=[line for line in original.splitlines() if not ((m:=dotenv.ASSIGNMENT.match(line.strip())) and m[1] in changes)]
    lines.extend(k+'='+dotenv.quote(v) for k,v in changes.items())
    # Preserve unrelated fields and detect a changed review base.
    try: current=guarded_read(path,1024*1024).decode()
    except FileNotFoundError: current=''
    if current!=original: raise ValueError('settings_changed_retry_review')
    dotenv.write_private(path,'\n'.join(lines)+'\n')
    return {'mode':mode,'saved':True,'accountAccess':'not_checked','license':'operator_managed','submission':'not_attempted'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env',required=True,type=Path);parser.add_argument('--home',required=True,type=Path)
    parser.add_argument('--interactive',action='store_true');parser.add_argument('--mode',choices=['hosted-readonly','local-terminal'])
    parser.add_argument('--account');parser.add_argument('--workspace');parser.add_argument('--executable')
    args=parser.parse_args()
    try:
        key=None
        if args.interactive:
            if not sys.stdin.isatty(): raise ValueError('interactive_terminal_required')
            mode=input('NetConverter: hosted-readonly / local-terminal / cancel [cancel]: ').strip() or 'cancel'
            if mode=='cancel': print('NetConverter settings unchanged.');return 0
            if mode not in ('hosted-readonly','local-terminal'): raise ValueError('invalid_mode')
            account=input('Local account reference (not a credential): ').strip()
            workspace=executable=None
            if mode=='local-terminal':
                workspace=input('Absolute Terminal workspace: ').strip()
                executable=input('Absolute licensed Terminal executable: ').strip()
            if input('Enter or replace API key now? [y/N]: ').lower()=='y': key=getpass.getpass('NetConverter API key: ')
            print('This saves settings only. It does not install/accept the Terminal license, verify the account or upload any file.')
            if input('Save for this selected runtime? [y/N]: ').lower()!='y': print('NetConverter settings unchanged.');return 0
        else: mode,account,workspace,executable=args.mode,args.account,args.workspace,args.executable
        print(json.dumps(configure(args.env,args.home,mode,account,workspace,executable,key)));return 0
    except (ValueError,OSError,EOFError):
        print('NetConverter settings unchanged: check mode, account reference and absolute selected paths.',file=sys.stderr);return 1


if __name__=='__main__': raise SystemExit(main())
