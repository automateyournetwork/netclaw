import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';

/** Local-only, atomic state; never workspace settings, Settings Sync or credentials. */
export class LocalState {
  constructor(private readonly directory:string){}
  private file(key:string):string{return path.join(this.directory,createHash('sha256').update(key).digest('hex')+'.json');}
  get<T>(key:string,fallback:T):T{
    const file=this.file(key);if(!fs.existsSync(file))return fallback;
    const stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.size>16*1024*1024)throw Error('Local saved state is unavailable.');
    const value=JSON.parse(fs.readFileSync(file,'utf8')) as {key:string;value:T};if(value.key!==key)throw Error('Local saved state binding changed.');return value.value;
  }
  async update<T>(key:string,value:T):Promise<void>{
    fs.mkdirSync(this.directory,{recursive:true,mode:0o700});if(fs.lstatSync(this.directory).isSymbolicLink())throw Error('Local state directory is unavailable.');
    const file=this.file(key),temporary=`${file}.${randomUUID()}.tmp`,bytes=JSON.stringify({key,value});
    if(Buffer.byteLength(bytes)>16*1024*1024)throw Error('Local saved state exceeds its limit.');
    const fd=fs.openSync(temporary,'wx',0o600);try{fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
    try{fs.renameSync(temporary,file);}finally{if(fs.existsSync(temporary))fs.unlinkSync(temporary);}
  }
}
