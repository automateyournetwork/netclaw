import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {canonical,privateFile,privateDirectory,writeArtifact,claimOriginal,assertExactReview,assertOriginal,unchangedCounters,sha256,loadQualification,verifyEnvelope,readBudgetClaim,awaitBudgetClaim} from './client_evidence.mjs';
import {runBrowser} from './client_qualification.mjs';
const golden=JSON.parse(fs.readFileSync(new URL('../../tests/fixtures/ha-179/cluster-golden.json',import.meta.url)));
const setup=t=>{const directory=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'r08-harness-source-')));fs.chmodSync(directory,0o700);t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));return directory;};
test('source import launches nothing and durable original-once lock cannot be retried',t=>{
 assert.equal(typeof runBrowser,'function');const dir=setup(t),context={config:{phase:'original_once',once_file:path.join(dir,'once.json'),source_commit:'a'.repeat(40),record_sha256:'b'.repeat(64)}};
 claimOriginal(context);assert.throws(()=>claimOriginal(context),/EEXIST/);assert.equal(JSON.parse(privateFile(context.config.once_file)).state,'original_once_claimed');assert.equal(fs.statSync(context.config.once_file).mode&0o777,0o600);
});
test('private evidence is bounded, append-only and cumulative counters cannot silently change',t=>{
 const dir=setup(t),first=writeArtifact(dir,'first.json',{counter:1});assert.equal(first.sha256,sha256(privateFile(first.file)));assert.throws(()=>writeArtifact(dir,'first.json',{}),/EEXIST/);assert.throws(()=>writeArtifact(dir,'../bad',{}));
 const context={config:{counter_file:first.file},counters_sha256:first.sha256};unchangedCounters(context);fs.writeFileSync(first.file,'{}');assert.throws(()=>unchangedCounters(context),/counters changed/);fs.chmodSync(first.file,0o644);assert.throws(()=>privateFile(first.file),/private/);assert.throws(()=>privateDirectory(first.file));
});
test('exact original review refuses changed arguments or effect counts and recovery binds original digest',()=>{
 const review={principal:golden.principal,border:{installation_id:golden.descriptors[0].installation_id,key_id:golden.descriptors[0].manifest.manifest.nodes[0].key_id},cluster:{...golden.stale_review.cluster,authority_epoch:7},member:{member_id:'original'},model_profile:{model:'original'},tool_call:{tool:'original',arguments:{cidr:'192.0.2.0/28'}},limits:{max_tool_calls:1,max_inference_calls:2,expires_at_ms:Date.now()+10000}};
 const operation={operation_id:'original-id',client_nonce:'original-nonce',review,review_digest:sha256(canonical(review)),state:'review_pending',attempt_count:0,may_have_executed:false},context={bundle:{descriptor:golden.descriptors[0],principal:golden.principal,expected_review:structuredClone(review)}};
 assertExactReview(operation,context);operation.review.tool_call.arguments.cidr='198.51.100.0/24';assert.throws(()=>assertExactReview(operation,context));operation.review=structuredClone(context.bundle.expected_review);
 const expected={reference:{operation_id:operation.operation_id,client_nonce:operation.client_nonce},review:operation.review,review_digest:operation.review_digest,attempt_count:0};assertOriginal(operation,expected);assert.throws(()=>assertOriginal({...operation,operation_id:'replacement-id'},expected));assert.throws(()=>assertOriginal({...operation,attempt_count:1},expected));
});

test('FIXTURE signed original result verifies exact protected domain; changed payload and manifest signature refuse',()=>{
 const script=`import json,base64,datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
import hashlib
k=ec.generate_private_key(ec.SECP256R1());name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'fixture-only')]);now=datetime.datetime.now(datetime.timezone.utc)
cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(k.public_key()).serial_number(1).not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=1)).sign(k,hashes.SHA256())
schema='netclaw.execution.result.v2';payload={'operation_id':'fixture-only'};body=json.dumps({'schema':schema,'payload':payload},sort_keys=True,separators=(',',':')).encode();sig=k.sign(b'netclaw.r02/'+schema.encode()+bytes([0])+body,ec.ECDSA(hashes.SHA256()))
print(json.dumps({'certificate':cert.public_bytes(serialization.Encoding.PEM).decode(),'envelope':{'schema':schema,'payload':payload,'signature':{'algorithm':'ecdsa-p256-sha256','key_id':hashlib.sha256(k.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest(),'value':base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}}}))`;
 const value=JSON.parse(execFileSync(process.env.NETCLAW_TEST_PYTHON||'python3',['-c',script],{encoding:'utf8'}));
 assert.equal(verifyEnvelope(value.envelope,value.certificate,'netclaw.execution.result.v2').payload.operation_id,'fixture-only');value.envelope.payload.operation_id='changed';assert.throws(()=>verifyEnvelope(value.envelope,value.certificate,'netclaw.execution.result.v2'),/signature/);
 assert.throws(()=>verifyEnvelope(golden.descriptors[0].manifest,golden.descriptors[0].anchor_certificate,'netclaw.execution.result.v2'));
});
test('REAL classification and pinned original evidence required before any browser launch',async t=>{
 const dir=setup(t),file=writeArtifact(dir,'config.json',{schema_version:1,classification:'FIXTURE',surface:'browser'}).file;await assert.rejects(loadQualification(file,'browser'));await assert.rejects(runBrowser(file));
});

test('native qualification module import cannot activate an extension or launch a client',async()=>{
 const {runInNewContext}=await import('node:vm'),module={exports:{}};let activated=0;
 const source=fs.readFileSync(new URL('../../extensions/netclaw-vscode/test/editor-ha.cjs',import.meta.url),'utf8');
 const {createRequire}=await import('node:module'),require=createRequire(import.meta.url);
 runInNewContext(source,{exports:module.exports,require:name=>name==='vscode'?{extensions:{getExtension(){activated++;throw Error('unexpected activation');}}}:require(name)});
 assert.equal(typeof module.exports.run,'function');assert.equal(activated,0);
});

function budgetFixture(t) {
 const dir=setup(t),now=Date.now(),operation={operation_id:'00000000-0000-4000-8000-000000000001',client_nonce:'original-native-nonce',review_digest:'b'.repeat(64)};
 const context={budget_started_at_ms:now,config:{surface:'browser',phase:'original_once',budget_run_id:'00000000-0000-4000-8000-000000000002',budget_claim_file:path.join(dir,'claim.json'),budget_wait_ms:200}};
 const body={schema_version:1,run_id:context.config.budget_run_id,claim_id:'00000000-0000-4000-8000-000000000003',...operation,surface:'hud',limits:{inferences:2,native_effects:1,operation_seconds:180,inference_seconds:60},reserved_at_ms:now};
 const signed=value=>({...value,claim_sha256:sha256(canonical(value))});
 return {dir,context,operation,body,signed};
}
test('native approval waits for exact shared-budget reservation without allocating one',async t=>{
 const {dir,context,operation,body,signed}=budgetFixture(t),claim=signed(body);
 const pending=awaitBudgetClaim(context,operation);assert.equal(fs.existsSync(context.config.budget_claim_file),false);
 setTimeout(()=>writeArtifact(dir,'claim.json',claim),10);assert.deepEqual(await pending,claim);assert.deepEqual(readBudgetClaim(context,operation),claim);
});
test('shared-budget binding, hash, freshness and exact per-operation limits fail closed',t=>{
 const {context,operation,body,signed}=budgetFixture(t);
 const changed=[{operation_id:'00000000-0000-4000-8000-000000000004'},{run_id:'00000000-0000-4000-8000-000000000004'},{client_nonce:'replacement'},
  {review_digest:'c'.repeat(64)},{surface:'vscode'},{limits:{...body.limits,native_effects:2}},{reserved_at_ms:0},{extra:true}];
 for(const mutation of changed){fs.writeFileSync(context.config.budget_claim_file,JSON.stringify(signed({...body,...mutation})),{mode:0o600});assert.throws(()=>readBudgetClaim(context,operation));}
 fs.writeFileSync(context.config.budget_claim_file,JSON.stringify({...signed(body),claim_sha256:'0'.repeat(64)}));assert.throws(()=>readBudgetClaim(context,operation),/hash changed/);
});
test('missing or malformed reservation leaves approval unsent and creates no reservation',async t=>{
 const {dir,context,operation}=budgetFixture(t);context.config.budget_wait_ms=10;
 await assert.rejects(awaitBudgetClaim(context,operation),/approval remains unsent/);assert.deepEqual(fs.readdirSync(dir),[]);
 writeArtifact(dir,'claim.json',{});await assert.rejects(awaitBudgetClaim(context,operation));assert.deepEqual(fs.readdirSync(dir),['claim.json']);
});
