import { fail, invariant } from './errors.js';
export function freezeAuthority(value) {
  return Object.freeze({ ...value, ...Object.fromEntries(['actions', 'targets', 'disclosure'].filter(k => value[k]).map(k => [k, Object.freeze([...value[k]])])) });
}
export function authorize(principal, action, targets = [], now = Date.now()) {
  invariant(principal?.principalId, 'UNAUTHENTICATED');
  if (principal.surface === 'operator') return true;
  invariant(principal.surface === 'assistant' && principal.grantId && !principal.revokedAt, 'DENIED');
  invariant(principal.expiresAt > now, 'EXPIRED');
  invariant(['inspect', 'delegate', 'propose', 'cancel', 'evidence'].includes(action) && principal.actions.includes(action), 'DENIED');
  invariant(targets.every(t => principal.targets.includes(t)), 'DENIED');
  return true;
}
export function attenuate(parent, next) {
  const intersection = key => parent[key].filter(item => next[key]?.includes(item));
  return freezeAuthority({ ...parent, actions: intersection('actions'), targets: intersection('targets'), disclosure: intersection('disclosure'),
    expiresAt: Math.min(parent.expiresAt, next.expiresAt ?? parent.expiresAt) });
}
export async function verifyChangeApproval(principal, intent, reference, authority) {
  invariant(principal.surface === 'operator', 'DENIED');
  if (intent.changeClass === 'operator-local') return { verified: true, source: 'operator-initiation' };
  if (intent.changeClass === 'terminal-local') {
    invariant(intent.action === 'terminal-intent.apply' && authority?.verifyLocal, 'DENIED');
    const decision = await authority.verifyLocal(reference, intent);
    invariant(decision?.verified === true && decision.phase === 'APPLY' && decision.designated === true && decision.apiCreated === true && decision.baselineVerified === true && decision.rollbackVerified === true && decision.explicitIntent === true && decision.actionDigest === intent.actionDigest && decision.collector !== true, 'DENIED');
    return decision;
  }
  if (intent.changeClass !== 'production' || !authority?.verify || !reference) fail('DENIED');
  const decision = await authority.verify(reference, intent);
  invariant(decision?.verified === true && decision.state === 'Implement' && decision.incidentsClear === true && decision.actionDigest === intent.actionDigest && decision.approverId && decision.approverId !== principal.principalId, 'DENIED');
  return decision;
}
