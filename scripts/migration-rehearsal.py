#!/usr/bin/env python3
"""Record local rehearsal scope, creation attempts and evidence; no network calls."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'lib'))
from migration_artifacts import Rehearsal, Refused
from artifacts import read_file

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path);parser.add_argument('--run',required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    for operation in ('begin','attempt','reconcile','evidence'):
        item=sub.add_parser(operation);item.add_argument('--input',required=True,type=Path)
    sub.add_parser('report')
    args=parser.parse_args()
    try:
        run=Rehearsal(args.root,args.run)
        if args.action=='report':
            result={'retention':'retain','records':[json.loads(read_file(p,limit=65536)[0]) for p in sorted(run.root.glob('*.json'))]}
        else:
            payload=json.loads(read_file(args.input,limit=65536)[0])
            result={'recorded':args.action,'reference':getattr(run,args.action)(**payload)}
        print(json.dumps(result,indent=2));return 0
    except Exception:
        print(json.dumps({'status':'unavailable','code':'invalid_rehearsal_record_or_ownership'}));return 2

if __name__=='__main__':raise SystemExit(main())
