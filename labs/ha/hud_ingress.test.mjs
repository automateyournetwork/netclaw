import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {validateBindings,validateUpgrade,verifyTls,readContext,nodeIndex} from './hud_ingress.mjs';

test('a serving process requires one explicit reviewed Border',()=>{
  for(const [name,index] of [['border0',0],['border1',1],['border2',2]])assert.equal(nodeIndex(name),index);
  for(const name of [undefined,null,'','all','border3','border0,border1','../border0',0])assert.throws(()=>nodeIndex(name),/one_border_required/);
});

function bindings() {
  const plan={root:'/private/owned/netclaw-r08-test',ports:{https:[41001,41002,41003],edge:[42001,42002,42003]}};
  const nodes=plan.ports.https.map((p,i)=>({installation_id:'installation'+i,endpoints:{https:'https://localhost:'+p,wss:'wss://localhost:'+p+'/mobile/ws'}}));
  const rows=nodes.map((n,i)=>({cert:'separate'+i,config:{schemaVersion:1,installationId:n.installation_id,home:path.join(plan.root,'homes','border'+i),kind:'openclaw',host:'127.0.0.1',port:plan.ports.https[i],origin:n.endpoints.https,access:{mode:'open-lab'}},contract:{schemaVersion:3,role:'border',control_only:true,installation_id:n.installation_id,home:path.join(plan.root,'homes','border'+i),origin:n.endpoints.https,source_root:path.join(plan.root,'source'),environment:{N2N_EDGE_WS_PORT:String(plan.ports.edge[i])}}}));
  return {plan,nodes,rows};
}
test('three production homes retain distinct ingress and edge bindings',()=>{const {plan,nodes,rows}=bindings();validateBindings(rows,plan,nodes);});
for(const [name,change] of [
  ['node swap',v=>v.rows[0].config.installationId=v.nodes[1].installation_id],
  ['foreign home',v=>v.rows[1].config.home='/private/retained/home'],
  ['public bind',v=>v.rows[0].config.host='0.0.0.0'],
  ['backend substitution',v=>v.rows[1].contract.environment.N2N_EDGE_WS_PORT='9999'],
  ['HTTPS substitution',v=>v.nodes[0].endpoints.https='https://untrusted.example'],
  ['WSS substitution',v=>v.nodes[0].endpoints.wss='wss://localhost:41002/mobile/ws'],
  ['shared TLS identity',v=>v.rows[1].cert=v.rows[0].cert],
  ['port overlap',v=>{v.plan.ports.edge[0]=41001;v.rows[0].contract.environment.N2N_EDGE_WS_PORT='41001';}],
  ['standalone contract',v=>v.rows[0].contract.schemaVersion=2],
])test('refuses '+name,()=>{const value=bindings();change(value);assert.throws(()=>validateBindings(value.rows,value.plan,value.nodes));});

const origin='https://localhost:41001';
function request(extra={}) {
  const headers={host:'localhost:41001',connection:'Upgrade',upgrade:'websocket','sec-websocket-key':'dGhlIHNhbXBsZSBub25jZQ==','sec-websocket-version':'13',...extra};
  return {method:'GET',url:'/mobile/ws',socket:{remoteAddress:'127.0.0.1'},headers,rawHeaders:Object.entries(headers).flat()};
}
test('exact same-origin and native-originless WSS handshakes are allowed',()=>{validateUpgrade(request(),{origin});validateUpgrade(request({origin}),{origin});});
for(const [name,change] of [
  ['cross-origin',r=>{r.headers.origin='https://evil.example';r.rawHeaders.push('origin',r.headers.origin);}],
  ['foreign Host',r=>r.headers.host='localhost:41002'],
  ['duplicate Host',r=>r.rawHeaders.push('Host','localhost:41001')],
  ['proxy route',r=>r.url='http://localhost:42001/mobile/ws'],
  ['query route',r=>r.url='/mobile/ws?token=anything'],
  ['non-loopback peer',r=>r.socket.remoteAddress='10.0.0.2'],
  ['HTTP body',r=>r.headers['content-length']='10'],
  ['forwarded credential',r=>r.headers.authorization='Bearer fixture'],
  ['invalid websocket key',r=>r.headers['sec-websocket-key']='bad'],
])test('WSS refuses '+name,()=>{const r=request();change(r);assert.throws(()=>validateUpgrade(r,{origin}));});
test('WSS refuses excessive pre-upgrade bytes',()=>assert.throws(()=>validateUpgrade(request(),{origin},Buffer.alloc(65537))));

test('TLS pins require the reviewed key, issuer, DNS/IP SAN and validity',()=>{
  const temporary=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'netclaw-r08-tls-source-')));
  try {
    const python=process.env.NETCLAW_TEST_PYTHON||'python3';
    execFileSync(python,['-c',String.raw`
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.x509.oid import NameOID
from pathlib import Path
import datetime,ipaddress,sys
root=Path(sys.argv[1]);now=datetime.datetime.now(datetime.timezone.utc)
def make(name,key,issuer_key=None,issuer=None,names=True):
 subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
 builder=x509.CertificateBuilder().subject_name(subject).issuer_name(issuer.subject if issuer else subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.BasicConstraints(ca=issuer is None,path_length=None),critical=True)
 if issuer and names:builder=builder.add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
 cert=builder.sign(issuer_key or key,hashes.SHA256());(root/(name+'.crt')).write_bytes(cert.public_bytes(serialization.Encoding.PEM));(root/(name+'.key')).write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));return cert
cakey=ec.generate_private_key(ec.SECP256R1());ca=make('ca',cakey)
make('node',ec.generate_private_key(ec.SECP256R1()),cakey,ca)
make('other',ec.generate_private_key(ec.SECP256R1()))
make('badname',ec.generate_private_key(ec.SECP256R1()),cakey,ca,False)
`,temporary],{stdio:'pipe'});
    const read=name=>fs.readFileSync(path.join(temporary,name));
    assert.match(verifyTls(read('node.crt'),read('node.key'),read('ca.crt')),/^[A-F0-9:]+$/);
    assert.throws(()=>verifyTls(read('node.crt'),read('other.key'),read('ca.crt')));
    assert.throws(()=>verifyTls(read('node.crt'),read('node.key'),read('other.crt')));
    assert.throws(()=>verifyTls(read('badname.crt'),read('badname.key'),read('ca.crt')));
    assert.throws(()=>verifyTls(read('node.crt'),read('node.key'),read('ca.crt'),0));
  } finally {fs.rmSync(temporary,{recursive:true});}
});
test('unfrozen source cannot serve an arbitrary owner directory',()=>{
  const temporary=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'netclaw-r08-source-')));fs.chmodSync(temporary,0o700);
  try {assert.throws(()=>readContext(temporary));} finally {fs.rmSync(temporary,{recursive:true});}
});
