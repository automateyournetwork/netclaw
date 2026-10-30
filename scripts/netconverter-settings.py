#!/usr/bin/env python3
"""Native operator review of an exact NetConverter disclosure request; never an MCP tool."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp-servers/netconverter-mcp'))
from artifacts import Refused
from core import Ledger
from server import Guard, load_config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',required=True)
    sub=parser.add_subparsers(dest='action',required=True)
    status=sub.add_parser('status');status.add_argument('--discover',action='store_true')
    review=sub.add_parser('review');review.add_argument('request_id')
    approve=sub.add_parser('approve-submission');approve.add_argument('request_id')
    approve.add_argument('--digest',required=True);approve.add_argument('--expires-in',type=int,default=300)
    args=parser.parse_args()
    try:
        config=load_config(args.env_file);ledger=Ledger(config)
        if args.action=='status': result=asyncio.run(Guard(config).status(args.discover))
        else:
            result=ledger.status(args.request_id)
            if args.action=='approve-submission':
                if not sys.stdin.isatty() or not sys.stdout.isatty(): raise Refused('interactive_operator_terminal_required')
                if args.digest!=result['review_digest']: raise Refused('review_digest_mismatch')
                print(json.dumps(result,indent=2))
                print('\nThis authorizes one hosted file submission to the displayed destination/account. No upload runs here.')
                print('Agents must present this review to the operator, never type approval themselves.')
                typed=input('To approve these exact bytes/options, type the full review digest: ').strip()
                if typed!=args.digest: raise Refused('approval_declined')
                result=ledger.approve(args.request_id,typed,args.expires_in)
        print(json.dumps(result,indent=2));return 0
    except Refused as exc:
        print(json.dumps({'status':'unavailable','code':str(exc)}));return 2
    except Exception:
        print(json.dumps({'status':'unavailable','code':'selected_configuration_or_state_unavailable'}));return 2


if __name__=='__main__': raise SystemExit(main())
