"""Local Risk provisioning using the existing certificate/token registry.

Called under the setup writer locks. Tokens exist only in this process; live
channel authentication and execution are separate verification evidence.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import sqlite3
import sys
from setup_schema import loads
from setup_state import Conflict,guarded_read
from ha_setup_guard import require_standalone_home


def materialize_remote_transport(runtime, bundle, registry_path, *, expected_revision):
    """Explicit reviewed public transport import; no token/key creation or dial.

    Existing local setup enrollment remains unchanged. R03 owns the surrounding
    remote installation workflow. An interrupted import is inspected, never
    silently converted into a replacement identity or enrollment token.
    """
    require_standalone_home(runtime.home)
    from bgp.federation.endpoint_registry import Registry, import_bundle
    runtime.fence()
    registry = Registry(registry_path, runtime.installation)
    result = import_bundle(registry, bundle, expected_revision=expected_revision)
    source = Path(__file__).resolve().parents[1]/'write-env.py'
    spec = importlib.util.spec_from_file_location('_remote_enrollment_env', source)
    writer = importlib.util.module_from_spec(spec); spec.loader.exec_module(writer)
    writer.update(runtime.env_file, 'N2N_ENDPOINT_REGISTRY', str(registry.path.absolute()))
    if bundle['endpoint']['service'] == 'in2n':
        writer.update(runtime.env_file, 'N2N_BORDER_REGISTRY_ID', bundle['endpoint']['id'])
    return result


def binding(record):
    for claw in (record['border'],record['claw']):
        home=Path(claw['runtimeHome'])
        require_standalone_home(home)
        owner=loads(guarded_read(home/'.netclaw-setup-owner.json',16384,private=True))
        if owner!={'schema':1,'runId':record['runId'],'installationId':claw['id'],'planHash':record['planHash']}:
            raise Conflict('risk_home_not_owned')
    return record['border']['id']+'/'+record['claw']['id']


def launch(record):
    claw=record['claw'];home=Path(claw['runtimeHome'])
    if claw['service']['mode']=='on-demand':
        return shlex.join([record['python'],str(home/'.setup/source/scripts/setup-member-start.py'),'--home',str(home)])
    return shlex.join([record['python'],str(home/'.setup/source/scripts/setup-service.py'),'--home',str(home),'--role','federation'])


def observe(record):
    """No migrations, token reissue, key creation or state mutation on recovery."""
    member_id=binding(record);border=record['border'];claw=record['claw']
    home=Path(claw['runtimeHome']);base=Path(border['runtimeHome'])/'n2n'
    def row(file,query,args=()):
        guarded_read(file,32*1024*1024,private=True)
        connection=sqlite3.connect(file.as_uri()+'?mode=ro',uri=True)
        try:
            connection.row_factory=sqlite3.Row;value=connection.execute(query,args).fetchone()
            return dict(value) if value else None
        finally:connection.close()
    try:
        risk=row(base/'federation.db','SELECT * FROM risk WHERE id=1')
        if not risk or risk['role']!='border' or risk['risk_name']!=border['id']:return False
        anchor=guarded_read(base/'keys/risk-ca/ca.crt',16384,private=True)
        if claw['role']=='border':return bool(anchor)
        member=row(base/'federation.db','SELECT * FROM member WHERE member_id=?',(member_id,))
        own=row(home/'n2n/federation.db','SELECT * FROM risk WHERE id=1')
        cert=guarded_read(home/'n2n/keys/self.crt',16384,private=True).decode()
        if not member or not own or member['state'] not in ('enrolled','active','unreachable') or member['pinned_key']!=cert:return False
        if own['self_member_id']!=member_id or own['risk_name']!=border['id'] or own['role']!='member':return False
        if guarded_read(home/'n2n/keys/risk-ca-anchor.pem',16384,private=True)!=anchor:return False
        if member['profile']!=claw['capabilities']['profile'] or member['launch_cmd']!=launch(record) or bool(member['on_demand'])!=(claw['service']['mode']=='on-demand'):return False
        scope={v['name'] for v in json.loads(member['scope']) if v.get('tier')=='specialty'}
        return scope==set(claw['capabilities']['skills'])
    except (OSError,sqlite3.Error,ValueError,KeyError):return False


def materialize(record):
    member_id=binding(record);border=record['border'];claw=record['claw']
    from bgp.federation.manager import FederationManager
    from bgp.federation.risk import RiskManager
    from bgp.federation.runtime import Runtime
    def manager(value):
        home=Path(value['runtimeHome']);identity=loads(guarded_read(home/'netclaw-hud/installation.json'))['installationId']
        require_standalone_home(home)
        Runtime(value['harness'],home,home/('config.yaml' if value['harness']=='hermes' else 'openclaw.json'),identity).fence(initialize=True)
        return FederationManager(base_dir=str(home/'n2n'))
    border_manager=manager(border);member_manager=None
    try:
        hub=RiskManager(border_manager)
        if claw['role']=='border':
            hub.set_role('border',risk_name=border['id'],description=border['displayName'],enabled_stacks='in2n')
            hub.ensure_self_identity(border['id']);hub.ensure_risk_ca();hub.hub_credential()
            return observe(record)
        if not hub.is_border() or hub.get_risk()['risk_name']!=border['id']:raise Conflict('border_not_provisioned')
        existing=hub.get_member(member_id)
        if existing:
            # The token may have been spent before an interrupted acknowledgement.
            # Observe exact pins; never create a replacement identity/token.
            return observe(record)
        member_manager=manager(claw);member=RiskManager(member_manager)
        member.set_role('member',risk_name=border['id'],description=claw['displayName'],enabled_stacks='in2n',
            border_endpoint='127.0.0.1:'+str(border['endpoints']['federationPort']),self_member_id=member_id)
        member.ensure_self_identity(member_id)
        provisioned=hub.add_member(claw['id'],profile=claw['capabilities']['profile'],specialty=claw['capabilities']['skills'],
            ttl_seconds=300,launch_cmd=launch(record),on_demand=claw['service']['mode']=='on-demand')
        token=provisioned.pop('enrollment_token');provisioned.clear()
        hub.consume_token(token,member_id,member.self_cert_pem(),runtime_kind='process',display_name=claw['displayName'],transport_binding='loopback')
        token=None
        member.store_risk_anchor(hub.risk_ca_pem())
        return observe(record)
    finally:
        if member_manager:member_manager.close()
        border_manager.close()
