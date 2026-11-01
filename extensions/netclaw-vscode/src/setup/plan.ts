import {canonical,hash,strictJson} from './data';

export type DraftInput=Record<string,any>;
export interface DraftChange {path:string;value:unknown}
const clone=<T>(value:T):T=>JSON.parse(canonical(value));
const same=(a:unknown,b:unknown)=>canonical(a)===canonical(b);

/** Closed schema vocabulary used by the bundled Claw Plan, including drafts. */
export function validateShape(value:any,schema:any,partial=false,root=schema):boolean{
  if(schema.$ref){const key=schema.$ref.replace(/^#\/\$defs\//,'');return !!root.$defs?.[key]&&validateShape(value,root.$defs[key],partial,root);}
  if(schema.oneOf){const matches=schema.oneOf.filter((s:any)=>validateShape(value,s,partial,root)).length;return partial?matches>0:matches===1;}
  if(Object.hasOwn(schema,'const')&&!same(value,schema.const))return false;
  if(schema.enum&&!schema.enum.some((item:any)=>same(value,item)))return false;
  if(schema.type==='object'){
    if(!value||typeof value!=='object'||Array.isArray(value))return false;
    if(!partial&&(schema.required||[]).some((key:string)=>!Object.hasOwn(value,key)))return false;
    return Object.entries(value).every(([key,item])=>{
      if(schema.propertyNames&&!validateShape(key,schema.propertyNames,partial,root))return false;
      const definition=schema.properties?.[key];
      if(definition)return validateShape(item,definition,partial,root);
      return schema.additionalProperties===true||typeof schema.additionalProperties==='object'&&validateShape(item,schema.additionalProperties,partial,root);
    });
  }
  if(schema.type==='array')return Array.isArray(value)&&value.length>=(partial?0:schema.minItems||0)&&value.length<=(schema.maxItems??Infinity)&&
    (!schema.uniqueItems||new Set(value.map(canonical)).size===value.length)&&value.every(v=>validateShape(v,schema.items,partial,root));
  if(schema.type==='string')return typeof value==='string'&&[...value].length>=(schema.minLength||0)&&[...value].length<=(schema.maxLength??Infinity)&&(!schema.pattern||new RegExp(schema.pattern).test(value));
  if(schema.type==='integer')return Number.isSafeInteger(value)&&value>=(schema.minimum??-Infinity)&&value<=(schema.maximum??Infinity);
  if(schema.type==='boolean')return typeof value==='boolean';
  if(schema.type==='null')return value===null;
  return !schema.type;
}

export class SetupDraft {
  private answers:DraftInput={schema:1,assumptions:[],unresolved:[]};
  private revision=0;
  private secretKeys=new Set<string>();
  constructor(private schema:any,readonly catalog:any){
    for(const entry of [...catalog.components,...catalog.choices])for(const field of entry.settings||[])
      if(field.classification==='secret')this.secretKeys.add(field.key);
  }
  get complete(){return validateShape(this.answers,this.schema)&&!(this.answers.unresolved||[]).length;}
  snapshot(){return {revision:this.revision,answers:clone(this.answers),hash:hash(canonical(this.answers)),complete:this.complete};}
  private check(value:DraftInput){
    strictJson(canonical(value));
    if(!validateShape(value,this.schema,true))throw Error('Draft has unknown, invalid or unsupported fields.');
    const inspect=(item:any)=>{
      if(typeof item==='string'&&/(?:\b(?:sk-(?:ant-)?|gh[pousr]_|github_pat_|xox[baprs]-|nck_(?:live|test)_)[A-Za-z0-9_-]{8,}|\bAKIA[A-Z0-9]{16}\b|\bBearer\s+\S+|\bBasic\s+[A-Za-z0-9+/=]{12,}|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----|[a-z][a-z0-9+.-]*:\/\/[^/\s]+@)/i.test(item))throw Error('Enter credentials only through native secret input.');
      if(item&&typeof item==='object')for(const [key,child] of Object.entries(item)){
        if(this.secretKeys.has(key)&&(!child||typeof child!=='object'||(child as any).kind!=='secret'))throw Error('Credential settings must contain scoped references, never values.');
        inspect(child);
      }
    };inspect(value);
    for(const claw of value.claws||[]){
      const mode=claw.settings?.NETCONVERTER_MODE;
      if(mode&&(mode.kind!=='value'||!['hosted-readonly','local-terminal'].includes(mode.value)))throw Error('Choose a supported NetConverter mode.');
      for(const key of ['NETCONVERTER_WORKSPACE','NETCONVERTER_EXECUTABLE']){
        const entry=claw.settings?.[key];if(entry?.kind==='value'&&entry.value&&
          (typeof entry.value!=='string'||!entry.value.startsWith('/')||entry.value.split('/').includes('..')))throw Error('NetConverter paths must be absolute host paths.');
      }
    }
  }
  replace(value:DraftInput,expected:number){
    if(expected!==this.revision)throw Error('Setup changed. Refresh before editing.');
    this.check(value);this.answers=clone(value);this.revision++;return this.snapshot();
  }
  private changed(change:DraftChange){
    if(!/^\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+$/.test(change.path)||change.path.split('/').some(p=>['__proto__','prototype','constructor'].includes(p)))throw Error('Unsupported setup field.');
    const data=clone(this.answers),discarded:string[]=[];
    const remove=(container:any,keys:string[],prefix:string)=>{for(const key of keys)if(Object.hasOwn(container,key)){delete container[key];discarded.push(prefix+'/'+key);}};
    const parts=change.path.slice(1).split('/');let target:any=data;
    for(const key of parts.slice(0,-1)){if(!target[key]||typeof target[key]!=='object')throw Error('Complete the parent choice first.');target=target[key];}
    const last=parts.at(-1)!;
    if(Object.hasOwn(target,last)&&same(target[last],change.value))return {data,discarded};
    const clawMatch=change.path.match(/^\/claws\/(\d+)\/(harness|provider|capabilities)$/);
    if(clawMatch){
      const index=Number(clawMatch[1]),claw=data.claws[index],prefix='/claws/'+index;
      if(clawMatch[2]==='harness'){
        remove(claw,['runtimeVersion','provider','channels','capabilities','settings','testbed'],prefix);
        if(claw.role==='border')data.claws.forEach((member:any,i:number)=>{
          if(member.role==='member'&&member.harnessChoice==='inherit'){
            member.harness=change.value;remove(member,['runtimeVersion','provider','channels','capabilities','settings','testbed'],'/claws/'+i);
          }
        });
      }else if(clawMatch[2]==='provider'){
        const prior=this.catalog.choices.find((c:any)=>c.kind==='provider'&&c.id===claw.provider?.id);
        for(const key of prior?.settingKeys||[])if(claw.settings&&Object.hasOwn(claw.settings,key)){delete claw.settings[key];discarded.push(prefix+'/settings/'+key);}
      }else {
        remove(claw,['settings'],prefix);
        const components=change.value&&typeof change.value==='object'&&'components' in change.value?change.value.components:undefined;
        if(!Array.isArray(components)||!components.includes('pyats'))remove(claw,['testbed'],prefix);
      }
    }
    if(change.path==='/host')remove(data,['source','claws','commsBindings'], '');
    if(change.path==='/source')remove(data,['commsBindings'],'');
    if(change.path==='/source'&&data.claws)for(const [index,claw] of data.claws.entries())remove(claw,['capabilities','settings','testbed'],'/claws/'+index);
    if(change.path==='/shape'&&data.claws?.length){
      remove(data,['commsBindings'],'');
      // Harness/provider/channel precede shape in the decision tree. Keep the
      // primary choices, while making downstream membership/profile changes
      // explicit before removing them.
      const primary=data.claws[0];
      if(data.claws.length>1)discarded.push('/claws/members');
      data.claws=[primary];primary.role=change.value==='risk'?'border':'focused';
      remove(primary,['capabilities','testbed'],'/claws/0');
      const keep=new Set<string>([
        ...(this.catalog.choices.find((c:any)=>c.kind==='provider'&&c.id===primary.provider?.id)?.settingKeys||[]),
        ...(primary.channels||[]).flatMap((c:any)=>c.settingKeys||[])]);
      for(const key of Object.keys(primary.settings||{}))if(!keep.has(key))remove(primary.settings,[key],'/claws/0/settings');
      for(const field of ['inventory','identity'])if(data[field]){
        if(data[field].some((item:any)=>item.owner!==primary.id))discarded.push('/'+field+'/members');
        data[field]=data[field].filter((item:any)=>item.owner===primary.id);
      }
      if(data.verification)data.verification.risk=change.value==='risk';
    }
    target[last]=clone(change.value);return {data,discarded};
  }
  preview(change:DraftChange){return {revision:this.revision,discarded:this.changed(change).discarded};}
  update(change:DraftChange,expected:number,discardConfirmed=false){
    const next=this.changed(change);
    if(next.discarded.length&&!discardConfirmed)throw Error('Review the dependent answers that will be discarded.');
    return this.replace(next.data,expected);
  }
}
