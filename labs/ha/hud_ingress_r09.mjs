/**
 * R09 public HUD ingress: one Border's protected HUD over public HTTPS on its DNS name.
 *
 * Adapted (copied, not imported) from the R08 loopback ingress `hud_ingress.mjs`, which stays
 * untouched. Differences: the origin comes from the signed manifest (`https://<dns-name>`,
 * port 443 implicit), the listener binds a configurable address, TLS is a real certificate
 * chain (lego/Let's Encrypt) verified for the DNS name rather than a private CA, there is no
 * run-root/plan coupling, the peer-is-loopback check is gone (clients are public), and the
 * lifetime self-stop is off unless NETCLAW_INGRESS_LIFETIME_S is set. No listeners or writes
 * happen on import.
 *
 * Usage:
 *   hud_ingress_r09.mjs prepare INPUT.json   compute pins, write <state_dir>/{assets,hud,ingress}.json, then check
 *   hud_ingress_r09.mjs check   INGRESS.json validate everything, start nothing
 *   hud_ingress_r09.mjs serve   INGRESS.json run (must be the frozen copy at <source_root>/labs/ha/)
 *
 * INPUT.json (exact fields, produced by the deploy script):
 *   origin                       https://<dns-name>   (must equal the signed manifest node's endpoints.https)
 *   bind, port                   listen address (default use 0.0.0.0) and TCP port (443)
 *   installation_id              this Border's installation UUID
 *   home                         private 0700 Border home (netclaw-hud/installation.json, netclaw-federation/...)
 *   source_root                  frozen source tree, no write bits, closed under source_manifest
 *   source_manifest_file         {schemaVersion:1, files:{relative:sha256}} (same format as the role launcher's)
 *   dist                         <source_root>/ui/netclaw-visual/dist
 *   edge_ws_port                 the Border's N2N_EDGE_WS_PORT on 127.0.0.1
 *   manifest_file                signed cluster manifest envelope
 *   anchor_certificate_file      offline enrollment anchor certificate
 *   anchor_key_id                sha256 key id of the anchor
 *   cluster                      {cluster_id, generation, anchor_key_id}
 *   tls                          {cert_file, chain_file|null, key_file}  (cert_file = leaf or fullchain, EC P-256 key)
 *   state_dir                    private 0700 directory for pins, claims and listening records
 *
 * INGRESS.json (written by prepare) adds the pins: assets{path,sha256}, hud{path,sha256},
 * source_manifest{path,sha256}, node_sha256, tls pins, and drops the *_file spelling.
 *
 * Node: R08 required 24.19+ or 26.1+. R09 keeps "24.19+" and accepts 25.x and 26.1+; it refuses
 * 26.0.x and anything older than 24.19. The VMs use Node 24 LTS (>=24.19).
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import https from 'node:https';
import http from 'node:http';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {once} from 'node:events';
import {boundedFile, noSymlink, buildProtectedManifest} from '../../ui/netclaw-visual/src/hud-server/protected-assets.js';
import {strictJson} from '../../ui/netclaw-visual/src/hud-server/protected-client.js';

const hash = raw => crypto.createHash('sha256').update(raw).digest('hex');
export const canonical = value => value === null || typeof value !== 'object' ? JSON.stringify(value) : Array.isArray(value) ? '['+value.map(canonical).join(',')+']' : '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
const need = (condition, reason) => {if (!condition) throw Error(reason);};
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join() === keys.split(' ').sort().join();
const json = (file, limit=128*1024) => strictJson(boundedFile(file,limit,true).toString('utf8'));
const sha = value => /^[a-f0-9]{64}$/.test(value);
const uuid = value => typeof value === 'string' && /^[a-f0-9-]{36}$/.test(value);
const absolute = value => typeof value === 'string' && path.isAbsolute(value) && path.normalize(value) === value;
const privateDirectory = directory => {noSymlink(directory); const s=fs.lstatSync(directory);need(s.isDirectory()&&s.uid===process.getuid()&&(s.mode&0o777)===0o700,'private_directory_required');};
function writeNew(file,value) {
  privateDirectory(path.dirname(file)); const fd=fs.openSync(file,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o600);
  try {fs.writeFileSync(fd,Buffer.from(canonical(value)));fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
}
function pinned(file,expected,privateFile=true,maximum=128*1024) {need(sha(expected),'invalid_digest');const raw=boundedFile(file,maximum,privateFile);need(hash(raw)===expected,'pinned_file_changed');return raw;}

export function nodeQualified(version=process.versions.node) {
  const [major,minor]=version.split('.').map(Number);
  return major===24&&minor>=19||major===25||major>=26&&!(major===26&&minor<1);
}

const INPUT_FIELDS='origin bind port installation_id home source_root source_manifest_file dist edge_ws_port manifest_file anchor_certificate_file anchor_key_id cluster tls state_dir';
const INGRESS_FIELDS='schema_version origin bind port installation_id home source_root dist edge_ws_port manifest_file anchor_certificate_file anchor_key_id cluster tls state_dir assets hud source_manifest node_sha256';

/** Origin is `https://<dns-name>` with an optional explicit port only for tests; no userinfo/path. */
export function parseOrigin(origin) {
  need(typeof origin==='string','invalid_origin');
  const url=new URL(origin);
  need(url.protocol==='https:'&&url.origin===origin&&!url.username&&!url.password&&url.hostname&&!/^[0-9.]+$/.test(url.hostname)&&!url.hostname.includes(':'),'invalid_origin');
  return {host:url.host,hostname:url.hostname,origin};
}

function validateShape(config,keys,tlsKeys,pinKeys) {
  need(exact(config,keys),'ingress_config_invalid');
  need(absolute(config.home)&&absolute(config.source_root)&&absolute(config.dist)&&absolute(config.manifest_file)&&absolute(config.anchor_certificate_file)&&absolute(config.state_dir),'absolute_path_required');
  parseOrigin(config.origin);
  need(typeof config.bind==='string'&&config.bind.length<=64&&/^[0-9a-fA-F:.]+$/.test(config.bind),'invalid_bind');
  for(const key of ['port','edge_ws_port'])need(Number.isSafeInteger(config[key])&&config[key]>=1&&config[key]<=65535,'invalid_port');
  need(config.port!==config.edge_ws_port,'port_collision');
  need(uuid(config.installation_id)&&sha(config.anchor_key_id),'invalid_identity');
  need(exact(config.cluster,'cluster_id generation anchor_key_id')&&uuid(config.cluster.cluster_id)&&uuid(config.cluster.generation)&&config.cluster.anchor_key_id===config.anchor_key_id,'invalid_cluster');
  need(exact(config.tls,tlsKeys),'invalid_tls_config');
  return config;
}

export function readInput(file) {
  const input=json(file,64*1024);
  validateShape(input,INPUT_FIELDS,'cert_file chain_file key_file');
  need(absolute(input.source_manifest_file)&&absolute(input.tls.cert_file)&&absolute(input.tls.key_file)&&(input.tls.chain_file===null||absolute(input.tls.chain_file)),'absolute_path_required');
  return input;
}

export function readIngress(file) {
  const config=json(file,64*1024);
  validateShape(config,INGRESS_FIELDS,'cert_file cert_sha256 chain_file chain_sha256 key_file key_sha256');
  need(config.schema_version===1,'ingress_config_invalid');
  for(const [name,value] of [['assets',config.assets],['hud',config.hud],['source_manifest',config.source_manifest]]) {
    need(exact(value,'path sha256')&&absolute(value.path)&&sha(value.sha256),'invalid_'+name+'_pin');
  }
  const t=config.tls;
  need(absolute(t.cert_file)&&absolute(t.key_file)&&sha(t.cert_sha256)&&sha(t.key_sha256)&&(t.chain_file===null?t.chain_sha256===null:absolute(t.chain_file)&&sha(t.chain_sha256)),'invalid_tls_pin');
  need(sha(config.node_sha256),'invalid_node_pin');
  return config;
}

/** Frozen source: closed under the manifest, hashes match, no write bits on files or directories. */
export function verifySource(config,{checkRunning=true}={}) {
  const source=config.source_root;
  need(absolute(source)&&source===fs.realpathSync(source),'source_root_invalid');
  if(checkRunning)need(fileURLToPath(import.meta.url)===path.join(source,'labs/ha/hud_ingress_r09.mjs'),'frozen_ingress_required');
  const manifest=strictJson(pinned(config.source_manifest.path,config.source_manifest.sha256,false,8*1024*1024).toString('utf8'));
  need(exact(manifest,'schemaVersion files')&&manifest.schemaVersion===1&&manifest.files&&typeof manifest.files==='object','source_manifest_invalid');
  const files=manifest.files; let count=0,total=0;
  need(Object.keys(files).length>=1&&Object.keys(files).length<=20000,'source_bound');
  const writable=stat=>(stat.mode&0o222)!==0;
  const walk=directory=>{
    need(!writable(fs.statSync(directory)),'source_writable');
    for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
      const file=path.join(directory,entry.name);need(!entry.isSymbolicLink(),'source_alias_refused');
      if(entry.isDirectory())walk(file);
      else {
        need(entry.isFile(),'source_file_required');
        const relative=path.relative(source,file).split(path.sep).join('/');
        need(Object.hasOwn(files,relative),'source_closure_changed');
        const raw=pinned(file,files[relative],false,128*1024*1024);
        need(!writable(fs.statSync(file)),'source_writable');
        count++;total+=raw.length;need(count<=20000&&total<=512*1024*1024,'source_bound');
      }
    }
  };
  walk(source);
  need(count===Object.keys(files).length,'source_closure_changed');
  need(config.dist===path.join(source,'ui/netclaw-visual/dist'),'dist_outside_source');
  return files;
}

function certificates(raw) {
  const text=raw.toString('utf8');
  const blocks=text.match(/-----BEGIN CERTIFICATE-----[\s\S]+?-----END CERTIFICATE-----/g)||[];
  need(blocks.length>=1&&blocks.length<=5,'tls_certificate_required');
  return blocks.map(b=>new crypto.X509Certificate(b));
}
/** DNS name covered, unexpired, key matches, EC P-256; the chain (if any) must issue the leaf. */
export function verifyTls(certRaw,keyRaw,chainRaw,hostname,now=Date.now()) {
  const chain=[...certificates(certRaw),...(chainRaw?certificates(chainRaw):[])],leaf=chain[0];
  need(leaf.checkHost(hostname)===hostname,'tls_name_changed');
  for(const item of chain)need(now>=Date.parse(item.validFrom)&&now<=Date.parse(item.validTo),'tls_expired');
  if(chain.length>1)need(leaf.checkIssued(chain[1])&&leaf.verify(chain[1].publicKey),'tls_chain_invalid');
  const key=crypto.createPrivateKey(keyRaw);
  need(leaf.checkPrivateKey(key),'tls_identity_changed');
  need(key.asymmetricKeyType==='ec'&&key.asymmetricKeyDetails?.namedCurve==='prime256v1','tls_key_algorithm');
  return {fingerprint:leaf.fingerprint256,notAfter:Date.parse(leaf.validTo)};
}

async function production(config) {return import(pathToFileURL(path.join(config.source_root,'ui/netclaw-visual/src/hud-server/protected-server.js')).href);}

function hudConfig(input,assets) {
  return {schemaVersion:1,installationId:input.installation_id,home:input.home,kind:'openclaw',origin:input.origin,host:'127.0.0.1',port:input.port,dist:input.dist,manifest:assets.path,manifestSha256:assets.sha256,access:{mode:'open-lab'}};
}

/** Load and verify one Border's complete private binding. Starts nothing. */
export async function loadOwned(config,{checkRunning=true,now=Date.now()}={}) {
  need(nodeQualified(),'qualified_node_required');
  privateDirectory(config.state_dir);
  need(config.node_sha256===hash(boundedFile(fs.realpathSync(process.execPath),256*1024*1024)),'node_changed');
  verifySource(config,{checkRunning});
  pinned(config.assets.path,config.assets.sha256);
  const hudRaw=pinned(config.hud.path,config.hud.sha256);
  const {readProtectedServerConfig}=await production(config);
  const hud=readProtectedServerConfig(config.hud.path);
  const expected=hudConfig(config,config.assets);
  need(canonical(strictJson(hudRaw.toString('utf8')))===canonical(expected),'hud_config_changed');
  need(hud.dist===config.dist&&hud.manifest===config.assets.path&&hud.manifestSha256===config.assets.sha256&&!hud.workspace,'production_assets_changed');
  const {hostname}=parseOrigin(config.origin);
  const certificate=pinned(config.tls.cert_file,config.tls.cert_sha256,false,64*1024);
  const chain=config.tls.chain_file?pinned(config.tls.chain_file,config.tls.chain_sha256,false,64*1024):null;
  const key=pinned(config.tls.key_file,config.tls.key_sha256,true,16*1024);
  const tls=verifyTls(certificate,key,chain,hostname,now);
  // Signed manifest: the node for this installation must carry exactly this origin.
  const manifestEnvelope=json(config.manifest_file);
  const anchor=boundedFile(config.anchor_certificate_file,16384).toString('utf8');
  const {verifyClusterDescriptor}=await import(pathToFileURL(path.join(config.source_root,'ui/netclaw-visual/src/shared/cluster-binding.js')).href);
  const node=manifestEnvelope.manifest?.nodes?.find(n=>n.installation_id===config.installation_id);
  need(node&&hud.cluster,'cluster_profile_required');
  need(node.endpoints.https===config.origin&&node.endpoints.wss===config.origin.replace(/^https:/,'wss:')+'/mobile/ws','manifest_endpoint_changed');
  need(hud.cluster.cluster_id===config.cluster.cluster_id&&hud.cluster.generation===config.cluster.generation&&hud.cluster.anchor_key_id===config.cluster.anchor_key_id,'cluster_profile_changed');
  await verifyClusterDescriptor({schema_version:1,mode:'cluster',...config.cluster,manifest_revision:manifestEnvelope.manifest.revision,node_id:node.node_id,installation_id:node.installation_id,manifest:manifestEnvelope,anchor_certificate:anchor,anchor_key_id:config.cluster.anchor_key_id,authority:{state:'no_quorum',leader_node_id:null,epoch:null,observed_at_ms:Date.now()}},{acceptedAnchor:config.cluster.anchor_key_id,origin:config.origin,now});
  return {config,hud,certificate,chain,key,tls,node};
}

/** Compute every pin and write <state_dir>/{assets,hud,ingress}.json; then run the full check. */
export async function prepare(inputFile) {
  const input=readInput(inputFile),state=input.state_dir;
  privateDirectory(state);
  const assets=buildProtectedManifest(input.dist),assetsFile=path.join(state,'assets.json');
  writeNew(assetsFile,assets);
  const assetsPin={path:assetsFile,sha256:hash(Buffer.from(canonical(assets)))};
  const hudFile=path.join(state,'hud.json'),hud=hudConfig(input,assetsPin);
  writeNew(hudFile,hud);
  const t=input.tls;
  const config={schema_version:1,...Object.fromEntries(Object.keys(input).filter(k=>!['source_manifest_file','tls'].includes(k)).map(k=>[k,input[k]])),
    assets:assetsPin,hud:{path:hudFile,sha256:hash(Buffer.from(canonical(hud)))},
    source_manifest:{path:input.source_manifest_file,sha256:hash(boundedFile(input.source_manifest_file,8*1024*1024,true))},
    node_sha256:hash(boundedFile(fs.realpathSync(process.execPath),256*1024*1024)),
    tls:{cert_file:t.cert_file,cert_sha256:hash(boundedFile(t.cert_file,64*1024)),chain_file:t.chain_file,chain_sha256:t.chain_file?hash(boundedFile(t.chain_file,64*1024)):null,
         key_file:t.key_file,key_sha256:hash(boundedFile(t.key_file,16*1024,true))}};
  const ingressFile=path.join(state,'ingress.json');
  writeNew(ingressFile,config);
  await loadOwned(readIngress(ingressFile),{checkRunning:false});
  return {prepared:true,ingress:ingressFile,listener_started:false};
}

/** Native clients may omit Origin; browser requests must be exact same-origin. Peers are public. */
export function validateUpgrade(request, config, head=Buffer.alloc(0)) {
  const once=name=>request.rawHeaders.filter((_,i)=>i%2===0&&request.rawHeaders[i].toLowerCase()===name).length===1;
  need(request.method==='GET'&&request.url==='/mobile/ws'&&head.length<=65536,'upgrade_refused');
  need(once('host')&&request.headers.host===new URL(config.origin).host&&once('upgrade')&&request.headers.upgrade.toLowerCase()==='websocket'&&once('connection')&&request.headers.connection.toLowerCase().split(',').map(s=>s.trim()).includes('upgrade'),'upgrade_refused');
  need(once('sec-websocket-key')&&/^[A-Za-z0-9+/]{22}==$/.test(request.headers['sec-websocket-key'])&&once('sec-websocket-version')&&request.headers['sec-websocket-version']==='13','upgrade_refused');
  need(request.headers.origin===undefined||once('origin')&&request.headers.origin===config.origin,'upgrade_origin_refused');
  need(!['authorization','proxy-authorization','transfer-encoding','content-length','sec-websocket-protocol'].some(k=>request.headers[k]!==undefined),'upgrade_header_refused');
}

export function bridgeUpgrade(request,socket,head,row,sockets) {
  try {validateUpgrade(request,row.config,head);} catch {socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');return;}
  if(sockets.size>=32){socket.destroy();return;}
  let upstream;const close=()=>{socket.destroy();upstream?.destroy();};sockets.add(socket);socket.once('close',()=>{sockets.delete(socket);upstream?.destroy();});socket.on('error',close);
  const headers={Host:new URL(row.config.origin).host,Connection:'Upgrade',Upgrade:'websocket','Sec-WebSocket-Key':request.headers['sec-websocket-key'],'Sec-WebSocket-Version':'13',...(request.headers.origin?{Origin:request.headers.origin}:{})};
  const outbound=http.request({host:'127.0.0.1',port:row.config.edge_ws_port,method:'GET',path:'/mobile/ws',headers,timeout:5000,maxHeaderSize:16384});
  const timer=setTimeout(()=>{outbound.destroy();close();},5000);timer.unref();
  outbound.once('error',()=>{clearTimeout(timer);close();});outbound.once('response',()=>{clearTimeout(timer);outbound.destroy();close();});
  outbound.once('upgrade',(response,peer,extra)=>{
    clearTimeout(timer);outbound.setTimeout(0);upstream=peer;
    const expected=crypto.createHash('sha1').update(request.headers['sec-websocket-key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    if(response.statusCode!==101||response.headers['sec-websocket-accept']!==expected||response.headers.upgrade?.toLowerCase()!=='websocket'){close();return;}
    socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+expected+'\r\n\r\n');
    let bytes=head.length+extra.length;const bound=data=>{bytes+=data.length;if(bytes>16*1024*1024)close();};
    for(const stream of [socket,peer]){stream.setTimeout(120000,close);stream.on('error',close);stream.on('data',bound);}
    peer.once('close',()=>socket.destroy());if(head.length)peer.write(head);if(extra.length)socket.write(extra);socket.pipe(peer);peer.pipe(socket);
  });outbound.end();
}

/**
 * Public front. The product handler admits only loopback peers, so this process does the
 * equivalent exact checks itself (Host, Origin, sec-fetch-site, method, size, headers) and then
 * proxies each request over a loopback hop to the in-process product server, with Host rewritten
 * to the configured authority. The product handler is never given a spoofed peer address.
 */
const HOP_BY_HOP=new Set(['connection','keep-alive','proxy-authenticate','proxy-authorization','proxy-connection','te','trailer','transfer-encoding','upgrade']);
export const FRONT_LIMITS=Object.freeze({body:1024*1024,url:4096,headers:100,requestMs:30000});
const refuse=(res,status,code)=>{if(res.headersSent){res.destroy();return;}const body=JSON.stringify({code});res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Content-Length':Buffer.byteLength(body),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Connection':'close'});res.end(body);};

/** Returns null when the request may proceed, else {status, code}. */
export function frontCheck(req,config) {
  const once=name=>{let n=0;for(let i=0;i<req.rawHeaders.length;i+=2)if(req.rawHeaders[i].toLowerCase()===name)n++;return n===1;};
  const host=new URL(config.origin).host;
  if(!once('host')||req.headers.host!==host)return {status:403,code:'ingress_refused'};
  if(req.headers.origin!==undefined&&(!once('origin')||req.headers.origin!==config.origin))return {status:403,code:'ingress_refused'};
  if(req.headers['sec-fetch-site']==='cross-site')return {status:403,code:'ingress_refused'};
  if(req.rawHeaders.length/2>FRONT_LIMITS.headers)return {status:431,code:'headers_refused'};
  if(typeof req.url!=='string'||!req.url.startsWith('/')||req.url.startsWith('//')||req.url.length>FRONT_LIMITS.url||/[\\#\u0000- \u007f]/.test(req.url))return {status:404,code:'route_unavailable'};
  if(!['GET','HEAD','POST','DELETE'].includes(req.method))return {status:405,code:'method_refused'};
  if(req.headers.upgrade!==undefined)return {status:403,code:'ingress_refused'};
  const length=req.headers['content-length'];
  if(length!==undefined&&(!/^[0-9]{1,10}$/.test(length)||Number(length)>FRONT_LIMITS.body))return {status:413,code:'body_too_large'};
  return null;
}

export function proxyRequest(req,res,config,upstreamPort) {
  const refused=frontCheck(req,config);
  if(refused){req.resume();refuse(res,refused.status,refused.code);return;}
  const headers={};
  for(let i=0;i<req.rawHeaders.length;i+=2){
    const name=req.rawHeaders[i].toLowerCase(),value=req.rawHeaders[i+1];
    if(HOP_BY_HOP.has(name)||name==='host')continue;
    headers[name]=name in headers?headers[name]+', '+value:value;
  }
  headers.host=new URL(config.origin).host;
  headers.connection='close';
  const upstream=http.request({host:'127.0.0.1',port:upstreamPort,method:req.method,path:req.url,headers,agent:false,timeout:FRONT_LIMITS.requestMs,maxHeaderSize:16384});
  const fail=()=>{upstream.destroy();refuse(res,502,'protected_service_unavailable');};
  upstream.once('timeout',fail);upstream.once('error',fail);
  res.once('close',()=>upstream.destroy());
  upstream.once('response',response=>{
    const out={};
    for(let i=0;i<response.rawHeaders.length;i+=2){
      const name=response.rawHeaders[i].toLowerCase();
      if(HOP_BY_HOP.has(name))continue;
      out[name]=name in out?[].concat(out[name],response.rawHeaders[i+1]):response.rawHeaders[i+1];
    }
    res.writeHead(response.statusCode,out);
    let sent=0;
    response.on('data',chunk=>{sent+=chunk.length;if(sent>64*1024*1024){response.destroy();res.destroy();}});
    response.once('error',()=>res.destroy());
    response.pipe(res);
  });
  let received=0;
  req.on('data',chunk=>{received+=chunk.length;if(received>FRONT_LIMITS.body){req.unpipe(upstream);upstream.destroy();refuse(res,413,'body_too_large');}});
  req.once('error',()=>upstream.destroy());
  req.pipe(upstream);
}

/** The public listener (https when tls is given; plain http only for loopback tests). */
export function createFront(config,upstreamPort,tls=null) {
  const options={maxHeaderSize:16384,headersTimeout:10000,requestTimeout:FRONT_LIMITS.requestMs,keepAliveTimeout:5000};
  const sockets=new Set();
  const handler=(req,res)=>proxyRequest(req,res,config,upstreamPort);
  const server=tls?https.createServer({...options,...tls,minVersion:'TLSv1.3'},handler):http.createServer(options,handler);
  server.maxConnections=32;
  server.on('clientError',(_e,s)=>s.destroy());server.on('tlsClientError',(_e,s)=>s.destroy());
  server.on('upgrade',(req,socket,head)=>bridgeUpgrade(req,socket,head,{config},sockets));
  // Upgraded sockets are not covered by closeAllConnections(); stop paths must call this.
  server.destroyBridges=()=>{for(const socket of sockets)socket.destroy();};
  server.once('close',server.destroyBridges);
  return server;
}

export async function serve(ingressFile) {
  const config=readIngress(ingressFile),row=await loadOwned(config),{createProtectedServer}=await production(config);
  const identity={schema_version:1,pid:process.pid,origin:config.origin,installation_id:config.installation_id,bind:config.bind,port:config.port};
  const stamp=Date.now()+'-'+process.pid;
  writeNew(path.join(config.state_dir,'serve-'+stamp+'.claim.json'),{...identity,at_ms:Date.now()});
  const listeners=[];let stopped=false;
  const stop=()=>{if(stopped)return;stopped=true;for(const server of listeners){server.close();server.closeAllConnections();server.destroyBridges?.();}};
  try {
    // Internal product server: loopback only, ephemeral port, reachable only through the front.
    const internal=createProtectedServer({...row.hud,authority:new URL(config.origin).host});
    listeners.push(internal);internal.listen(0,'127.0.0.1');await once(internal,'listening');
    const upstreamPort=internal.address().port;
    const front=createFront(config,upstreamPort,{cert:row.chain?Buffer.concat([row.certificate,Buffer.from('\n'),row.chain]):row.certificate,key:row.key});
    listeners.push(front);front.listen(config.port,config.bind);await once(front,'listening');
    writeNew(path.join(config.state_dir,'listening-'+stamp+'.json'),{...identity,at_ms:Date.now(),execution_ready:false,tls_not_after_ms:row.tls.notAfter,internal:'127.0.0.1:'+upstreamPort});
    process.once('SIGTERM',stop);process.once('SIGINT',stop);
    let timer;
    if(process.env.NETCLAW_INGRESS_LIFETIME_S!==undefined){
      const lifetimeSeconds=Number(process.env.NETCLAW_INGRESS_LIFETIME_S);
      if(!Number.isInteger(lifetimeSeconds)||lifetimeSeconds<60||lifetimeSeconds>5400)throw Error('invalid_ingress_lifetime');
      timer=setTimeout(stop,lifetimeSeconds*1000);timer.unref();
    }
    await Promise.all(listeners.map(s=>once(s,'close')));if(timer)clearTimeout(timer);
    writeNew(path.join(config.state_dir,'stopped-'+stamp+'.json'),{...identity,at_ms:Date.now()});
  } catch(error){stop();throw error;}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    need(process.argv.length===4&&['prepare','check','serve'].includes(process.argv[2]),'usage: hud_ingress_r09.mjs prepare INPUT.json | check INGRESS.json | serve INGRESS.json');
    const action=process.argv[2],file=process.argv[3];
    if(action==='prepare')console.log(JSON.stringify(await prepare(file)));
    else if(action==='check'){await loadOwned(readIngress(file));console.log(JSON.stringify({configuration_valid:true,listener_started:false}));}
    else await serve(file);
  } catch(error){console.error('R09 HUD ingress refused: '+(error&&error.message||'error')+'. Preserve configuration and inspect.');process.exitCode=1;}
}
