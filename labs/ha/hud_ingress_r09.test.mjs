import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import http from 'node:http';
import net from 'node:net';
import {once} from 'node:events';
import {validateUpgrade,verifyTls,verifySource,loadOwned,parseOrigin,readInput,readIngress,nodeQualified,canonical,createFront,frontCheck,FRONT_LIMITS,frontTimeout} from './hud_ingress_r09.mjs';

const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const temp=()=>fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'netclaw-r09-ingress-')));
const private700=d=>{fs.mkdirSync(d,{recursive:true,mode:0o700});fs.chmodSync(d,0o700);return d;};

/** Self-signed EC P-256 certificate through python `cryptography` (already a repo dependency). */
function tlsPair(dir,{name='nne1-abc123.example.test',days=3,backdate=0}={}) {
  const python=process.env.NETCLAW_TEST_PYTHON||'python3';
  execFileSync(python,['-c',String.raw`
import sys,datetime
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.x509.oid import NameOID
d,name,days,back=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
key=ec.generate_private_key(ec.SECP256R1())
now=datetime.datetime.now(datetime.timezone.utc)
subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
  .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=back+1))
  .not_valid_after(now+datetime.timedelta(days=days-back*2 if back else days))
  .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]),False).sign(key,hashes.SHA256()))
open(d+'/cert.pem','wb').write(cert.public_bytes(serialization.Encoding.PEM))
open(d+'/key.pem','wb').write(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
`,dir,name,String(days),String(backdate)]);
  return {cert:fs.readFileSync(path.join(dir,'cert.pem')),key:fs.readFileSync(path.join(dir,'key.pem'))};
}

test('origin is exactly https://<dns-name> without userinfo, path, query or IP literals',()=>{
  assert.deepEqual(parseOrigin('https://nne1-abc123.automateyournetwork.com'),{host:'nne1-abc123.automateyournetwork.com',hostname:'nne1-abc123.automateyournetwork.com',origin:'https://nne1-abc123.automateyournetwork.com'});
  for(const bad of ['http://x.example','https://x.example/','https://x.example/path','https://u:p@x.example','https://127.0.0.1','https://[::1]','x.example',undefined,null,5])assert.throws(()=>parseOrigin(bad),/invalid_origin|Invalid URL/);
});

const origin='https://nne1-abc123.automateyournetwork.com';
function request(extra={},peer='203.0.113.9') {
  const headers={host:'nne1-abc123.automateyournetwork.com',connection:'Upgrade',upgrade:'websocket','sec-websocket-key':'dGhlIHNhbXBsZSBub25jZQ==','sec-websocket-version':'13',...extra};
  return {method:'GET',url:'/mobile/ws',socket:{remoteAddress:peer},headers,rawHeaders:Object.entries(headers).flat()};
}
test('exact same-origin and native-originless WSS handshakes from public peers are allowed',()=>{
  validateUpgrade(request(),{origin});validateUpgrade(request({origin}),{origin});validateUpgrade(request({},'2001:db8::1'),{origin});
});
for(const [name,change] of [
  ['cross-origin',r=>{r.headers.origin='https://evil.example';r.rawHeaders.push('origin',r.headers.origin);}],
  ['sibling Border Origin',r=>{r.headers.origin='https://ew1-abc123.automateyournetwork.com';r.rawHeaders.push('origin',r.headers.origin);}],
  ['explicit-port Origin',r=>{r.headers.origin=origin+':443';r.rawHeaders.push('origin',r.headers.origin);}],
  ['foreign Host',r=>r.headers.host='ew1-abc123.automateyournetwork.com'],
  ['port-suffixed Host',r=>r.headers.host+=':443'],
  ['duplicate Host',r=>r.rawHeaders.push('Host','nne1-abc123.automateyournetwork.com')],
  ['proxy route',r=>r.url='http://localhost:42001/mobile/ws'],
  ['query route',r=>r.url='/mobile/ws?token=anything'],
  ['wrong method',r=>r.method='POST'],
  ['HTTP body',r=>r.headers['content-length']='10'],
  ['forwarded credential',r=>r.headers.authorization='Bearer fixture'],
  ['subprotocol',r=>r.headers['sec-websocket-protocol']='x'],
  ['invalid websocket key',r=>r.headers['sec-websocket-key']='bad'],
  ['wrong version',r=>r.headers['sec-websocket-version']='8'],
  ['not an upgrade',r=>r.headers.upgrade='h2c'],
])test('WSS refuses '+name,()=>{const r=request();change(r);assert.throws(()=>validateUpgrade(r,{origin}));});
test('WSS refuses excessive pre-upgrade bytes',()=>assert.throws(()=>validateUpgrade(request(),{origin},Buffer.alloc(65537))));
test('an explicit non-default port origin (test topology) matches its own Host exactly',()=>{
  const o='https://localhost:41001';
  validateUpgrade(request({host:'localhost:41001'}),{origin:o});
  assert.throws(()=>validateUpgrade(request({host:'localhost'}),{origin:o}));
});

test('TLS requires the DNS name, an unexpired matching EC P-256 key and a valid chain',()=>{
  const dir=temp();
  try {
    const {cert,key}=tlsPair(dir);
    const result=verifyTls(cert,key,null,'nne1-abc123.example.test');
    assert.match(result.fingerprint,/^([A-F0-9]{2}:){31}[A-F0-9]{2}$/);
    assert.throws(()=>verifyTls(cert,key,null,'ew1-abc123.example.test'),/tls_name_changed/);
    assert.throws(()=>verifyTls(cert,key,null,'nne1-abc123.example.test',Date.now()+10*24*3600*1000),/tls_expired/);
    assert.throws(()=>verifyTls(cert,key,null,'nne1-abc123.example.test',Date.now()-10*24*3600*1000),/tls_expired/);
    const other=tlsPair(temp());
    assert.throws(()=>verifyTls(cert,other.key,null,'nne1-abc123.example.test'),/tls_identity_changed/);
    // A chain that did not issue the leaf is refused.
    assert.throws(()=>verifyTls(cert,key,other.cert,'nne1-abc123.example.test'),/tls_chain_invalid/);
    assert.throws(()=>verifyTls(Buffer.from('not a certificate'),key,null,'x.example'),/tls_certificate_required/);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});

test('TLS refuses a non-P-256 key even when it matches',()=>{
  const dir=temp();
  try {
    execFileSync(process.env.NETCLAW_TEST_PYTHON||'python3',['-c',String.raw`
import sys,datetime
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.x509.oid import NameOID
d=sys.argv[1];key=ec.generate_private_key(ec.SECP384R1());now=datetime.datetime.now(datetime.timezone.utc)
s=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'x.example.test')])
c=(x509.CertificateBuilder().subject_name(s).issuer_name(s).public_key(key.public_key()).serial_number(1)
  .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=1))
  .add_extension(x509.SubjectAlternativeName([x509.DNSName('x.example.test')]),False).sign(key,hashes.SHA256()))
open(d+'/c.pem','wb').write(c.public_bytes(serialization.Encoding.PEM))
open(d+'/k.pem','wb').write(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
`,dir]);
    assert.throws(()=>verifyTls(fs.readFileSync(path.join(dir,'c.pem')),fs.readFileSync(path.join(dir,'k.pem')),null,'x.example.test'),/tls_key_algorithm/);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});

test('Node qualification: 24.19+, 25.x, 26.1+; refuses older and 26.0',()=>{
  for(const ok of ['24.19.0','24.20.1','25.3.0','26.1.0','27.0.0'])assert.equal(nodeQualified(ok),true,ok);
  for(const bad of ['22.12.0','24.18.9','23.9.0','26.0.5'])assert.equal(nodeQualified(bad),false,bad);
});

/** A minimal frozen source tree + pinned config shell sufficient to reach the asset/source pins. */
function frozen() {
  const root=temp(),source=path.join(root,'source'),state=private700(path.join(root,'state'));
  const files={'labs/ha/hud_ingress_r09.mjs':'// stand-in\n','ui/netclaw-visual/dist/index.html':'<html></html>\n'};
  for(const [name,body] of Object.entries(files)){
    const file=path.join(source,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,body);fs.chmodSync(file,0o400);
  }
  const lock=d=>{for(const e of fs.readdirSync(d,{withFileTypes:true}))if(e.isDirectory())lock(path.join(d,e.name));fs.chmodSync(d,0o500);};
  lock(source);
  const manifestFile=path.join(root,'source-manifest.json');
  fs.writeFileSync(manifestFile,canonical({schemaVersion:1,files:Object.fromEntries(Object.entries(files).map(([k,v])=>[k,hash(v)]))}),{mode:0o600});
  const assetsFile=path.join(state,'assets.json');fs.writeFileSync(assetsFile,canonical({schemaVersion:1,entry:'index.html',files:[]}),{mode:0o600});
  const hudFile=path.join(state,'hud.json');fs.writeFileSync(hudFile,'{}',{mode:0o600});
  const dir=temp();const {cert,key}=tlsPair(dir);
  const certFile=path.join(root,'cert.pem'),keyFile=path.join(root,'key.pem');
  fs.writeFileSync(certFile,cert);fs.writeFileSync(keyFile,key,{mode:0o600});
  const config={schema_version:1,origin:'https://nne1-abc123.example.test',bind:'127.0.0.1',port:44301,installation_id:'11111111-1111-4111-8111-111111111111',
    home:path.join(root,'home'),source_root:source,dist:path.join(source,'ui/netclaw-visual/dist'),edge_ws_port:44302,
    manifest_file:path.join(root,'manifest.json'),anchor_certificate_file:path.join(root,'root.crt'),anchor_key_id:'a'.repeat(64),
    cluster:{cluster_id:'22222222-2222-4222-8222-222222222222',generation:'33333333-3333-4333-8333-333333333333',anchor_key_id:'a'.repeat(64)},
    tls:{cert_file:certFile,cert_sha256:hash(cert),chain_file:null,chain_sha256:null,key_file:keyFile,key_sha256:hash(key)},
    state_dir:state,assets:{path:assetsFile,sha256:hash(fs.readFileSync(assetsFile))},hud:{path:hudFile,sha256:hash(fs.readFileSync(hudFile))},
    source_manifest:{path:manifestFile,sha256:hash(fs.readFileSync(manifestFile))},
    node_sha256:hash(fs.readFileSync(fs.realpathSync(process.execPath)))};
  const cleanup=()=>{const unlock=d=>{try{fs.chmodSync(d,0o700);for(const e of fs.readdirSync(d,{withFileTypes:true}))if(e.isDirectory())unlock(path.join(d,e.name));}catch{}};unlock(source);fs.rmSync(root,{recursive:true,force:true});fs.rmSync(dir,{recursive:true,force:true});};
  return {root,source,state,config,assetsFile,manifestFile,cleanup};
}

test('a frozen source closure verifies; a changed, extra or writable file is refused',()=>{
  const f=frozen();
  try {
    verifySource(f.config,{checkRunning:false});
    const target=path.join(f.source,'ui/netclaw-visual/dist/index.html');
    fs.chmodSync(path.dirname(target),0o700);fs.chmodSync(target,0o600);
    assert.throws(()=>verifySource(f.config,{checkRunning:false}),/source_writable/);
    fs.writeFileSync(target,'<html>tampered</html>\n');fs.chmodSync(target,0o400);fs.chmodSync(path.dirname(target),0o500);
    assert.throws(()=>verifySource(f.config,{checkRunning:false}),/pinned_file_changed/);
  } finally {f.cleanup();}
});

test('a source file outside the manifest is refused',()=>{
  const f=frozen();
  try {
    const dir=path.join(f.source,'ui/netclaw-visual/dist');fs.chmodSync(dir,0o700);
    fs.writeFileSync(path.join(dir,'extra.js'),'x');fs.chmodSync(path.join(dir,'extra.js'),0o400);fs.chmodSync(dir,0o500);
    assert.throws(()=>verifySource(f.config,{checkRunning:false}),/source_closure_changed/);
  } finally {f.cleanup();}
});

test('the running ingress must be the frozen copy',()=>{
  const f=frozen();
  try {assert.throws(()=>verifySource(f.config,{checkRunning:true}),/frozen_ingress_required/);} finally {f.cleanup();}
});

test('a tampered asset manifest is refused before anything is served',async()=>{
  const f=frozen();
  try {
    fs.writeFileSync(f.assetsFile,canonical({schemaVersion:1,entry:'index.html',files:[{path:'assets/evil.js',sha256:'0'.repeat(64),size:1}]}));
    await assert.rejects(loadOwned(f.config,{checkRunning:false}),/pinned_file_changed/);
  } finally {f.cleanup();}
});

test('a changed node binary pin is refused',async()=>{
  const f=frozen();
  try {await assert.rejects(loadOwned({...f.config,node_sha256:'1'.repeat(64)},{checkRunning:false}),/node_changed/);} finally {f.cleanup();}
});

test('a non-private state directory is refused',async()=>{
  const f=frozen();
  try {fs.chmodSync(f.state,0o755);await assert.rejects(loadOwned(f.config,{checkRunning:false}),/private_directory_required/);} finally {f.cleanup();}
});

test('ingress configuration is exact: unknown, missing or malformed fields are refused',()=>{
  const f=frozen();
  try {
    const write=value=>{const file=path.join(f.state,'ingress-test-'+crypto.randomUUID()+'.json');fs.writeFileSync(file,JSON.stringify(value),{mode:0o600});return file;};
    assert.equal(readIngress(write(f.config)).origin,f.config.origin);
    assert.throws(()=>readIngress(write({...f.config,extra:1})),/ingress_config_invalid/);
    const {tls,...missing}=f.config;assert.throws(()=>readIngress(write(missing)),/ingress_config_invalid/);
    assert.throws(()=>readIngress(write({...f.config,origin:'http://x.example'})),/invalid_origin/);
    assert.throws(()=>readIngress(write({...f.config,port:f.config.edge_ws_port})),/port_collision/);
    assert.throws(()=>readIngress(write({...f.config,home:'relative'})),/absolute_path_required/);
    assert.throws(()=>readIngress(write({...f.config,tls:{...f.config.tls,cert_sha256:'bad'}})),/invalid_tls_pin/);
    assert.throws(()=>readIngress(write({...f.config,cluster:{...f.config.cluster,anchor_key_id:'b'.repeat(64)}})),/invalid_cluster/);
    const input={...f.config};for(const k of ['schema_version','assets','hud','source_manifest','node_sha256'])delete input[k];
    input.source_manifest_file=f.config.source_manifest.path;input.tls={cert_file:f.config.tls.cert_file,chain_file:null,key_file:f.config.tls.key_file};
    assert.equal(readInput(write(input)).origin,f.config.origin);
  } finally {f.cleanup();}
});

test('workspace is an optional pinned entry: absent keeps the exact shape, present must be an absolute path pin',()=>{
  const f=frozen();
  try {
    const write=value=>{const file=path.join(f.state,'ingress-ws-'+crypto.randomUUID()+'.json');fs.writeFileSync(file,JSON.stringify(value),{mode:0o600});return file;};
    const withPin={...f.config,workspace:{path:path.join(f.state,'workspace.json'),sha256:'c'.repeat(64)}};
    assert.equal(readIngress(write(withPin)).workspace.sha256,'c'.repeat(64));
    assert.throws(()=>readIngress(write({...withPin,workspace:{path:'relative',sha256:'c'.repeat(64)}})),/invalid_workspace_pin/);
    assert.throws(()=>readIngress(write({...withPin,workspace:{path:withPin.workspace.path,sha256:'bad'}})),/invalid_workspace_pin/);
    assert.throws(()=>readIngress(write({...withPin,workspace:{path:withPin.workspace.path,sha256:'c'.repeat(64),extra:1}})),/invalid_workspace_pin/);
    const input={...f.config};for(const k of ['schema_version','assets','hud','source_manifest','node_sha256'])delete input[k];
    input.source_manifest_file=f.config.source_manifest.path;input.tls={cert_file:f.config.tls.cert_file,chain_file:null,key_file:f.config.tls.key_file};
    assert.equal(readInput(write({...input,workspace:{path:withPin.workspace.path}})).workspace.path,withPin.workspace.path);
    assert.throws(()=>readInput(write({...input,workspace:{path:'relative'}})),/invalid_workspace_input/);
    assert.throws(()=>readInput(write({...input,workspace:{path:withPin.workspace.path,sha256:'c'.repeat(64)}})),/invalid_workspace_input/);
  } finally {f.cleanup();}
});

test('loopback hop idle timeout: long chat turns are not cut at 30 s, protected routes keep the short bound',()=>{
  assert.equal(frontTimeout('POST','/api/chat'),600000);
  assert.equal(frontTimeout('POST','/api/n2n/chat'),330000);
  assert.equal(frontTimeout('POST','/api/chat/conversations/abc.1:2/open'),135000);
  assert.equal(frontTimeout('GET','/api/hud/logs?q=x'),90000);
  assert.equal(frontTimeout('GET','/api/n2n'),90000);
  for(const route of ['/api/runtime','/api/hud/operations','/api/hud/operations/catalog','/api/hud/owner/session','/api/hud/mobile/enrollment','/api/hud/cluster','/'])
    assert.equal(frontTimeout('GET',route),FRONT_LIMITS.requestMs,route);
  assert.equal(frontTimeout('GET','/api/chat'),90000,'only the POST turn gets the long bound');
});

// ---- public front + loopback proxy -------------------------------------------------------

const AUTHORITY='nne1-abc123.example.test',ORIGIN='https://'+AUTHORITY;

/** Trivial stand-in for the product handler: records what it saw, enforces the product's loopback rule. */
async function mockProduct() {
  const seen=[];
  const server=http.createServer((req,res)=>{
    const loop=['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress);
    const row={method:req.method,url:req.url,host:req.headers.host,origin:req.headers.origin,loop,bytes:0,connection:req.headers.connection};
    seen.push(row);
    req.on('data',c=>{row.bytes+=c.length;});
    req.on('end',()=>{
      if(!loop||req.headers.host!==AUTHORITY){res.writeHead(403,{'content-type':'application/json'});res.end('{"code":"ingress_refused"}');return;}
      res.writeHead(201,{'content-type':'text/plain','x-product':'yes','keep-alive':'timeout=5','set-cookie':['a=1','b=2'],'cache-control':'no-store'});
      res.write('hello ');res.end('world '+row.bytes);
    });
  });
  server.listen(0,'127.0.0.1');await once(server,'listening');
  return {server,seen,port:server.address().port};
}
const config=edge=>({origin:ORIGIN,edge_ws_port:edge});
async function listening(server){server.listen(0,'127.0.0.1');await once(server,'listening');return server.address().port;}
function call(port,{method='GET',url='/',headers={},body=null,host=AUTHORITY}={}) {
  return new Promise((resolve,reject)=>{
    const h={host,...headers};if(host===null)delete h.host;
    const req=http.request({host:'127.0.0.1',port,method,path:url,headers:h,agent:false},res=>{
      const chunks=[];res.on('data',c=>chunks.push(c));res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,rawHeaders:res.rawHeaders,body:Buffer.concat(chunks).toString()}));res.on('error',reject);
    });
    req.on('error',reject);
    if(body)req.write(body);
    req.end();
  });
}
function raw(port,text) {
  return new Promise(resolve=>{
    const socket=net.connect(port,'127.0.0.1',()=>socket.write(text));
    const chunks=[];socket.on('data',c=>chunks.push(c));socket.on('close',()=>resolve(Buffer.concat(chunks).toString()));socket.on('error',()=>resolve(Buffer.concat(chunks).toString()));
    setTimeout(()=>socket.destroy(),1500).unref();
  });
}
async function withFront(fn,edge=1) {
  const product=await mockProduct(),front=createFront(config(edge),product.port);
  const port=await listening(front);
  try {await fn({product,front,port});} finally {front.close();front.closeAllConnections();product.server.close();product.server.closeAllConnections();}
}

test('a request through the public listener reaches the product handler as a loopback peer with the authority Host',()=>withFront(async({product,port})=>{
  const r=await call(port,{method:'POST',url:'/api/hud/operations?x=1',headers:{origin:ORIGIN,'content-type':'application/json'},body:'{"a":1}'});
  assert.equal(r.status,201);
  assert.equal(r.body,'hello world 7');
  assert.equal(r.headers['x-product'],'yes');
  assert.equal(r.headers['cache-control'],'no-store');
  assert.deepEqual(r.headers['set-cookie'],['a=1','b=2']);
  assert.equal(r.headers['keep-alive'],undefined,'hop-by-hop response header dropped');
  assert.equal(product.seen.length,1);
  const seen=product.seen[0];
  assert.equal(seen.loop,true);
  assert.equal(seen.host,AUTHORITY);
  assert.equal(seen.origin,ORIGIN);
  assert.equal(seen.url,'/api/hud/operations?x=1');
  assert.equal(seen.method,'POST');
  assert.equal(seen.bytes,7);
}));

test('Origin is preserved only when present; a request without Origin stays without one',()=>withFront(async({product,port})=>{
  await call(port,{});
  assert.equal(product.seen[0].origin,undefined);
}));

for(const [name,options] of [
  ['foreign Host',{host:'ew1-abc123.example.test'}],
  ['port-suffixed Host',{host:AUTHORITY+':443'}],
  ['IP Host',{host:'127.0.0.1'}],
  ['cross-origin Origin',{headers:{origin:'https://evil.example'}}],
  ['sibling Border Origin',{headers:{origin:'https://ew1-abc123.example.test'}}],
  ['cross-site fetch',{headers:{'sec-fetch-site':'cross-site'}}],
  ['PUT',{method:'PUT'}],
  ['PATCH',{method:'PATCH'}],
  ['double-slash route',{url:'//evil.example/x'}],
  ['fragment route',{url:'/x#y'}],
  ['backslash route',{url:'/x\\y'}],
])test('front refuses '+name+' without reaching the product handler',()=>withFront(async({product,port})=>{
  const r=await call(port,options);
  assert.ok([403,404,405].includes(r.status),String(r.status));
  assert.equal(product.seen.length,0);
}));

test('front refuses same-site and same-origin fetch metadata only as the product would allow',()=>withFront(async({product,port})=>{
  for(const site of ['same-origin','same-site','none'])assert.equal((await call(port,{headers:{'sec-fetch-site':site}})).status,201);
  assert.equal(product.seen.length,3);
}));

test('front refuses duplicate Host and duplicate Origin headers (raw)',()=>withFront(async({product,port})=>{
  const dupHost=await raw(port,`GET / HTTP/1.1\r\nHost: ${AUTHORITY}\r\nHost: ${AUTHORITY}\r\nConnection: close\r\n\r\n`);
  assert.match(dupHost,/^HTTP\/1\.1 (403|400)/);
  const dupOrigin=await raw(port,`GET / HTTP/1.1\r\nHost: ${AUTHORITY}\r\nOrigin: ${ORIGIN}\r\nOrigin: ${ORIGIN}\r\nConnection: close\r\n\r\n`);
  assert.match(dupOrigin,/^HTTP\/1\.1 (403|400)/);
  assert.equal(product.seen.length,0);
}));

test('front refuses a request that asks to upgrade on an ordinary route',()=>withFront(async({product,port})=>{
  const r=await raw(port,`GET / HTTP/1.1\r\nHost: ${AUTHORITY}\r\nConnection: close\r\nUpgrade: h2c\r\n\r\n`);
  assert.match(r,/^HTTP\/1\.1 (403|400|426)/);
  assert.equal(product.seen.length,0);
}));

test('frontCheck returns exact refusals and null for an allowed request',()=>{
  const req=(over={})=>{const headers={host:AUTHORITY,...(over.headers||{})};return {method:'GET',url:'/',headers,rawHeaders:Object.entries(headers).flat(),...over,headers};};
  assert.equal(frontCheck(req(),{origin:ORIGIN}),null);
  assert.deepEqual(frontCheck(req({headers:{host:'x.example'}}),{origin:ORIGIN}),{status:403,code:'ingress_refused'});
  assert.deepEqual(frontCheck(req({method:'PUT'}),{origin:ORIGIN}),{status:405,code:'method_refused'});
  assert.deepEqual(frontCheck(req({headers:{'content-length':String(FRONT_LIMITS.body+1)}}),{origin:ORIGIN}),{status:413,code:'body_too_large'});
  assert.deepEqual(frontCheck(req({headers:{'content-length':'-1'}}),{origin:ORIGIN}),{status:413,code:'body_too_large'});
  assert.deepEqual(frontCheck(req({url:'/'+'a'.repeat(FRONT_LIMITS.url)}),{origin:ORIGIN}),{status:404,code:'route_unavailable'});
});

test('the body bound: oversized Content-Length is refused before the product sees it',()=>withFront(async({product,port})=>{
  const r=await call(port,{method:'POST',url:'/api/hud/operations',headers:{'content-length':String(FRONT_LIMITS.body+1)},body:Buffer.alloc(16)});
  assert.equal(r.status,413);
  assert.equal(product.seen.length,0);
}));

test('the body bound: a chunked body past the limit is cut off, not buffered or forwarded whole',()=>withFront(async({product,port})=>{
  const total=3*FRONT_LIMITS.body;
  const result=await new Promise(resolve=>{
    const socket=net.connect(port,'127.0.0.1',()=>{
      socket.write(`POST /api/hud/operations HTTP/1.1\r\nHost: ${AUTHORITY}\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n`);
      const chunk=Buffer.alloc(65536,97);let sent=0;
      const pump=()=>{while(sent<total){if(!socket.write(`${chunk.length.toString(16)}\r\n`)||!socket.write(chunk)||!socket.write('\r\n')){sent+=chunk.length;return socket.once('drain',pump);}sent+=chunk.length;}socket.end('0\r\n\r\n');};
      pump();
    });
    const chunks=[];socket.on('data',c=>chunks.push(c));socket.on('close',()=>resolve(Buffer.concat(chunks).toString()));socket.on('error',()=>resolve(Buffer.concat(chunks).toString()));
    setTimeout(()=>{socket.destroy();resolve(Buffer.concat(chunks).toString());},4000).unref();
  });
  assert.ok(result===''||/^HTTP\/1\.1 (413|400|502)/.test(result),result.slice(0,60));
  for(const row of product.seen)assert.ok(row.bytes<2*FRONT_LIMITS.body,'forwarded '+row.bytes);
}));

test('the public listener keeps its 32-connection bound',()=>withFront(async({front})=>{assert.equal(front.maxConnections,32);}));

test('an unavailable product server fails closed with a 502, not a hang',async()=>{
  const dead=http.createServer();dead.listen(0,'127.0.0.1');await once(dead,'listening');const port=dead.address().port;dead.close();await once(dead,'close');
  const front=createFront(config(1),port),fport=await listening(front);
  try {const r=await call(fport,{});assert.equal(r.status,502);assert.match(r.body,/protected_service_unavailable/);} finally {front.close();front.closeAllConnections();}
});

test('the /mobile/ws upgrade still bridges to the Border edge port with exact validation',async()=>{
  const edge=http.createServer();
  const upgrades=[],edgeSockets=new Set();
  edge.on('upgrade',(req,socket)=>{
    edgeSockets.add(socket);upgrades.push({host:req.headers.host,origin:req.headers.origin});
    const accept=crypto.createHash('sha1').update(req.headers['sec-websocket-key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n');
    socket.on('data',d=>socket.write(d));
  });
  const edgePort=await listening(edge),product=await mockProduct();
  const front=createFront(config(edgePort),product.port),port=await listening(front);
  const handshake=(extra='',host=AUTHORITY)=>`GET /mobile/ws HTTP/1.1\r\nHost: ${host}\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n${extra}\r\n`;
  try {
    const echoed=await new Promise(resolve=>{
      const socket=net.connect(port,'127.0.0.1',()=>socket.write(handshake()));
      let buffer='';socket.on('data',d=>{buffer+=d.toString('latin1');if(buffer.includes('\r\n\r\n')&&!buffer.endsWith('ping'))return;if(buffer.endsWith('ping'))socket.destroy();});
      socket.once('close',()=>resolve(buffer));
      socket.once('data',()=>setTimeout(()=>socket.write('ping'),100));
      setTimeout(()=>{socket.destroy();},2000).unref();
    });
    assert.match(echoed,/^HTTP\/1\.1 101 Switching Protocols/);
    assert.match(echoed,/ping$/);
    assert.equal(upgrades[0].host,AUTHORITY);
    const bad=await raw(port,handshake(`Origin: https://evil.example\r\n`));
    assert.match(bad,/^HTTP\/1\.1 403/);
    const wrongHost=await raw(port,handshake('','ew1-abc123.example.test'));
    assert.match(wrongHost,/^HTTP\/1\.1 403/);
    assert.equal(upgrades.length,1,'refused handshakes never reach the Border edge port');
    assert.equal(product.seen.length,0);
  } finally {front.close();front.closeAllConnections();front.destroyBridges();for(const s of edgeSockets)s.destroy();edge.close();edge.closeAllConnections();product.server.close();product.server.closeAllConnections();}
});

test('the front serves over TLS 1.3 with the configured identity and refuses older TLS',async()=>{
  const dir=temp();
  const {cert,key}=tlsPair(dir,{name:AUTHORITY});
  const product=await mockProduct(),front=createFront(config(1),product.port,{cert,key}),port=await listening(front);
  try {
    const tlsRequest=maxVersion=>new Promise((resolve,reject)=>{
      import('node:https').then(({default:https})=>{
        const req=https.request({host:'127.0.0.1',port,path:'/',method:'GET',headers:{host:AUTHORITY},ca:cert,servername:AUTHORITY,maxVersion,agent:false},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});
        req.on('error',reject);req.end();
      });
    });
    assert.equal(await tlsRequest('TLSv1.3'),201);
    await assert.rejects(tlsRequest('TLSv1.2'));
  } finally {front.close();front.closeAllConnections();product.server.close();product.server.closeAllConnections();fs.rmSync(dir,{recursive:true,force:true});}
});
