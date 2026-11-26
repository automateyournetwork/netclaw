"""Signed synthetic fixtures; no cloud, device, provider or live acceptance."""
import copy
import json
from pathlib import Path
import sys
import unittest
import uuid
sys.path[:0]=[str(Path(__file__).resolve().parents[4]/'tests/n2n'),
              str(Path(__file__).resolve().parents[4]/'mcp-servers/protocol-mcp')]
from protected_support_171 import identity, approval
from test_ha_contract_179 import manifest_fixture
from bgp.federation import protected_contract as p
from bgp.federation.ha.config import sign_manifest, HAError
from bgp.federation.ha.signatures import sign
import campaign as c
import matrix as m

NOW=1795700000000


def world(stage=5):
    groups={};anchors={};keys={}
    for cloud in (['aws'] if stage==4 else ['aws','azure','gcp']):
        value,cert,key=manifest_fixture();nodekeys={}
        for n in value['nodes']:
            signer=identity(cloud+'-border');n.update(certificate=signer['cert_pem'],key_id=signer['key_id'])
            nodekeys[n['node_id']]=signer
        members=[];memberkeys={}
        for i in range(3 if cloud=='aws' else 1):
            signer=identity(cloud+'-member');sample=approval(next(iter(nodekeys.values())),signer,now=NOW)
            sample['member']['member_id']=cloud+'-member-'+str(i)
            members.append(dict(binding=sample['member'],certificate=signer['cert_pem'],
                                model_profile=sample['model_profile'],tool_call=sample['tool_call'],
                                mcp_input_schema_sha256='a'*64))
            memberkeys[sample['member']['member_id']]=signer
        groups[cloud]=dict(enrollment={'manifest':sign_manifest(value,key),'anchor_certificate':cert},
            regions={n['node_id']:cloud+'-region-'+str(i) for i,n in enumerate(value['nodes'])},members=members)
        anchors[cloud]=p.key_id(cert);keys[cloud]=(nodekeys,memberkeys)
    matrix=m.freeze(stage,groups,anchors,NOW,NOW+600000)
    return matrix,keys


def cell_fixture(matrix,keys,cell):
    cell=copy.deepcopy(cell)
    target=matrix['groups'][cell['receiving_cloud']]['enrollment']['manifest']['manifest']
    source=matrix['groups'][cell['ingress_cloud']]['enrollment']['manifest']['manifest']
    issuer=target['nodes'][0];accepter=target['nodes'][1]
    origin=next(n for n in source['nodes'] if n['node_id']==cell['ingress_node'])
    nk,mk=keys[cell['receiving_cloud']];member=mk[cell['member']['member_id']]
    a=approval(nk[issuer['node_id']],member,now=NOW+1)
    a.update(principal=cell['receiving_principal'],border=m._binding(issuer,target['generation']),
        member=cell['member'],model_profile=cell['model_profile'],tool_call=cell['tool_call'],
        cluster=dict(cell['receiving_group'],manifest_revision=target['revision'],issuer_node_id=issuer['node_id'],authority_epoch=1))
    a['review_sha256']=p.sha256(p.review_from_payload(a));signed_a=p.sign(p.HA_APPROVAL,a,nk[issuer['node_id']]['key_pem'])
    selected=next(m for m in matrix['groups'][cell['receiving_cloud']]['members'] if m['binding']==cell['member'])
    tool={'schemaVersion':1,'tool':cell['tool_call']['tool'],'arguments':cell['tool_call']['arguments'],
        'endpoint_sha256':cell['tool_call']['endpoint_sha256'],'mcp_schema_sha256':selected['mcp_input_schema_sha256'],'mcp_calls':1}
    r=dict(receipt_id=str(uuid.uuid4()),operation_id=a['operation_id'],approval_id=a['approval_id'],approval_sha256=p.digest(p.HA_APPROVAL,a),
        attempt_id=str(uuid.uuid4()),**{k:a[k] for k in ('principal','border','member','model_profile','cluster')},
        tool_call_sha256=p.sha256(a['tool_call']),started_at_ms=NOW+2,finished_at_ms=NOW+3,outcome='succeeded',effect_status='finished',
        output={'fixture':True},output_sha256=p.sha256({'fixture':True}),tool_evidence_sha256=p.sha256(tool),
        usage={'inference_calls':2,'tool_calls':1},audit_refs={'fixture':'fixture'},error_code=None)
    signed_r=p.sign(p.HA_RESULT,r,member['key_pem'])
    k=dict(ack_id=str(uuid.uuid4()),**{key:r[key] for key in ('operation_id','approval_id','attempt_id','receipt_id','border','member','cluster')},
        receipt_sha256=p.digest(p.HA_RESULT,r),accepted_at_ms=NOW+4,audit_ref='fixture',
        acceptance=dict(node_id=accepter['node_id'],border=m._binding(accepter,target['generation']),authority_epoch=2))
    signed_k=p.sign(p.HA_ACK,k,nk[accepter['node_id']]['key_pem'])
    row=dict(side='member',state='acknowledged',ack_pending=0,effect_claimed=1,effect_finished=1,
        operation_id=a['operation_id'],attempt_id=r['attempt_id'],approval_digest=r['approval_sha256'],receipt_digest=k['receipt_sha256'],
        approval=json.dumps(signed_a),receipt=json.dumps(signed_r),ack=json.dumps(signed_k),tool_evidence=json.dumps(tool))
    dto=dict(operation_id=a['operation_id'],result={'digest':k['receipt_sha256']},authority={
        'cluster_id':source['cluster_id'],'generation':source['generation'],'served_by':origin['node_id']})
    if cell['ingress_cloud']!=cell['receiving_cloud']:
        dto['remote']={'cluster':cell['receiving_group'],'label':cell['receiving_cloud']}
        enrollment=matrix['groups'][cell['receiving_cloud']]['enrollment']
        proof=dict(origin=dict(cluster_id=source['cluster_id'],generation=source['generation'],node_id=origin['node_id']),
            principal=cell['operator'],peer_anchor_key_id=matrix['anchors'][cell['receiving_cloud']],
            peer_manifest_sha256=p.sha256(enrollment['manifest']),operation_sha256=p.sha256(dto))
        dto['remote']['client_binding']=dict(enrollment,endorsement=sign('peer-client',proof,keys[cell['ingress_cloud']][0][origin['node_id']]['key_pem']))
    capture=dict(origin=origin['endpoints']['https'],operation_id=a['operation_id'],status=200,body=dto)
    assignment=dict(cell_id=cell['cell_id'],operation_id=a['operation_id'],approval_sha256=r['approval_sha256'],capture_sha256=c.digest(capture))
    return assignment,{'member_row':row,'ingress_capture':capture}


class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.matrix,cls.keys=world()

    def test_full_27_cells_are_signed_exact_and_include_all_three_aws_members(self):
        matrix=self.matrix;assignments={};artifacts={}
        for cell in matrix['cells']:
            a,r=cell_fixture(matrix,self.keys,cell);assignments[cell['cell_id']]=a;artifacts[cell['cell_id']]=r
        result=m.verify_all(matrix,c.digest(matrix),assignments,{k:c.digest(v) for k,v in assignments.items()},artifacts)
        self.assertEqual(result['verified_cells'],27);self.assertFalse(result['live_acceptance'])
        self.assertEqual(len({r['member_id'] for r in result['results'] if r['receiving_cloud']=='aws'}),3)

    def test_stage_four_has_exact_nine_aws_pairs(self):
        matrix,keys=world(4);self.assertEqual(len(matrix['cells']),9)
        for cell in matrix['cells']:
            a,r=cell_fixture(matrix,keys,cell)
            self.assertTrue(m.verify_cell(matrix,c.digest(matrix),a,c.digest(a),r)['original_signatures_verified'])

    def test_input_schema_pin_is_required_and_distinct_from_tool_contract(self):
        matrix,keys=world(4);cell=matrix['cells'][0]
        member=next(row for row in matrix['groups']['aws']['members'] if row['binding']==cell['member'])
        self.assertNotEqual(member['mcp_input_schema_sha256'],cell['tool_call']['tool_schema_sha256'])
        assignment,artifacts=cell_fixture(matrix,keys,cell)
        self.assertTrue(m.verify_cell(matrix,c.digest(matrix),assignment,c.digest(assignment),artifacts)['original_signatures_verified'])
        # Altering the independent preflight pin cannot bless an old signed result.
        changed=copy.deepcopy(matrix);changed['groups']['aws']['members'][0]['mcp_input_schema_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'one_exact_native_call_required'):
            m.verify_cell(changed,c.digest(changed),assignment,c.digest(assignment),artifacts)
        for bad in (None,'','z'*64):
            changed=copy.deepcopy(matrix)
            if bad is None:del changed['groups']['aws']['members'][0]['mcp_input_schema_sha256']
            else:changed['groups']['aws']['members'][0]['mcp_input_schema_sha256']=bad
            with self.assertRaisesRegex(ValueError,'pinned_mcp_input_schema_required'):
                m.freeze(4,changed['groups'],changed['anchors'],changed['start_ms'],changed['deadline_ms'])

    def test_original_signature_ack_tool_and_unknown_row_cannot_be_replaced(self):
        cell=self.matrix['cells'][0]
        for attack in ('signature','ack','tool','unknown','no_effect','wrong_operation','wrong_profile','old_window'):
            a,art=cell_fixture(self.matrix,self.keys,cell);row=art['member_row']
            if attack=='signature':
                r=json.loads(row['receipt']);r['payload']['output']={'forged':True};row['receipt']=r
            if attack=='ack':
                k=json.loads(row['ack']);k['payload']['receipt_sha256']='a'*64;row['ack']=k
            if attack=='tool':
                t=json.loads(row['tool_evidence']);t['mcp_calls']=2;row['tool_evidence']=t
            if attack=='unknown':row['ack_pending']=1
            if attack=='no_effect':row['effect_finished']=0
            if attack=='wrong_operation':a['operation_id']=str(uuid.uuid4())
            if attack=='wrong_profile':
                r=json.loads(row['receipt']);r['payload']['model_profile']['profile_id']='replacement';row['receipt']=r
            if attack=='old_window':
                r=json.loads(row['receipt']);r['payload']['started_at_ms']=NOW-10000;row['receipt']=r
            with self.subTest(attack=attack),self.assertRaises((ValueError,p.ProtectedError,HAError)):
                m.verify_cell(self.matrix,c.digest(self.matrix),a,c.digest(a),art)

    def test_wrong_remote_group_node_member_and_device_principal_refused(self):
        cell=next(x for x in self.matrix['cells'] if x['ingress_cloud']!=x['receiving_cloud'])
        for attack in ('group','node','member','device','endorsement'):
            a,art=cell_fixture(self.matrix,self.keys,cell);dto=art['ingress_capture']['body']
            if attack=='group':dto['remote']['cluster']['cluster_id']=str(uuid.uuid4())
            if attack=='node':dto['authority']['served_by']=str(uuid.uuid4())
            if attack=='member':
                row=art['member_row'];r=json.loads(row['receipt']);r['payload']['member']['member_id']='foreign';row['receipt']=r
            if attack=='device':dto['remote']['client_binding']['endorsement']['payload']['principal']['issuer']='device-key'
            if attack=='endorsement':dto['remote']['client_binding']['endorsement']['signature']='a'*60
            a['capture_sha256']=c.digest(art['ingress_capture'])
            with self.subTest(attack=attack),self.assertRaises((ValueError,p.ProtectedError,HAError)):
                m.verify_cell(self.matrix,c.digest(self.matrix),a,c.digest(a),art)

    def test_grant_refusal_is_preserved_and_cannot_satisfy_success_cell(self):
        cell=self.matrix['cells'][0];a,art=cell_fixture(self.matrix,self.keys,cell)
        row=art['member_row'];r=json.loads(row['receipt']);r['payload'].update(outcome='refused',effect_status='not_started',error_code='peer_grant_refused')
        signer=self.keys[cell['receiving_cloud']][1][cell['member']['member_id']]
        row['receipt']=p.sign(p.HA_RESULT,r['payload'],signer['key_pem'])
        # A valid signed refusal and matching ACK are still not a successful cell.
        row['receipt_digest']=p.digest(p.HA_RESULT,r['payload']);ack=json.loads(row['ack'])
        ack['payload']['receipt_sha256']=row['receipt_digest']
        nodekey=self.keys[cell['receiving_cloud']][0][ack['payload']['acceptance']['node_id']]
        row['ack']=p.sign(p.HA_ACK,ack['payload'],nodekey['key_pem'])
        with self.assertRaisesRegex(ValueError,'successful_native_result_required'):
            m.verify_cell(self.matrix,c.digest(self.matrix),a,c.digest(a),art)

    def test_missing_and_reused_cells_and_changed_frozen_inputs_refused(self):
        a,art=cell_fixture(self.matrix,self.keys,self.matrix['cells'][0])
        with self.assertRaisesRegex(ValueError,'complete_exact_cell_coverage_required'):
            m.verify_all(self.matrix,c.digest(self.matrix),{}, {}, {})
        assignments={x['cell_id']:a for x in self.matrix['cells']}
        with self.assertRaisesRegex(ValueError,'operation_reused_across_cells'):
            m.verify_all(self.matrix,c.digest(self.matrix),assignments,{k:c.digest(v) for k,v in assignments.items()},
                         {k:art for k in assignments})
        changed=copy.deepcopy(self.matrix);changed['cells'][0]['member']['member_id']='foreign'
        with self.assertRaisesRegex(ValueError,'frozen_matrix_changed'):
            m.verify_cell(changed,c.digest(self.matrix),a,c.digest(a),art)


if __name__=='__main__':unittest.main()
