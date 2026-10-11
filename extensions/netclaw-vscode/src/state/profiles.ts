import * as vscode from 'vscode';
import { randomUUID } from 'node:crypto';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';

export interface ConnectionProfile {
  id:string;label:string;transport:'local'|'ssh';nodePath:string;launcherPath:string;home:string;
  harness:'openclaw'|'hermes';sshAlias?:string;context:string;installationId?:string;hostId?:string;
}
export interface Identity {
  contract:{major:number;minor:number};installationId:string;principalId:string;hostId:string;sourceVersion:string;
  harness:{type:string;version:string|null};role:string;configurationRevision:string;observedAt:string;
  capabilities:Record<string,unknown>;
}
export const hostContext=()=>`${vscode.env.remoteName||'local'}:${os.hostname()}:${os.userInfo().uid}`;
const absolute=(value:unknown):value is string=>typeof value==='string'&&value.startsWith('/')&&!/[\r\n\0]/.test(value)&&value.length<4096;
export function validateProfile(value:ConnectionProfile):ConnectionProfile {
  if(!value||!['local','ssh'].includes(value.transport)||!['openclaw','hermes'].includes(value.harness)||
    !absolute(value.nodePath)||!absolute(value.launcherPath)||!value.launcherPath.endsWith('/scripts/netclaw-operator.mjs')||!absolute(value.home)||
    typeof value.label!=='string'||value.label.length>100||/[\r\n\0]/.test(value.label)||
    (value.transport==='ssh'&&(!value.sshAlias||!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value.sshAlias))))throw Error('Choose absolute backend paths and an existing SSH alias.');
  return Object.freeze({...value});
}
export class Profiles {
  constructor(private readonly state:vscode.Memento,private readonly directory?:string){}
  list():ConnectionProfile[]{
    const all=new Map(this.state.get<ConnectionProfile[]>('netclaw.profiles.v1',[]).map(p=>[p.id,p]));
    const entries:[string,ConnectionProfile|{deleted:true}|undefined][]=[];
    if(this.directory&&fs.existsSync(path.join(this.directory,'profiles'))){
      for(const file of fs.readdirSync(path.join(this.directory,'profiles')).filter(name=>/^[a-f\d-]{36}\.json$/.test(name))){
        const target=path.join(this.directory,'profiles',file),stat=fs.lstatSync(target);
        if(!stat.isFile()||stat.isSymbolicLink()||stat.size>32768)throw Error('Invalid local profile storage.');
        entries.push([file.slice(0,-5),JSON.parse(fs.readFileSync(target,'utf8'))]);
      }
    }else for(const key of this.state.keys().filter(k=>k.startsWith('netclaw.profile.v2.')))entries.push([key.slice('netclaw.profile.v2.'.length),this.state.get(key)]);
    for(const [id,value] of entries){
      if(value&&'deleted' in value)all.delete(id);
      else if(value)all.set(value.id,value);
    }
    return [...all.values()].filter(p=>p.context===hostContext()).map(validateProfile);
  }
  async save(profile:Omit<ConnectionProfile,'id'|'context'> & Partial<Pick<ConnectionProfile,'id'|'context'>>):Promise<ConnectionProfile>{
    const item=validateProfile({...profile,id:profile.id||randomUUID(),context:profile.context||hostContext()} as ConnectionProfile);
    await this.write(item.id,item);return item;
  }
  private async write(id:string,value:ConnectionProfile|{deleted:true}):Promise<void>{
    if(!this.directory){await this.state.update(`netclaw.profile.v2.${id}`,value);return;}
    if(!/^[a-f\d-]{36}$/.test(id))throw Error('Invalid profile identity.');
    const directory=path.join(this.directory,'profiles');fs.mkdirSync(directory,{recursive:true,mode:0o700});
    if(fs.lstatSync(directory).isSymbolicLink())throw Error('Invalid local profile storage.');
    const temporary=path.join(directory,`${id}.${randomUUID()}.tmp`),target=path.join(directory,`${id}.json`);
    // VS Code 1.102 echoes whole Memento snapshots asynchronously. Separate
    // atomic files preserve unrelated writes across windows and stale echoes.
    const fd=fs.openSync(temporary,'wx',0o600);
    try{fs.writeFileSync(fd,JSON.stringify(value));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
    try{fs.renameSync(temporary,target);}finally{if(fs.existsSync(temporary))fs.unlinkSync(temporary);}
  }
  async remove(id:string):Promise<void>{await this.write(id,{deleted:true});}
}
