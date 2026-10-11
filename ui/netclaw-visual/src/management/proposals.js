import { randomUUID, randomBytes, createHmac } from 'node:crypto';
import path from 'node:path';
import { ArtifactStore } from './evidence.js';
import { readOwned, atomicPrivate } from './files.js';
import { canonical, digest } from './journal.js';
import { authorize, verifyChangeApproval } from './policy.js';
import { invariant, fail, safeError } from './errors.js';

export class Proposals {
  constructor({ binding, journal, audit, adapters, authority }) {
    Object.assign(this, { binding, journal, audit, adapters, authority }); this.artifacts = new ArtifactStore(journal);
  }
  revision() { return this.journal.revision([this.binding.configPath, this.binding.envPath]); }
  async prepare(principal, input) {
    this.binding.assertCurrent(); authorize(principal, 'propose', input.targets);
    invariant(input.expectedRevision === this.revision(), 'STALE_REVISION');
    const adapter = this.adapters[input.action]; invariant(adapter, 'UNSUPPORTED');
    invariant(adapter.qualified === true, 'UNQUALIFIED');
    // Secret proposals contain intents only. Values are supplied in the human apply call.
    invariant(!(input.patch.fields || []).some(field => adapter.isSecret?.(field.key) && field.value !== undefined));
    const operation = this.journal.admit(principal, input.nonce, 'proposal', input);
    if (operation.state !== 'admitted') return operation;
    const lock = this.journal.lock(adapter.resource || 'configuration', operation.operationId);
    try {
      this.journal.transition(operation.operationId, 'preparing');
      await this.audit.record({ operationId: operation.operationId, action: input.action, state: 'preparing' });
      this.binding.assertCurrent(); invariant(input.expectedRevision === this.revision(), 'STALE_REVISION');
      const prepared = await adapter.prepare(input, principal);
      invariant(prepared?.baseline !== undefined && prepared?.rollback !== undefined, 'DENIED');
      const proposalId = randomUUID();
      const baseline = this.artifacts.write(principal, prepared.baseline, 'baseline');
      const rollback = this.artifacts.write(principal, prepared.rollback, 'rollback');
      const proposal = { proposalId, operationId: operation.operationId, action: input.action, targets: input.targets,
        expectedRevision: input.expectedRevision, patch: input.patch, actionDigest: digest({ action: input.action, targets: input.targets, patch: input.patch, revision: input.expectedRevision }),
        changeClass: prepared.changeClass, impact: prepared.impact, baseline, rollback,
        expiresAt: Date.now()+15*60*1000, state: 'pending-approval' };
      this.journal.put('proposal', proposalId, principal, proposal);
      this.journal.transition(operation.operationId, 'waiting-approval', { proposalId, approvalRequired: true });
      return { ...this.journal.get(principal, operation.operationId), proposalId, approvalRequired: true, proposal };
    } catch (error) {
      if (this.journal.get(principal, operation.operationId).state === 'preparing') this.journal.transition(operation.operationId,'failed',safeError(error));
      throw error;
    } finally { this.journal.unlock(adapter.resource || 'configuration', lock); }
  }
  secretDigest(replacements) {
    const file = path.join(this.journal.directory, '.env');
    let bytes = readOwned(file, { missing: true });
    if (!bytes) { atomicPrivate(file, `MANAGEMENT_INTEGRITY_KEY=${randomBytes(32).toString('hex')}\n`); bytes = readOwned(file); }
    const key = bytes.toString().match(/^MANAGEMENT_INTEGRITY_KEY=([a-f\d]{64})$/m)?.[1]; invariant(key, 'DENIED');
    return createHmac('sha256', key).update(canonical(replacements || {})).digest('hex');
  }
  admitApply(principal,input) {
    invariant(principal.surface==='operator','DENIED');
    return this.journal.admit(principal,input.nonce,'apply',{proposalId:input.proposalId,expectedRevision:input.expectedRevision,approvalReference:input.approvalReference,replacementDigest:this.secretDigest(input.replacements)});
  }
  async apply(principal, input, { lease } = {}) {
    this.binding.assertCurrent(); invariant(principal.surface === 'operator', 'DENIED');
    const proposal = this.journal.record('proposal', input.proposalId, principal);
    const adapter = this.adapters[proposal.action]; invariant(adapter?.qualified === true, 'UNQUALIFIED');
    const lock = this.journal.lock(adapter.resource || 'configuration', proposal.proposalId);
    let operation, dispatched = false;
    try {
      // Dedupe before expiry/revision checks: a lost successful response remains recoverable.
      operation = this.admitApply(principal,input);
      if (lease) invariant(this.journal._row(operation.operationId).lease===lease && operation.state==='running','UNKNOWN_OUTCOME');
      else if (operation.state !== 'admitted') return operation;
      invariant(proposal.state === 'pending-approval', 'DENIED');
      invariant(proposal.expiresAt > Date.now(), 'EXPIRED');
      invariant(input.expectedRevision === proposal.expectedRevision && this.revision() === proposal.expectedRevision, 'STALE_REVISION');
      const baseline = this.artifacts.read(principal, proposal.baseline.id), rollback = this.artifacts.read(principal, proposal.rollback.id);
      await verifyChangeApproval(principal, proposal, input.approvalReference, this.authority);
      await this.audit.record({ operationId: operation.operationId, proposalId: proposal.proposalId, action: proposal.action, state: 'before-apply' });
      // Audit/approval can take time; check the file revision again under the same lock.
      this.binding.assertCurrent(); invariant(this.revision() === proposal.expectedRevision, 'STALE_REVISION');
      await verifyChangeApproval(principal, proposal, input.approvalReference, this.authority);
      if(!lease)this.journal.transition(operation.operationId,'running');
      this.journal.put('proposal', proposal.proposalId, principal, { ...proposal, state:'executing' }, { replace:true });
      dispatched = true;
      const applied = await adapter.apply(proposal, { baseline, replacements: input.replacements || {}, revalidate: () => verifyChangeApproval(principal, proposal, input.approvalReference, this.authority) });
      const verified = await adapter.verify(proposal, applied);
      invariant(verified?.verified === true, 'UNKNOWN_OUTCOME');
      await this.audit.record({ operationId: operation.operationId, proposalId: proposal.proposalId, action: proposal.action, state:'verified' });
      this.journal.put('proposal', proposal.proposalId, principal, { ...proposal, state:'verified' }, { replace:true });
      const result={ verified:true, ...(verified.pendingRestart ? { pendingRestart:true } : {}), revision:this.revision() };
      return lease?this.journal.finish(operation.operationId,lease,'succeeded',result):this.journal.transition(operation.operationId,'succeeded',result);
    } catch (error) {
      if (operation && (operation.state === 'admitted'||lease)) {
        const state = this.journal.get(principal,operation.operationId).state;
        if (dispatched) {
          let recovered = false;
          try { recovered = (await adapter.rollback(proposal,this.artifacts.read(principal,proposal.rollback.id)))?.verified === true; } catch { /* retained failure */ }
          const outcome = recovered ? 'rolled-back' : 'rollback-failed';
          try { await this.audit.record({ operationId:operation.operationId,proposalId:proposal.proposalId,state:outcome }); } catch { /* preserve local outcome without claiming GAIT success */ }
          this.journal.put('proposal',proposal.proposalId,principal,{...proposal,state:outcome},{replace:true});
          const result={error:safeError(error),recoveryVerified:recovered,approvalClosed:false};
          return lease?this.journal.finish(operation.operationId,lease,outcome,result):this.journal.transition(operation.operationId,outcome,result);
        }
        if(lease&&state==='running')this.journal.finish(operation.operationId,lease,'failed',safeError(error));
        else if (state === 'admitted') this.journal.transition(operation.operationId,'denied',safeError(error));
      }
      throw error;
    } finally { this.journal.unlock(adapter.resource || 'configuration',lock); }
  }
}
