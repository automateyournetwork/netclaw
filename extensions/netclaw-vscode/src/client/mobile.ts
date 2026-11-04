import { randomUUID } from 'node:crypto';
import { HudClient, Json } from './hud';
export const mobileRoute = '/api/hud/mobile/enrollment';
export const mobileNonce = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
const exact = (v: Json, required: string[], optional: string[] = []) => v && typeof v === 'object' && !Array.isArray(v) && required.every(k=>Object.hasOwn(v,k)) && Object.keys(v).every(k=>[...required,...optional].includes(k));
export function mobileInfo(value: Json, id: string): Json {
  if(!exact(value,['schema','installation_id','available'],['reason','endpoint','mode','enrollment_ttl_seconds']) || value.schema!==1 || value.installation_id!==id || typeof value.available!=='boolean') throw Error('Enrollment response does not match the selected Border.');
  if(!value.available) {
    if(!/^[a-z][a-z0-9_]{0,79}$/.test(value.reason || '') || value.endpoint!=null)throw Error('Enrollment readiness is invalid.');
    return value;
  }
  const e=value.endpoint;
  if(!exact(e,['border_host','border_port','claw_domain','ws_path']) || typeof e.claw_domain!=='string' || !/^(?=.{1,253}$)[a-z0-9]+(?:[.-][a-z0-9]+)*$/.test(e.claw_domain) || e.border_host!==e.claw_domain || !Number.isInteger(e.border_port) || e.border_port<1 || e.border_port>65535 || !['/','/mobile/ws'].includes(e.ws_path) || !['protected','legacy'].includes(value.mode) || value.enrollment_ttl_seconds!==120)throw Error('Enrollment destination is invalid.');
  return value;
}
export function mobileRecord(value: Json,id: string,nonce: string,allowMatrix=false): Json {
  if(!exact(value,['schema','installation_id','client_nonce','status','expires_ms'],['member_id',...(allowMatrix?['qr_matrix']:[])]) || value.schema!==1 || value.installation_id!==id || !mobileNonce(nonce) || value.client_nonce!==nonce || !['absent','issued','consumed','expired','replaced'].includes(value.status) || !(value.expires_ms===null&&value.status==='absent'||Number.isSafeInteger(value.expires_ms)&&value.expires_ms>0) || value.member_id!==undefined&&(typeof value.member_id!=='string'||value.member_id.length>200||/[\u0000-\u001f\u007f]/.test(value.member_id)))throw Error('Enrollment status does not match the original request.');
  if(value.qr_matrix!==undefined){const matrix=value.qr_matrix,n=matrix?.length;if(value.status!=='issued'||!Array.isArray(matrix)||n<21||n>177||(n-21)%4!==0||matrix.some((row: unknown)=>!Array.isArray(row)||row.length!==n||row.some(bit=>typeof bit!=='boolean')))throw Error('Enrollment QR is invalid.');}
  return value;
}
/** A selected-installation client; the only persisted field is a request nonce. */
export class MobileEnrollment {
  info?: Json;
  record?: Json;
  private busy=false;
  constructor(readonly client: HudClient,private persist:(value:{client_nonce:string})=>Promise<void>,marker?:unknown){
    if(marker!==undefined){if(!exact(marker as Json,['client_nonce'])||!mobileNonce((marker as Json).client_nonce))throw Error('Saved enrollment reference is invalid.');this.record={client_nonce:(marker as Json).client_nonce,status:'unknown'};}
  }
  private async identity(){const value=await this.client.verifyIdentity();return value.installationId;}
  private retain(value:Json){const {qr_matrix,...metadata}=value;this.record=metadata;}
  async load(){const id=await this.identity();this.info=mobileInfo(await this.client.request('GET',mobileRoute),id);if(this.record)await this.recover();return {info:this.info,record:this.record};}
  async recover(){if(!this.record)return undefined;const nonce=this.record.client_nonce;const id=await this.identity();const value=mobileRecord(await this.client.request('GET',mobileRoute+'/'+nonce),id,nonce);this.retain(value);return value;}
  async generate(){
    if(this.busy)throw Error('An enrollment request is already in progress.');
    if(!this.info?.available)throw Error('Mobile enrollment is not ready on this Border.');
    if(this.record?.status==='unknown')throw Error('Check the original enrollment request before generating another code.');
    this.busy=true;
    try{
      if(this.record)await this.recover();
      const id=await this.identity(),previous=this.record,nonce=randomUUID();
      await this.persist({client_nonce:nonce});this.record={client_nonce:nonce,status:'unknown'};
      const value=mobileRecord(await this.client.request('POST',mobileRoute,{client_nonce:nonce,replace_client_nonce:previous?.status==='issued'?previous.client_nonce:null}),id,nonce,true);
      this.retain(value);return value;
    }finally{this.busy=false;}
  }
}
