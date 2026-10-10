"""Pure shared argument policy for the qualified existing n2n MCP subset."""
import ipaddress
import json
import re

OPERATIONS=frozenset(('n2n_status','n2n_risk_status','n2n_member_list','n2n_member_health','n2n_peer_capabilities',
    'n2n_invoke','n2n_delegate','n2n_route','n2n_chat','n2n_task_status','n2n_task_result'))


def wire_operation(name,args):
    def refuse():raise ValueError('unqualified federation operator arguments')
    def identifier(value):
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}',value) or '..' in value:refuse()
        return value
    def text(value):
        if not isinstance(value,str) or len(value.encode())>65536:refuse()
        return value
    if name not in OPERATIONS or not isinstance(args,dict):refuse()
    method='GET';body={}
    fields={'n2n_status':set(),'n2n_risk_status':set(),'n2n_member_list':set(),'n2n_member_health':{'member_id'},
        'n2n_peer_capabilities':{'peer','query'},'n2n_invoke':{'peer','target_type','target_name','arguments','input_text'},
        'n2n_delegate':{'peer','target_name','target_type','input_text'},'n2n_route':{'request_text','target_hint'},
        'n2n_chat':{'peer','message','session_id'},'n2n_task_status':{'task_id'},'n2n_task_result':{'task_id'}}
    if set(args)-fields[name]:refuse()
    if name in ('n2n_status','n2n_risk_status','n2n_member_list','n2n_member_health'):
        route={'n2n_status':'/n2n/status','n2n_risk_status':'/n2n/risk','n2n_member_list':'/n2n/members','n2n_member_health':'/n2n/members/health'}[name]
        if args.get('member_id'):identifier(args['member_id'])
    elif name=='n2n_peer_capabilities':
        route='/n2n/peers/'+identifier(args.get('peer'))+'/inventory'
        if args.get('query'):body['query']=text(args['query'])
    elif name in ('n2n_invoke','n2n_delegate'):
        kind=args.get('target_type','skill');target=args.get('target_name')
        if (kind,target) not in (('skill','subnet-calculator'),('tool','subnet-calc-mcp/subnet_calculator')):refuse()
        if name=='n2n_delegate' and kind!='skill':refuse()
        body={'peer':identifier(args.get('peer')),'target_type':kind,'target_name':target}
        if name=='n2n_delegate':body['input_text']=text(args.get('input_text',''))
        elif args.get('input_text'):body['input_text']=text(args['input_text'])
        if kind=='tool':
            values=json.loads(args.get('arguments') or '{}')
            if not isinstance(values,dict) or set(values)!={'cidr'}:refuse()
            network=ipaddress.IPv4Network(values['cidr'],strict=False)
            if not 24<=network.prefixlen<=30:refuse()
            body['arguments']=values
        elif args.get('arguments'):refuse()
        method='POST';route='/n2n/tasks' if name=='n2n_delegate' else '/n2n/invoke'
    elif name=='n2n_route':
        if args.get('target_hint')!='subnet-calculator':refuse()
        method='POST';route='/n2n/route';body={'request_text':text(args.get('request_text')),'capability':'subnet-calculator'}
    elif name=='n2n_chat':
        method='POST';route='/n2n/chat/send';body={'peer':identifier(args.get('peer')),'text':text(args.get('message'))}
        if args.get('session_id'):body['session_id']=identifier(args['session_id'])
    else:route='/n2n/tasks/'+identifier(args.get('task_id'))
    return {'method':method,'path':route,'body':body}
