"""Strict, domain-separated signed contracts for opt-in protected execution (171)."""
import base64
import hashlib
import json
import ipaddress
import re
import uuid

APPROVAL = 'netclaw.execution.approval.v1'
RESULT = 'netclaw.execution.result.v1'
ACK = 'netclaw.execution.ack.v1'
MAX_ENVELOPE = 1024 * 1024
MAX_OUTPUT = 512 * 1024
MAX_ARGUMENTS = 64 * 1024
HEX = re.compile(r'^[0-9a-f]{64}$')


class ProtectedError(ValueError):
    """Public errors contain a bounded code, never sensitive exception text."""
    def __init__(self, code='invalid_contract', status=400):
        self.code, self.status = code, status
        super().__init__(code)


class ProtectedOutcomeUnknown(ProtectedError):
    """A guarded provider/integration may have accepted a dispatched request."""
    def __init__(self, code='executor_outcome_unknown'):
        super().__init__(code, 409)


def require(condition, code='invalid_contract', status=400):
    if not condition:
        raise ProtectedError(code, status)


def _json_value(value, depth=0):
    require(depth <= 32)
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(abs(value) <= 2**53 - 1)
    elif isinstance(value, str):
        try:
            value.encode('utf-8', errors='strict')
        except UnicodeError:
            raise ProtectedError() from None
    elif isinstance(value, list):
        require(len(value) <= 10000)
        for item in value:
            _json_value(item, depth + 1)
    elif isinstance(value, dict):
        require(len(value) <= 10000)
        for key, item in value.items():
            require(isinstance(key, str) and key.isascii() and len(key) <= 200)
            _json_value(item, depth + 1)
    else:
        raise ProtectedError()


def encode(value):
    _json_value(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def decode(raw, limit=MAX_ENVELOPE):
    if isinstance(raw, str):
        raw = raw.encode('utf-8', errors='strict')
    require(isinstance(raw, bytes) and len(raw) <= limit, 'oversized_or_invalid_json')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ProtectedError()))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ProtectedError):
            raise
        raise ProtectedError('invalid_json') from None
    _json_value(value)
    return value


def sha256(value):
    return hashlib.sha256(encode(value)).hexdigest()


def exact(value, fields):
    require(isinstance(value, dict) and set(value) == set(fields.split()))


def ident(value):
    require(isinstance(value, str) and 0 < len(value) <= 200 and not any(ord(c) < 32 for c in value))


def digest_field(value):
    require(isinstance(value, str) and HEX.fullmatch(value) is not None)


def uuid_field(value):
    ident(value)
    try:
        require(str(uuid.UUID(value)) == value)
    except (ValueError, AttributeError):
        raise ProtectedError() from None


def timestamp(value):
    require(type(value) is int and 0 <= value <= 2**53 - 1)


def validate_principal(value):
    exact(value, 'issuer subject display_name roles')
    require(value['issuer'] == 'local' and value['roles'] == ['owner'] or
            value['issuer'] == 'open-lab' and value['roles'] == ['lab-operator']
            and value['display_name'] == 'Unauthenticated lab operator')
    uuid_field(value['subject'])
    ident(value['display_name'])


def validate_binding(value, role):
    fields = 'installation_id identity key_id authority_generation' if role == 'border' else 'installation_id member_id key_id enrollment_generation'
    exact(value, fields)
    for key in fields.split():
        ident(value[key])
    digest_field(value['key_id'])


def validate_model(value):
    exact(value, 'profile_id profile_revision runtime_kind runtime_version provider model guard_policy_sha256')
    for item in value.values():
        ident(item)
    digest_field(value['guard_policy_sha256'])


def validate_tool(value):
    exact(value, 'tool tool_schema_sha256 arguments arguments_sha256 device_ref inventory_revision endpoint_sha256')
    for key in ('tool', 'device_ref', 'inventory_revision'):
        ident(value[key])
    for key in ('tool_schema_sha256', 'arguments_sha256', 'endpoint_sha256'):
        digest_field(value[key])
    require(len(encode(value['arguments'])) <= MAX_ARGUMENTS, 'arguments_too_large')
    require(sha256(value['arguments']) == value['arguments_sha256'], 'arguments_digest_mismatch')
    validate_tool_arguments(value['tool'], value['arguments'])


NETBOX_FIELDS = {
    'dcim.device': ['id', 'name', 'status', 'site', 'device_type', 'last_updated'],
    'ipam.prefix': ['id', 'prefix', 'status', 'vrf', 'last_updated'],
}


def validate_tool_arguments(tool, args):
    if tool == 'pyats_run_show_command':
        exact(args, 'device_name command timeout retries')
        ident(args['device_name'])
        require(args['command'] == 'show version' and type(args['retries']) is int and args['retries'] == 1, 'unsupported_tool_policy')
        require(type(args['timeout']) is int and 1 <= args['timeout'] <= 300, 'unsupported_tool_policy')
    elif tool == 'netbox_get_object_by_id':
        exact(args, 'object_type object_id fields brief')
        require(isinstance(args['object_type'], str) and args['object_type'] in NETBOX_FIELDS, 'unsupported_object_type')
        require(type(args['object_id']) is int and 0 < args['object_id'] < 2**53, 'invalid_object_id')
        require(args['fields'] == NETBOX_FIELDS[args['object_type']] and args['brief'] is False, 'unsupported_netbox_fields')
    elif tool == 'subnet_calculator':
        exact(args, 'cidr')
        require(isinstance(args['cidr'], str), 'invalid_subnet')
        try:
            network = ipaddress.IPv4Network(args['cidr'], strict=True)
            require(str(network) == args['cidr'] and 24 <= network.prefixlen <= 30, 'unsupported_subnet')
            require(int(network.network_address) >= network.num_addresses and int(network.broadcast_address) + network.num_addresses < 2**32, 'subnet_boundary_refused')
        except (ValueError, TypeError):
            raise ProtectedError('unsupported_subnet') from None
    else:
        raise ProtectedError('unsupported_tool')


def validate_limits(value):
    exact(value, 'expires_at_ms inference_timeout_ms tool_timeout_ms max_inference_calls max_tool_calls max_output_bytes')
    for item in value.values():
        timestamp(item)
    require(value['max_inference_calls'] == 2 and value['max_tool_calls'] == 1)
    require(0 < value['max_output_bytes'] <= MAX_OUTPUT)
    require(0 < value['inference_timeout_ms'] <= 600000 and 0 < value['tool_timeout_ms'] <= 300000)


def validate_catalog_entry(entry):
    """Validate one member's public catalog without loading an execution runtime.

    A tool name plus its complete arguments is the browser's selection identity.
    Even identical duplicates are refused rather than relying on list order.
    Catalog limits omit expiry; preparation alone creates the expiring review.
    """
    require(len(encode(entry)) <= MAX_ENVELOPE, 'catalog_too_large', 413)
    exact(entry, 'member model_profiles tools')
    validate_binding(entry['member'], 'member')
    require(isinstance(entry['model_profiles'], list) and isinstance(entry['tools'], list))
    models, calls = set(), set()
    for model in entry['model_profiles']:
        validate_model(model)
        require(model['profile_id'] not in models, 'duplicate_model_profile', 409)
        models.add(model['profile_id'])
    for tool in entry['tools']:
        exact(tool, 'tool tool_schema_sha256 arguments arguments_sha256 device_ref inventory_revision endpoint_sha256 limits')
        validate_tool({key: value for key, value in tool.items() if key != 'limits'})
        identity = (tool['tool'], encode(tool['arguments']))
        require(identity not in calls, 'duplicate_tool_profile', 409)
        calls.add(identity)
        exact(tool['limits'], 'inference_timeout_ms tool_timeout_ms max_inference_calls max_tool_calls max_output_bytes')
        validate_limits(dict(tool['limits'], expires_at_ms=1))


def review_from_payload(payload):
    return {key: payload[key] for key in ('principal', 'border', 'member', 'model_profile', 'tool_call', 'limits', 'change_request_ref')}


def validate_review(review):
    exact(review, 'principal border member model_profile tool_call limits change_request_ref')
    validate_principal(review['principal'])
    validate_binding(review['border'], 'border')
    if review['principal']['issuer'] == 'open-lab':
        require(review['principal']['subject'] == str(uuid.uuid5(uuid.UUID(review['border']['installation_id']), 'netclaw.open-lab.operator')), 'lab_principal_mismatch')
    validate_binding(review['member'], 'member')
    validate_model(review['model_profile'])
    validate_tool(review['tool_call'])
    validate_limits(review['limits'])
    require(review['change_request_ref'] is None, 'writes_not_supported')


def validate_payload(schema, p):
    if schema == APPROVAL:
        exact(p, 'approval_id operation_id nonce issued_at_ms principal border member model_profile tool_call limits change_request_ref review_sha256')
        uuid_field(p['approval_id']); uuid_field(p['operation_id'])
        require(isinstance(p['nonce'], str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', p['nonce']) is not None)
        timestamp(p['issued_at_ms'])
        validate_review(review_from_payload(p))
        digest_field(p['review_sha256'])
        require(sha256(review_from_payload(p)) == p['review_sha256'], 'review_digest_mismatch')
        require(p['issued_at_ms'] < p['limits']['expires_at_ms'])
    elif schema == RESULT:
        exact(p, 'receipt_id operation_id approval_id approval_sha256 attempt_id principal border member model_profile tool_call_sha256 started_at_ms finished_at_ms outcome effect_status output output_sha256 tool_evidence_sha256 usage audit_refs error_code')
        for key in ('receipt_id', 'operation_id', 'approval_id', 'attempt_id'):
            uuid_field(p[key])
        for key in ('approval_sha256', 'tool_call_sha256', 'output_sha256', 'tool_evidence_sha256'):
            digest_field(p[key])
        validate_principal(p['principal']); validate_binding(p['border'], 'border'); validate_binding(p['member'], 'member'); validate_model(p['model_profile'])
        timestamp(p['started_at_ms']); timestamp(p['finished_at_ms'])
        require(p['finished_at_ms'] >= p['started_at_ms'])
        require(p['outcome'] in ('succeeded', 'refused', 'failed') and p['effect_status'] in ('not_started', 'finished'))
        require(p['outcome'] != 'succeeded' or p['effect_status'] == 'finished')
        require(len(encode(p['output'])) <= MAX_OUTPUT, 'output_too_large')
        require(sha256(p['output']) == p['output_sha256'], 'output_digest_mismatch')
        require(isinstance(p['usage'], dict) and isinstance(p['audit_refs'], dict))
        if p['error_code'] is not None:
            require(isinstance(p['error_code'], str) and re.fullmatch('[a-z0-9_]{1,80}', p['error_code']) is not None)
    elif schema == ACK:
        exact(p, 'ack_id operation_id approval_id attempt_id receipt_id receipt_sha256 border member accepted_at_ms audit_ref')
        for key in ('ack_id', 'operation_id', 'approval_id', 'attempt_id', 'receipt_id'):
            uuid_field(p[key])
        digest_field(p['receipt_sha256'])
        validate_binding(p['border'], 'border'); validate_binding(p['member'], 'member')
        timestamp(p['accepted_at_ms']); ident(p['audit_ref'])
    else:
        raise ProtectedError('unsupported_schema')


def canonical_bytes(schema, payload):
    validate_payload(schema, payload)
    return encode({'schema': schema, 'payload': payload})


def digest(schema, payload):
    return hashlib.sha256(canonical_bytes(schema, payload)).hexdigest()


def key_id(cert_pem):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    return hashlib.sha256(cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()


def sign(schema, payload, key_pem):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    body = canonical_bytes(schema, payload)
    key = serialization.load_pem_private_key(key_pem.encode(), password=None)
    require(isinstance(key, ec.EllipticCurvePrivateKey) and isinstance(key.curve, ec.SECP256R1))
    kid = hashlib.sha256(key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()
    signature = key.sign(b'netclaw.r02/' + schema.encode('ascii') + b'\0' + body, ec.ECDSA(hashes.SHA256()))
    result = {'schema': schema, 'payload': payload, 'signature': {'algorithm': 'ecdsa-p256-sha256', 'key_id': kid, 'value': base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')}}
    require(len(encode(result)) <= MAX_ENVELOPE, 'envelope_too_large')
    return result


def verify(envelope, cert_pem, expected_schema=None):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    if isinstance(envelope, (bytes, str)):
        envelope = decode(envelope)
    require(len(encode(envelope)) <= MAX_ENVELOPE, 'envelope_too_large')
    exact(envelope, 'schema payload signature')
    schema, signature = envelope['schema'], envelope['signature']
    if expected_schema:
        require(schema == expected_schema, 'wrong_schema')
    body = canonical_bytes(schema, envelope['payload'])
    exact(signature, 'algorithm key_id value')
    require(signature['algorithm'] == 'ecdsa-p256-sha256', 'unsupported_algorithm')
    digest_field(signature['key_id'])
    require(signature['key_id'] == key_id(cert_pem), 'untrusted_key')
    require(isinstance(signature['value'], str) and re.fullmatch(r'[A-Za-z0-9_-]{8,200}', signature['value']) is not None)
    try:
        raw = base64.urlsafe_b64decode(signature['value'] + '=' * (-len(signature['value']) % 4))
        require(base64.urlsafe_b64encode(raw).rstrip(b'=').decode() == signature['value'])
        public = x509.load_pem_x509_certificate(cert_pem.encode()).public_key()
        require(isinstance(public, ec.EllipticCurvePublicKey) and isinstance(public.curve, ec.SECP256R1))
        public.verify(raw, b'netclaw.r02/' + schema.encode('ascii') + b'\0' + body, ec.ECDSA(hashes.SHA256()))
    except Exception as exc:
        if isinstance(exc, ProtectedError):
            raise
        raise ProtectedError('invalid_signature') from None
    return envelope['payload']
