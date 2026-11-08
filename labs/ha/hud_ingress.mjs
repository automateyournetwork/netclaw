/** Private REAL rehearsal ingress. No listeners or writes on import. */
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
const canonical = value => value === null || typeof value !== 'object' ? JSON.stringify(value) : Array.isArray(value) ? '['+value.map(canonical).join(',')+']' : '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
const need = (condition, reason) => {if (!condition) throw Error(reason);};
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join() === keys.split(' ').sort().join();
const json = (file, limit=128*1024) => strictJson(boundedFile(file,limit,true).toString('utf8'));
const privateDirectory = directory => {noSymlink(directory); const s=fs.lstatSync(directory);need(s.isDirectory()&&s.uid===process.getuid()&&(s.mode&0o777)===0o700,'private_directory_required');};
function writeNew(file,value) {
  privateDirectory(path.dirname(file)); const fd=fs.openSync(file,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o600);
  try {fs.writeFileSync(fd,Buffer.from(canonical(value)));fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
}
function pinned(file,expected,privateFile=true,maximum=128*1024) {need(/^[a-f0-9]{64}$/.test(expected),'invalid_digest');const raw=boundedFile(file,maximum,privateFile);need(hash(raw)===expected,'pinned_file_changed');return raw;}

/** Production source, dependencies and built assets must be frozen together. */
export function readContext(root) {
  privateDirectory(root);
  const plan=json(path.join(root,'reviewed-plan.json'),8*1024*1024), source=path.join(root,'source');
  need(plan.root===root&&plan.schema_version===1&&hash(canonical(plan.source_files))===plan.source_sha256,'reviewed_source_changed');
  need(fileURLToPath(import.meta.url)===path.join(source,'labs/ha/hud_ingress.mjs'),'frozen_ingress_required');
  const [major,minor]=process.versions.node.split('.').map(Number);
  need(major===24&&minor>=19||major>=26&&!(major===26&&minor<1),'qualified_node_required');
  let count=0,total=0;
  const walk=directory=>{for(const entry of fs.readdirSync(directory,{withFileTypes:true})){const file=path.join(directory,entry.name);need(!entry.isSymbolicLink(),'source_alias_refused');if(entry.isDirectory())walk(file);else {need(entry.isFile(),'source_file_required');const relative=path.relative(source,file).split(path.sep).join('/');need(Object.hasOwn(plan.source_files,relative),'source_closure_changed');const raw=pinned(file,plan.source_files[relative],false,128*1024*1024);need(!(fs.statSync(file).mode&0o222),'source_writable');count++;total+=raw.length;need(count<=20000&&total<=512*1024*1024,'source_bound');}}};
  walk(source);need(count===Object.keys(plan.source_files).length,'source_closure_changed');
  const gateRaw=pinned(plan.fixture_gate_file,plan.fixture_gate_sha256),gate=strictJson(gateRaw.toString('utf8'));
  need(gate.class==='FIXTURE'&&gate.passed===true&&gate.source_sha256===plan.source_sha256,'fixture_gate_required');
  const materialized=json(path.join(root,'materialized.json'));
  need(materialized.profile_kind===2&&materialized.launch_schema===3,'ha_materialization_required');
  return {root,source,plan};
}

export function validateBindings(rows, plan, nodes) {
  need(Array.isArray(rows)&&rows.length===3&&Array.isArray(nodes)&&nodes.length===3,'three_borders_required');
  const installations=new Set(),certs=new Set(),ports=new Set();
  rows.forEach((row,i)=>{
    const {config,contract,cert}=row,node=nodes[i],expected='https://localhost:'+plan.ports.https[i];
    need(config.origin===expected&&node.endpoints.https===expected&&node.endpoints.wss==='wss://localhost:'+plan.ports.https[i]+'/mobile/ws','manifest_endpoint_changed');
    need(config.installationId===node.installation_id&&contract.installation_id===node.installation_id&&config.home===path.join(plan.root,'homes','border'+i),'node_identity_changed');
    need(config.schemaVersion===1&&config.kind==='openclaw'&&config.host==='127.0.0.1'&&config.port===plan.ports.https[i]&&config.access?.mode==='open-lab','hud_binding_changed');
    need(contract.schemaVersion===3&&contract.role==='border'&&contract.control_only===true&&contract.home===config.home&&contract.origin===config.origin&&contract.source_root===path.join(plan.root,'source')&&contract.environment.N2N_EDGE_WS_PORT===String(plan.ports.edge[i]),'role_contract_changed');
    need(!installations.has(node.installation_id)&&!certs.has(cert),'distinct_node_identity_required'); installations.add(node.installation_id);certs.add(cert);
    for(const port of [config.port,plan.ports.edge[i]]) {need(Number.isSafeInteger(port)&&port>=1024&&port<=65535&&!ports.has(port),'port_collision');ports.add(port);}
  });
}

function verifyCertificate(certRaw,caRaw,now=Date.now()) {
  const cert=new crypto.X509Certificate(certRaw),ca=new crypto.X509Certificate(caRaw);
  need(ca.ca&&cert.checkIssued(ca)&&cert.verify(ca.publicKey),'tls_identity_changed');
  need(cert.checkHost('localhost')==='localhost'&&cert.checkIP('127.0.0.1')==='127.0.0.1','tls_name_changed');
  for(const item of [cert,ca])need(now>=Date.parse(item.validFrom)&&now<=Date.parse(item.validTo),'tls_expired');
  return cert;
}
export function verifyTls(certRaw,keyRaw,caRaw,now=Date.now()) {
  const cert=verifyCertificate(certRaw,caRaw,now),key=crypto.createPrivateKey(keyRaw);
  need(cert.checkPrivateKey(key),'tls_identity_changed');
  need(key.asymmetricKeyType==='ec'&&key.asymmetricKeyDetails?.namedCurve==='prime256v1','tls_key_algorithm');
  return cert.fingerprint256;
}

async function production(context) {return import(pathToFileURL(path.join(context.source,'ui/netclaw-visual/src/hud-server/protected-server.js')).href);}
export function nodeIndex(name) {need(typeof name==='string'&&/^border[012]$/.test(name),'one_border_required');return Number(name.slice(-1));}
async function loadOwned(context,prepared,selected=null) {
  const {root,plan,source}=context,directory=path.join(root,'hud-ingress');privateDirectory(directory);
  const cfg=json(path.join(directory,'ingress.json'));
  need(exact(cfg,'schema_version run_id source_sha256 node_sha256 assets_sha256 ca_sha256 endpoints')&&cfg.schema_version===1&&cfg.run_id===plan.run_id&&cfg.source_sha256===plan.source_sha256,'ingress_changed');
  need(cfg.node_sha256===hash(boundedFile(fs.realpathSync(process.execPath),256*1024*1024)),'node_changed');
  pinned(path.join(directory,'assets.json'),cfg.assets_sha256);
  need(Array.isArray(cfg.endpoints)&&cfg.endpoints.length===3,'three_borders_required');
  const {readProtectedServerConfig}=await production(context),rows=[];
  for(let i=0;i<3;i++) {
    const record=cfg.endpoints[i];need(exact(record,'hud_sha256 contract_sha256 certificate_sha256 key_sha256'),'endpoint_config_changed');
    const configFile=path.join(directory,'border'+i+'.json');pinned(configFile,record.hud_sha256);
    // The coordinator's prepare/check validates every private binding. A serving
    // process loads only its own private runtime descriptor and HTTPS key.
    const active=selected===null||selected===i;
    const config=active?readProtectedServerConfig(configFile):json(configFile),contract=strictJson(pinned(path.join(root,'contracts','border'+i+'.json'),record.contract_sha256).toString('utf8'));
    need(config.dist===path.join(source,'ui/netclaw-visual/dist')&&config.manifest===path.join(directory,'assets.json')&&config.manifestSha256===cfg.assets_sha256&&!config.workspace,'production_assets_changed');
    const certificate=pinned(path.join(root,'https-pki','border'+i+'.crt'),record.certificate_sha256),key=active?pinned(path.join(root,'https-pki','border'+i+'.key'),record.key_sha256):undefined;
    const ca=pinned(path.join(root,'https-pki/https-ca.crt'),cfg.ca_sha256);
    if(active)verifyTls(certificate,key,ca);else verifyCertificate(certificate,ca);
    const cert=hash(new crypto.X509Certificate(certificate).publicKey.export({format:'der',type:'spki'}));
    rows.push({config,contract,certificate,key,cert});
  }
  const identity=path.join(root,'voters/cluster-identity'),manifest=json(path.join(identity,'manifest.json'));
  const {verifyClusterDescriptor}=await import(pathToFileURL(path.join(source,'ui/netclaw-visual/src/shared/cluster-binding.js')).href);
  for(const row of selected===null?rows:[rows[selected]]) {
    const node=manifest.manifest.nodes.find(n=>n.installation_id===row.config.installationId),cluster=row.config.cluster;
    need(node&&cluster,'cluster_profile_required');
    await verifyClusterDescriptor({schema_version:1,mode:'cluster',...cluster,manifest_revision:manifest.manifest.revision,node_id:node.node_id,installation_id:node.installation_id,manifest,anchor_certificate:boundedFile(path.join(identity,'root.crt'),16384,true).toString('utf8'),anchor_key_id:cluster.anchor_key_id,authority:{state:'no_quorum',leader_node_id:null,epoch:null,observed_at_ms:Date.now()}},{acceptedAnchor:cluster.anchor_key_id,origin:row.config.origin});
  }
  validateBindings(rows,plan,manifest.manifest.nodes);
  if(prepared)need(canonical(cfg)===canonical(prepared),'prepared_configuration_changed');
  return {rows,cfg,directory};
}

export async function prepare(root) {
  const context=readContext(root),{plan,source}=context,directory=path.join(root,'hud-ingress');
  // Explicit file preparation only. Existing descriptors must come from actual daemons.
  fs.mkdirSync(directory,{mode:0o700});
  const assets=buildProtectedManifest(path.join(source,'ui/netclaw-visual/dist'));writeNew(path.join(directory,'assets.json'),assets);
  const assetsSha=hash(canonical(assets)),endpoints=[];
  for(let i=0;i<3;i++) {
    const home=path.join(root,'homes','border'+i),profile=json(path.join(home,'netclaw-federation/protected-profile.json'));
    const config={schemaVersion:1,installationId:profile.identity.installation_id,home,kind:'openclaw',origin:'https://localhost:'+plan.ports.https[i],host:'127.0.0.1',port:plan.ports.https[i],dist:path.join(source,'ui/netclaw-visual/dist'),manifest:path.join(directory,'assets.json'),manifestSha256:assetsSha,access:{mode:'open-lab'}};
    writeNew(path.join(directory,'border'+i+'.json'),config);
    endpoints.push({hud_sha256:hash(canonical(config)),contract_sha256:hash(boundedFile(path.join(root,'contracts','border'+i+'.json'),128*1024,true)),certificate_sha256:hash(boundedFile(path.join(root,'https-pki','border'+i+'.crt'),16384,true)),key_sha256:hash(boundedFile(path.join(root,'https-pki','border'+i+'.key'),16384,true))});
  }
  const cfg={schema_version:1,run_id:plan.run_id,source_sha256:plan.source_sha256,node_sha256:hash(boundedFile(fs.realpathSync(process.execPath),256*1024*1024)),assets_sha256:assetsSha,ca_sha256:hash(boundedFile(path.join(root,'https-pki/https-ca.crt'),16384,true)),endpoints};
  writeNew(path.join(directory,'ingress.json'),cfg);await loadOwned(context,cfg);
  return {prepared:true,endpoints:3,listener_started:false};
}

/** Native clients may omit Origin; browser requests must be exact same-origin. */
export function validateUpgrade(request, config, head=Buffer.alloc(0)) {
  const once=name=>request.rawHeaders.filter((_,i)=>i%2===0&&request.rawHeaders[i].toLowerCase()===name).length===1;
  need(['127.0.0.1','::1','::ffff:127.0.0.1'].includes(request.socket.remoteAddress)&&request.method==='GET'&&request.url==='/mobile/ws'&&head.length<=65536,'upgrade_refused');
  need(once('host')&&request.headers.host===new URL(config.origin).host&&once('upgrade')&&request.headers.upgrade.toLowerCase()==='websocket'&&once('connection')&&request.headers.connection.toLowerCase().split(',').map(s=>s.trim()).includes('upgrade'),'upgrade_refused');
  need(once('sec-websocket-key')&&/^[A-Za-z0-9+/]{22}==$/.test(request.headers['sec-websocket-key'])&&once('sec-websocket-version')&&request.headers['sec-websocket-version']==='13','upgrade_refused');
  need(request.headers.origin===undefined||once('origin')&&request.headers.origin===config.origin,'upgrade_origin_refused');
  need(!['authorization','proxy-authorization','transfer-encoding','content-length','sec-websocket-protocol'].some(k=>request.headers[k]!==undefined),'upgrade_header_refused');
}

function bridgeUpgrade(request,socket,head,row,sockets) {
  try {validateUpgrade(request,row.config,head);} catch {socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n');return;}
  if(sockets.size>=32){socket.destroy();return;}
  let upstream;const close=()=>{socket.destroy();upstream?.destroy();};sockets.add(socket);socket.once('close',()=>{sockets.delete(socket);upstream?.destroy();});socket.on('error',close);
  const headers={Host:new URL(row.config.origin).host,Connection:'Upgrade',Upgrade:'websocket','Sec-WebSocket-Key':request.headers['sec-websocket-key'],'Sec-WebSocket-Version':'13',...(request.headers.origin?{Origin:request.headers.origin}:{})};
  const outbound=http.request({host:'127.0.0.1',port:Number(row.contract.environment.N2N_EDGE_WS_PORT),method:'GET',path:'/mobile/ws',headers,timeout:5000,maxHeaderSize:16384});
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

export async function serve(root,name) {
  const selected=nodeIndex(name),context=readContext(root),{rows,cfg,directory}=await loadOwned(context,undefined,selected),{createProtectedServer}=await production(context);
  const row=rows[selected],identity={schema_version:1,run_id:cfg.run_id,border:name,pid:process.pid,origin:row.config.origin,installation_id:row.config.installationId};
  writeNew(path.join(directory,'serve-'+name+'.claim.json'),{...identity,at_ms:Date.now()});
  const listeners=[],sockets=new Set();let stopped=false;
  const stop=()=>{if(stopped)return;stopped=true;for(const server of listeners){server.close();server.closeAllConnections();}for(const socket of sockets)socket.destroy();};
  try {
    {
      const productionServer=createProtectedServer(row.config);
      const server=https.createServer({cert:row.certificate,key:row.key,minVersion:'TLSv1.3',maxHeaderSize:16384,headersTimeout:10000,requestTimeout:30000,keepAliveTimeout:5000},(req,res)=>productionServer.emit('request',req,res));
      server.maxConnections=32;server.on('clientError',(_e,s)=>s.destroy());server.on('tlsClientError',(_e,s)=>s.destroy());server.on('upgrade',(req,socket,head)=>bridgeUpgrade(req,socket,head,row,sockets));
      listeners.push(server);server.listen(row.config.port,'127.0.0.1');await once(server,'listening');
    }
    writeNew(path.join(directory,'listening-'+name+'.json'),{...identity,at_ms:Date.now(),execution_ready:false});
    process.once('SIGTERM',stop);process.once('SIGINT',stop);
    const lifetimeSeconds=Number(process.env.NETCLAW_INGRESS_LIFETIME_S||1800);if(!Number.isInteger(lifetimeSeconds)||lifetimeSeconds<60||lifetimeSeconds>5400)throw Error('invalid_ingress_lifetime');
    const timer=setTimeout(stop,lifetimeSeconds*1000);timer.unref();
    await Promise.all(listeners.map(server=>once(server,'close')));clearTimeout(timer);
    writeNew(path.join(directory,'stopped-'+name+'.json'),{...identity,at_ms:Date.now()});
  } catch(error){stop();throw error;}
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    need(process.argv[2]==='serve'?process.argv.length===5:process.argv.length===4&&['prepare','check'].includes(process.argv[2]),'usage: hud_ingress.mjs prepare|check ROOT; hud_ingress.mjs serve ROOT border0|border1|border2');
    const action=process.argv[2],root=process.argv[3];
    if(action==='prepare')console.log(JSON.stringify(await prepare(root)));
    else if(action==='check'){const {rows}=await loadOwned(readContext(root));console.log(JSON.stringify({configuration_valid:true,endpoints:rows.length,listener_started:false}));}
    else await serve(root,process.argv[4]);
  } catch {console.error('R08 private HUD ingress refused; preserve owned configuration and inspect readiness.');process.exitCode=1;}
}
