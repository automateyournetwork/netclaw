"""Offline R06 saved-plan ownership and one-use execution controls."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'labs/cloud/gcp/r06'


def module(name):
    spec = importlib.util.spec_from_file_location('r06_' + name, SOURCE / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
    path.chmod(0o600)


budget, plan = [module(n) for n in ('budget_observation', 'review_plan')]


def observation():
    name='billingAccounts/AAAAAA-BBBBBB-CCCCCC/budgets/fixture'
    data={'budgets':[{'name':name,'budgetFilter':{'projects':['projects/12345678'],'creditTypesTreatment':'EXCLUDE_ALL_CREDITS','calendarPeriod':'MONTH'},'amount':{'specifiedAmount':{'currencyCode':'CAD','units':'50'}},'thresholdRules':[{'thresholdPercent':v} for v in (.5,.9,1)],'notificationsRule':{}}]}
    return name,data


def test_existing_budget_is_verified_and_never_adopted():
    name,data=observation(); result=budget.verify(json.dumps(data).encode(),'12345678',name)
    assert result['ownership']=='preexisting_preserved' and not result['mutated'] and not result['hard_cap']
    for kind in ('pagination','scope','credits','currency','disabled'):
        changed=json.loads(json.dumps(data));b=changed['budgets'][0]
        if kind=='pagination':changed['nextPageToken']='more'
        if kind=='scope':b['budgetFilter']['services']=['compute']
        if kind=='credits':b['budgetFilter']['creditTypesTreatment']='INCLUDE_ALL_CREDITS'
        if kind=='currency':b['amount']['specifiedAmount']['currencyCode']='USD'
        if kind=='disabled':b['notificationsRule']['disableDefaultIamRecipients']=True
        with pytest.raises(ValueError):budget.verify(json.dumps(changed).encode(),'12345678',name)


def test_foreign_budget_or_role_plan_address_is_refused():
    good={'mode':'managed','type':'google_compute_instance','address':'google_compute_instance.role["a"]','change':{'actions':['create']}}
    assert plan.validate_plan({'resource_changes':[good]})
    for address,kind in [('google_compute_instance.r01','google_compute_instance'),('google_billing_budget.r01','google_billing_budget')]:
        with pytest.raises(ValueError):plan.validate_plan({'resource_changes':[dict(good,address=address,type=kind)]})


def plan_runner(monkeypatch):
    monkeypatch.setitem(sys.modules, 'review_plan', plan)
    return module('run_plan')


def saved_review(tmp_path):
    source=tmp_path/'source';source.mkdir()
    write(source/'main.tf',b'# exact reviewed source\n')
    tool=tmp_path/'tofu';write(tool,b'not executed by fixture')
    saved=tmp_path/'foundation.tfplan';write(saved,b'exact binary plan fixture')
    return dict(applied=False,delegation_required=True,source_root=str(source),
        source_files={'main.tf':hashlib.sha256((source/'main.tf').read_bytes()).hexdigest()},
        tofu=str(tool),tofu_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),
        saved_plan=str(saved),plan_sha256=hashlib.sha256(saved.read_bytes()).hexdigest(),
        state_path=str(tmp_path/'r06.tfstate'),state_sha256=None,teardown_plan=False,
        window_started_at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        expires_at=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        run_id='20261106-aabbcc',project='netclaw-fixture')


def test_saved_plan_and_source_changes_refused_before_execution(tmp_path,monkeypatch):
    runner=plan_runner(monkeypatch);review=saved_review(tmp_path)
    assert runner.verify(review)==review
    Path(review['saved_plan']).write_bytes(b'different')
    with pytest.raises(ValueError,match='plan_changed'):runner.verify(review)
    Path(review['saved_plan']).write_bytes(b'exact binary plan fixture')
    (Path(review['source_root'])/'extra.tf').write_text('unreviewed')
    with pytest.raises(ValueError,match='source_closure'):runner.verify(review)


def test_unknown_apply_attempt_is_never_replayed(tmp_path,monkeypatch):
    runner=plan_runner(monkeypatch);review=saved_review(tmp_path);file=tmp_path/'review.json';write(file,review)
    authorization=tmp_path/'authorization.json';write(authorization,dict(schemaVersion=1,scope='r06',plan_sha256=review['plan_sha256'],owner_message='fixture authorization only',approved_at='2026-11-06T12:00:00Z'))
    monkeypatch.setattr(sys,'argv',['run_plan.py','--review',str(file),'--authorization',str(authorization),'apply'])
    calls=[]
    def lost_reply(*args,**kwargs):
        calls.append(args);raise TimeoutError('lost outcome')
    monkeypatch.setattr(runner.subprocess,'run',lost_reply)
    with pytest.raises(TimeoutError):runner.main()
    assert json.loads(file.with_suffix('.attempt.json').read_text())['outcome']=='unknown'
    with pytest.raises(FileExistsError):runner.main()
    assert len(calls)==1


def test_teardown_requires_current_export_integrity(tmp_path,monkeypatch):
    runner=plan_runner(monkeypatch);review=saved_review(tmp_path);review['teardown_plan']=True
    with pytest.raises(ValueError,match='export_required'):runner.verify(review)
    evidence=tmp_path/'evidence.json';write(evidence,b'current actual evidence fixture')
    manifest=tmp_path/'export.json';write(manifest,dict(schemaVersion=1,run_id=review['run_id'],files={str(evidence):hashlib.sha256(evidence.read_bytes()).hexdigest()}))
    assert runner.verify(review,str(manifest))==review
    evidence.write_bytes(b'changed')
    with pytest.raises(ValueError,match='export_changed'):runner.verify(review,str(manifest))


def test_foreign_state_even_with_allowed_type_refused():
    own = {'version': 4, 'resources': [{'mode': 'managed', 'type': 'google_service_account',
           'instances': [{'attributes': {'project': 'netclaw-fixture', 'account_id': 'r06-20261106-aabbcc-a'}}]}]}
    plan.validate_state(json.dumps(own).encode(),'netclaw-r06-20261106-aabbcc','netclaw-fixture')
    own['resources'][0]['instances'][0]['attributes']['account_id']='r01-20261101-member'
    with pytest.raises(ValueError,match='foreign_run'):plan.validate_state(json.dumps(own).encode(),'netclaw-r06-20261106-aabbcc','netclaw-fixture')


def test_expired_saved_plan_refuses_before_partial_cloud_apply(tmp_path,monkeypatch):
    runner=plan_runner(monkeypatch);review=saved_review(tmp_path)
    review['expires_at']='2020-01-01T00:00:00Z'
    with pytest.raises(ValueError,match='expired'):runner.verify(review)
