"""Read-only proof of a completed, denied native NetBox read. Never replay work.

Only trusted operation artifacts are considered. Client/model supplied evidence,
HTTP timeouts and missing results cannot resolve an unknown execution.
"""
import asyncio
import hashlib
import os
from pathlib import Path
import stat

from .protected_contract import (APPROVAL, decode, digest, encode, exact, require,
                                 review_from_payload, sha256, verify)

# This exact managed adapter writes status only after the strict TLS GET has
# returned and never retries/redirects. A schema-shaped file is not enough.
SUPPORTED_HTTP_ADAPTER = 'd8306e420aa6d4198aa1da54c8071bb066bbe9a0fcf415a2ba894b832d282f2c'


def authority_digest(row):
    return sha256({key: row[key] for key in (
        'operation_id', 'owner_subject', 'review', 'review_digest', 'approval',
        'approval_digest', 'approval_id', 'attempt_id', 'started_ms',
        'effect_authorization', 'trust_snapshot')})


class VerifiedFailure:
    """Private verifier result, rechecked inside the store transaction."""
    def __init__(self, root, configuration):
        self.root = root
        self.configuration = configuration
        self.configuration_bytes = encode(configuration)
        self.files = {}
        self.directories = {}
        self.proof = None
        self.proof_bytes = None

    def directory(self, path):
        path = Path(path)
        require(path.is_absolute() and path == path.resolve(), 'failure_evidence_path')
        require(path == self.root or path.is_relative_to(self.root), 'failure_evidence_path')
        for parent in [path, *path.parents]:
            info = parent.lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
                    and not info.st_mode & 0o077, 'failure_evidence_directory')
            self.directories.setdefault(parent, (info.st_dev, info.st_ino, info.st_mode, info.st_uid))
            if parent == self.root:
                break

    def read(self, relative, maximum=65536):
        path = self.root / relative
        self.directory(path.parent)
        require(path == path.resolve(), 'failure_evidence_path')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and info.st_nlink == 1 and not info.st_mode & 0o077
                    and info.st_size <= maximum, 'failure_evidence_file')
            raw = stream.read(maximum + 1)
            require(len(raw) <= maximum, 'failure_evidence_size')
        signature = (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
                     info.st_size, info.st_mtime_ns, hashlib.sha256(raw).hexdigest())
        if relative in self.files:
            require(self.files[relative] == (maximum, signature), 'failure_evidence_changed')
        else:
            self.files[relative] = (maximum, signature)
        return raw

    def document(self, relative, maximum=65536):
        return decode(self.read(relative, maximum), maximum)

    def recheck(self):
        if self.proof_bytes is not None:
            require(encode(self.proof) == self.proof_bytes, 'failure_proof_changed')
        require(encode(self.configuration) == self.configuration_bytes, 'failure_configuration_changed')
        for path, expected in self.directories.items():
            info = path.lstat()
            require(path == path.resolve() and
                    (info.st_dev, info.st_ino, info.st_mode, info.st_uid) == expected,
                    'failure_evidence_changed')
        for relative, (maximum, _) in list(self.files.items()):
            self.read(relative, maximum)
        source = self.root / 'tool/source'
        actual = {str(path.relative_to(self.root)) for path in source.rglob('*')
                  if path.is_file() or path.is_symlink()}
        expected = {name for name in self.files if name.startswith('tool/source/')}
        require(actual == expected, 'failure_source_changed')
        for name in ('tool/mcp-result.json', 'tool/tool-evidence.json'):
            path = self.root / name
            require(not path.exists() and not path.is_symlink(), 'failure_success_evidence_present')


async def inspect_containers(runtime, names):
    """The only subprocess allowed by recovery: inspect exact owned containers."""
    command = [runtime['docker'], '--host', runtime['docker_host'], '--config',
               str(Path(runtime['state_dir']) / '.docker-client'), 'inspect', *names]
    process = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        env={'PATH': '/usr/bin:/bin'}, limit=262144)
    async def bounded_read():
        try:
            raw = await process.stdout.readexactly(262145)
        except asyncio.IncompleteReadError as exc:
            raw = exc.partial
        require(len(raw) <= 262144, 'failure_container_inspection')
        await process.wait()
        return raw
    try:
        raw = await asyncio.wait_for(bounded_read(), 10)
        require(process.returncode == 0 and len(raw) <= 262144, 'failure_container_inspection')
        # Docker timestamps may contain strings but no floating-point data is
        # needed; use its ordinary JSON decoder, then retain a small projection.
        import json
        return json.loads(raw)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def verify_known_netbox_failure(row, configuration, *, inspector=None):
    require(row['side'] == 'member' and row['state'] == 'outcome_unknown'
            and row['effect_claimed'] == 1 and row['effect_finished'] == 0
            and row['attempt_id'] and all(row[key] is None for key in
                ('receipt', 'receipt_digest', 'ack', 'executor_result', 'tool_evidence')),
            'failure_state_not_recoverable')
    approval = verify(row['approval'], row['trust_snapshot']['border'], APPROVAL)
    require(approval['operation_id'] == row['operation_id']
            and approval['approval_id'] == row['approval_id']
            and digest(APPROVAL, approval) == row['approval_digest']
            and review_from_payload(approval) == row['review']
            and approval['review_sha256'] == row['review_digest'], 'failure_authority_mismatch')
    require(configuration['role'] == 'member' and configuration['identity'] == approval['member']
            and configuration['border'] == approval['border'], 'failure_authority_mismatch')
    authorization = {'operation_id': row['operation_id'], 'approval_digest': row['approval_digest'],
                     'attempt_id': row['attempt_id'], 'tool_call_digest': sha256(approval['tool_call']),
                     'authorized': True}
    require(row['effect_authorization'] == authorization, 'failure_authority_mismatch')
    packet = configuration['runtime']
    exact(packet, 'schemaVersion profiles')
    require(type(packet['schemaVersion']) is int and packet['schemaVersion'] == 1
            and isinstance(packet['profiles'], list) and 1 <= len(packet['profiles']) <= 16,
            'failure_profile_invalid')
    selected = [item for item in packet['profiles'] if item.get('tool_call') == approval['tool_call']
                and item.get('runtime', {}).get('model_profile') == approval['model_profile']
                and item.get('model_profile_id') == approval['model_profile']['profile_id']]
    require(len(selected) == 1, 'failure_profile_mismatch')
    runtime = selected[0]['runtime']
    require(runtime.get('mcp', {}).get('kind') == 'netbox'
            and approval['tool_call']['tool'] == 'netbox_get_object_by_id', 'failure_tool_not_supported')
    require(runtime['mcp']['source_sha256'].get('src/netbox_mcp_server/netclaw_http.py') == SUPPORTED_HTTP_ADAPTER,
            'failure_http_implementation_unsupported')
    # These historical adapters deliberately remain unchanged by this feature.
    from .protected_docker import validate_execution_bindings
    validate_execution_bindings(runtime, approval)
    state = Path(runtime['state_dir'])
    root = state / row['operation_id']
    require(state.is_absolute() and state == state.resolve() and root == root.resolve(), 'failure_evidence_path')
    info = state.stat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077,
            'failure_evidence_directory')
    evidence = VerifiedFailure(root, configuration)
    evidence.directory(root)
    mcp = runtime['mcp']
    for relative, expected in mcp['source_sha256'].items():
        raw = evidence.read('tool/source/' + relative, 16 * 1024 * 1024)
        require(hashlib.sha256(raw).hexdigest() == expected, 'failure_source_changed')
    call = evidence.document('tool/mcp-call.json')
    exact(call, 'tool arguments dispatched_at_ms')
    require(call['tool'] == mcp['tool'] and encode(call['arguments']) == encode(approval['tool_call']['arguments']), 'failure_call_mismatch')
    schema = evidence.document('tool/mcp-schema.json', 1024 * 1024)
    exact(schema, 'tool inputSchema')
    require(schema['tool'] == mcp['tool'] and sha256(schema['inputSchema']) == mcp['input_schema_sha256'], 'failure_schema_mismatch')
    arguments = call['arguments']
    endpoint = {'dcim.device': 'dcim/devices', 'ipam.prefix': 'ipam/prefixes'}.get(arguments['object_type'])
    require(endpoint is not None, 'failure_tool_not_supported')
    policy = {'schemaVersion': 1, 'url': mcp['origin'] + '/api/' + endpoint + '/' + str(arguments['object_id']) + '/',
              'params': {'fields': ','.join(arguments['fields'])}}
    require(encode(evidence.document('tool/http-policy.json', 16384)) == encode(policy), 'failure_policy_mismatch')
    http = evidence.document('tool/netbox-http-receipt.json', 16384)
    exact(http, 'schemaVersion method url params http_requests state started_at_ms captured_at_ms status error_code')
    require(type(http['schemaVersion']) is int and http['schemaVersion'] == 1
            and http['method'] == 'GET' and http['url'] == policy['url'] and http['params'] == policy['params']
            and type(http['http_requests']) is int and http['http_requests'] == 1
            and http['state'] == 'failed' and type(http['status']) is int and http['status'] in (401, 403)
            and http['error_code'] == 'netbox_read_failed_or_unknown', 'failure_http_not_definitive')
    times = [approval['issued_at_ms'], row['started_ms'], call['dispatched_at_ms'],
             http['started_at_ms'], http['captured_at_ms'], approval['limits']['expires_at_ms']]
    require(all(type(value) is int for value in times) and times == sorted(times)
            and times[-2] < times[-1], 'failure_time_mismatch')
    prefix = 'netclaw-r02-' + hashlib.sha256(row['operation_id'].encode()).hexdigest()[:20]
    images = {prefix + '-agent': runtime['agent_image'], prefix + '-relay': runtime['relay_image'],
              prefix + '-guard': runtime['guard']['image']}
    cleanup = evidence.document('cleanup.json')
    exact(cleanup, 'owned unresolved')
    require(cleanup['unresolved'] == [] and isinstance(cleanup['owned'], list)
            and len(cleanup['owned']) == 3 and set(cleanup['owned']) == set(images), 'failure_cleanup_incomplete')
    containment = evidence.document('containment.json')
    require(containment.get('image') == runtime['agent_image'] and containment.get('network') == prefix + '-net'
            and containment.get('read_only') is True and containment.get('no_new_privileges') is True
            and containment.get('user') == str(os.getuid())
            and containment.get('capabilities_dropped') == ['ALL']
            and containment.get('mount_destinations') == ['/run/netclaw'], 'failure_containment_mismatch')
    evidence.recheck()
    inspected = await (inspector or inspect_containers)(runtime, sorted(images))
    require(isinstance(inspected, list) and len(inspected) == 3, 'failure_container_inspection')
    seen = set()
    for container in inspected:
        name = container.get('Name', '').removeprefix('/')
        status = container.get('State', {})
        require(name in images and name not in seen and container.get('Image') == images[name]
                and status.get('Running') is False and status.get('Restarting') is False
                and type(status.get('Pid')) is int and status['Pid'] == 0
                and status.get('Status') in ('exited', 'dead')
                and container.get('Config', {}).get('Labels', {}).get('netclaw.spec') == '171',
                'failure_runtime_not_stopped')
        seen.add(name)
    evidence.recheck()
    evidence.proof = {'schemaVersion': 1, 'kind': 'native_netbox_http_authorization_response',
        'operation_id': row['operation_id'], 'attempt_id': row['attempt_id'], 'approval_sha256': row['approval_digest'],
        'review_sha256': row['review_digest'], 'authority_sha256': authority_digest(row),
        'source_profile_sha256': sha256(configuration), 'original_revision': row['revision'],
        'original_error_code': row['error_code'], 'http_status': http['status'], 'http_requests': 1, 'mcp_calls': 1,
        'artifact_sha256': {name: signature[-1] for name, (_, signature) in sorted(evidence.files.items())},
        'stopped_owned_containers': sorted(images)}
    evidence.proof_bytes = encode(evidence.proof)
    return evidence
