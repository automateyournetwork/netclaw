"""Claw Plan validation and deterministic effect disclosure, without host writes."""
import hashlib
import ipaddress
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit

from setup_schema import Invalid, canonical, loads, validate
from setup_state import guarded_read
from setup_comms import CommsCatalog

SECRET_PATTERN = re.compile(r'(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:sk-(?:ant-)?|gh[pousr]_|github_pat_|xox[baprs]-|nck_(?:live|test)_)[A-Za-z0-9_-]{8,}|\bAKIA[A-Z0-9]{16}\b|\bBearer\s+\S+|\bBasic\s+[A-Za-z0-9+/=]{12,}|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)', re.I)
BORDER_COMPONENTS = {'n2n', 'protocol', 'gait', 'mempalace', 'memory-mcp', 'humanrail', 'tts', 'hermes-hud', 'claw-certs', 'in2n-production'}


def contains_literal(value):
    if isinstance(value, dict):
        return any(contains_literal(k) or contains_literal(v) for k, v in value.items())
    if isinstance(value, list):
        return any(contains_literal(v) for v in value)
    if isinstance(value, str):
        if SECRET_PATTERN.search(value):
            return True
        try:
            if '://' in value:
                parsed = urlsplit(value)
                return bool(parsed.username or parsed.password)
        except ValueError:
            return True
    return False


def condition_met(condition, settings):
    if condition is None:
        return False
    if 'present' in condition:
        setting = settings.get(condition['present'])
        return bool(setting and (setting.get('kind') == 'secret' and setting.get('source') != 'later' or setting.get('kind') == 'value' and setting.get('value') not in ('', False)))
    if 'equals' in condition:
        expected = condition['equals']
        return settings.get(expected['key'], {}).get('value') == expected['value']
    if 'all' in condition:
        return all(condition_met(v, settings) for v in condition['all'])
    if 'any' in condition:
        return any(condition_met(v, settings) for v in condition['any'])
    raise Invalid('invalid_condition')


class PlanValidator:
    def __init__(self, repository):
        self.repository = Path(repository)
        self.schema = loads(guarded_read(self.repository / 'config/claw-plan.schema.json'), 1024*1024)
        self.catalog = loads(guarded_read(self.repository / 'config/components/catalog.json',16*1024*1024), 16*1024*1024)
        self.components = {c['id']: c for c in self.catalog['components']}
        self.skills = {s['id']: s for s in self.catalog['skills']}
        self.choices = {(c['kind'], c['id']): c for c in self.catalog['choices']}
        self.profiles = {p['id']: p for p in self.catalog['profiles']}
        self.members = {p['id']: p for p in self.catalog['memberProfiles']}
        self.adapters = loads(guarded_read(self.repository/'config/components/harness-adapters.json'))
        self.comms = CommsCatalog(self.repository)

    def read(self, path, *, draft=False):
        try:
            p = Path(path)
            if p.is_symlink() or not p.is_file() or p.stat().st_size > 1024*1024:
                raise Invalid('unsafe_plan_file')
            plan = loads(guarded_read(p,1024*1024))
            return plan, self.inspect(plan, draft=draft)
        except (OSError, Invalid) as exc:
            return None, {'valid': False, 'applyReady': False, 'hash': None,
                          'errors': [{'pointer': '', 'code': getattr(exc, 'code', 'plan_unreadable')}], 'configurationRequired': []}

    def fields(self, claw):
        entries = [self.components[c] for c in claw['capabilities']['components'] if c in self.components]
        entries += [self.choices[k] for k in [('harness', claw['harness']), ('provider', claw['provider']['id'])] if k in self.choices]
        for channel in claw['channels']:
            descriptor = self.choices.get(('channel', channel['id']))
            if not descriptor:
                continue
            try:
                contract = self.comms.channel(claw['harness'], channel['id'])
                fields = contract['setup']['settings']
            except Invalid:
                fields = []
            entries.append({'settings': fields or descriptor['settings']})
        result = {}
        for entry in entries:
            for field in entry.get('settings', []):
                previous = result.get(field['key'])
                # Conflicting classifications are confidential; one required use
                # cannot be weakened by an optional declaration elsewhere.
                if previous:
                    field = dict(field)
                    if previous['classification'] == 'secret': field['classification'] = 'secret'
                    if previous['required'] == 'always': field['required'] = 'always'
                result[field['key']] = field
        return result

    def inspect(self, plan, *, draft=False):
        errors, required = [], []
        try:
            encoded = canonical(plan)
            if len(encoded) > 1024*1024: raise Invalid('size_limit')
        except Invalid as exc:
            return {'valid': False, 'applyReady': False, 'hash': None, 'errors': [{'pointer': '', 'code': exc.code}], 'configurationRequired': []}
        errors.extend(validate(plan, self.schema))
        if contains_literal(plan): errors.append({'pointer': '', 'code': 'literal_credential_refused'})
        digest = hashlib.sha256(encoded).hexdigest()
        # Only structurally sound plans enter semantic traversal. No submitted
        # values (including unknown names) are copied into error messages.
        if errors:
            return {'valid': False, 'applyReady': False, 'hash': digest, 'errors': errors, 'configurationRequired': []}
        def bad(pointer, code): errors.append({'pointer': pointer, 'code': code})
        host = plan['host']; claws = plan['claws']; ids = set(); paths = []; ports = set(); services = set()
        if (host['platform'] == 'macos') != (host['remote'] == 'local'): bad('/host', 'host_context_mismatch')
        if host['platform'] == 'wsl2' and host['osVersion'] not in ('24.04', '26.04'): bad('/host', 'unsupported_distribution')
        roles = [c['role'] for c in claws]
        if plan['shape'] == 'focused' and (len(claws) != 1 or roles != ['focused']): bad('/shape', 'focused_shape_mismatch')
        if plan['shape'] == 'risk' and (roles.count('border') != 1 or roles.count('member') < 1 or 'focused' in roles): bad('/shape', 'risk_shape_mismatch')
        border = next((c for c in claws if c['role'] == 'border'), None)
        source = plan['source']['path']
        if not self.absolute(source): bad('/source/path', 'absolute_path_required')
        for index, claw in enumerate(claws):
            pointer = f'/claws/{index}'
            if claw['id'] in ids: bad(pointer, 'duplicate_installation')
            ids.add(claw['id'])
            runtime = claw['runtimeHome']; workspace = claw['workspace']
            if not self.absolute(runtime) or not self.absolute(workspace): bad(pointer, 'absolute_path_required')
            if runtime in ('/', '/Users', '/home', '/tmp', '/private/tmp'): bad(pointer, 'unsafe_runtime_root')
            if claw['harness']=='hermes':
                if workspace!=runtime:bad(pointer+'/workspace','hermes_native_workspace_required')
            elif not workspace.startswith(runtime.rstrip('/')+'/'): bad(pointer+'/workspace', 'workspace_outside_home')
            if self.overlaps(runtime, source): bad(pointer, 'source_home_overlap')
            if any(self.overlaps(runtime, other) for other in paths): bad(pointer, 'home_collision')
            paths.append(runtime)
            for port in claw['endpoints'].values():
                if port in ports: bad(pointer+'/endpoints', 'endpoint_collision')
                ports.add(port)
            if claw['service']['name'] in services: bad(pointer+'/service', 'service_collision')
            services.add(claw['service']['name'])
            if claw['harnessChoice'] == 'inherit' and (not border or claw['role'] != 'member' or claw['harness'] != border['harness']): bad(pointer, 'inheritance_mismatch')
            if claw['role'] != 'member' and claw['service']['mode'] != 'hot': bad(pointer, 'primary_must_be_hot')
            provider = self.choices.get(('provider', claw['provider']['id']))
            if not provider or claw['harness'] not in provider['harnesses']: bad(pointer+'/provider', 'unsupported_provider')
            adapter = self.adapters[claw['harness']]
            if claw['runtimeVersion'] not in adapter['versions']: bad(pointer+'/runtimeVersion', 'harness_version_unqualified')
            if claw['provider']['apiMode'] not in adapter['apiModes'] or claw['provider']['apiMode'] not in self.adapters['providerApiModes'].get(claw['provider']['id'],[]): bad(pointer+'/provider/apiMode','unsupported_api_mode')
            if claw['provider']['id'] in ('ollama','lm-studio') and claw['provider']['kind']!='local': bad(pointer+'/provider','provider_kind_mismatch')
            if claw['provider']['kind'] == 'local' and claw['provider']['id'] not in ('ollama', 'lm-studio', 'custom'): bad(pointer+'/provider', 'provider_kind_mismatch')
            endpoint = claw['provider']['endpoint']
            if endpoint:
                try:
                    parsed = urlsplit(endpoint)
                    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query or parsed.port==0: raise ValueError()
                    if claw['provider']['kind'] == 'local' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'): raise ValueError()
                    if claw['provider']['id']=='ollama' and parsed.path.rstrip('/') != ('' if claw['provider']['apiMode']=='ollama' else '/v1'):raise ValueError()
                    if claw['provider']['id']=='lm-studio' and parsed.path.rstrip('/')!='/v1':raise ValueError()
                except ValueError: bad(pointer+'/provider/endpoint', 'unsafe_provider_endpoint')
            if claw['provider']['kind'] == 'local' and not endpoint: bad(pointer+'/provider', 'local_endpoint_required')
            if claw['provider']['id']=='custom' and not endpoint:bad(pointer+'/provider','custom_endpoint_required')
            chosen = set(claw['capabilities']['components'])
            from pyats_testbeds import policy, TestbedError
            try:
                testbed = policy(claw.get('testbed'))
                if 'testbed' in claw and 'pyats' not in chosen:bad(pointer+'/testbed','testbed_requires_pyats')
                if testbed['mode']=='dynamic' and any(i['owner']==claw['id'] for i in plan['inventory']):bad(pointer+'/testbed','dynamic_static_input_conflict')
            except TestbedError as exc:bad(pointer+'/testbed',str(exc))
            if plan['shape']=='risk' and ('n2n' not in chosen or claw['role']=='border' and 'protocol' not in chosen):bad(pointer+'/capabilities','risk_runtime_components_missing')
            for component in chosen:
                descriptor = self.components.get(component)
                if not descriptor: bad(pointer+'/capabilities', 'unknown_component'); continue
                if host['platform'] not in descriptor['platforms']: bad(pointer+'/capabilities', 'unsupported_component_platform')
                if component in self.adapters.get('unavailableComponents',{}):bad(pointer+'/capabilities',self.adapters['unavailableComponents'][component]['code'])
                if descriptor['installer']['mode'] == 'unsupported': bad(pointer+'/capabilities', 'unsupported_component')
                if not set(descriptor['dependencies']) <= chosen: bad(pointer+'/capabilities', 'missing_dependency')
            profile = claw['capabilities']['profile']
            if claw['role'] == 'member':
                member = self.members.get(profile)
                if not member or claw['harness'] not in member['harnesses']: bad(pointer+'/capabilities/profile', 'unsupported_member_profile')
                elif not set(member['components']) <= chosen: bad(pointer+'/capabilities', 'member_profile_components_missing')
                if profile=='comms' and not chosen.intersection({'twilio','zoom-rtms'}):bad(pointer+'/capabilities','comms_capability_required')
            elif profile not in self.profiles: bad(pointer+'/capabilities/profile', 'unknown_profile')
            if claw['role'] == 'border' and not chosen <= BORDER_COMPONENTS: bad(pointer+'/capabilities', 'border_domain_capability')
            for skill_id in claw['capabilities']['skills']:
                skill = self.skills.get(skill_id)
                if not skill: bad(pointer+'/capabilities', 'unknown_skill'); continue
                if not set(skill['components']) <= chosen: bad(pointer+'/capabilities', 'skill_dependency_missing')
                if skill['availability'] != 'supported' and not any(skill_id.startswith(c['id']+'-') for c in claw['channels']): bad(pointer+'/capabilities', 'external_skill_unconfigured')
                if claw['role'] == 'border' and not set(skill['components']) <= BORDER_COMPONENTS: bad(pointer+'/capabilities', 'border_domain_skill')
            channel_ids = [c['id'] for c in claw['channels']]
            if len(set(channel_ids)) != len(channel_ids) or 'none' in channel_ids: bad(pointer+'/channels', 'invalid_channel_selection')
            if claw['role'] == 'member' and channel_ids: bad(pointer+'/channels', 'member_channels_forbidden')
            for channel in claw['channels']:
                descriptor = self.choices.get(('channel', channel['id']))
                if not descriptor or claw['harness'] not in descriptor['harnesses']: bad(pointer+'/channels', 'unsupported_channel')
                elif channel['id'] in adapter.get('unavailableChannels',{}):bad(pointer+'/channels','channel_plugin_api_incompatible')
                elif not set(channel['settingKeys']) <= set(descriptor['settingKeys']): bad(pointer+'/channels', 'unknown_channel_setting')
                if descriptor and claw['harness'] in descriptor['harnesses']:
                    try:
                        entry = self.comms.channel(claw['harness'], channel['id'])
                        resolved = self.comms.resolve(entry['id'], role=claw['role'], host=host['platform'], version=claw['runtimeVersion'])
                        state = resolved['state']
                        # Legacy selections remain readable. Their new Comms
                        # effect must still settle before service activation.
                        legacy = channel['id'] in ('slack','telegram','discord') and state == 'incomplete-adapter'
                        if not resolved['selectable'] and not legacy:
                            bad(pointer+'/channels', 'channel_'+state.replace('-', '_'))
                        from setup_comms import access_list
                        for key in entry['setup']['access']:
                            setting=claw['settings'].get(key,{})
                            if setting.get('kind')=='value':
                                try:access_list(setting['value'])
                                except Invalid:bad(pointer+'/settings/*','invalid_comms_access')
                    except Invalid:
                        bad(pointer+'/channels', 'unsupported_channel')
            fields = self.fields(claw)
            for key, setting in claw['settings'].items():
                field = fields.get(key)
                setting_pointer = pointer+'/settings/*'
                if not field: bad(setting_pointer, 'unknown_setting'); continue
                if field['input'] == 'generated': bad(setting_pointer, 'generated_setting_override'); continue
                if field['classification'] == 'secret':
                    if setting['kind'] != 'secret': bad(setting_pointer, 'secret_reference_required'); continue
                    if setting['owner'] != claw['id'] or setting['key'] != key: bad(setting_pointer, 'secret_owner_mismatch')
                elif setting['kind'] != 'value': bad(setting_pointer, 'value_required')
                else:
                    value = setting['value']; typ = field['valueType']
                    if key=='NETCONVERTER_MODE' and value not in ('hosted-readonly','local-terminal'): bad(setting_pointer,'invalid_netconverter_mode')
                    if key in ('NETCONVERTER_WORKSPACE','NETCONVERTER_EXECUTABLE') and value and (not isinstance(value,str) or not self.absolute(value)): bad(setting_pointer,'absolute_netconverter_path_required')
                    if typ == 'boolean' and type(value) is not bool or typ == 'integer' and type(value) is not int or typ in ('string','path','url') and not isinstance(value,str): bad(setting_pointer, 'setting_type')
                    if typ == 'url' and isinstance(value,str) and value:
                        try:
                            u = urlsplit(value)
                            if u.scheme not in ('http','https') or not u.hostname or u.username or u.password: raise ValueError()
                        except ValueError: bad(setting_pointer, 'unsafe_setting_url')
            for key, field in fields.items():
                needed = field['required'] == 'always' or field['required'] == 'conditional' and condition_met(field['condition'], claw['settings'])
                if needed and field['input'] != 'generated':
                    setting = claw['settings'].get(key)
                    if not setting or setting.get('source') == 'later' or setting.get('value') == '': required.append({'owner': claw['id'], 'key': key, 'state': 'configuration_required'})
            provider_secrets={f['key'] for f in (provider or {}).get('settings',[]) if f['classification']=='secret'}
            provider_required={f['key'] for f in (provider or {}).get('settings',[]) if f['classification']=='secret' and f['required']=='always'}
            if not provider_required <= set(claw['provider']['credentialKeys']) <= provider_secrets: bad(pointer+'/provider', 'unknown_provider_credential')
            if any(key in claw['settings'] and key not in claw['provider']['credentialKeys'] for key in provider_secrets):bad(pointer+'/provider','unused_provider_credential')
        binding_ids, binding_owners, binding_borders = set(), set(), set()
        from setup_comms import channel_listening_ports
        for port in channel_listening_ports(plan):
            if type(port) is not int or not 1024<=port<=65535:bad('/claws/*/settings','invalid_channel_port')
            elif port in ports:bad('/claws/*/settings','endpoint_collision')
            else:ports.add(port)
        for binding in plan.get('commsBindings', []):
            pointer = '/commsBindings'
            owner = next((c for c in claws if c['id'] == binding['owner']), None)
            target = next((c for c in claws if c['id'] == binding['border']), None)
            if plan['shape'] != 'risk' or not owner or not target or target['role'] != 'border' or owner['id'] == target['id']:
                bad(pointer, 'comms_binding_owner_mismatch')
            if owner and 'zoom-rtms' not in owner['capabilities']['components']:
                bad(pointer, 'comms_binding_component_missing')
            if binding['id'] in binding_ids or binding['owner'] in binding_owners or binding['border'] in binding_borders:
                bad(pointer, 'duplicate_comms_binding')
            binding_ids.add(binding['id']); binding_owners.add(binding['owner']);binding_borders.add(binding['border'])
            if owner and any(k in owner['settings'] for k in ('N2N_ZOOM_CHANNEL_HOST','N2N_ZOOM_CHANNEL_PORT','N2N_ZOOM_CHANNEL_SECRET')):
                bad(pointer,'comms_binding_setting_override')
            if binding['port'] in ports:
                bad(pointer, 'endpoint_collision')
            ports.add(binding['port'])
        if not {1,2,3} <= set(plan['verification']['tiers']): bad('/verification/tiers', 'mandatory_tiers_missing')
        if plan['verification']['risk'] != (plan['shape'] == 'risk'): bad('/verification/risk', 'risk_verification_mismatch')
        if not plan['verification']['networkReadOnly']: bad('/verification/networkReadOnly', 'network_write_forbidden')
        for kind in ('inventory','identity'):
            seen = set()
            for item in plan[kind]:
                if item['owner'] not in ids: bad('/'+kind, 'unknown_file_owner')
                identity=(item['owner'],kind if kind=='inventory' else item['kind'])
                if identity in seen: bad('/'+kind, 'duplicate_file_input')
                seen.add(identity)
                if not self.absolute(item['path']): bad('/'+kind, 'absolute_path_required')
                if (kind=='inventory') != item['kind'].startswith('testbed-'): bad('/'+kind,'input_kind_mismatch')
        channel_tests=set()
        for channel in plan['verification']['channelTests']:
            owner=next((c for c in claws if c['id']==channel['owner']),None)
            if owner is None or channel['channel'] not in [c['id'] for c in owner['channels']]: bad('/verification/channelTests','channel_test_owner_mismatch')
            key=(channel['owner'],channel['channel'],channel.get('direction','outbound'),channel['destinationRef'])
            if key in channel_tests:bad('/verification/channelTests','duplicate_channel_test')
            channel_tests.add(key)
        valid = not errors
        return {'valid': valid, 'applyReady': valid and not plan['unresolved'], 'hash': digest,
                'errors': errors, 'configurationRequired': required}

    @staticmethod
    def absolute(path):
        return path.startswith('/') and posixpath.normpath(path) == path and not path.startswith('//') and not any(c in path for c in '\r\n\0')

    @staticmethod
    def overlaps(first, second):
        return first == second or first.startswith(second.rstrip('/')+'/') or second.startswith(first.rstrip('/')+'/')

    def explain(self, plan):
        report = self.inspect(plan)
        if not report['valid']: return report
        effects = []
        for phase in ('home','runtime','credentials','onboard','components','skills','registration','inventory','identity','comms','comms-binding','risk','services','verification'):
            for claw in plan['claws']:
                if phase == 'risk' and plan['shape'] != 'risk': continue
                if phase == 'comms':
                    for channel in claw['channels']:
                        entry = self.comms.channel(claw['harness'], channel['id'])
                        effects.append({'id': claw['id']+':comms:'+channel['id'], 'owner': claw['id'],
                            'phase': phase, 'component': None, 'channel': channel['id'],
                            'scope': ['runtime-home'], 'startupEffects':entry['setup']['startupEffects'],
                            'adapter':entry['setup']['adapter'],'dependencies':entry['setup']['dependencies'],
                            'documentation':entry['documentation'],'nativeId':entry['nativeId'],
                            'kind':entry['kind'],'setupExplanation':entry['setup']['reason'],
                            'accessPolicy':'Explicit sender/room scope; empty allowlists grant no access. Adapter-enforced mention/signature rules remain enabled.',
                            'callbackSettings':{f['key']:claw['settings'].get(f['key'],{'kind':'value','value':''})
                                for f in entry['setup']['settings'] if f['classification']!='secret' and
                                any(word in f['key'] for word in ('WEBHOOK','PUBLIC_URL','HTTP_URL','PORT'))},
                            'access':{key:claw['settings'].get(key,{'kind':'value','value':''}) for key in entry['setup']['access']},
                            'native': entry['setup']['method'] == 'native'})
                    continue
                if phase == 'comms-binding':
                    for binding in plan.get('commsBindings', []):
                        if binding['owner'] != claw['id']: continue
                        effects.append({'id': claw['id']+':comms-binding:'+binding['id'], 'owner': claw['id'],
                            'phase': phase, 'component': None, 'binding': binding['id'],
                            'scope': ['runtime-home','paired-border-home','loopback-port'], 'native': False})
                    continue
                components = claw['capabilities']['components'] if phase == 'components' else [None]
                for component in components:
                    effects.append({'id': claw['id']+':'+phase+(':'+component if component else ''),
                        'owner': claw['id'], 'phase': phase, 'component': component,
                        **({'testbed':claw.get('testbed',{'mode':'static','sources':[]}),
                            'setupExplanation':'Configure inventory policy only; source access, candidate validation and activation are separate.'}
                           if phase=='inventory' and 'pyats' in claw['capabilities']['components'] else {}),
                        'scope': self.components[component]['installer']['effects'] if component else
                            ['runtime-home','user-service-manager','owned-service-files'] if phase=='services' else ['runtime-home'],
                        **({'startupEffects':sorted({value for entry in self.comms.entries
                            if entry['harness']==claw['harness'] and entry['component']==component
                            for value in entry['setup']['startupEffects']})} if component in ('zoom-rtms','twilio') else {}),
                        'native': self.components[component]['installer']['mode']=='native' if component else phase=='onboard'})
        return {**report, 'effects': effects, 'posture': plan['posture']['mode'],
                'reviewRequired': True, 'liveTiers': [t for t in plan['verification']['tiers'] if t>3],
                'downloadSizes': 'Adapter-specific estimates appear before each reviewed acquisition; unknown sizes are labelled.',
                'existingInstallations': 'New homes only. Existing installations and mutable source bindings must be observed before apply.'}
