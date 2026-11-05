// Enrollment authority is returned only once as a QR matrix. Retained UI state
// is a non-secret nonce; loading/recovering can only read that original offer.
export const ENROLLMENT_ROUTE = '/api/hud/mobile/enrollment';
export const enrollmentNonce = value => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const exact = (value, required, optional = []) => object(value) && required.every(k => Object.hasOwn(value, k)) && Object.keys(value).every(k => [...required, ...optional].includes(k));
export function enrollmentInfo(value, installationId) {
  if (!exact(value, ['schema','installation_id','available'], ['reason','endpoint','mode','enrollment_ttl_seconds']) || value.schema !== 1 || value.installation_id !== installationId || typeof value.available !== 'boolean') throw Error('Enrollment response does not match the selected Border.');
  if (!value.available) {
    if (typeof value.reason !== 'string' || !/^[a-z][a-z0-9_]{0,79}$/.test(value.reason) || value.endpoint != null) throw Error('Enrollment readiness is invalid.');
    return value;
  }
  const e = value.endpoint;
  if (!exact(e, ['border_host','border_port','claw_domain','ws_path']) || typeof e.claw_domain !== 'string' || !/^(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/.test(e.claw_domain) || e.claw_domain.includes('..') || e.border_host !== e.claw_domain || !Number.isInteger(e.border_port) || e.border_port < 1 || e.border_port > 65535 || !['/','/mobile/ws'].includes(e.ws_path) || !['protected','legacy'].includes(value.mode) || value.enrollment_ttl_seconds !== 120) throw Error('Enrollment destination is invalid.');
  return value;
}
export function enrollmentRecord(value, installationId, nonce, allowMatrix = false) {
  if (!exact(value, ['schema','installation_id','client_nonce','status','expires_ms'], ['member_id', ...(allowMatrix ? ['qr_matrix'] : [])]) || value.schema !== 1 || value.installation_id !== installationId || !enrollmentNonce(nonce) || value.client_nonce !== nonce || !['absent','issued','consumed','expired','replaced'].includes(value.status) || !(value.expires_ms === null && value.status === 'absent' || Number.isSafeInteger(value.expires_ms) && value.expires_ms > 0) || value.member_id !== undefined && (typeof value.member_id !== 'string' || value.member_id.length > 200 || /[\u0000-\u001f\u007f]/.test(value.member_id))) throw Error('Enrollment status does not match the original request.');
  if (value.qr_matrix !== undefined) {
    const matrix = value.qr_matrix, n = matrix?.length;
    if (value.status !== 'issued' || !Array.isArray(matrix) || n < 21 || n > 177 || (n - 21) % 4 !== 0 || matrix.some(row => !Array.isArray(row) || row.length !== n || row.some(bit => typeof bit !== 'boolean'))) throw Error('Enrollment QR is invalid.');
  }
  return value;
}
export function drawEnrollmentQr(canvas, matrix) {
  const scale = Math.max(2, Math.floor(360 / (matrix.length + 8))), width = (matrix.length + 8) * scale;
  canvas.width = canvas.height = width;
  const context = canvas.getContext('2d');
  if (!context) throw Error('QR drawing is unavailable.');
  context.fillStyle = '#fff'; context.fillRect(0, 0, width, width);
  context.fillStyle = '#000';
  matrix.forEach((row, y) => row.forEach((bit, x) => { if (bit) context.fillRect((x + 4) * scale, (y + 4) * scale, scale, scale); }));
}
export const enrollmentMessage = record => !record ? 'Generate a code, then open NetClaw Mobile and choose Scan QR code.' : ({
  unknown: 'The request may have been accepted. Check its status before generating another code.',
  issued: 'Scan this code with NetClaw Mobile. A code can enroll one device.',
  consumed: 'Device enrolled. Open NetClaw Mobile to connect with its saved key.',
  expired: 'This code expired. Generate a new code when your phone is ready.',
  replaced: 'This code was replaced. It can no longer enroll a device.',
  absent: 'No offer was recorded for this request. You can generate a new code.',
}[record.status] || 'Enrollment status is unavailable.');
