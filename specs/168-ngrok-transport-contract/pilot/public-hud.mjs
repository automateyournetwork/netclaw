// Explicit owner-approved public R01 lab workspace. Account/RBAC work is later roadmap.
// The upstream remains loopback-only; this ingress publishes a fixed application surface.
import http from 'node:http';
import { readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const PUBLIC_HOST = 'r01-gcp-montreal.lobsternet.automateyournetwork.com';
const scalar = value => typeof value === 'string' ? value.slice(0, 500) : typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value)) ? value : null;
const pick = (value, fields) => Object.fromEntries(fields.filter(k => value?.[k] !== undefined).map(k => [k, scalar(value[k])]));
const rows = value => Array.isArray(value) ? value.slice(0, 128) : [];
function inventory(value) {
  const v = value?.inventory || value;
  if (!v) return null;
  return { ...pick(v, ['available','source','issued_at','received_at']), received_at: scalar(value.received_at || v.received_at),
    harness: pick(v.harness, ['type','version']), llm: { ...pick(v.llm, ['primary_model','guarded']), fallbacks: rows(v.llm?.fallbacks).map(scalar) },
    mcp_servers: rows(v.mcp_servers).map(s => ({ name: scalar(s.name), tools: rows(s.tools).map(scalar) })) };
}
export function project(endpoint, value) {
  if (endpoint === '/api/runtime') return { ...pick(value, ['kind','installationId','label']), capabilities: value.capabilities || {}, readiness: pick(value.readiness,['ready','executionVerified']), publicLab: true };
  if (endpoint === '/api/hud/runtime') return { ...value, controlUi: { available: false, reason: 'Native gateway administration uses the private IAP link. Chat and Canvas work here.' } };
  if (endpoint !== '/api/n2n') return value;
  return { ...pick(value, ['available','generatedAt']), risk: pick(value.risk,['risk_name','name','role','description']),
    members: rows(value.members).map(v => ({ ...(v.member_id === 'r01-20261101/onprem' ? { purpose: 'Mac on premises · subnet calculation · no pyATS/device access' } : {}), ...pick(v,['member_id','display_name','profile','status','state','live','last_seen','last_heartbeat','updated_at','heartbeat_age_s','node_type']), skills: rows(v.skills).map(scalar), inventory: inventory(v.inventory) })),
    peers: rows(value.peers).map(v => ({ ...(['as64519-198.18.168.3','as64521-198.18.168.3'].includes(v.identity) ? { purpose: v.state === 'severed' ? 'Retired transport probe · retained audit identity' : 'Independent on-prem Border · NCFED transport qualification', model: 'No LLM configured · transport probe' } : {}), ...pick(v,['identity','display_name','state','channel_state','last_seen','updated_at','transport','remote_as','router_id','consent_local','consent_remote']), inventory: inventory(v.inventory) })),
    posture: { ...pick(value.posture,['mode','state','computed_at']), controls: rows(value.posture?.controls).map(c=>pick(c,['name','available','detail'])) }, advisors: [] };
}
const READ = new Set(['/api/runtime','/api/n2n','/api/graph','/api/bgp','/api/gateway/status','/api/budget/status',
  '/api/hud/runtime','/api/hud/security','/api/hud/tokenomics','/api/hud/configuration','/api/hud/documentation','/api/hud/reference','/api/hud/openapi.json',
  '/api/chat/models','/api/chat/conversations','/api/rag/documents','/api/rag/stats','/api/terminal/devices','/api/layout']);
const WRITE = new Set(['/api/hud/session','/api/hud/session/revoke','/api/chat','/api/chat/usage','/api/rag/search','/api/rag/upload']);
const ID = '[a-zA-Z0-9_.:-]{1,128}';
function permitted(method, target) {
  if (['GET','HEAD'].includes(method)) return READ.has(target) || new RegExp(`^/api/(?:hud/documentation|skill)/${ID}$`).test(target) || new RegExp(`^/api/hud/tasks/${ID}/assessments/${ID}$`).test(target);
  return method === 'POST' && (WRITE.has(target) || new RegExp(`^/api/chat/conversations/${ID}/open$`).test(target));
}
export async function createViewer({ dist, upstream = 'http://127.0.0.1:13001', fetcher = fetch, publicHost = PUBLIC_HOST }) {
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(upstream)) throw Error('Fixed loopback HUD upstream required');
  const root = await realpath(dist), files = new Map();
  for (const dir of ['assets','logos','avatars']) {
    async function walk(relative) {
      for (const item of await readdir(path.join(root, relative), { withFileTypes: true })) {
        const name = path.posix.join(relative, item.name);
        if (item.isDirectory()) await walk(name);
        else if (item.isFile() && /\.(?:js|css|png|svg|jpg|jpeg|webp|woff2?|glb|mp3|wav)$/.test(name)) {
          const resolved = await realpath(path.join(root,name)); if (resolved.startsWith(root+path.sep)) files.set('/'+name,resolved);
        }
      }
    }
    await walk(dir).catch(e=>{if(e.code!=='ENOENT')throw e;});
  }
  const pages = new Map();
  for (const page of ['index.html','canvas.html','classic.html']) {
    try { pages.set('/'+page,(await readFile(path.join(root,page),'utf8')).replace('<head>','<head><script src="/lab-config.js"></script>')); }
    catch(e){if(e.code!=='ENOENT')throw e;}
  }
  let activeChats = 0;
  const server = http.createServer(async (req,res)=>{
    res.setHeader('Cache-Control','no-store'); res.setHeader('X-Content-Type-Options','nosniff'); res.setHeader('Referrer-Policy','no-referrer'); res.setHeader('X-Frame-Options','SAMEORIGIN');
    res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'");
    const send=(status,type,body)=>{res.writeHead(status,{'Content-Type':type});res.end(req.method==='HEAD'?'':body);};
    if(req.headers.host !== publicHost || (req.headers.origin && req.headers.origin !== 'https://'+publicHost) || req.headers['sec-fetch-site']==='cross-site') return send(403,'application/json','{"error":"Use the public lab origin"}');
    const target=req.url;
    // No arbitrary URLs, encoded path tricks, queries, authorization headers or forwarded headers.
    if(permitted(req.method,target)) {
      if(target==='/api/chat' && activeChats>=2)return send(429,'application/json','{"error":"Lab model capacity busy; try later"}');
      const chat=target==='/api/chat';if(chat)activeChats++;
      try {
        let size=0;const chunks=[];
        for await (const chunk of req){size+=chunk.length;if(size>4*1024*1024) return send(413,'application/json','{"error":"Lab request exceeds 4 MiB"}');chunks.push(chunk);}
        const headers={};for(const name of ['content-type','cookie','x-netclaw-installation'])if(req.headers[name])headers[name]=req.headers[name];
        // Origin was checked above. The owned loopback hop is intentionally a local API request.
        const response=await fetcher(upstream+target,{method:req.method==='HEAD'?'GET':req.method,headers,body:chunks.length?Buffer.concat(chunks):undefined,redirect:'error',signal:AbortSignal.timeout(chat?590000:90000)});
        let count=0;const output=[];for await(const chunk of response.body){count+=chunk.length;if(count>8*1024*1024)throw Error('Response bound');output.push(chunk);}
        const text=Buffer.concat(output).toString();let body;
        try{body=JSON.stringify(response.ok?project(target,JSON.parse(text)):JSON.parse(text));}catch{throw Error('Non-JSON upstream');}
        const cookies=response.headers.getSetCookie?.() || [];if(cookies.length)res.setHeader('Set-Cookie',cookies.map(c=>c+'; Secure'));
        return send(response.status,'application/json',body);
      }catch{return send(503,'application/json','{"available":false,"error":"Cloud service unavailable"}');}
      finally{if(chat)activeChats--;}
    }
    if(!['GET','HEAD'].includes(req.method))return send(405,'application/json','{"error":"This operation is not enabled in the public R01 lab"}');
    if(target==='/api/hud/logs')return send(200,'application/json','{"sources":[],"reason":"Runtime logs are retained in the private operator evidence."}');
    if(target==='/lab-config.js')return send(200,'text/javascript','globalThis.NETCLAW_PUBLIC_LAB=true;');
    const page=target==='/'?'/index.html':target==='/canvas.html?embedded=1'?'/canvas.html':target;
    if(pages.has(page))return send(200,'text/html; charset=utf-8',pages.get(page));
    if(!files.has(target))return send(404,'application/json','{"error":"Not published"}');
    const types={'.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.woff':'font/woff','.woff2':'font/woff2','.glb':'model/gltf-binary','.mp3':'audio/mpeg','.wav':'audio/wav'};
    try{send(200,types[path.extname(target)],await readFile(files.get(target)));}catch{send(404,'application/json','{"error":"Asset unavailable"}');}
  });
  server.on('upgrade',(_req,socket)=>socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'));
  server.headersTimeout=10000;server.requestTimeout=30000;server.maxConnections=100;
  return server;
}
if(process.argv[1] && fileURLToPath(import.meta.url)===path.resolve(process.argv[1])) {
  const server=await createViewer({dist:process.env.R01_HUD_DIST});server.listen(13002,'127.0.0.1',()=>console.log('R01 full lab HUD behind HTTPS on loopback13002'));
}
