export type ChatMessage={viewId:string;requestId:string;type:'ready'|'refresh'|'cancel'|'new'|'send'|'draft';payload?:{text:string;retain?:boolean;contextIds?:string[]}};
export function chatMessage(value:unknown,viewId:string):ChatMessage|undefined {
  if(!value||typeof value!=='object'||Array.isArray(value))return;
  const m=value as Record<string,unknown>;
  if(Object.keys(m).some(k=>!['viewId','requestId','type','payload'].includes(k))||m.viewId!==viewId||typeof m.requestId!=='string'||m.requestId.length>100||typeof m.type!=='string'||!['ready','refresh','cancel','new','send','draft'].includes(m.type))return;
  if(['send','draft'].includes(m.type)){
    if(!m.payload||typeof m.payload!=='object'||Array.isArray(m.payload))return;
    const p=m.payload as Record<string,unknown>;
    if(Object.keys(p).some(k=>!['text','retain','contextIds'].includes(k))||typeof p.text!=='string'||Buffer.byteLength(p.text)>65536)return;
    if(p.retain!==undefined&&typeof p.retain!=='boolean')return;
    if(p.contextIds!==undefined&&(!Array.isArray(p.contextIds)||p.contextIds.length>20||p.contextIds.some(id=>typeof id!=='string'||!/^[a-f\d-]{36}$/.test(id))))return;
  }else if(m.payload!==undefined)return;
  return m as ChatMessage;
}
