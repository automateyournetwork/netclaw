"""QUALIFICATION-ONLY fault instrumentation for REAL spec-179 rows.

This module is never imported by product code. It is loaded only by
``labs/ha/real_role_launcher.py`` inside a REAL role process that the REAL runner
launched from the frozen run source, and only when a private instrument
configuration names exactly one scenario. It wraps frozen production classes at
the process boundary (class attributes, like the wire fixture's audited
observers); it never edits production source and adds no product bypass: every
product check still runs, only its *input* (a clock reading) or one delivery /
commit-reply boundary is perturbed, once, for one armed operation.

Safety properties (unit tested):
  * default-off: nothing is patched unless a valid configuration is supplied;
  * scenario-exact: one scenario per process, exact name, exact role;
  * armed: an injection needs a second new-only arm file naming the operation;
  * one-shot: a new-only claim file (O_EXCL) is consumed before any fault and
    survives restarts, so a second process or restart cannot repeat it;
  * evidenced: every phase is written to a private new-only evidence file before
    and after the fault; if evidence cannot be written the fault is suppressed;
  * refuses unless the role contract is the REAL qualification profile.
"""
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid

SCHEMA = 1
CLASS = 'REAL-INSTRUMENT'
ROLE_NAMES = {'border0': 'border', 'border1': 'border', 'border2': 'border', 'member': 'member'}
KINDS = ('model', 'tool')
CONFIG_FIELDS = ('schema_version class run_id run_name root role_name role installation_id contract_sha256 '
                 'source_root scenario parameters evidence_dir').split()
ARM_FIELDS = 'schema_version run_id scenario operation_id armed_ms'.split()
# scenario -> (role, parameter validators, default parameters)
SCENARIOS = {
    'clock-wall-step': ('member', {'kind', 'ordinal', 'delta_ms'}, {'kind': 'model', 'ordinal': 1, 'delta_ms': 1500}),
    'clock-monotonic-step': ('member', {'kind', 'ordinal', 'delta_ms'}, {'kind': 'model', 'ordinal': 1, 'delta_ms': 1500}),
    'stale-leader-held-claim': ('member', {'kind', 'ordinal', 'hold_ms'}, {'kind': 'model', 'ordinal': 1, 'hold_ms': 30000}),
    'result-reply-loss': ('member', set(), {}),
    'ack-delivery-loss': ('member', set(), {}),
    'result-and-ack-loss': ('member', set(), {}),  # both, independently one-shot, on the same armed operation
    'unknown-commit-recovered': ('border', {'kind'}, {'kind': 'model'}),
    'unknown-commit-unresolved': ('border', {'kind'}, {'kind': 'model'}),
    # Record-only receiver observer (no fault, no arm): failed peer-certificate verification and the exact
    # production iN2N hello refusal, so unauthenticated-client negatives can be correlated with the receiver.
    'border-trust-observer': ('border', set(), {}),
}
OBSERVER_LIMIT = 256


class InstrumentRefused(ValueError):
    pass


def need(value, code):
    if not value:
        raise InstrumentRefused(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def _pairs(rows):
    result = {}
    for key, value in rows:
        need(key not in result, 'duplicate_field')
        result[key] = value
    return result


def private_bytes(path, maximum=65536):
    path = Path(path)
    need(path.is_absolute() and '\x00' not in str(path), 'absolute_path_required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
             and info.st_size <= maximum, 'private_file_required')
        return stream.read(maximum + 1)


def private_json(path, maximum=65536):
    return json.loads(private_bytes(path, maximum), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(InstrumentRefused('invalid_number')))


def private_directory(path):
    path = Path(path)
    need(path.is_absolute(), 'absolute_path_required')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
         and path.resolve() == path, 'private_directory_required')
    return path


def write_new(path, value):
    """Create a new private file; never overwrites (the one-shot primitive)."""
    path = Path(path)
    raw = value if isinstance(value, bytes) else canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def uuid_text(value):
    try:
        need(isinstance(value, str) and str(uuid.UUID(value)) == value, 'invalid_uuid')
    except (ValueError, AttributeError):
        raise InstrumentRefused('invalid_uuid') from None
    return value


def validate_parameters(scenario, parameters):
    need(scenario in SCENARIOS, 'unknown_scenario')
    _, allowed, defaults = SCENARIOS[scenario]
    need(isinstance(parameters, dict) and set(parameters) == set(defaults), 'parameters_invalid')
    if 'kind' in parameters:
        need(parameters['kind'] in KINDS, 'kind_invalid')
    if 'ordinal' in parameters:
        need(type(parameters['ordinal']) is int and 1 <= parameters['ordinal'] <= 2, 'ordinal_invalid')
    if 'delta_ms' in parameters:
        value = parameters['delta_ms']
        need(type(value) is int and 400 <= abs(value) <= 2000, 'delta_ms_invalid')
        need(scenario == 'clock-wall-step' or value > 0, 'monotonic_delta_must_be_positive')
    if 'hold_ms' in parameters:
        # Above the 3 s admission bound, below the 60 s inference bound.
        need(type(parameters['hold_ms']) is int and 4000 <= parameters['hold_ms'] <= 45000, 'hold_ms_invalid')
    return parameters


def validate_config(config):
    need(isinstance(config, dict) and set(config) == set(CONFIG_FIELDS), 'config_fields_invalid')
    need(type(config['schema_version']) is int and config['schema_version'] == SCHEMA and config['class'] == CLASS,
         'config_class_invalid')
    uuid_text(config['run_id']); uuid_text(config['installation_id'])
    need(isinstance(config['run_name'], str) and re.fullmatch('netclaw-r08-[a-z0-9-]{6,48}', config['run_name']), 'run_name_invalid')
    need(config['role_name'] in ROLE_NAMES and ROLE_NAMES[config['role_name']] == config['role'], 'role_invalid')
    need(isinstance(config['contract_sha256'], str) and re.fullmatch('[a-f0-9]{64}', config['contract_sha256']), 'digest_invalid')
    need(config['scenario'] in SCENARIOS and SCENARIOS[config['scenario']][0] == config['role'], 'scenario_role_mismatch')
    validate_parameters(config['scenario'], config['parameters'])
    for key in ('root', 'source_root', 'evidence_dir'):
        need(isinstance(config[key], str) and Path(config[key]).is_absolute() and '\x00' not in config[key], 'path_invalid')
    root = Path(config['root'])
    need(Path(config['source_root']) == root / 'source', 'source_root_invalid')
    need(Path(config['evidence_dir']) == root / 'instrument' / config['scenario'], 'evidence_dir_invalid')
    return config


def default_validator():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/lib'))
    from protected_role import validate
    return validate


def check_qualification(contract_path, config_path, *, source_root, validator=None, environ=None, module_file=None):
    """Refuse unless this is exactly the REAL qualification role profile.

    ``validator`` is the production ``protected_role.validate``; its refusal is
    propagated, so every production launch check also applies here.
    """
    contract_path, config_path, source_root = Path(contract_path), Path(config_path), Path(source_root)
    config = validate_config(private_json(config_path))
    root = Path(config['root'])
    need(contract_path.is_absolute() and contract_path.parent == root / 'contracts'
         and contract_path.name == config['role_name'] + '.json', 'contract_location_invalid')
    need(source_root == Path(config['source_root']) and Path(module_file or __file__).resolve() == source_root / 'labs/ha/real_instrument.py',
         'frozen_source_required')
    plan = private_json(root / 'reviewed-plan.json', 8 * 1024 * 1024)
    need(isinstance(plan, dict) and plan.get('run_id') == config['run_id'] and plan.get('name') == config['run_name']
         and plan.get('root') == str(root) and isinstance(plan.get('source_files'), dict), 'run_plan_mismatch')
    # Only reviewed, frozen instrumentation source may run in a REAL role.
    for name in ('labs/ha/real_instrument.py', 'labs/ha/real_role_launcher.py'):
        need(plan['source_files'].get(name) == hashlib.sha256((source_root / name).read_bytes()).hexdigest(),
             'instrument_source_not_frozen')
    materialized = private_json(root / 'materialized.json')
    need(materialized.get('launch_schema') == 3 and materialized.get('profile_kind') == 2, 'not_real_ha_profile')
    raw = private_bytes(contract_path, 1048576)
    need(hashlib.sha256(raw).hexdigest() == config['contract_sha256'], 'contract_changed')
    validate = validator or default_validator()
    cfg, environment = validate(contract_path)
    need(cfg.get('schemaVersion') == 3 and cfg.get('runtime_kind') == 'openclaw' and cfg.get('role') == config['role']
         and cfg.get('installation_id') == config['installation_id']
         and cfg.get('control_only') is (config['role'] == 'border'), 'contract_profile_refused')
    need(Path(cfg['home']) == root / 'homes' / config['role_name'] and Path(cfg['source_root']) == source_root,
         'contract_not_run_local')
    if environ is not None:
        # macOS injects exactly this one key into every exec'd process; it is not caller-supplied.
        ambient = {k: v for k, v in dict(environ).items() if k != '__CF_USER_TEXT_ENCODING' or k in environment}
        need(ambient == dict(environment), 'ambient_environment_refused')
    return config, cfg, environment


def build_config(root, role_name, scenario, contract_sha256, installation_id, run_id, run_name, parameters=None):
    role = ROLE_NAMES[role_name]
    value = {'schema_version': SCHEMA, 'class': CLASS, 'run_id': run_id, 'run_name': run_name, 'root': str(root),
             'role_name': role_name, 'role': role, 'installation_id': installation_id,
             'contract_sha256': contract_sha256, 'source_root': str(Path(root) / 'source'), 'scenario': scenario,
             'parameters': dict(SCENARIOS[scenario][2], **(parameters or {})),
             'evidence_dir': str(Path(root) / 'instrument' / scenario)}
    return validate_config(value)


class Clock:
    """Wall/monotonic readings for the admission gate only; zero offset until stepped."""

    def __init__(self, monotonic=time.monotonic, wall=time.time):
        self._m, self._w, self.mono_offset, self.wall_offset = monotonic, wall, 0.0, 0.0

    def monotonic(self):
        return self._m() + self.mono_offset

    def wall(self):
        return self._w() + self.wall_offset


class Instrument:
    def __init__(self, config, *, clock=None, pid=None):
        self.config = validate_config(dict(config))
        self.scenario, self.params = config['scenario'], dict(config['parameters'])
        self.directory = private_directory(config['evidence_dir'])
        self.clock = clock or Clock()
        self.pid, self.sequence, self.patches = pid or os.getpid(), 0, []
        self.config_sha256 = sha(config)
        self.observed_fresh, self.stepped = False, None
        self.reply_fault = None  # unknown-commit-unresolved: decision key whose recovery read must fail
        self._armed = None

    # -- private evidence and one-shot primitives --------------------------------------------------
    def record(self, phase, operation_id=None, **details):
        self.sequence += 1
        body = {'schema_version': SCHEMA, 'class': CLASS, 'run_id': self.config['run_id'], 'role_name': self.config['role_name'],
                'role': self.config['role'], 'scenario': self.scenario, 'phase': phase, 'operation_id': operation_id,
                'pid': self.pid, 'wall_ms': int(time.time() * 1000), 'monotonic_ns': time.monotonic_ns(),
                'config_sha256': self.config_sha256, 'details': details}
        write_new(self.directory / f"{self.config['role_name']}-{self.pid}-{self.sequence:03d}-{phase}.json", body)
        return body

    def armed(self):
        """Operation ID from the new-only arm file, else None (the default)."""
        if self._armed is not None:
            return self._armed
        try:
            arm = private_json(self.directory / 'arm.json', 4096)
        except (OSError, ValueError):
            return None
        if (isinstance(arm, dict) and set(arm) == set(ARM_FIELDS) and arm['schema_version'] == SCHEMA
                and arm['run_id'] == self.config['run_id'] and arm['scenario'] == self.scenario
                and isinstance(arm['operation_id'], str)):
            try:
                self._armed = uuid_text(arm['operation_id'])
            except InstrumentRefused:
                return None
        return self._armed

    def wants(self, operation_id):
        armed = self.armed()
        return armed is not None and armed == operation_id

    def claim(self, operation_id, fault=None):
        """Consume the one-shot claim. False means it was already spent (never fires twice)."""
        try:
            write_new(self.directory / f'claim-{fault or self.scenario}.json',
                      {'class': CLASS, 'scenario': self.scenario, 'operation_id': operation_id,
                       'role_name': self.config['role_name'], 'pid': self.pid, 'wall_ms': int(time.time() * 1000)})
            return True
        except FileExistsError:
            return False

    def fire(self, operation_id, phase, fault=None, **details):
        """Claim, then write pre-fault evidence. True only if the fault may proceed."""
        if not self.wants(operation_id) or not self.claim(operation_id, fault):
            return False
        try:
            self.record(phase, operation_id, **details)
        except OSError:
            return False
        return True

    # -- installation -------------------------------------------------------------------------------
    def _patch(self, owner, name, wrapper):
        self.patches.append((owner, name, owner.__dict__.get(name, None), name in owner.__dict__))
        setattr(owner, name, wrapper)

    def uninstall(self):
        for owner, name, original, own in reversed(self.patches):
            setattr(owner, name, original) if own else delattr(owner, name)
        self.patches = []

    def install(self, *, MemberAdmission=None, MemberAttachments=None, ClusterMemberOperations=None,
                EtcdStore=None, HAError=None, exporter_tls=None, AttachmentChannel=None):
        if self.scenario == 'border-trust-observer':
            self._trust(exporter_tls=exporter_tls, AttachmentChannel=AttachmentChannel)
            self.record('installed', None, patched=[f'{o.__name__}.{n}' for o, n, _, _ in self.patches],
                        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), parameters=self.params)
            return self
        targets = {'clock-wall-step': self._clock, 'clock-monotonic-step': self._clock,
                   'stale-leader-held-claim': self._stale, 'result-reply-loss': self._result,
                   'ack-delivery-loss': self._ack, 'unknown-commit-recovered': self._commit,
                   'unknown-commit-unresolved': self._commit}
        modules = dict(MemberAdmission=MemberAdmission, MemberAttachments=MemberAttachments,
                       ClusterMemberOperations=ClusterMemberOperations, EtcdStore=EtcdStore, HAError=HAError)
        if self.scenario == 'result-and-ack-loss':
            self._result(**modules); self._ack(**modules)
        else:
            targets[self.scenario](**modules)
        self.record('installed', None, patched=[f'{o.__name__}.{n}' for o, n, _, _ in self.patches],
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), parameters=self.params)
        return self

    # -- border-trust-observer ------------------------------------------------------------------------
    def _observe(self, phase, **details):
        """Bounded, never raises into the product: an evidence failure only latches `observer_failed`."""
        try:
            self.observed = getattr(self, 'observed', 0) + 1
            if self.observed > OBSERVER_LIMIT:
                raise OSError('observer_capacity')
            self.record(phase, None, **details)
        except (OSError, ValueError):
            self.observer_failed = True

    def _trust(self, *, exporter_tls, AttachmentChannel):
        need(exporter_tls is not None and AttachmentChannel is not None, 'observer_targets_missing')
        instrument, original_context, original_init = self, exporter_tls._context, AttachmentChannel.__init__

        def context(**options):
            ctx = original_context(**options)
            if options.get('require_peer'):
                def verify(connection, certificate, error, depth, ok):
                    if not ok and depth == 0:
                        try:
                            from OpenSSL import crypto
                            digest = hashlib.sha256(crypto.dump_certificate(crypto.FILETYPE_ASN1, certificate)).hexdigest()
                        except Exception:  # noqa: BLE001 - observation only
                            digest = None
                        instrument._observe('tls-verify-failed', certificate_sha256=digest, verify_error=error, depth=depth)
                    return bool(ok)  # the frozen production decision, unchanged
                ctx.set_verify(ctx.get_verify_mode(), verify)
            return ctx

        def init(channel, *args, **options):
            handlers = options.get('handlers', {})
            if options.get('is_border_side') and 'in2n/hello' in handlers:
                hello = handlers['in2n/hello']
                async def observed(ch, params):
                    try:
                        return await hello(ch, params)
                    except Exception as exc:
                        proof = params.get('proof') if isinstance(params, dict) else None
                        instrument._observe('in2n-hello-refused', params_sha256=sha(params), proof_sha256=sha(proof),
                                            error_code=getattr(exc, 'code', None), error_type=type(exc).__name__,
                                            trusted=getattr(ch, 'trusted', None),
                                            tls_profile=ch.writer.get_extra_info('tls_profile'))
                        raise
                options = dict(options, handlers=dict(handlers, **{'in2n/hello': observed}))
            original_init(channel, *args, **options)

        self._patch(exporter_tls, '_context', context)
        self._patch(AttachmentChannel, '__init__', init)

    # -- (a) clock uncertainty ------------------------------------------------------------------------
    def _clock(self, *, MemberAdmission, **_):
        instrument, clock, original_init, original_begin, original_fresh = self, self.clock, MemberAdmission.__init__, \
            MemberAdmission.begin, MemberAdmission.fresh

        def init(self, home, manifest, member, **options):
            # Production passes no clock; the product constructor is otherwise unchanged.
            options.setdefault('monotonic', clock.monotonic); options.setdefault('wall', clock.wall)
            original_init(self, home, manifest, member, **options)

        def begin(self, context, kind, ordinal, request_digest):
            request, started = original_begin(self, context, kind, ordinal, request_digest)
            matches = (kind == instrument.params['kind'] and ordinal == instrument.params['ordinal']
                       and instrument.wants(context['operation_id']))
            limits = self.manifest.limits
            delta = instrument.params['delta_ms']
            bounded = abs(delta) > limits['clock_uncertainty_ms'] + 100 and (
                instrument.scenario == 'clock-wall-step' or delta < limits['admission_ms'] - 1000)
            if matches and bounded and instrument.fire(context['operation_id'], 'clock-step', kind=kind, ordinal=ordinal,
                    delta_ms=delta, clock='wall' if instrument.scenario == 'clock-wall-step' else 'monotonic',
                    started_monotonic=started[0], started_wall=started[1], limits={k: limits[k] for k in ('admission_ms', 'clock_uncertainty_ms')}):
                if instrument.scenario == 'clock-wall-step':
                    clock.wall_offset += delta / 1000
                else:
                    clock.mono_offset += delta / 1000
                instrument.stepped = context['operation_id']
            return request, started

        def fresh(self, started):
            try:
                return original_fresh(self, started)
            except BaseException as exc:
                if instrument.stepped and not instrument.observed_fresh:
                    instrument.observed_fresh = True
                    instrument.record('gate-refusal', instrument.stepped, code=getattr(exc, 'code', type(exc).__name__))
                raise

        self._patch(MemberAdmission, '__init__', init)
        self._patch(MemberAdmission, 'begin', begin)
        self._patch(MemberAdmission, 'fresh', fresh)

    # -- (d) stale leader at the guard ------------------------------------------------------------------
    def _stale(self, *, MemberAttachments, **_):
        instrument, original = self, MemberAttachments.send_admission

        async def send_admission(self, request):
            proof = await original(self, request)  # the claim is genuinely committed by the sending leader
            operation_id = request.get('operation_id') if isinstance(request, dict) else None
            if (isinstance(request, dict) and request.get('kind') == instrument.params['kind']
                    and request.get('ordinal') == instrument.params['ordinal']
                    and instrument.fire(operation_id, 'claim-held', proof_sha256=sha(proof), hold_ms=instrument.params['hold_ms'],
                                        claim_epoch=proof['payload']['claim']['epoch'],
                                        leader_node_id=proof['payload']['claim']['leader']['node_id'],
                                        commit_revision=proof['payload']['commit_revision'])):
                release = instrument.directory / 'release.json'
                started, reason = time.monotonic(), 'timeout'
                while time.monotonic() - started < instrument.params['hold_ms'] / 1000:
                    if release.exists():
                        reason = 'released'; break
                    await asyncio.sleep(0.1)
                instrument.record('claim-released', operation_id, reason=reason, proof_sha256=sha(proof),
                                  held_ms=int((time.monotonic() - started) * 1000))
            return proof

        self._patch(MemberAttachments, 'send_admission', send_admission)

    # -- (b) lost result / ACK --------------------------------------------------------------------------
    @staticmethod
    def _authenticated(channel):
        return (getattr(channel, 'trusted', False) and getattr(channel, 'strict', False)
                and getattr(channel, 'attestation', None) == 'possession' and not getattr(channel, '_closed', True))

    def _result(self, *, ClusterMemberOperations, **_):
        instrument, original = self, ClusterMemberOperations.member_result

        async def member_result(self, channel, params):
            envelope = await original(self, channel, params)  # production lookup and reply construction
            operation_id = params.get('operation_id') if isinstance(params, dict) else None
            if instrument._authenticated(channel) and instrument.fire(operation_id, 'result-reply-dropped', 'result-reply-loss',
                    envelope_sha256=sha(envelope), peer=getattr(channel, 'protected_peer_binding', None),
                    interception='after production result lookup, before reply write'):
                await channel.close()
                raise ConnectionError('instrumented_result_reply_loss')
            return envelope

        self._patch(ClusterMemberOperations, 'member_result', member_result)

    def _ack(self, *, ClusterMemberOperations, **_):
        instrument, original = self, ClusterMemberOperations.acknowledge

        async def acknowledge(self, channel, params):
            try:
                ack = params['ack']; operation_id = ack['payload']['operation_id']
            except (KeyError, TypeError):
                ack = operation_id = None
            if (ack is not None and instrument._authenticated(channel) and instrument.fire(operation_id, 'ack-delivery-dropped', 'ack-delivery-loss',
                    ack_sha256=sha(ack), peer=getattr(channel, 'protected_peer_binding', None),
                    interception='after authenticated RPC delivery, before production acknowledge/persistence')):
                await channel.close()
                raise ConnectionError('instrumented_ack_delivery_loss')
            return await original(self, channel, params)

        self._patch(ClusterMemberOperations, 'acknowledge', acknowledge)

    # -- (c) unknown consensus commit -------------------------------------------------------------------
    def _commit(self, *, EtcdStore, HAError, **_):
        instrument, original = self, EtcdStore._request

        def decode_key(item):
            return base64.b64decode(item['key']).decode()

        def request(self, path, body, *, read_only=False, login=False):
            if instrument.reply_fault and path == '/v3/kv/range' and read_only and isinstance(body, dict) \
                    and body.get('key') == instrument.reply_fault:
                key, instrument.reply_fault = instrument.reply_fault, None
                instrument.record('recovery-read-refused', None, decision_key_b64=key)
                raise HAError('no_quorum', 503)
            if path != '/v3/kv/txn' or read_only or login or not isinstance(body, dict):
                return original(self, path, body, read_only=read_only, login=login)
            try:
                puts = [decode_key(row['request_put']) for row in body['success']]
                decision_put = next(row['request_put'] for row in body['success']
                                    if decode_key(row['request_put']).split('/', 6)[-2:-1] == ['decisions'])
                decision = json.loads(base64.b64decode(decision_put['value']))
            except (KeyError, StopIteration, ValueError, TypeError):
                return original(self, path, body, read_only=read_only, login=login)
            prefix = '/'.join(puts[0].split('/')[:5]) + '/'
            operation_ids = [k[len(prefix) + 11:] for k in puts if k.startswith(prefix + 'operations/')]
            if (decision.get('action') != 'admit_' + instrument.params['kind'] or len(operation_ids) != 1
                    or not instrument.fire(operation_ids[0], 'commit-reply-drop-armed', action=decision['action'],
                        decision_id=decision['decision_id'], writes_sha256=decision['writes_sha256'],
                        unresolved=instrument.scenario == 'unknown-commit-unresolved')):
                return original(self, path, body, read_only=read_only, login=login)
            reply = original(self, path, body, read_only=read_only, login=login)  # the real etcd commit
            try:
                instrument.record('commit-reply-dropped', operation_ids[0], succeeded=reply.get('succeeded'),
                                  etcd_revision=reply.get('header', {}).get('revision'), decision_id=decision['decision_id'])
            finally:
                if instrument.scenario == 'unknown-commit-unresolved':
                    instrument.reply_fault = decision_put['key']
            raise HAError('commit_unknown', 503)

        self._patch(EtcdStore, '_request', request)


# -- process-boundary helpers used by the launcher ------------------------------------------------------
def load_production():
    from bgp.federation.ha.admission import MemberAdmission
    from bgp.federation.ha.config import HAError
    from bgp.federation import exporter_tls
    from bgp.federation.ha.internal import AttachmentChannel, MemberAttachments
    from bgp.federation.ha.member import ClusterMemberOperations
    from bgp.federation.ha.store import EtcdStore
    return dict(MemberAdmission=MemberAdmission, MemberAttachments=MemberAttachments,
                ClusterMemberOperations=ClusterMemberOperations, EtcdStore=EtcdStore, HAError=HAError,
                exporter_tls=exporter_tls, AttachmentChannel=AttachmentChannel)


def arm(config_path, operation_id):
    config = validate_config(private_json(config_path))
    directory = private_directory(config['evidence_dir'])
    write_new(directory / 'arm.json', {'schema_version': SCHEMA, 'run_id': config['run_id'], 'scenario': config['scenario'],
                                       'operation_id': uuid_text(operation_id), 'armed_ms': int(time.time() * 1000)})
    return {'armed': config['scenario'], 'operation_id': operation_id}


def release(config_path):
    config = validate_config(private_json(config_path))
    write_new(private_directory(config['evidence_dir']) / 'release.json', {'released_ms': int(time.time() * 1000)})
    return {'released': config['scenario']}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='Qualification-only REAL instrumentation helper (arm/release/create-config).')
    commands = parser.add_subparsers(dest='command', required=True)
    sub = commands.add_parser('arm'); sub.add_argument('--config', required=True); sub.add_argument('--operation-id', required=True)
    sub = commands.add_parser('release'); sub.add_argument('--config', required=True)
    sub = commands.add_parser('create-config')
    for name in ('root', 'role-name', 'scenario'): sub.add_argument('--' + name, required=True)
    sub.add_argument('--param', action='append', default=[], help='name=integer or name=text')
    args = parser.parse_args(argv)
    try:
        if args.command == 'arm': result = arm(args.config, args.operation_id)
        elif args.command == 'release': result = release(args.config)
        else:
            root = Path(args.root)
            plan = private_json(root / 'reviewed-plan.json', 8 * 1024 * 1024)
            contract = root / 'contracts' / (args.role_name + '.json')
            raw = private_bytes(contract, 1048576)
            parameters = {}
            for item in args.param:
                key, _, value = item.partition('=')
                parameters[key] = int(value) if re.fullmatch('-?[0-9]+', value) else value
            config = build_config(root, args.role_name, args.scenario, hashlib.sha256(raw).hexdigest(),
                                  json.loads(raw)['installation_id'], plan['run_id'], plan['name'], parameters)
            directory = private_directory(root / 'instrument')
            target = directory / f'{args.role_name}-{args.scenario}.json'
            write_new(target, config)
            result = {'config_file': str(target)}
        print(json.dumps(result))
        return 0
    except (InstrumentRefused, OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'error': 'real_instrument_refused'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
