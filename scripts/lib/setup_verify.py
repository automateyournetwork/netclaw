"""Installation-bound evidence, without model turns or device calls by default."""
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from setup_deploy import helper
from setup_report import outcome, summarize
from setup_schema import canonical, loads
from setup_state import Conflict, guarded_read, revision
from setup_secrets import read_owned_environment
from setup_process import WriterUncertain


def wait_for_readiness(probe,pause,*,timeout=30,clock=time.monotonic):
    """Bounded read-only startup polling; failures/identity mismatches stop."""
    deadline=clock()+timeout
    while True:
        if pause is not None and pause.is_set():return outcome('unverified','service_unverified')
        result=probe()
        if result['state']!='unverified' or result['code'] not in ('service_unverified','probe_failed','probe_timeout'):
            return result
        remaining=deadline-clock()
        if remaining<=0:return result
        delay=min(1,remaining)
        if pause is not None:
            if pause.wait(delay):return result
        else:time.sleep(delay)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*_args,**_kwargs):raise Conflict('verification_redirect_refused')


# Seconds per HUD request. /api/hud/management runs `openclaw agents list --json`
# on every call, which management.js allows 15 s and which can take 10 s or more
# on slower hosts, so it gets longer than the server's own limit (as the
# extension's HudClient does). Other routes answer in milliseconds.
HUD_REQUEST_TIMEOUT=5
HUD_MANAGEMENT_TIMEOUT=20


def timed_out(error):
    """True when a HUD request failed because it ran out of time."""
    if isinstance(error,TimeoutError):return True  # includes socket.timeout
    return isinstance(error,urllib.error.URLError) and isinstance(error.reason,TimeoutError)


class HudProbe:
    """Same loopback session/identity contract as the extension's HudClient."""
    def __init__(self,claw,identity):
        self.claw=claw;self.identity=identity
        self.base='http://127.0.0.1:'+str(claw['endpoints']['hudPort'])
        self.cookies=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self,route,body=None,*,timeout=None):
        if timeout is None:
            timeout=HUD_MANAGEMENT_TIMEOUT if route=='/api/hud/management' else HUD_REQUEST_TIMEOUT
        request=urllib.request.Request(self.base+route,data=canonical(body) if body is not None else None,
            headers={'Accept':'application/json','Content-Type':'application/json','x-netclaw-installation':self.identity})
        with self.opener.open(request,timeout=timeout) as response:
            raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise Conflict('verification_response_limit')
            # Runtime responses may contain floats. They are bounded in memory
            # and only typed booleans/identities are inspected, never exported.
            data=json.loads(raw)
            if not isinstance(data,dict):raise Conflict('verification_response_invalid')
            return data

    def check(self):
        try:
            runtime=self.request('/api/runtime')
            if runtime.get('installationId')!=self.identity or runtime.get('kind')!=self.claw['harness']:
                return outcome('failed','identity_mismatch')
            self.request('/api/hud/session',{})
            if not any(c.name.startswith('nc_hud_') for c in self.cookies):return outcome('unverified','service_unverified')
            management=self.request('/api/hud/management')
            if any(management.get(k)!=v for k,v in {'installationId':self.identity,'kind':self.claw['harness'],
                    'home':self.claw['runtimeHome']}.items()):return outcome('failed','identity_mismatch')
            if self.claw['harness']=='openclaw' and management.get('expectedWorkspace')!=self.claw['workspace']:
                return outcome('failed','identity_mismatch')
            # An identity response alone does not prove a running gateway/engine.
            if runtime.get('readiness',{}).get('ready') is not True:return outcome('unverified','service_unverified')
            return outcome('verified','identity_verified')
        except Exception as error:
            return outcome('unverified','probe_timeout' if timed_out(error) else 'probe_failed')
        finally:
            if list(self.cookies):
                try:self.request('/api/hud/session/revoke',{})
                except Exception:pass
            self.cookies.clear()


class Probes:
    def __init__(self,effect,context,deploy,harness):
        self.effect,self.context,self.deploy,self.harness=effect,context,deploy,harness
        self.claw=deploy.claw;self.home=deploy.root
        self.latest={a['path']:a for e in context['journal']['effects'] for a in e.get('artifacts',[])}
        self.identity=loads(guarded_read(self.home/'netclaw-hud/installation.json'))['installationId']

    def credentials(self):
        artifact=self.latest.get(str(self.home/'.env'))
        if not artifact:raise Conflict('environment_ownership_missing')
        return read_owned_environment(self.home/'.env',artifact['sha256'])

    def comms(self):
        from setup_comms_evidence import observe
        return observe(self)

    def installed(self):
        rows=[]
        for effect in self.context['journal']['effects']:
            if effect['owner']!=self.claw['id'] or effect['phase'] in ('services','verification','risk'):continue
            if effect['state']!='verified':rows.append(outcome(effect['state'],'effect_unsettled'));continue
            changed=any(revision(a['path'])!=self.latest[a['path']]['sha256'] for a in effect.get('artifacts',[]))
            if effect['phase']=='comms' and effect.get('channel')=='whatsapp' and any(a.get('class')=='comms-auth' for a in effect.get('artifacts',[])):
                from setup_comms_evidence import configuration
                # Linked-device keys rotate in the owned runtime. Revalidate
                # its account identity and native configuration, retaining
                # immutable checks for every other artifact in the effect.
                changed=any(revision(a['path'])!=self.latest[a['path']]['sha256'] for a in effect.get('artifacts',[]) if a.get('class')!='comms-auth')
                changed=changed or configuration(self,'whatsapp')['state']!='verified'
            if effect['phase']=='components':
                from setup_components import dependency_ready
                component=effect['component']
                try:
                    changed=changed or not dependency_ready(component,self.deploy,self.harness,effect=self.effect)
                    if component=='pyats':changed=changed or not self.harness.observe_pyats(self.effect)
                    if component in ('n2n','hermes-hud','claw-certs','gait'):changed=changed or not self.harness.observe_python_component(self.effect,component)
                except WriterUncertain:raise
                except Exception:changed=True
            rows.append(outcome('failed' if changed else 'verified','artifact_changed' if changed else 'artifact_present'))
        runtime=self.harness.observe_runtime(self.effect)
        rows.append(outcome('verified' if runtime else 'unverified','artifact_present' if runtime else 'runtime_unavailable'))
        return outcome(summarize(rows),'artifact_present' if summarize(rows)=='verified' else 'artifact_missing')

    def component(self,component):
        prior=next(e for e in self.context['journal']['effects'] if e['owner']==self.claw['id'] and e['component']==component)
        if prior['state']!='verified':return outcome(prior['state'],'effect_unsettled')
        if component=='claw-certs':
            from setup_certificates import observe
            try:
                state=observe(prior,self.context,self.deploy,self.harness)
                return outcome('verified','certificate_verified') if state=='completed' else outcome('unverified','artifact_changed')
            except WriterUncertain:raise
            except Exception:return outcome('unverified','probe_failed')
        descriptor=self.deploy.validator.components[component]
        from setup_components import selected_servers
        servers=selected_servers(component,self.claw,descriptor)
        if not servers:return outcome('verified','artifact_present')
        try:
            values=self.credentials();env=self.harness.environment(values)
            if component=='zoom-rtms':
                # Transient child-only discovery authority, never written to
                # active MCP registration or the installation environment.
                values={**values,'NETCLAW_MCP_DISCOVERY_ONLY':'1'}
            requirements=self.deploy.validator.inspect(self.context['plan'])['configurationRequired']
            if any(v['owner']==self.claw['id'] for v in requirements):return outcome('configuration_required','credentials_required')
            if self.claw['harness']=='openclaw':
                readiness=helper(self.deploy.source,'installer-readiness.py')
                rules=loads(guarded_read(self.deploy.source/'config/installer-access.json'))['components']
                for server in servers:
                    if server=='hermes-hud-mcp':continue
                    command=self.harness.command()+['mcp','probe',server,'--json']
                    if component=='zoom-rtms':
                        bootstrap=guarded_read(self.home/'.setup/python312',8192,private=True).decode().strip()
                        command=[bootstrap,str(self.deploy.source/'scripts/setup-openclaw-comms-discovery.py')]
                    result=self.harness.call(self.effect,command,credentials=values,capture=True,
                        timeout=100 if component=='zoom-rtms' else 35)
                    if result['returncode'] or not readiness.native_result(json.loads(result['stdout']),server,rules.get(component,{}).get('expected_tools',[])):
                        return outcome('unverified','discovery_unverified')
                return outcome('verified','discovery_verified')
            manifest=loads(guarded_read(self.deploy.source/'config/hermes-hud-tool-policy.json'))
            if any(server not in manifest['servers'] for server in servers):
                # Native Hermes exposes more than the protected HUD companion.
                # Use its actual registry and live connection, not direct MCP
                # discovery or a broadened companion allowlist.
                python=self.home/'python-runtimes/hermes-hud-agent/venv/bin/python'
                result=self.harness.call(self.effect,[str(python),str(self.deploy.source/'scripts/setup-hermes-discovery.py'),component],
                    credentials=values,capture=True,timeout=90)
                valid={'state':'verified','code':'discovery_verified'}
                return valid if result['returncode']==0 and loads(result['stdout'])==valid else outcome('unverified','discovery_unverified')
            # The protected Hermes companion's authenticated health enumerates
            # the actual frozen native discovery catalog for its qualified scope.
            auth=loads(guarded_read(self.home/'netclaw-hud/companion-auth.json',8192,private=True))
            request=urllib.request.Request('http://127.0.0.1:'+str(self.claw['endpoints']['companionPort'])+'/health/detailed',
                                          headers={'Authorization':'Bearer '+auth['key']})
            with urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(request,timeout=5) as response:
                data=json.loads(response.read(65537))
            if data.get('installationId')!=self.identity or data.get('authenticated') is not True or data.get('ready') is not True:
                return outcome('unverified','discovery_unverified')
            expected=['mcp__'+server.replace('-','_')+'__'+tool for server in servers
                      for tool in manifest['servers'].get(server,{}).get('tools',[])]
            return outcome('verified','discovery_verified') if expected and set(expected)<=set(data.get('tools',[])) else outcome('unverified','discovery_unverified')
        except WriterUncertain:raise
        except Exception:return outcome('unverified','probe_failed')

    def canary(self):
        # A direct local calculator call is deliberately separate from native
        # discovery. Neither can substitute for the other, or for a model turn.
        selected=self.claw['capabilities']['components']
        component=next((name for name in ('subnet-calc','anta') if name in selected),None)
        if component is None and 'n2n' in selected and self.claw['role'] in ('member','border'):component='n2n'
        if component is None:
            return outcome('unverified','canary_unverified')
        try:
            pointer=self.home/'python-runtimes/records'/component
            artifact=self.latest.get(str(pointer))
            if not artifact or artifact.get('owner')!=self.claw['id'] or revision(pointer)!=artifact['sha256']:raise Conflict('runtime_record_unowned')
            record=guarded_read(pointer,8192,private=True).decode().strip()
            if not Path(record).is_relative_to(self.home) or not Path(record).resolve().is_relative_to(self.home):raise Conflict('runtime_outside_home')
            result=self.harness.call(self.effect,[record,str(self.deploy.source/'scripts/setup-canary.py'),component],
                credentials={'N2N_ROLE':self.claw['role']} if component=='n2n' else None,capture=True,timeout=35)
            if result['returncode']==0 and loads(result['stdout'])=={'state':'verified','code':'canary_verified'}:
                return outcome('verified','canary_verified')
        except WriterUncertain:raise
        except Exception:pass
        return outcome('unverified','canary_unverified')

    def running(self):
        return wait_for_readiness(self._running_once,self.context.get('pause'))

    def _running_once(self):
        from setup_risk import observe_services
        if not observe_services(self.effect,self.context,self.deploy,self.harness):return outcome('unverified','service_unverified')
        if self.claw['harness']=='openclaw':
            try:
                result=self.harness.call(self.effect,self.harness.command()+['gateway','health','--json'],
                    credentials=self.credentials(),capture=True,timeout=20)
                if result['returncode'] or json.loads(result['stdout']).get('ok') is not True:
                    return outcome('unverified','service_unverified')
            except WriterUncertain:raise
            except Exception:return outcome('unverified','service_unverified')
        return HudProbe(self.claw,self.identity).check()

    def risk(self):
        from setup_risk import observe_risk
        try:
            if not observe_risk(self.effect,self.context,self.deploy,self.harness):return outcome('unverified','risk_unverified')
            border=next(c for c in self.context['plan']['claws'] if c['role']=='border')
            identity=loads(guarded_read(Path(border['runtimeHome'])/'netclaw-hud/installation.json'))['installationId']
            client=HudProbe(border,identity);client.base='http://127.0.0.1:'+str(border['endpoints']['bgpApiPort'])
            status=client.request('/status')
            if status.get('installation_id')!=identity or status.get('harness_type')!=border['harness'] or status.get('federation_ready') is not True:
                return outcome('unverified','risk_unverified')
            members=[c for c in self.context['plan']['claws'] if c['role']=='member'] if self.claw['role']=='border' else [self.claw]
            for member in members:
                if member['service']['mode']=='on-demand':continue
                expected=loads(guarded_read(Path(member['runtimeHome'])/'netclaw-hud/installation.json'))['installationId']
                response=client.request('/n2n/members/self-status',{'member_id':border['id']+'/'+member['id']},timeout=12)
                if response.get('memberId')!=border['id']+'/'+member['id'] or response.get('installationId')!=expected or response.get('kind')!=member['harness'] or response.get('ready') is not True:
                    return outcome('unverified','risk_unverified')
            return outcome('verified','risk_verified')
        except WriterUncertain:raise
        except Exception:return outcome('unverified','risk_unverified')


def verify_installation(effect,context,deploy,harness,*,probes=None,live=None):
    probes=probes or Probes(effect,context,deploy,harness)
    # Native managers can acknowledge launch before the HUD/companion has
    # finished startup. Wait on actual readiness before querying its discovery
    # catalog; never turn a loaded definition into evidence of readiness.
    running=probes.running()
    components=[{'id':c,**probes.component(c)} for c in deploy.claw['capabilities']['components']]
    discover=summarize(components+[probes.canary()])
    tiers=[{'tier':1,**probes.installed()}, {'tier':2,**outcome(discover,'discovery_verified' if discover=='verified' else 'discovery_unverified')},
           {'tier':3,**running}]
    for tier in (4,5,6):
        selected=tier in context['plan']['verification']['tiers']
        # Plan costConsent/channel booleans express intent, never authority.
        result=live.verify(tier,deploy.claw,context) if selected and live else outcome('unverified' if selected else 'skipped','native_consent_required' if selected else 'not_selected')
        tiers.append({'tier':tier,**outcome(result.get('state'),result.get('code'))})
    if context['plan']['shape']=='risk':tiers.append({'tier':'risk',**probes.risk()})
    report={'harness':deploy.claw['harness'],'version':deploy.claw['runtimeVersion'],'createdAt':int(time.time()),
            'identity':{'home':str(deploy.root),'source':str(deploy.source),'installationId':probes.identity,
                'hudEndpoint':'http://127.0.0.1:'+str(deploy.claw['endpoints']['hudPort'])},'tiers':tiers,'components':components}
    if deploy.claw.get('channels'):report['comms']=probes.comms()
    if 'pyats' in deploy.claw['capabilities']['components']:
        from pyats_testbeds import policy
        report['testbed']={**policy(deploy.claw.get('testbed')),'sourceAccess':'unverified',
                           'candidate':'not_built','activation':'not_observed','execution':'not_checked'}
    path=deploy.root/'.setup/verification.json'
    deploy.write(effect,path,canonical(report)+b'\n',kind='verification',expected=revision(path))
    context['journal'].setdefault('reports',{})[deploy.claw['id']]=report
    return {'state':summarize([t for t in tiers if t['state']!='skipped'])}
