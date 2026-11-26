"""Offline exact-cell acceptance using the existing NCFED signed contracts.

Public anchors, topology, cell assignments and original HTTP captures must be
frozen in the private campaign before verification. This verifier grants no
authority, sends no request, and proves neither live placement nor HA recovery.
Local ingress attribution relies on the archived authenticated HTTP capture;
remote ingress additionally requires the production peer-client endorsement.
"""
import copy
import json
from pathlib import Path
import sys
import uuid
import campaign as c


def contracts():
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'mcp-servers/protocol-mcp'))
    from bgp.federation import protected_contract
    from bgp.federation.ha.config import verify_manifest
    from bgp.federation.ha.signatures import verify
    return protected_contract,verify_manifest,verify


def principal(cluster_id):
    return dict(issuer='open-lab',subject=str(uuid.uuid5(uuid.UUID(cluster_id),'netclaw.open-lab.operator')),
                display_name='Unauthenticated lab operator',roles=['lab-operator'])


def manifests(groups, anchors):
    p,verify,_=contracts();result={};members=set();nodes=set();clusters=set();keys=set();runtime_keys=set()
    c.need(set(groups)==set(anchors),'exact_anchor_set_required')
    for cloud,group in groups.items():
        e=group['enrollment'];m=verify(e['manifest'],e['anchor_certificate'],expected_key_id=anchors[cloud])
        scope=group.get('qualification_scope','three-region')
        c.need(scope in ('three-region','ohio-three-az'),'unknown_qualification_scope')
        c.need(len(m.nodes)==3 and set(group['regions'])=={n['node_id'] for n in m.nodes},'three_regional_borders_per_cloud_required')
        if scope=='ohio-three-az':
            c.need(cloud=='aws' and set(group['regions'].values())=={'us-east-2'},'aws_ohio_scope_only')
            zones=group.get('zones',{});zone_ids=group.get('zone_ids',{})
            c.need(set(zones)==set(zone_ids)==set(group['regions']) and len(set(zones.values()))==len(set(zone_ids.values()))==3,
                   'three_aws_azs_required')
            import re
            c.need(all(re.fullmatch(r'us-east-2[a-z]',z) for z in zones.values())
                   and all(re.fullmatch(r'use2-az[1-9][0-9]*',z) for z in zone_ids.values()),'ohio_az_identity_required')
            c.need(bool(re.fullmatch(r'[a-f0-9]{64}',group.get('scope_amendment_sha256',''))),'scope_amendment_required')
        else:c.need(len(set(group['regions'].values()))==3,'three_regional_borders_per_cloud_required')
        c.need(m.cluster_id not in clusters and m.anchor_key_id not in keys,'separate_cloud_authorities_required')
        clusters.add(m.cluster_id);keys.add(m.anchor_key_id)
        for n in m.nodes:
            c.need(n['node_id'] not in nodes,'distinct_ingress_nodes_required');nodes.add(n['node_id'])
            c.need(n['key_id'] not in runtime_keys,'distinct_runtime_keys_required');runtime_keys.add(n['key_id'])
        c.need(group['members'],'receiving_group_member_required')
        for member in group['members']:
            binding=member['binding'];p.validate_binding(binding,'member');p.validate_model(member['model_profile'])
            p.validate_tool(member['tool_call'],model=member['model_profile'])
            import re
            # The contract digest also binds source, interpreter and selection.
            # Native evidence reports the discovered MCP input-schema digest.
            # Pin that separate value from no-effect preflight before dispatch.
            c.need(bool(re.fullmatch(r'[a-f0-9]{64}',member.get('mcp_input_schema_sha256',''))),
                   'pinned_mcp_input_schema_required')
            c.need(p.key_id(member['certificate'])==binding['key_id'],'member_certificate_changed')
            c.need(binding['key_id'] not in runtime_keys,'distinct_runtime_keys_required');runtime_keys.add(binding['key_id'])
            c.need(binding['member_id'] not in members,'distinct_member_identities_required');members.add(binding['member_id'])
        if cloud=='aws':c.need(len(group['members'])==3,'three_aws_members_required')
        result[cloud]=m
    return result


def freeze(stage, groups, anchors, start_ms, deadline_ms):
    c.need(stage in (4,5),'matrix_stage_required')
    c.need(set(groups)==({'aws'} if stage==4 else {'aws','azure','gcp'}),'exact_cloud_groups_required')
    c.need(type(start_ms) is int and type(deadline_ms) is int and 0<deadline_ms-start_ms<=c.MAX_SECONDS[stage]*1000,
           'bounded_matrix_window_required')
    verified=manifests(groups,anchors);cells=[]
    ingresses=[(cloud,node) for cloud in sorted(groups) for node in verified[cloud].nodes]
    for index,(cloud,node) in enumerate(ingresses):
        targets=[('aws',member) for member in groups['aws']['members']] if stage==4 else [
            (target,groups[target]['members'][index%3 if target=='aws' else 0]) for target in sorted(groups)]
        for target,member in targets:
            identity=dict(ingress_cloud=cloud,ingress_region=groups[cloud]['regions'][node['node_id']],
                qualification_scope=groups[cloud].get('qualification_scope','three-region'),
                ingress_zone=groups[cloud].get('zones',{}).get(node['node_id']),
                ingress_zone_id=groups[cloud].get('zone_ids',{}).get(node['node_id']),
                ingress_node=node['node_id'],receiving_cloud=target,receiving_group=verified[target].audience,
                member=member['binding'],model_profile=member['model_profile'],tool_call=member['tool_call'],
                operator=principal(verified[cloud].cluster_id),receiving_principal=principal(verified[target].cluster_id))
            cells.append(dict(identity,cell_id=c.digest(identity)))
    return copy.deepcopy(dict(schema=1,stage=stage,groups=groups,anchors=anchors,cells=cells,
                start_ms=start_ms,deadline_ms=deadline_ms,live_acceptance=False))


def _binding(node,generation):
    return {**{k:node[k] for k in ('installation_id','identity','key_id')},'authority_generation':generation}


def _json(value):return json.loads(value) if isinstance(value,str) else value


def verify_cell(matrix, expected_matrix_sha256, assignment, expected_assignment_sha256, artifacts):
    c.need(c.digest(matrix)==expected_matrix_sha256,'frozen_matrix_changed')
    c.need(c.digest(assignment)==expected_assignment_sha256,'original_cell_assignment_changed')
    # Rebuild coverage from pinned inputs; a caller cannot replace a cell's member
    # while leaving the topological claim unchanged.
    rebuilt=freeze(matrix['stage'],matrix['groups'],matrix['anchors'],matrix['start_ms'],matrix['deadline_ms'])
    c.need(rebuilt==matrix,'matrix_coverage_changed')
    found=[x for x in matrix['cells'] if x['cell_id']==assignment['cell_id']]
    c.need(len(found)==1,'exact_matrix_cell_required');cell=found[0]
    p,verify_manifest,verify_proof=contracts();ms=manifests(matrix['groups'],matrix['anchors'])
    source,target=ms[cell['ingress_cloud']],ms[cell['receiving_cloud']]
    ingress=source.node(cell['ingress_node'])
    member=next(m for m in matrix['groups'][cell['receiving_cloud']]['members'] if m['binding']==cell['member'])
    row=artifacts['member_row'];approval=_json(row['approval']);receipt=_json(row['receipt']);ack=_json(row['ack'])
    issuer=target.node(approval['payload']['cluster']['issuer_node_id'])
    a=p.verify(approval,issuer['certificate'],p.HA_APPROVAL)
    r=p.verify(receipt,member['certificate'],p.HA_RESULT)
    accepter=target.node(ack['payload']['acceptance']['node_id'])
    k=p.verify(ack,accepter['certificate'],p.HA_ACK)
    for payload in (a,r,k):
        c.need(payload['operation_id']==assignment['operation_id'],'original_operation_required')
        c.need(payload['member']==cell['member'],'wrong_receiving_member')
        cluster=payload['cluster']
        c.need(all(cluster[key]==value for key,value in target.audience.items())
               and cluster['manifest_revision']==target.revision,'wrong_receiving_group')
    c.need(r['cluster']==k['cluster']==a['cluster'],'original_authority_changed')
    c.need(a['border']==r['border']==k['border']==_binding(issuer,target.generation),'issuer_binding_changed')
    c.need(k['acceptance']['border']==_binding(accepter,target.generation)
           and k['acceptance']['authority_epoch']>=a['cluster']['authority_epoch'],'ack_authority_changed')
    c.need(a['principal']==r['principal']==cell['receiving_principal'],'receiving_principal_changed')
    c.need(a['model_profile']==r['model_profile']==cell['model_profile'],'model_profile_changed')
    c.need(a['tool_call']==cell['tool_call'] and r['tool_call_sha256']==p.sha256(cell['tool_call']),'tool_call_changed')
    approval_sha=p.digest(p.HA_APPROVAL,a);receipt_sha=p.digest(p.HA_RESULT,r)
    c.need(assignment['approval_sha256']==approval_sha==r['approval_sha256']==row['approval_digest'],'original_approval_changed')
    c.need(k['receipt_sha256']==receipt_sha==row['receipt_digest'],'original_receipt_changed')
    for field in ('approval_id','attempt_id','receipt_id'):
        c.need(r[field]==k[field],'ack_result_identity_mismatch')
    c.need(a['approval_id']==r['approval_id'],'approval_result_identity_mismatch')
    c.need(matrix['start_ms']<=a['issued_at_ms']<=r['started_at_ms']<=r['finished_at_ms']<=k['accepted_at_ms']<=matrix['deadline_ms'],
           'result_outside_campaign_window')
    c.need(r['outcome']=='succeeded' and r['effect_status']=='finished' and r['error_code'] is None,'successful_native_result_required')
    c.need(row['side']=='member' and row['state']=='acknowledged' and row['ack_pending']==0
           and row['operation_id']==a['operation_id'] and row['attempt_id']==r['attempt_id']
           and row['effect_claimed']==row['effect_finished']==1,'durable_original_member_row_required')
    tool=_json(row['tool_evidence'])
    c.need(p.sha256(tool)==r['tool_evidence_sha256'],'native_evidence_digest_mismatch')
    c.need(tool['tool']==cell['tool_call']['tool'] and tool['arguments']==cell['tool_call']['arguments']
           and tool['endpoint_sha256']==cell['tool_call']['endpoint_sha256']
           and tool['mcp_schema_sha256']==member['mcp_input_schema_sha256']
           and type(tool['mcp_calls']) is int and tool['mcp_calls']==1,'one_exact_native_call_required')
    c.need(r['usage'].get('tool_calls')==1 and r['usage'].get('inference_calls')==2,'bounded_native_counts_required')
    capture=artifacts['ingress_capture']
    c.need(c.digest(capture)==assignment['capture_sha256'],'original_ingress_capture_changed')
    c.need(capture['origin']==ingress['endpoints']['https'] and capture['operation_id']==a['operation_id']
           and capture['status']==200,'wrong_ingress_capture')
    dto=copy.deepcopy(capture['body'])
    c.need(dto['operation_id']==a['operation_id'] and dto['result']['digest']==receipt_sha,'stale_ingress_result')
    authority=dto['authority']
    c.need(all(authority[key]==value for key,value in source.audience.items())
           and authority['served_by']==ingress['node_id'],'wrong_ingress_node')
    if source.cluster_id!=target.cluster_id:
        c.need(cell['operator']==principal(source.cluster_id),'cross_group_principal_refused')
        binding=dto['remote'].pop('client_binding');proof=verify_proof(binding['endorsement'],ingress['certificate'],'peer-client')
        c.need(proof['origin']==dict(source.audience,node_id=ingress['node_id']) and proof['principal']==cell['operator']
               and proof['operation_sha256']==p.sha256(dto),'remote_ingress_endorsement_mismatch')
        c.need(proof['peer_anchor_key_id']==matrix['anchors'][cell['receiving_cloud']]
               and proof['peer_manifest_sha256']==p.sha256(binding['manifest']),'wrong_remote_anchor_or_manifest')
        peer=verify_manifest(binding['manifest'],binding['anchor_certificate'],expected_key_id=proof['peer_anchor_key_id'])
        c.need(peer.value==target.value,'wrong_remote_group')
        c.need(dto['remote']['cluster']==target.audience,'remote_group_attribution_changed')
    else:c.need('remote' not in dto,'unexpected_remote_attribution')
    return dict(cell_id=cell['cell_id'],operation_id=a['operation_id'],result_sha256=receipt_sha,
        ack_sha256=p.digest(p.HA_ACK,k),member_id=cell['member']['member_id'],receiving_cloud=cell['receiving_cloud'],
        original_signatures_verified=True,live_placement_verified=False)


def verify_all(matrix, matrix_sha256, assignments, assignment_digests, artifacts):
    expected={cell['cell_id'] for cell in matrix['cells']}
    c.need(set(assignments)==set(assignment_digests)==set(artifacts)==expected,'complete_exact_cell_coverage_required')
    c.need(len({row['operation_id'] for row in assignments.values()})==len(expected),'operation_reused_across_cells')
    results=[verify_cell(matrix,matrix_sha256,assignments[key],assignment_digests[key],artifacts[key]) for key in sorted(expected)]
    c.need({r['member_id'] for r in results if r['receiving_cloud']=='aws'}==
           {m['binding']['member_id'] for m in matrix['groups']['aws']['members']},'all_three_aws_members_required')
    return {'verified_cells':len(results),'results':results,'live_acceptance':False}
