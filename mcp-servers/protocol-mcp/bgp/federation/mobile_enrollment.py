"""Spec175: finite native device offers; no generic daemon or user authority."""
import hashlib
import json
import re
import secrets
import time
import uuid
from urllib.parse import urlsplit

from .protected_contract import exact, require, uuid_field, ProtectedError

TTL_SECONDS = 120
WS_PATH = '/mobile/ws'
MOBILE_METHODS = tuple('n2n/edge/operations/' + action for action in
                       ('catalog', 'prepare', 'status', 'decision', 'reconcile'))


def endpoint(service):
    """Only a currently listening transport can be advertised or issue an offer."""
    status = getattr(service, 'edge_status', {})
    require(service.risk.is_border(), 'mobile_border_required', 503)
    require(status.get('state') == 'listening', 'mobile_listener_unavailable', 503)
    if service.protected_enabled:
        origin = status.get('public_origin', '')
        parsed = urlsplit(origin)
        require(parsed.scheme == 'https' and origin == 'https://' + parsed.netloc
                and parsed.hostname and not parsed.username and not parsed.password
                and status.get('host') == '127.0.0.1' and status.get('path') == WS_PATH,
                'mobile_transport_unavailable', 503)
        host, port, ws_path = parsed.hostname, parsed.port or 443, WS_PATH
    else:
        host, port, ws_path = status.get('domain'), status.get('port'), '/'
    require(isinstance(host, str) and len(host) <= 253 and host == host.lower()
            and re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host) is not None
            and '..' not in host and type(port) is int and 1 <= port <= 65535,
            'mobile_endpoint_unavailable', 503)
    return {'border_host': host, 'border_port': port, 'claw_domain': host, 'ws_path': ws_path}


def https_origin(point):
    return 'https://' + point['claw_domain'] + (':' + str(point['border_port']) if point['border_port'] != 443 else '')


class MobileEnrollment:
    def __init__(self, service, *, clock_ms=None, matrix_factory=None):
        self.service = service
        self.now = clock_ms or (lambda: int(time.time() * 1000))
        self.matrix_factory = matrix_factory or self._matrix

    @property
    def installation(self):
        value = self.service.runtime.installation
        uuid_field(value)
        return value

    def _binding(self, params, fields):
        exact(params, fields)
        require(params['installation_id'] == self.installation, 'installation_changed', 409)

    def info(self, params):
        self._binding(params, 'installation_id')
        result = {'schema': 1, 'installation_id': self.installation,
                  'mode': 'protected' if self.service.protected_enabled else 'legacy',
                  'enrollment_ttl_seconds': TTL_SECONDS}
        try:
            point = endpoint(self.service)
            if self.service.protected_enabled:
                require(self.service.protected_operations is not None, 'protected_operations_unavailable', 503)
            return dict(result, available=True, endpoint=point)
        except ProtectedError as exc:
            return dict(result, available=False, endpoint=None, reason=exc.code)

    @staticmethod
    def _matrix(payload):
        # qrcode is an existing protocol component dependency. No remote renderer.
        import qrcode
        qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(json.dumps(payload, separators=(',', ':'), sort_keys=True))
        qr.make(fit=True)
        matrix = qr.get_matrix()
        require(21 <= len(matrix) <= 177 and all(len(row) == len(matrix) for row in matrix),
                'mobile_qr_unavailable', 503)
        return [[bool(cell) for cell in row] for row in matrix]

    def _row(self, conn, nonce):
        return conn.execute('''SELECT o.*, t.spent_at, t.spent_by_member_id
          FROM mobile_enrollment_offer o JOIN enrollment_token t USING(token_hash)
          WHERE o.installation_id=? AND o.client_nonce=?''', (self.installation, nonce)).fetchone()

    def _status(self, row, nonce):
        value = {'schema': 1, 'installation_id': self.installation, 'client_nonce': nonce,
                 'status': 'absent', 'expires_ms': None}
        if row:
            state = ('replaced' if row['replaced_ms'] is not None else
                     'consumed' if row['spent_at'] is not None else
                     'expired' if not row['issued_ms'] <= self.now() < row['expires_ms'] else 'issued')
            value.update(status=state, expires_ms=row['expires_ms'])
            if state == 'consumed' and row['spent_by_member_id']:
                value['member_id'] = row['spent_by_member_id']
        return value

    def status(self, params):
        self._binding(params, 'installation_id client_nonce')
        uuid_field(params['client_nonce'])
        return self._status(self._row(self.service.manager._conn, params['client_nonce']), params['client_nonce'])

    def issue(self, params):
        self._binding(params, 'installation_id client_nonce replace_client_nonce')
        nonce, replace = params['client_nonce'], params['replace_client_nonce']
        uuid_field(nonce)
        if replace is not None:
            uuid_field(replace)
            require(replace != nonce, 'mobile_replacement_invalid', 409)
        conn = self.service.manager._conn
        # Repeated requests only observe retained state, including after listener loss.
        old = self._row(conn, nonce)
        if old:
            return self._status(old, nonce)
        readiness = self.info({'installation_id': self.installation})
        require(readiness['available'], readiness.get('reason', 'mobile_listener_unavailable'), 503)
        point = readiness['endpoint']
        raw = 'in2n_' + secrets.token_urlsafe(24)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        matrix = self.matrix_factory(dict(point, installation_id=self.installation, enrollment_token=raw))
        now, expires = self.now(), self.now() + TTL_SECONDS * 1000
        conn.execute('BEGIN IMMEDIATE')
        try:
            old = self._row(conn, nonce)
            if old:
                conn.rollback()
                return self._status(old, nonce)
            active = conn.execute('''SELECT o.client_nonce FROM mobile_enrollment_offer o
              JOIN enrollment_token t USING(token_hash) WHERE o.installation_id=?
              AND o.replaced_ms IS NULL AND t.spent_at IS NULL AND o.issued_ms<=? AND o.expires_ms>?''',
              (self.installation, now, now)).fetchall()
            require(len(active) <= 1, 'mobile_offer_state_conflict', 409)
            if active:
                require(replace == active[0]['client_nonce'], 'mobile_offer_outstanding', 409)
                conn.execute('UPDATE mobile_enrollment_offer SET replaced_ms=? WHERE installation_id=? AND client_nonce=?',
                             (now, self.installation, replace))
            elif replace is not None:
                require(self._row(conn, replace) is not None, 'mobile_replacement_unknown', 409)
            issued_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now / 1000))
            expires_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(expires / 1000))
            conn.execute('INSERT INTO enrollment_token(token_hash,label,issued_at,expires_at) VALUES(?,?,?,?)',
                         (hashed, 'mobile-device', issued_at, expires_at))
            conn.execute('INSERT INTO mobile_enrollment_offer(installation_id,client_nonce,token_hash,endpoint_json,issued_ms,expires_ms,replaced_ms) VALUES(?,?,?,?,?,?,NULL)',
                         (self.installation, nonce, hashed, json.dumps(point, sort_keys=True), now, expires))
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        # Audit only bounded public references. Never log the raw token or QR matrix.
        self.service.audit.record(direction='local', peer_identity=self.installation,
            target_type='mobile_enrollment', target_name=nonce, request_id=nonce,
            decision='issued', outcome='success', channel_kind='in2n', event='enrollment')
        return dict(self._status(self._row(conn, nonce), nonce), qr_matrix=matrix)


def protected_ws_request_allowed(ws, origin):
    """Only the exact trusted TLS proxy ingress may reach the clear loopback hop."""
    try:
        address = ws.remote_address
        if not address or address[0] not in ('127.0.0.1', '::1', '::ffff:127.0.0.1'):
            return False
        parsed = urlsplit(origin)
        if parsed.scheme != 'https' or origin != 'https://' + parsed.netloc or not parsed.hostname or parsed.username or parsed.password:
            return False
        request = getattr(ws, 'request', None)
        path = request.path if request is not None else ws.path
        headers = request.headers if request is not None else ws.request_headers
        if path != WS_PATH or headers.get_all('Host') != [parsed.netloc]:
            return False
        return headers.get_all('Origin') in ([], [origin])
    except Exception:
        return False
