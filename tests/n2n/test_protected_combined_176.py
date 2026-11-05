"""Synthetic authority tests derived from Thermidor004, not provider/live evidence."""
import asyncio
import copy
import uuid
import pytest
from protected_support_171 import OperationPair, module, sha

contract=module('protected_contract')


async def close(pair):
    await pair.border.close()
    await pair.member.close()


def setup(tmp_path):
    pair=OperationPair(tmp_path)
    entries=[]
    for index,(family,cidr) in enumerate([(4,'192.0.2.0/26'),(6,'2001:db8:1234::/48')]):
        entry=copy.deepcopy(pair.catalog_entry)
        entry['member']['member_id']='fixture/member'+str(family)
        entry['member']['installation_id']=str(uuid.uuid4())
        model=entry['model_profiles'][0]
        model.update(profile_id='ollama-cpu-ipv'+str(family),profile_revision='r05-fixture',
                     provider='ollama',model='qwen3:0.6b',runtime_kind='openclaw',runtime_version='2026.7.1-2')
        tool=entry['tools'][0]
        tool.update(tool='subnet_calculator' if family==4 else 'subnet_calculator_v6',
                    arguments={'cidr':cidr},arguments_sha256=sha({'cidr':cidr}),device_ref='calculator'+str(family))
        tool['limits'].update(inference_timeout_ms=60000 if family==4 else 120000,max_output_bytes=32768)
        pair.accepted_bindings.append(entry['member'])
        entries.append(entry)
    pair.border.catalog_provider=lambda:copy.deepcopy(entries)
    calls=[]
    async def transport(member,method,args):
        calls.append((member,method,args))
        if method=='execution/submit':return {'operation_id':args['approval']['payload']['operation_id']}
        return {'operation_id':args['operation_id'],'state':'admitted','receipt_ready':False}
    pair.border.transport=transport
    request={'auth_context':pair.auth,'client_nonce':'combined-fixture','children':[
        {'family':4 if i==0 else 6,'member_id':e['member']['member_id'],
         'profile_revision':'r05-fixture','cidr':e['tools'][0]['arguments']['cidr']} for i,e in enumerate(entries)]}
    return pair,entries,request,calls


def decide(pair,child,decision='approve'):
    return pair.border.decision({'auth_context':pair.auth,'operation_id':child['operation_id'],
        'revision':child['revision'],'review_digest':child['review_digest'],'decision':decision})


def test_parent_preparation_atomic_stable_no_dispatch(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path)
        first=await pair.border.combined_prepare(req)
        second=await pair.border.combined_prepare(req)
        assert first==second and first['state']=='awaiting_decisions' and not calls
        assert first['children'][0]['operation_id']!=first['children'][1]['operation_id']
        assert 'approve' in first['children'][0]['allowed_actions']
        assert 'approve' not in first['children'][1]['allowed_actions']
        assert [c['family'] for c in first['children']]==[4,6]
        changed=copy.deepcopy(req);changed['children'][0]['cidr']='192.0.2.64/26'
        with pytest.raises(contract.ProtectedError,match='client_nonce_conflict'):
            await pair.border.combined_prepare(changed)
        with pair.border.store.connection() as conn:
            assert conn.execute('SELECT count(*) FROM protected_combined').fetchone()[0]==1
            assert conn.execute("SELECT count(*) FROM protected_operation WHERE side='border'").fetchone()[0]==2
        await close(pair)
    asyncio.run(run())


def test_separate_ordered_decisions_never_replay_and_get_is_read_only(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path)
        parent=await pair.border.combined_prepare(req)
        with pytest.raises(contract.ProtectedError,match='combined_previous_decision_pending'):
            await decide(pair,parent['children'][1])
        assert not calls
        await decide(pair,parent['children'][0], 'deny')
        parent=await pair.border.combined_status({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        assert 'approve' in parent['children'][1]['allowed_actions']
        await decide(pair,parent['children'][1])
        await decide(pair,parent['children'][1])
        assert sum(method=='execution/submit' for _,method,_ in calls)==1
        for _ in range(3):
            result=await pair.border.combined_status({'auth_context':pair.auth,'client_nonce':req['client_nonce']})
            assert result['parent_id']==parent['parent_id']
        assert sum(method=='execution/submit' for _,method,_ in calls)==1
        assert result['children'][0]['state']=='refused'
        await close(pair)
    asyncio.run(run())


def test_cancel_refuses_late_approval_and_preserves_original_rows(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path);parent=await pair.border.combined_prepare(req)
        cancelled=await pair.border.combined_cancel({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        assert cancelled['cancelled'] and cancelled['state']=='cancelled'
        with pytest.raises(contract.ProtectedError):await decide(pair,cancelled['children'][0])
        assert not calls
        repeated=await pair.border.combined_prepare(req)
        assert [c['operation_id'] for c in repeated['children']]==[c['operation_id'] for c in parent['children']]
        assert repeated['cancelled']
        await close(pair)
    asyncio.run(run())


def test_changed_current_profile_and_expired_review_refused(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path);parent=await pair.border.combined_prepare(req)
        entries[0]['model_profiles'][0]['profile_revision']='new-profile'
        with pytest.raises(contract.ProtectedError,match='profile_changed'):await decide(pair,parent['children'][0])
        entries[0]['model_profiles'][0]['profile_revision']='r05-fixture'
        pair.now+=180001
        with pytest.raises(contract.ProtectedError,match='approval_expired'):await decide(pair,parent['children'][0])
        assert not calls
        await close(pair)
    asyncio.run(run())


@pytest.mark.parametrize('change',['third','duplicate','family','unknown','foreign_profile'])
def test_invalid_combined_selection_creates_no_child_authority(tmp_path,change):
    async def run():
        pair,entries,req,calls=setup(tmp_path)
        if change=='third':req['children'].append(req['children'][0])
        elif change=='duplicate':req['children'][1]=dict(req['children'][0])
        elif change=='family':req['children'][0]['family']=True
        elif change=='unknown':req['url']='http://127.0.0.1'
        else:req['children'][1]['profile_revision']='stale'
        with pytest.raises(contract.ProtectedError):await pair.border.combined_prepare(req)
        with pair.border.store.connection() as conn:
            assert conn.execute('SELECT count(*) FROM protected_operation').fetchone()[0]==0
        assert not calls
        await close(pair)
    asyncio.run(run())


def test_parent_scope_and_atomic_rollback(tmp_path,monkeypatch):
    async def run():
        pair,entries,req,calls=setup(tmp_path)
        create=pair.border.store.create_combined
        def duplicate(parent,rows):
            rows[1]['operation_id']=rows[0]['operation_id']
            return create(parent,rows)
        monkeypatch.setattr(pair.border.store,'create_combined',duplicate)
        with pytest.raises(Exception):await pair.border.combined_prepare(req)
        with pair.border.store.connection() as conn:
            assert conn.execute('SELECT count(*) FROM protected_combined').fetchone()[0]==0
            assert conn.execute('SELECT count(*) FROM protected_operation').fetchone()[0]==0
        monkeypatch.setattr(pair.border.store,'create_combined',create)
        parent=await pair.border.combined_prepare(req)
        foreign=OperationPair(tmp_path/'foreign')
        with pytest.raises(contract.ProtectedError):
            await pair.border.combined_status({'auth_context':foreign.auth,'parent_id':parent['parent_id']})
        await close(foreign);await close(pair)
    asyncio.run(run())


def test_unknown_child_does_not_overwrite_completed_sibling(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path);parent=await pair.border.combined_prepare(req)
        # Only state projection is synthetic here; no forged signed receipt is supplied.
        with pair.border.store.transaction() as conn:
            conn.execute("UPDATE protected_operation SET state='completed' WHERE operation_id=?",(parent['children'][0]['operation_id'],))
            conn.execute("UPDATE protected_operation SET state='reconciliation_required' WHERE operation_id=?",(parent['children'][1]['operation_id'],))
        result=await pair.border.combined_status({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        assert result['state']=='unknown' and result['children'][0]['state']=='completed'
        assert result['children'][0]['result'] is None  # no invented success evidence
        assert not calls
        pair.border.store.recover()
        recovered=await pair.border.combined_status({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        assert recovered==result and not calls
        await close(pair)
    asyncio.run(run())


def test_session_deadline_clips_plan_and_child_expiry(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path)
        with pair.owner.locked() as conn:
            conn.execute('UPDATE owner_session SET expires_ms=?',(pair.now+60000,))
        parent=await pair.border.combined_prepare(req)
        assert parent['expires_at_ms']==pair.now+60000
        assert all(c['review']['limits']['expires_at_ms']==parent['expires_at_ms'] for c in parent['children'])
        await close(pair)
    asyncio.run(run())


def test_second_approval_does_not_wait_for_first_runtime_and_cancel_retains_late_result(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path);parent=await pair.border.combined_prepare(req)
        await decide(pair,parent['children'][0])
        await decide(pair,parent['children'][1])
        assert sum(method=='execution/submit' for _,method,_ in calls)==2
        cancelled=await pair.border.combined_cancel({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        assert cancelled['cancelled']
        # A terminal refusal from dispatched work remains collectible after cancellation.
        child=parent['children'][0]['operation_id']
        pair.border.store.transition('border',child,'member_admitted',state='refused')
        result=await pair.border.combined_status({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        assert result['children'][0]['state']=='refused' and result['cancelled']
        assert sum(method=='execution/submit' for _,method,_ in calls)==2
        await close(pair)
    asyncio.run(run())


def test_changed_enrollment_blocks_decision_and_foreign_installation_blocks_parent(tmp_path):
    async def run():
        pair,entries,req,calls=setup(tmp_path);parent=await pair.border.combined_prepare(req)
        pair.accepted_bindings.remove(entries[0]['member'])
        with pytest.raises(contract.ProtectedError):await decide(pair,parent['children'][0])
        assert not calls
        pair.border.identity=dict(pair.border.identity,installation_id=str(uuid.uuid4()))
        with pytest.raises(contract.ProtectedError,match='combined_not_found'):
            await pair.border.combined_status({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        await close(pair)
    asyncio.run(run())


def test_mobile_routes_use_native_device_principal_and_exact_allowlist(tmp_path):
    from types import SimpleNamespace
    from bgp.federation.service import FederationService
    from bgp.federation.edge import RpcError, EDGE_METHODS
    from bgp.federation.mobile_enrollment import MOBILE_METHODS
    async def run():
        pair,entries,req,calls=setup(tmp_path)
        installation=pair.border.identity['installation_id']
        member={'node_type':'edge','state':'active','installation_id':installation,
                'key_fingerprint':'test-device-key','enrollment_generation':'generation-1'}
        channel=SimpleNamespace(trusted=True,_closed=False,member_id='test-device',
            owner_generation=member['key_fingerprint'],enrollment_generation=member['enrollment_generation'])
        service=SimpleNamespace(protected_enabled=True,protected_operations=pair.border,
            runtime=SimpleNamespace(installation=installation),edge_channels={'test-device':channel},
            risk=SimpleNamespace(get_member=lambda _:member))
        routes={name:FederationService._edge_protected_handler(service,name) for name in
                ('combined_prepare','combined_status','combined_cancel')}
        assert tuple('n2n/edge/operations/'+name for name in routes)==MOBILE_METHODS[-3:]
        assert set(MOBILE_METHODS)<=set(EDGE_METHODS)
        body={k:v for k,v in req.items() if k!='auth_context'};body['installation_id']=installation
        for bad in (dict(body,principal={}),dict(body,auth_context=req['auth_context']),dict(body,installation_id=str(uuid.uuid4()))):
            with pytest.raises(RpcError) as caught:await routes['combined_prepare'](channel,bad)
            assert caught.value.data['admission']=='not_submitted'
        parent=await routes['combined_prepare'](channel,body)
        assert all(c['review']['principal']['issuer']=='device-key' for c in parent['children'])
        assert all('revoke' not in c['allowed_actions'] for c in parent['children'])
        selected={'installation_id':installation,'parent_id':parent['parent_id']}
        assert (await routes['combined_status'](channel,selected))['parent_id']==parent['parent_id']
        assert (await routes['combined_cancel'](channel,selected))['cancelled']
        channel._closed=True
        with pytest.raises(RpcError):await routes['combined_status'](channel,selected)
        assert not calls
        await close(pair)
    asyncio.run(run())


def test_signed_success_survives_sibling_unknown_lost_ack_cancel_and_restart(tmp_path):
    """Real authority/signature/SQLite path; executor output is explicitly synthetic."""
    async def run():
        pair,entries,req,calls=setup(tmp_path)
        pair.template['member']=entries[0]['member']
        pair.catalog_entry=entries[0]
        def rebuild():
            pair._build()
            pair.border.catalog_provider=lambda:copy.deepcopy(entries)
            transport=pair.border.transport
            async def combined_transport(member,method,args):
                calls.append((member,method,args))
                if member==entries[1]['member']['member_id']:
                    raise ConnectionError('synthetic sibling outcome unknown')
                return await transport(member,method,args)
            pair.border.transport=combined_transport
        rebuild()
        parent=await pair.border.combined_prepare(req)
        pair.drop_submit_reply=True
        await decide(pair,parent['children'][0])
        await pair.drain()
        pair.drop_ack_reply=True
        successful=await pair.border.combined_status({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        result=successful['children'][0]['result']
        assert result['verified'] and result['durable_ack'] and result['ack_delivery_pending']
        assert successful['children'][0]['state']=='completed'
        await decide(pair,parent['children'][1])
        unknown=await pair.border.combined_cancel({'auth_context':pair.auth,'parent_id':parent['parent_id']})
        assert unknown['state']=='unknown' and unknown['children'][0]['result']==result
        before=[c['operation_id'] for c in unknown['children']]
        claims_before=pair.executor_calls,len(pair.effects),sum(m=='execution/submit' for _,m,_ in calls)
        await close(pair);rebuild()
        await pair.border.start();await pair.member.start()
        pair.drop_ack_reply=False
        for _ in range(3):
            recovered=await pair.border.combined_status({'auth_context':pair.auth,'client_nonce':req['client_nonce']})
            assert recovered['state']=='unknown' and recovered['cancelled']
            assert [c['operation_id'] for c in recovered['children']]==before
            assert recovered['children'][0]['result']['digest']==result['digest']
            assert recovered['children'][0]['result']['durable_ack']
            assert not recovered['children'][0]['result']['ack_delivery_pending']
        assert claims_before==(pair.executor_calls,len(pair.effects),sum(m=='execution/submit' for _,m,_ in calls))==(1,1,2)
        await close(pair)
    asyncio.run(run())
