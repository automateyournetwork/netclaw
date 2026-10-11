import { randomUUID,randomBytes,createHash,timingSafeEqual } from 'node:crypto';
import { environment,patchEnvironment } from './configuration.js';
import { readOwned,atomicPrivate } from './files.js';
import { ownerKey } from './journal.js';
import { freezeAuthority,authorize } from './policy.js';
import { invariant } from './errors.js';

export class ClientGrants {
  constructor({binding,journal,audit}){Object.assign(this,{binding,journal,audit});}
  async prepare(principal,input){
    invariant(principal.surface==='operator','DENIED');this.binding.assertCurrent();
    invariant(input.expiresAt>Date.now()&&input.expiresAt<=Date.now()+30*86400000,'EXPIRED');
    invariant(input.targets.every(t=>t===this.binding.installationId),'UNQUALIFIED');
    const op=this.journal.admit(principal,input.nonce,'client-prepare',input);if(op.result)return op.result;
    const proposalId=randomUUID();const revision=this.journal.revision([this.binding.configPath,this.binding.envPath]);
    const proposal={...input,nonce:undefined,proposalId,state:'pending-review',expectedRevision:revision,
      disclosureNotice:'Permitted tool results can enter this external assistant’s model provider. NetClaw credentials and unrestricted logs remain excluded.'};
    this.journal.put('client-proposal',proposalId,principal,proposal);
    this.journal.transition(op.operationId,'running');this.journal.transition(op.operationId,'succeeded',proposal);return proposal;
  }
  async apply(principal,input){
    invariant(principal.surface==='operator','DENIED');this.binding.assertCurrent();
    const op=this.journal.admit(principal,input.nonce,'client-apply',input);if(op.state!=='admitted')return op;
    const lock=this.journal.lock('configuration',op.operationId);
    try{
      const proposal=this.journal.record('client-proposal',input.proposalId,principal);
      invariant(proposal.state==='pending-review','DENIED');invariant(proposal.expiresAt>Date.now(),'EXPIRED');
      invariant(input.expectedRevision===proposal.expectedRevision&&input.expectedRevision===this.journal.revision([this.binding.configPath,this.binding.envPath]),'STALE_REVISION');
      await this.audit.record({operationId:op.operationId,proposalId:proposal.proposalId,action:'client-grant',state:'before-apply'});
      invariant(input.expectedRevision===this.journal.revision([this.binding.configPath,this.binding.envPath]),'STALE_REVISION');
      const grantId=randomUUID(),credentialRef=`NETCLAW_CLIENT_${grantId.replaceAll('-','').toUpperCase()}_TOKEN`,token=randomBytes(32).toString('base64url');
      const grant={installationId:this.binding.installationId,principalId:`client:${grantId}`,grantId,generation:1,surface:'assistant',client:proposal.client,
        actions:proposal.actions,targets:proposal.targets,disclosure:proposal.disclosure,expiresAt:proposal.expiresAt,revokedAt:null,credentialRef,credentialHash:createHash('sha256').update(token).digest('hex')};
      this.journal.transition(op.operationId,'running');
      // A crash can leave an unreferenced env token; no live grant exists until its hash is committed.
      const source=(readOwned(this.binding.envPath,{missing:true})||Buffer.from('')).toString();
      atomicPrivate(this.binding.envPath,patchEnvironment(source,{[credentialRef]:token}));
      this.journal.put('grant',grantId,principal,grant);
      this.journal.put('client-proposal',proposal.proposalId,principal,{...proposal,state:'applied',grantId},{replace:true});
      return this.journal.transition(op.operationId,'succeeded',{grantId,credentialRef,generation:1,expiresAt:grant.expiresAt,client:grant.client});
    }finally{this.journal.unlock('configuration',lock);}
  }
  resolve(credentialRef){
    this.binding.assertCurrent();invariant(/^NETCLAW_CLIENT_[A-F\d]{32}_TOKEN$/.test(credentialRef),'UNAUTHENTICATED');
    const token=environment(this.binding)[credentialRef];invariant(typeof token==='string'&&token.length>20,'UNAUTHENTICATED');
    const hash=createHash('sha256').update(token).digest();
    const grant=this.journal.records('grant',this.binding.principal).find(g=>g.credentialRef===credentialRef);
    invariant(grant && timingSafeEqual(hash,Buffer.from(grant.credentialHash,'hex')),'UNAUTHENTICATED');
    invariant(grant.installationId===this.binding.installationId,'IDENTITY_CHANGED');
    invariant(!grant.revokedAt&&grant.surface==='assistant','DENIED');invariant(grant.expiresAt>Date.now(),'EXPIRED');
    const {credentialHash,credentialRef:reference,id,...publicGrant}=grant;
    return freezeAuthority(publicGrant);
  }
  async revoke(principal,{grantId,nonce}){
    invariant(principal.surface==='operator','DENIED');
    const grant=this.journal.record('grant',grantId,principal),op=this.journal.admit(principal,nonce,'client-revoke',{grantId});
    if(op.state!=='admitted')return op;
    await this.audit.record({operationId:op.operationId,action:'client-revoke',state:'before-apply'});
    this.journal.transition(op.operationId,'running');
    this.journal.put('grant',grantId,principal,{...grant,revokedAt:Date.now(),generation:grant.generation+1},{replace:true});
    return this.journal.transition(op.operationId,'succeeded',{grantId,revoked:true,inFlight:'Revoked authority prevents new dispatch. Existing execution must be reconciled; cancellation is not assumed.'});
  }
}
