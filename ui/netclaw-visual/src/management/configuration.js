import fs from 'node:fs';
import path from 'node:path';
import { parseEnvData } from '../security/private-files.js';
import { ENV_MAP } from '../hud-server/integration-environment.js';
import { configurationInventory } from '../hud-server/configuration.js';
import { readOwned, atomicPrivate } from './files.js';
import { invariant } from './errors.js';

export const secretField = key => /KEY|TOKEN|PASSWORD|SECRET|AUTH|CREDENTIAL/i.test(key);
const providerFields=['ANTHROPIC_API_KEY','OPENAI_API_KEY','OPENROUTER_API_KEY','GEMINI_API_KEY','OPENCLAW_GATEWAY_TOKEN','OPENCLAW_GATEWAY_PASSWORD','NETCLAW_HERMES_HUD_API_KEY'];
const known = new Set([...providerFields,...Object.values(ENV_MAP).flatMap(item=>item.env)]);
const prohibited = /(?:^PATH$|^HOME$|^LD_|^DYLD_|^NODE_|^PYTHON|_PATH$|_DIR$|_SCRIPT$|_COMMAND$|_EXEC|^NETCLAW_LAB_MODE$|^N2N_RISK_MODE$|^N2N_STRICT_ALL$)/;
export function environment(binding) { return parseEnvData((readOwned(binding.envPath,{missing:true}) || Buffer.from('')).toString()); }
export function configurationSnapshot(binding) {
  return { ...configurationInventory({...ENV_MAP,providers:{env:providerFields,files:[],notes:'Selected runtime provider credentials.'}},environment(binding),'Selected installation .env'),
    managedFields:[...known].filter(key=>!prohibited.test(key)).map(key=>({key,secret:secretField(key),restartRequired:true})),
    source:'Stored configuration; effective running values require runtime verification.' };
}

/** Preserve all unrelated bytes, including comments/newlines and multiline values. */
export function patchEnvironment(original, updates) {
  invariant(typeof original==='string');
  const lines=original.match(/[^\n]*\n|[^\n]+$/g)||[];
  const spans=[];
  for(let i=0;i<lines.length;i++) {
    const match=lines[i].match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)/);
    if(!match)continue;
    let end=i;const value=match[2].trim(),quote=['"',"'",'`'].includes(value[0])?value[0]:null;
    if(quote) {
      let joined=value;const closed=()=>{for(let n=1;n<joined.length;n++){if(joined[n]===quote && joined[n-1]!=='\\')return true;}return false;};
      while(!closed() && end+1<lines.length)joined+=lines[++end];
      invariant(closed());
    }
    spans.push({start:i,end,key:match[1]});i=end;
  }
  const removed=new Set();for(const span of spans)if(Object.hasOwn(updates,span.key))for(let i=span.start;i<=span.end;i++)removed.add(i);
  let output=lines.filter((_,i)=>!removed.has(i)).join('');
  if(output && !output.endsWith('\n'))output+='\n';
  for(const [key,value] of Object.entries(updates)) {
    invariant(/^[A-Z][A-Z0-9_]*$/.test(key)&&typeof value==='string'&&!/[\r\n\0]/.test(value));
    output+=`${key}=${JSON.stringify(value)}\n`;
  }
  return output;
}
export function configurationAdapters(binding) {
  const configuration={qualified:true,resource:'configuration',isSecret:secretField,
    async prepare(input) {
      invariant(input.targets.length===1&&input.targets[0]===binding.installationId,'DENIED');
      invariant(input.patch.fields?.length && Object.keys(input.patch).every(key=>key==='fields'));
      invariant(new Set(input.patch.fields.map(f=>f.key)).size===input.patch.fields.length);
      for(const field of input.patch.fields) {
        invariant(known.has(field.key)&&!prohibited.test(field.key),'UNSUPPORTED');
        invariant(!secretField(field.key)||field.value===undefined);
        invariant(field.value===undefined || !/[\r\n\0]/.test(field.value));
      }
      const original=readOwned(binding.envPath,{missing:true});
      const baseline=Buffer.from(JSON.stringify({format:1,exists:original!==null,bytes:(original||Buffer.from('')).toString('base64')}));
      return {baseline,rollback:baseline,changeClass:'operator-local',impact:'Save selected .env fields. Running services are unchanged; restart may be required.'};
    },
    async apply(proposal,{baseline,replacements}) {
      const saved=JSON.parse(baseline);invariant(saved.format===1);
      const updates={};
      const replacementFields=proposal.patch.fields.filter(f=>secretField(f.key)&&f.intent==='replace').map(f=>f.key);
      invariant(Object.keys(replacements).every(key=>replacementFields.includes(key)));
      for(const field of proposal.patch.fields) {
        if(field.intent==='keep')continue;
        if(field.intent==='clear'){updates[field.key]='';continue;}
        const value=secretField(field.key)?replacements[field.key]:field.value;
        // Blank/mask/omission is always keep, never an accidental erase.
        if(value===undefined||value===''||/^[*•]+$/.test(value))continue;
        invariant(typeof value==='string'&&value.length<=65536&&!/[\r\n\0]/.test(value));updates[field.key]=value;
      }
      const actual=readOwned(binding.envPath,{missing:true});
      const current=actual||Buffer.from('');invariant((actual!==null)===saved.exists&&current.equals(Buffer.from(saved.bytes,'base64')),'STALE_REVISION');
      const next=patchEnvironment(current.toString(),updates);atomicPrivate(binding.envPath,next);
      return {expected:Buffer.from(next)};
    },
    async verify(_proposal,result){return {verified:readOwned(binding.envPath).equals(result.expected),pendingRestart:true};},
    async rollback(_proposal,bytes){
      const saved=JSON.parse(bytes);invariant(saved.format===1);
      if(!saved.exists){if(readOwned(binding.envPath,{missing:true})!==null)fs.unlinkSync(binding.envPath);return {verified:readOwned(binding.envPath,{missing:true})===null};}
      const original=Buffer.from(saved.bytes,'base64');atomicPrivate(binding.envPath,original);return{verified:readOwned(binding.envPath).equals(original)};
    },
  };
  return {'integration.configure':configuration};
}
