"""Finite cloud controls, secret projections and exact plan ownership: fixtures only."""
import base64
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'labs/cloud/gcp/r04'


def module(name):
    spec = importlib.util.spec_from_file_location('r04_' + name, SOURCE / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


guard, secret, host, budget, plan = [module(n) for n in ('host_guard', 'project_secret', 'render_host', 'budget_observation', 'review_plan')]
NOW = dt.datetime(2026, 11, 3, 12, tzinfo=dt.timezone.utc)
CONFIG = dict(schemaVersion=1, run_id='20261103-aabbcc', interface='ens4', quota_bytes=1024, rate_bits=1000000, expires_at='2026-11-04T12:00:00Z')


def write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode()); path.chmod(0o600)


def test_named_quota_shared_by_output_and_forward_and_metadata_refused():
    rules = guard.rules(CONFIG, True, False).decode()
    assert rules.count('quota egress {') == 1
    assert rules.count('quota name egress drop') == 2
    assert 'hook output priority -300' in rules and 'hook forward priority -300' in rules
    assert 'ip daddr 169.254.0.0/16 drop' in rules and 'fd20:ce::254' in rules
    assert rules.index('169.254.0.0/16 drop') < rules.rindex('quota name egress drop')
    assert 'flush ruleset' not in rules


def test_closed_boot_blocks_forwarding_and_allows_only_dhcp_host_exception():
    rules = guard.rules({}, False, True, bootstrap=True).decode()
    assert 'quota' not in rules and 'delete table inet netclaw_r04' in rules
    assert 'udp sport 68 udp dport 67 accept' in rules
    assert 'chain forward' in rules and 'drop' in rules.split('chain forward')[1]
    assert 'dhcp' not in rules.split('chain forward')[1]


def test_only_reviewed_links_present_at_guard_activation():
    links = [{'ifname':'lo','flags':['UP']},{'ifname':'ens4','flags':['UP']},
             {'ifname':'docker0','flags':['UP'],'linkinfo':{'info_kind':'bridge'}}]
    assert guard.validate_links(links, 'ens4')
    for extra in ('eth1','br-012345abcdef','veth42'):
        with pytest.raises(guard.Refused, match='unknown_active_link'):
            guard.validate_links(links + [{'ifname':extra,'flags':['UP']}], 'ens4')
    links[-1]['linkinfo']['info_kind'] = 'dummy'
    with pytest.raises(guard.Refused, match='docker_bridge'): guard.validate_links(links, 'ens4')


def test_spent_guard_and_qdisc_failure_remain_closed(tmp_path):
    calls=[]
    def command(args, **kwargs):
        calls.append((args,kwargs))
        if args[:3] == ['ip','-j','-d']:
            return Mock(stdout=json.dumps([{'ifname':'lo','flags':['UP']},{'ifname':'ens4','flags':['UP']}]).encode(),returncode=0)
        if args[:3] == ['tc','-j','qdisc']: return Mock(stdout=b'[]',returncode=0)
        if args[:3] == ['tc','qdisc','replace']: raise guard.Refused('injected')
        return Mock(stdout=b'',returncode=1 if args[:2]==['nft','list'] else 0)
    with pytest.raises(guard.Refused, match='injected'): guard.activate(CONFIG,tmp_path,command=command,now=NOW)
    assert (tmp_path/'allocation.json').exists()
    with pytest.raises(guard.Refused, match='spent'): guard.activate(CONFIG,tmp_path,command=command,now=NOW)
    assert all(b'quota egress' not in kw.get('input',b'') for _,kw in calls)


@pytest.fixture
def projection(tmp_path):
    home=tmp_path/'claw';home.mkdir(mode=0o700);(home/'netclaw-federation').mkdir(mode=0o700)
    installation=str(uuid.uuid4())
    write(home/'netclaw-hud/installation.json',dict(schemaVersion=1,installationId=installation))
    values={'netbox':{'NETBOX_TOKEN':'nbt_fixture.fixture'},'guard':{'ANTHROPIC_API_KEY':'sk-ant-fixture','DEFENSECLAW_GATEWAY_TOKEN':'g'*43}}
    payloads={k:json.dumps(dict(schemaVersion=1,installationId=installation,environment=v)).encode() for k,v in values.items()}
    cfg=dict(schemaVersion=1,installationId=installation,home=str(home),role='member',secrets={
        k:dict(version='projects/netclaw-fixture/secrets/netclaw-r04-20261103-aabbcc-'+k+'/versions/1',payloadSha256=hashlib.sha256(v).hexdigest()) for k,v in payloads.items()})
    calls=[]
    def request(url,headers):
        calls.append((url,headers))
        if url.startswith('http://169.254.'): return {'access_token':'workload-token'}
        name=next(k for k in payloads if '-'+k+'/versions/' in url)
        return {'payload':{'data':base64.b64encode(payloads[name]).decode()}}
    return home,cfg,request,calls


def test_member_secret_projection_separates_broker_guard_and_capability(projection):
    home,cfg,request,calls=projection
    outputs=secret.retrieve(cfg,request);secret.project(cfg,outputs);secret.project(cfg,outputs)
    root=home/'netclaw-federation'
    assert (root/'broker-secrets/netbox.env').read_text()=='NETBOX_TOKEN=nbt_fixture.fixture\n'
    assert 'NETBOX' not in (root/'guard-secrets/guard.env').read_text()
    assert 'ANTHROPIC' not in (root/'guard-capability').read_text()
    assert not (home/'.env').exists()
    for p in root.rglob('*'):
        if p.is_file(): assert p.stat().st_mode&0o777==0o600
    assert len(calls)==3 and all('latest' not in url for url,_ in calls)


@pytest.mark.parametrize('change', ['border','latest','foreign_run','payload','foreign_installation'])
def test_secret_scope_and_integrity_refuse(projection,change):
    _,cfg,request,_=projection
    if change=='border': cfg['role']='border'
    elif change=='latest': cfg['secrets']['netbox']['version']=cfg['secrets']['netbox']['version'].replace('/1','/latest')
    elif change=='foreign_run': cfg['secrets']['netbox']['version']=cfg['secrets']['netbox']['version'].replace('aabbcc','ddeeff')
    elif change=='payload': cfg['secrets']['netbox']['payloadSha256']='0'*64
    else: cfg['installationId']=str(uuid.uuid4())
    with pytest.raises(secret.Refused): secret.retrieve(cfg,request)


def test_existing_changed_or_symlinked_secret_refused(projection):
    home,cfg,request,_=projection;outputs=secret.retrieve(cfg,request);secret.project(cfg,outputs)
    p=home/'netclaw-federation/broker-secrets/netbox.env';p.write_text('different')
    with pytest.raises(secret.Refused,match='changed'):secret.project(cfg,outputs)


def host_config(role):
    c=dict(schemaVersion=1,role=role,hostname='r04-gcp-montreal.lobsternet.automateyournetwork.com',source='/opt/netclaw-r04/source',home='/var/lib/netclaw-r04/claw',python='/opt/netclaw-r04/venv/bin/python',node='/opt/netclaw-r04/bin/node',caddy='/opt/netclaw-r04/bin/caddy',role_contract='/var/lib/netclaw-r04/role.json',hud_config='/var/lib/netclaw-r04/hud.json',secret_config='/var/lib/netclaw-r04/secret-projection.json',network_config='/var/lib/netclaw-r04/network/config.json',expires_at=CONFIG['expires_at'])
    if role=='member':
        for k in ('node','caddy','hud_config'):c[k]=None
    return c


def test_member_renderer_has_no_public_edge_and_enforces_docker_ordering():
    files=host.render(host_config('member'))
    assert not {'Caddyfile','netclaw-r04-hud.service','netclaw-r04-caddy.service'}&files.keys()
    unit=files['netclaw-r04-federation.service']
    assert 'docker.service' in unit and 'claw/execution' in unit
    assert 'BindReadOnlyPaths=/etc/netclaw-r04/resolv.conf:/etc/resolv.conf' in unit
    assert json.loads(files['docker-daemon.json'])['dns'] == ['8.8.8.8']
    assert files['resolv.conf'].startswith('nameserver 8.8.8.8')
    assert 'IPAddressDeny=169.254.0.0/16' in unit and 'IPAddressDeny=fd20:ce::254/128' in unit
    assert 'ProtectSystem=strict' in unit and 'Restart=no' in unit
    assert 'BindsTo=netclaw-r04-guard.service' in files['docker-r04-guard.conf']


def test_border_renderer_keeps_separate_edge_and_no_docker():
    files=host.render(host_config('border'))
    assert 'docker-r04-guard.conf' not in files
    assert 'SupplementaryGroups=docker' not in files['netclaw-r04-federation.service']
    assert 'InaccessiblePaths=/var/lib/netclaw-r04' in files['netclaw-r04-caddy.service']
    assert '10.173.0.2' in files['Caddyfile']


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
    good={'mode':'managed','type':'google_compute_instance','address':'google_compute_instance.role["member"]','change':{'actions':['create']}}
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
    return dict(applied=False,delegation_required=False,source_root=str(source),
        source_files={'main.tf':hashlib.sha256((source/'main.tf').read_bytes()).hexdigest()},
        tofu=str(tool),tofu_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),
        saved_plan=str(saved),plan_sha256=hashlib.sha256(saved.read_bytes()).hexdigest(),
        state_path=str(tmp_path/'r04.tfstate'),state_sha256=None,teardown_plan=False,
        window_started_at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        expires_at=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        run_id='20261103-aabbcc',project='netclaw-fixture')


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
    monkeypatch.setattr(sys,'argv',['run_plan.py','--review',str(file),'apply'])
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
           'instances': [{'attributes': {'project': 'netclaw-fixture', 'account_id': 'r04-20261103-aabbcc-member'}}]}]}
    plan.validate_state(json.dumps(own).encode(),'netclaw-r04-20261103-aabbcc','netclaw-fixture')
    own['resources'][0]['instances'][0]['attributes']['account_id']='r01-20261101-member'
    with pytest.raises(ValueError,match='foreign_run'):plan.validate_state(json.dumps(own).encode(),'netclaw-r04-20261103-aabbcc','netclaw-fixture')


def test_expired_saved_plan_refuses_before_partial_cloud_apply(tmp_path,monkeypatch):
    runner=plan_runner(monkeypatch);review=saved_review(tmp_path)
    review['expires_at']='2020-01-01T00:00:00Z'
    with pytest.raises(ValueError,match='expired'):runner.verify(review)
