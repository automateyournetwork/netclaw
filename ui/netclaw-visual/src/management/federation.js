import { federationEndpoint, federationReadiness } from '../hud-server/runtime/federation.js';
import { invariant } from './errors.js';

export function federationReader(binding,getEnvironment,fetcher=fetch) {
  return async kind=>{
    binding.assertCurrent();const endpoint=federationEndpoint(getEnvironment());
    const ready=await federationReadiness({installationId:binding.installationId,kind:binding.kind},endpoint,fetcher);
    invariant(ready.ready,ready.code==='federation_owner_mismatch'?'IDENTITY_CHANGED':'SOURCE_UNAVAILABLE');
    const route={member:'/n2n/members',peer:'/n2n/status',edge:'/n2n/risk',overview:'/n2n/risk'}[kind];invariant(route,'UNSUPPORTED');
    const response=await fetcher(endpoint+route,{signal:AbortSignal.timeout(10000),redirect:'error'});
    invariant(response.ok,'SOURCE_UNAVAILABLE');
    const reader=response.body.getReader();const parts=[];let size=0;
    for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>1024*1024){await reader.cancel();invariant(false,'INVALID_INPUT');}parts.push(Buffer.from(value));}
    return {value:JSON.parse(Buffer.concat(parts).toString()),source:'Selected installation federation control API',qualification:'Observed inventory; advertisements do not grant execution authority.'};
  };
}
