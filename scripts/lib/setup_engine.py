"""Single durable execution engine shared by CLI and the editor frontend."""
import copy
import hashlib
import os
from pathlib import Path
import secrets
import threading
import time
from contextlib import ExitStack

from setup_observation import HostObservation
from setup_plan import PlanValidator
from setup_schema import Invalid, canonical, loads
from setup_state import Conflict, ResourceLocks, StateStore, directory, guarded_read, revision
from ha_setup_guard import require_standalone_home


class ReviewRefused(Invalid):
    pass

class ControlRefusal(Conflict):
    def __init__(self,blocked):
        super().__init__('production_controls_unverified')
        self.blocked_controls=blocked


class _Review:
    def __init__(self, binding, session, action):
        self.binding, self.session, self.action = copy.deepcopy(binding), session, action
        self.expires, self.used = time.monotonic() + 300, False

    def consume(self, binding, action):
        if self.used or time.monotonic() > self.expires or self.action != action or self.binding != binding:
            raise ReviewRefused('review_expired_or_changed')
        self.used = True


class ReviewAuthority:
    """In-process native/controlling-TTY authority; never serialized to a tool."""
    def __init__(self, session):
        self.session = session

    def approve(self, binding, action='apply'):
        return _Review(binding, self.session, action)


def default_state_root():
    # Do not accept an environment override from a plan or assistant tool. The
    # user account is shared with the editor and CLI; both use this lock domain.
    import pwd
    return Path(pwd.getpwuid(os.getuid()).pw_dir).resolve() / '.local/state/netclaw/setup'


class Engine:
    def __init__(self, repository, state_root=None, runner=None, *, observation=None, emit=None):
        self.repository = Path(repository).resolve()
        self.validator = PlanValidator(self.repository)
        self.state_root = Path(state_root) if state_root is not None else default_state_root()
        self.store = None  # Read-only validation/review does not create state.
        self.observation = observation or HostObservation()
        self.runner = runner
        self.emit = emit or (lambda event: None)
        self.pause = threading.Event()
        self.sequence = 0

    def review_binding(self, plan):
        explanation = self.validator.explain(plan)
        if not explanation.get('applyReady'):
            raise Invalid('plan_not_apply_ready')
        actual = self.observation.binding(plan)
        return {'planHash': explanation['hash'], 'observed': actual,
                'catalogHash': hashlib.sha256(guarded_read(self.repository/'config/components/catalog.json', 16*1024*1024)).hexdigest(),
                'commsHash': hashlib.sha256(guarded_read(self.repository/'config/components/comms.json', 4*1024*1024)).hexdigest(),
                'policyHash': hashlib.sha256(guarded_read(self.repository/'config/components/security-policy.json')).hexdigest(),
                'effectsHash': hashlib.sha256(canonical(explanation['effects'])).hexdigest()}

    def request_pause(self):
        self.pause.set()

    def _state(self, *, create=True):
        if self.store is None:
            self.store = StateStore(self.state_root, create=create)
        return self.store

    def _locks(self, plan):
        resources = ['host:'+plan['host']['fingerprint'], 'source:'+plan['source']['path']]
        resources += ['home:'+c['runtimeHome'] for c in plan['claws']]
        return ResourceLocks(self.state_root/'locks', resources)

    def _targets(self, plan, run=None):
        for claw in plan['claws']:
            path = Path(claw['runtimeHome'])
            require_standalone_home(path)
            if self.validator.overlaps(str(path), str(self.state_root)) or self.validator.overlaps(plan['source']['path'], str(self.state_root)):
                raise Conflict('state_target_overlap')
            try:
                with directory(path, private=True) as fd:
                    names = os.listdir(fd)
                if run is None and names:
                    raise Conflict('existing_installation_detected')
                if run is not None and names:
                    try:
                        marker = loads(guarded_read(path/'.netclaw-setup-owner.json', 16384, private=True))
                    except FileNotFoundError:
                        raise Conflict('target_ownership_missing') from None
                    if marker != {'schema': 1, 'runId': run['runId'], 'installationId': claw['id'], 'planHash': run['planHash']}:
                        raise Conflict('target_ownership_changed')
            except FileNotFoundError:
                if run is not None and any(e['owner'] == claw['id'] and e['phase'] == 'home' and e['state'] == 'verified' for e in run['effects']):
                    raise Conflict('owned_home_missing')

    def _controls(self, plan):
        if plan['posture']['mode'] != 'production':
            return []
        policy = loads(guarded_read(self.repository/'config/components/security-policy.json'))
        required = [('host', c) for c in policy['minimum']['host']];unsupported=set()
        for claw in plan['claws']:
            controls = set(policy['minimum']['claw']) | set(plan['posture']['requiredControls'])
            unsupported.update((claw['id'],c) for c in controls.intersection(policy['unsupported'].get(claw['harness'], [])))
            required += [(claw['id'], control) for control in sorted(controls)]
        actual = self.observation.controls(plan, required)
        verified = {(c['owner'], c['control']) for c in actual if c.get('state') == 'verified'}
        blocked=[{'owner':owner,'control':control,'state':'unsupported' if (owner,control) in unsupported else 'unverified'}
                 for owner,control in required if (owner,control) not in verified or (owner,control) in unsupported]
        if blocked:raise ControlRefusal(blocked)
        return actual

    def _save(self, run):
        run['updatedAt'] = int(time.time())
        self._state().save(run['runId'], run)

    def _event(self, run, effect=None, *, typ='phase', code='checkpoint'):
        self.sequence += 1
        event = {'protocol': 1, 'runId': run['runId'], 'sequence': self.sequence, 'type': typ,
                 'phase': effect['phase'] if effect else 'run', 'owner': effect['owner'] if effect else '',
                 'state': effect['state'] if effect else run['state'], 'code': code}
        # Never forward runner messages, paths, arbitrary data, or exceptions.
        self.emit(event)

    def apply(self, plan, review):
        plan = copy.deepcopy(plan)
        binding = self.review_binding(plan)
        if not isinstance(review, _Review):
            raise ReviewRefused('native_review_required')
        self._state()
        with self._locks(plan) as locks:
            review.consume(self.review_binding(plan), 'apply')
            self.observation.check(plan)
            self._targets(plan)
            controls = self._controls(plan)
            now = int(time.time())
            run = {'schema': 1, 'runId': 'run-'+secrets.token_hex(16), 'planHash': binding['planHash'],
                   'binding': binding, 'state': 'applying', 'createdAt': now, 'updatedAt': now,
                   'frontend': review.session, 'controls': controls,
                   'effects': [{**e, 'state': 'pending', 'artifacts': []} for e in self.validator.explain(plan)['effects']]}
            # Private plan has references only and supports explicit resumption.
            run['plan'] = plan
            self._save(run)
            return self._execute(plan, run, locks)

    def status(self, run_id):
        run = self._state(create=False).load(run_id,hydrate=False)
        # A durable in-progress intent after a dead engine is not a success or an
        # implicit instruction to restart. Status is observational only.
        if run['state'] in ('applying', 'verifying', 'pause_requested', 'observing'):
            run['state'] = 'unknown'
        return self.projection(run)

    def verify(self, run_id):
        run=self._state(create=False).load(run_id);plan=run['plan']
        if run.get('cleanup'):raise Conflict('run_cleanup_started')
        with self._locks(plan) as locks:
            if self.review_binding(plan)!=run['binding']:raise Conflict('verification_binding_changed')
            self._targets(plan,run)
            if any(e['state'] in ('running','unknown','pending') for e in run['effects']):
                raise Conflict('verification_run_unsettled')
            self._controls(plan)
            if self.runner is None:raise Invalid('effect_adapter_required')
            for effect in run['effects']:
                if effect['phase']!='verification':continue
                if self.pause.is_set():
                    run['state']='paused';self._save(run);self._event(run,code='paused_at_checkpoint')
                    return self.projection(run)
                effect['state']='running';run['state']='verifying';self._save(run)
                try:
                    result=self.runner(effect,self._context(plan,run,locks))
                    if result.get('state') not in ('verified','failed','configuration_required','unverified'):
                        raise Invalid('adapter_outcome_invalid')
                    effect['state']=result['state']
                except Exception:effect['state']='unknown'
                self._save(run);self._event(run,effect,typ='outcome',code='verification_'+effect['state'])
                if effect['state']=='unknown':break
            states={e['state'] for e in run['effects']}
            run['state']=next((s for s in ('unknown','failed','configuration_required','unverified') if s in states),'completed')
            self._save(run)
            return self.projection(run)

    def report(self,run_id):
        from setup_report import project
        run=self._state(create=False).load(run_id,hydrate=False)
        return project({'installations':[run.get('reports',{}).get(c['id'],{}) for c in run['plan']['claws']]},self.validator.catalog)

    def connections(self,run_id):
        """Local native UI handoff only; never part of assistant projections."""
        run=self._state(create=False).load(run_id,hydrate=False)
        if run.get('cleanup'):return {'candidates':[]}
        candidates=[]
        for claw in run['plan']['claws']:
            report=run.get('reports',{}).get(claw['id'],{})
            if not any(t.get('tier')==3 and t.get('state')=='verified' for t in report.get('tiers',[])):continue
            identity=report.get('identity',{})
            if identity.get('home')!=claw['runtimeHome']:continue
            candidates.append({'id':claw['id'],'label':claw['displayName'],'harness':claw['harness'],
                'installationId':identity['installationId'],'home':claw['runtimeHome'],'workspace':claw['workspace'],
                'url':'http://127.0.0.1:'+str(claw['endpoints']['hudPort'])})
        return {'candidates':candidates}

    def cleanup_preview(self,run_id):
        from setup_cleanup import preview,cleanup_binding
        run=self._state(create=False).load(run_id)
        with self._locks(run['plan']):
            value=preview(run);return {'preview':value,'binding':cleanup_binding(run,value)}

    def cleanup(self,run_id,review):
        from setup_cleanup import apply_cleanup,management_lock
        from setup_cleanup_services import NativeCleanup
        run=self._state(create=False).load(run_id)
        with self._locks(run['plan']) as locks, ExitStack() as management:
            # Bind a durable cleanup intent before unlinking. An interrupted
            # cleanup is never resumed as an installation.
            accepted=False
            def started(binding,proposed):
                nonlocal accepted
                for claw in run['plan']['claws']:
                    if claw['id'] in proposed['ownerBindings']:management.enter_context(management_lock(claw['runtimeHome'],run_id))
                accepted=True
                run.setdefault('preCleanupReports',copy.deepcopy(run.get('reports',{})))
                from setup_report import invalidate_for_cleanup
                for report in run.get('reports',{}).values():
                    invalidate_for_cleanup(report)
                run['cleanup']={'state':'running','binding':binding};run['state']='configuration_required';self._save(run)
            try:
                result=apply_cleanup(run,review,started=started,services=NativeCleanup(run,lock_fds=locks.fds));run['cleanup']={'state':result['state'],'result':result};self._save(run);return result
            except Exception:
                if accepted:run['cleanup']['state']='unknown';self._save(run)
                raise

    def resume(self, plan, run_id, review):
        plan = copy.deepcopy(plan)
        if not isinstance(review, _Review):
            raise ReviewRefused('native_review_required')
        with self._locks(plan) as locks:
            run = self._state().load(run_id)
            if run.get('cleanup'):raise Conflict('run_cleanup_started')
            binding = self.review_binding(plan)
            if binding != run['binding']:
                raise Conflict('resume_binding_changed')
            review.consume(binding, 'apply')
            self.observation.check(plan, run)
            self._targets(plan, run)
            run['controls'] = self._controls(plan)
            if run['state'] == 'completed':
                return self.projection(run)
            self.pause.clear()
            run['state'] = 'observing'
            self._save(run)
            retry_owners=set()
            for effect in run['effects']:
                writer = effect.get('writer')
                if writer:
                    try:
                        os.killpg(writer['group'], 0)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        raise Conflict('writer_ownership_unknown') from None
                    else:
                        raise Conflict('writer_still_active')
                if effect['state'] == 'verified' and hasattr(self.runner, 'observe'):
                    if self.runner.observe(effect, self._context(plan, run, locks)) != 'completed':
                        raise Conflict('completed_effect_changed')
                if effect['state'] not in ('running', 'unknown', 'failed', 'configuration_required'):
                    continue
                observation = 'unknown'
                if hasattr(self.runner, 'observe'):
                    try:
                        observation = self.runner.observe(effect, self._context(plan, run, locks))
                    except Exception:
                        pass
                if observation == 'completed':
                    effect['state'] = 'verified'
                elif observation in ('not_applied','retry_owned'):
                    effect['state'] = 'pending'
                    if effect['phase']=='components':retry_owners.add(effect['owner'])
                elif observation == 'configuration_required':
                    effect['state'] = 'configuration_required'
                else:
                    effect['state'] = 'unknown'
                    run['state'] = 'unknown'
                    self._save(run)
                    self._event(run, effect, code='observation_required')
                    return self.projection(run)
            for effect in run['effects']:
                if effect['owner'] in retry_owners and effect['phase'] in ('registration','verification'):
                    effect['state']='pending'
            return self._execute(plan, run, locks)

    def _context(self, plan, run, locks):
        def writer_started(effect_id, identity):
            effect = next(e for e in run['effects'] if e['id'] == effect_id)
            effect['writer'] = identity
            self._save(run)
        def artifact_intent(effect_id, artifacts):
            effect = next(e for e in run['effects'] if e['id'] == effect_id)
            effect['artifacts'].extend(artifacts)
            self._save(run)
        return {'plan': plan, 'runId': run['runId'], 'planHash': run['planHash'], 'stateRoot': self.state_root,
                'lockFds': tuple(locks.fds), 'pause': self.pause, 'journal': run, 'writerStarted': writer_started,
                'artifactIntent': artifact_intent,'save':lambda:self._save(run)}

    def _execute(self, plan, run, locks):
        if self.runner is None:
            raise Invalid('effect_adapter_required')
        for effect in run['effects']:
            if effect['state'] != 'pending':
                # Resume must not step around a still-unsettled prerequisite.
                if effect['phase'] in ('home','runtime','onboard','comms','comms-binding') and effect['state'] != 'verified':
                    run['state'] = 'configuration_required' if effect['state']=='skipped' else effect['state']
                    break
                continue
            if self.pause.is_set():
                run['state'] = 'pause_requested'; self._save(run); self._event(run, code='pause_requested')
                run['state'] = 'paused'; self._save(run); self._event(run, code='paused_at_checkpoint')
                return self.projection(run)
            run['state'] = 'verifying' if effect['phase'] == 'verification' else 'applying'
            effect['state'] = 'running'
            self._save(run)  # Durable intent always precedes adapter effects.
            self._event(run, effect, code='effect_started')
            try:
                result = self.runner(effect, self._context(plan, run, locks))
                state = result.get('state')
                if state not in ('verified', 'failed', 'unknown', 'configuration_required', 'skipped', 'unverified'):
                    raise Invalid('adapter_outcome_invalid')
                # Artifacts are adapter-owned typed local evidence, never stdout.
                artifacts = result.get('artifacts', effect['artifacts'])
                if not isinstance(artifacts, list) or len(canonical(artifacts)) > 8*1024*1024:
                    raise Invalid('adapter_artifacts_invalid')
                effect.update(state=state, artifacts=artifacts)
            except Exception:
                effect['state'] = 'unknown'
            self._save(run)
            self._event(run, effect, typ='outcome', code='postcondition_'+effect['state'])
            if effect['state'] == 'unknown':
                run['state'] = 'unknown'; break
            if effect['state'] == 'failed' and effect['phase'] not in ('components', 'verification'):
                run['state'] = 'failed'; break
            # A partial/cancelled onboarding step may have changed the selected
            # configuration. Reconcile it before any component, registration or
            # service phase; a terminal exit or deferred input is not approval.
            if effect['phase'] in ('home','runtime','onboard','comms','comms-binding') and effect['state'] != 'verified':
                run['state'] = 'configuration_required' if effect['state']=='skipped' else effect['state']; break
        else:
            states = {e['state'] for e in run['effects']}
            run['state'] = ('failed' if 'failed' in states else 'configuration_required' if 'configuration_required' in states
                            else 'unverified' if 'unverified' in states else 'completed')
        self._save(run)
        self._event(run, typ='outcome', code='run_'+run['state'])
        return self.projection(run)

    @staticmethod
    def projection(run):
        return {'protocol': 1, 'runId': run['runId'], 'planHash': run['planHash'], 'state': run['state'],
                'effects': [{k: e[k] for k in ('id', 'owner', 'phase', 'component', 'state')} for e in run['effects']]}
