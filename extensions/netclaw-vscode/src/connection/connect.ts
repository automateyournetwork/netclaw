import * as vscode from 'vscode';
import { ConnectionProfile,Identity,hostContext,validateProfile } from '../state/profiles';
import type { Client } from '@modelcontextprotocol/client' with { "resolution-mode": "import" };
export const quotePosix=(value:string):string=>`'${value.replaceAll("'","'\\''")}'`;

export function launchProfile(profile:ConnectionProfile):{command:string;args:string[];env:Record<string,string>} {
  validateProfile(profile);
  const args=[profile.launcherPath,'--home',profile.home,'--runtime',profile.harness,...(profile.installationId?['--installation',profile.installationId]:[])];
  const env=Object.fromEntries(['HOME','USER','LOGNAME','PATH','SHELL','SystemRoot','WINDIR','TEMP','TMP'].flatMap(k=>process.env[k]===undefined?[]:[[k,process.env[k]!]]));
  if(profile.transport==='ssh')return {command:'ssh',args:['-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ForwardAgent=no','-o','ClearAllForwardings=yes','--',profile.sshAlias!,[profile.nodePath,...args].map(quotePosix).join(' ')],env};
  if(process.platform==='win32')throw Error('Open the intended WSL distribution using “WSL: Connect to WSL using Distro”, or select an existing SSH profile.');
  return {command:profile.nodePath,args,env};
}

export class Connection implements vscode.Disposable {
  private client?:Client;
  private serial=0;
  identity?:Identity;profile?:ConnectionProfile;
  readonly changed=new vscode.EventEmitter<void>();
  get generation():number{return this.serial;}
  get ready():boolean{return Boolean(this.client&&this.identity&&vscode.workspace.isTrusted);}
  constructor(private readonly output:vscode.OutputChannel){}
  async connect(profile:ConnectionProfile):Promise<Identity>{
    if(!vscode.workspace.isTrusted)throw Error('Trust this workspace before connecting.');
    if(profile.context!==hostContext())throw Error('This profile belongs to a different extension host.');
    await this.disconnect();const generation=++this.serial;
    const {Client}=await import('@modelcontextprotocol/client');
    const {StdioClientTransport}=await import('@modelcontextprotocol/client/stdio');
    const client=new Client({name:'netclaw-vscode-operator',version:'0.1.0'});
    const transport=new StdioClientTransport({...launchProfile(profile),stderr:'pipe'});
    // Never forward arbitrary child stderr: it may contain paths or credentials.
    transport.stderr?.on('data',()=>this.output.appendLine('Backend diagnostic received. Connection errors are shown without private process output.'));
    try{
      await client.connect(transport,{timeout:15000});
      const response=await client.callTool({name:'operator_identity',arguments:{}},{timeout:15000});
      if(response.isError)throw Error('The backend refused the identity handshake. Check supported Node and installed management prerequisites.');
      const identity=response.structuredContent as unknown as Identity;
      if(identity?.contract?.major!==1||!identity.installationId||!identity.hostId||!identity.principalId)throw Error('Backend management contract 1 with stable identity is required.');
      if(identity.harness?.type!==profile.harness)throw Error('The backend returned a different harness. Review the selected runtime home.');
      if((profile.installationId&&identity.installationId!==profile.installationId)||(profile.hostId&&identity.hostId!==profile.hostId))throw Error('The installation or host identity changed. Review a new connection.');
      if(generation!==this.serial||!vscode.workspace.isTrusted)throw Error('Connection cancelled.');
      this.client=client;this.identity=identity;this.profile=profile;
      client.onclose=()=>{if(this.client===client){this.client=undefined;this.identity=undefined;this.serial++;this.changed.fire();}};
      this.changed.fire();return identity;
    }catch(error){await client.close().catch(()=>{});throw error;}
  }
  async call<T=Record<string,unknown>>(name:string,args:Record<string,unknown>={}):Promise<T>{
    if(!this.ready||!this.client)throw Error('Connect to a trusted existing installation first.');
    const generation=this.serial,client=this.client;
    const timeout=name==='operator_workspace'&&['rag-list','rag-search'].includes(String(args.action))?150000:15000;
    const response=await client.callTool({name,arguments:args},{timeout});
    if(generation!==this.serial)throw Error('The active connection changed. This response was discarded.');
    const data=response.structuredContent||JSON.parse(response.content.filter(c=>c.type==='text').map(c=>c.text).join(''));
    if(response.isError){const failure=(data as {error?:{code?:string;message?:string}}).error;throw Error(`${failure?.code||'SOURCE_UNAVAILABLE'}: ${failure?.message||'The backend refused this request.'}`);}
    return data as T;
  }
  async disconnect():Promise<void>{this.serial++;const client=this.client;this.client=undefined;this.identity=undefined;this.profile=undefined;this.changed.fire();if(client)await client.close();}
  dispose():void{void this.disconnect();this.changed.dispose();}
}
