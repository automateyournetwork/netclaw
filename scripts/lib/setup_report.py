"""Allowlisted report projections. Unknown objects and free text never export."""
import hashlib
from pathlib import Path
import re
import time
from urllib.parse import urlsplit, urlunsplit

from setup_schema import canonical
from setup_state import guarded_write

STATES = frozenset(('verified','failed','configuration_required','skipped','unverified'))
CODES = frozenset(('artifact_present','artifact_missing','artifact_changed','runtime_unavailable',
    'discovery_verified','discovery_unverified','credentials_required','identity_verified','identity_mismatch',
    'service_unverified','canary_verified','canary_unverified','native_consent_required','not_selected',
    'channel_unconfigured','channel_verified','network_unconfigured','risk_unverified','risk_verified','probe_failed','probe_timeout',
    'source_verified','source_changed','effect_unsettled','configured','unsupported','model_verified','model_unverified','network_verified','network_unverified','cleanup_started','certificate_verified'))

COMMS_DIMENSIONS=('configuration','authentication','transport','inbound','outbound')
COMMS_STATES=STATES|frozenset(('cancelled','blocked','unknown'))
COMMS_CODES=frozenset(('configuration_valid','configuration_changed','configuration_required','dependency_unverified',
    'authentication_verified','authentication_failed','transport_connected','transport_unverified','not_checked',
    'not_requested','unsupported','consent_required','cancelled','attempt_unknown','submission_accepted','delivery_verified',
    'delivery_failed','inbound_verified','receipt_unverified','policy_blocked','effect_unsettled','cleanup_started'))
COMMS_CHECKERS=frozenset(('netclaw-setup','openclaw-config','hermes-config','hermes-gateway','native-send','twilio-callback'))
COMMS_SUCCESS={'configuration':{'configuration_valid'},'authentication':{'authentication_verified'},
    'transport':{'transport_connected'},'inbound':{'inbound_verified'},
    'outbound':{'submission_accepted','delivery_verified'}}


def comms_observation(state='unverified',code='not_checked',*,checker='netclaw-setup',observed_at=None):
    result={'state':state if state in COMMS_STATES else 'unverified',
        'code':code if code in COMMS_CODES else 'effect_unsettled',
        'checker':checker if checker in COMMS_CHECKERS else 'netclaw-setup'}
    if type(observed_at) is int and 946684800<=observed_at<=int(time.time())+5:result['observedAt']=observed_at
    return result


def project_comms(rows,catalog,harness):
    allowed={c['id'] for c in catalog.get('choices',[]) if c.get('kind')=='channel' and harness in c.get('harnesses',[])}
    result=[];seen=set()
    if not isinstance(rows,list):return result
    for row in rows[:64]:
        if not isinstance(row,dict) or row.get('channel') not in allowed or row['channel'] in seen:continue
        seen.add(row['channel'])
        item={'channel':row['channel'],'account':'account-1'}
        for dimension in COMMS_DIMENSIONS:
            value=row.get(dimension,{})
            if not isinstance(value,dict):value={}
            item[dimension]=comms_observation(value.get('state'),value.get('code'),
                checker=value.get('checker'),observed_at=value.get('observedAt'))
            if item[dimension]['state']=='verified' and (item[dimension]['code'] not in COMMS_SUCCESS[dimension] or
                'observedAt' not in item[dimension]):item[dimension]=comms_observation('unverified','effect_unsettled')
        result.append(item)
    return result


def invalidate_for_cleanup(report):
    for row in report.get('tiers',[])+report.get('components',[]):
        if row.get('state')!='skipped':row.update(state='unverified',code='cleanup_started')
    for channel in report.get('comms',[]):
        for dimension in COMMS_DIMENSIONS:
            channel[dimension]=comms_observation('unverified','cleanup_started')


def outcome(state, code):
    return {'state':state if state in STATES else 'unverified',
            'code':code if code in CODES else 'effect_unsettled'}


def summarize(rows):
    states={r.get('state') for r in rows}
    if not states:return 'unverified'
    return next((s for s in ('failed','configuration_required','unverified') if s in states),
                'verified' if states=={'verified'} else 'unverified')


def project(report, catalog, *, detailed=False):
    """Structural projection beats scrubbing: no arbitrary nested values survive."""
    components={item['id'] for item in catalog['components']}
    result={'schema':1,'export':'detailed-local' if detailed else 'redacted',
            'generatedAt':int(time.time()),'installations':[]}
    for index,row in enumerate(report.get('installations',[])[:128]):
        if not isinstance(row,dict):continue
        item={'installation':'claw-'+str(index+1),'harness':row.get('harness') if row.get('harness') in ('openclaw','hermes') else 'unknown',
              'tiers':[], 'components':[]}
        # Only the adapter's qualified version syntax is useful in a public report.
        version=row.get('version','')
        if isinstance(version,str) and re.fullmatch(r'v?\d{1,4}(?:\.\d{1,4}){1,3}(?:-\d{1,3})?',version):item['version']=version
        for tier in row.get('tiers',[])[:7]:
            if not isinstance(tier,dict) or tier.get('tier') not in (1,2,3,4,5,6,'risk'):continue
            item['tiers'].append({'tier':tier['tier'],**outcome(tier.get('state'),tier.get('code'))})
        for component in row.get('components',[])[:200]:
            if not isinstance(component,dict) or component.get('id') not in components:continue
            item['components'].append({'id':component['id'],**outcome(component.get('state'),component.get('code'))})
        if row.get('comms'):item['comms']=project_comms(row['comms'],catalog,item['harness'])
        if isinstance(row.get('testbed'),dict):
            from pyats_testbeds import policy,TestbedError
            try:
                value=row['testbed'];selection=policy({key:value.get(key) for key in ('mode','sources')})
                item['testbed']={**selection,'sourceAccess':'unverified','candidate':'not_built',
                                 'activation':'not_observed','execution':'not_checked'}
            except TestbedError:pass
        # Default provenance identifies the checker and tier; not a filesystem
        # reference, raw error, URL, run ID, token hash or host-derived identity.
        item['provenance']={'checker':'netclaw-setup','protocol':1}
        if detailed:
            owner=row.get('identity',{})
            identity={}
            if isinstance(owner,dict):
                for key in ('home','source'):
                    value=owner.get(key)
                    if isinstance(value,str) and len(value)<=4096 and Path(value).is_absolute():identity[key]=value
                ident=owner.get('installationId','')
                if isinstance(ident,str) and re.fullmatch(r'[a-f0-9-]{36}',ident):identity['installationId']=ident
                endpoint=owner.get('hudEndpoint','')
                if isinstance(endpoint,str):
                    try:
                        url=urlsplit(endpoint)
                        if url.scheme=='http' and url.hostname in ('127.0.0.1','localhost','::1') and url.port:
                            identity['hudEndpoint']=urlunsplit((url.scheme,url.netloc.split('@')[-1],'','',''))
                    except ValueError:pass
            item['identity']=identity
        result['installations'].append(item)
    return result


def export_binding(run, destination, *, detailed=False):
    return {'planHash':run['planHash'],'runId':run['runId'],'operation':'export',
            'destination':str(Path(destination)), 'detailed':detailed,
            'reportHash':hashlib.sha256(canonical(run.get('reports',{}))).hexdigest()}


def export_report(run, catalog, destination, *, detailed=False, review=None):
    binding=export_binding(run,destination,detailed=detailed)
    if detailed:
        from setup_engine import _Review, ReviewRefused
        if not isinstance(review,_Review):raise ReviewRefused('detailed_export_review_required')
        review.consume(binding,'export-detailed')
    report={'installations':[run.get('reports',{}).get(c['id'],{}) for c in run['plan']['claws']]}
    data=canonical(project(report,catalog,detailed=detailed))+b'\n'
    guarded_write(destination,data,expected=None)
    return {'protocol':1,'operation':'export','state':'verified','detailed':detailed}
