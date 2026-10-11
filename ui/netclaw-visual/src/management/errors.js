const explanations = Object.freeze({
  UNAUTHENTICATED: 'Authentication is required.', DENIED: 'The operation is outside the current authority.',
  INCOMPATIBLE: 'This installation needs a compatible management component and stable installation identity.',
  IDENTITY_CHANGED: 'Installation identity changed. Disconnect and review the connection again.',
  UNSUPPORTED: 'This action is not supported by the selected runtime.', UNQUALIFIED: 'This action has not been qualified for the selected runtime.',
  STALE_REVISION: 'Configuration changed. Refresh and prepare a new proposal.', NONCE_CONFLICT: 'This nonce already identifies different input.',
  EXPIRED: 'This request or grant expired.', AUDIT_UNAVAILABLE: 'Required audit recording is unavailable. No new action was dispatched.',
  BUSY: 'The resource is owned by another operation.', UNKNOWN_OUTCOME: 'The outcome is unknown. Reconcile existing work; do not resubmit it.',
  INVALID_INPUT: 'Input does not match the supported contract.', SOURCE_UNAVAILABLE: 'The selected source is unavailable.',
});
export class ManagementError extends Error {
  constructor(code) { super(explanations[code] || explanations.SOURCE_UNAVAILABLE); this.code = Object.hasOwn(explanations, code) ? code : 'SOURCE_UNAVAILABLE'; }
}
export function fail(code) { throw new ManagementError(code); }
export function safeError(error) { const value = error instanceof ManagementError ? error : new ManagementError('SOURCE_UNAVAILABLE'); return { code: value.code, message: value.message }; }
export function invariant(condition, code = 'INVALID_INPUT') { if (!condition) fail(code); }
