import test from 'node:test';
import childProcess from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
import { EventEmitter } from 'node:events';
import { createManager } from '../../scripts/genie-worlds/manager.mjs';
import { openGoogle } from '../../scripts/genie-worlds/provider.mjs';
import { createSessionWorker } from '../../scripts/genie-worlds/worker.mjs';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, chmodSync, rmSync, readFileSync, readdirSync, mkdirSync, copyFileSync, symlinkSync, lstatSync, renameSync, linkSync } from 'node:fs';
import { join, resolve, dirname, relative } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import { loadLivePacket, loadCredential, loadCampaignAuthority, readReviewedArtifact, loadCampaignReview, admitReviewedCampaign, LIVE_SOURCE_FILES } from '../../scripts/genie-worlds/live-packet.mjs';
import { CampaignBudget, CAMPAIGN_POLICY } from '../../scripts/genie-worlds/campaign-budget.mjs';
import { Ledger } from '../../scripts/genie-worlds/ledger.mjs';
import { POLICY, CAMPAIGN_SESSION_POLICY, hash, projection } from '../../scripts/genie-worlds/model.mjs';
function fixture(t) {
  const root = mkdtempSync(join(process.env.NETCLAW_TEST_TMP, 'live-gate-'));
  t.after(() => rmSync(root, {recursive:true, force:true}));
  const credential = join(root, 'synthetic-credential.txt');
  writeFileSync(credential, 'GOOGLE_API_KEY=fixture_key_not_a_real_credential_12345\n', {mode:0o600});
  const source_files = Object.fromEntries(LIVE_SOURCE_FILES.map(name => {
    return [name, createHash('sha256').update(readFileSync(name)).digest('hex')];
  }));
  const authorityRoot = join(root, 'authority');
  new CampaignBudget(authorityRoot, 'synthetic-campaign', {initialize:true}).close();
  const st = lstatSync(join(authorityRoot, 'campaign-budget.sqlite'));
  const authority = {schema:1, campaign_id:'synthetic-campaign', authority_root:authorityRoot,
    authority_dev:st.dev, authority_ino:st.ino, policy_sha256:hash(CAMPAIGN_POLICY)};
  const authorityPath = join(root, 'authority.json'), authorityBytes = JSON.stringify(authority);
  writeFileSync(authorityPath, authorityBytes, {mode:0o600});
  const authorityHash = createHash('sha256').update(authorityBytes).digest('hex');
  const env = {NETCLAW_GENIE_CAMPAIGN_AUTHORITY:authorityPath, NETCLAW_GENIE_CAMPAIGN_AUTHORITY_SHA256:authorityHash};
  const packet = {schema:1, campaign_authority_sha256:authorityHash, state_root:root, credential_file:credential, projection_sha256:projection().sha256, policy_sha256:hash(POLICY), allowance_usd:15, attempts:1, authorized:true, authorization_ref:'TEST ONLY', expires_at:new Date(Date.now()+60000).toISOString(), source_files};
  const path = join(root, 'packet.json');
  const save = () => writeFileSync(path, JSON.stringify(packet), {mode:0o600});
  save(); return {root, packet, path, credential, save, env, authority, authorityPath};
}
test('private credential is read without importing other environment values', t => {
  const f=fixture(t); assert.match(loadCredential(f.credential), /^fixture_key/);
  chmodSync(f.credential,0o644);
  assert.throws(()=>loadCredential(f.credential),/private_file_required/);
});
test('live launch requires exact authorization and unchanged source', t => {
  const f=fixture(t); assert.equal(loadLivePacket(f.path, f.env).attempts,1);
  f.packet.authorized=false; f.save(); assert.throws(()=>loadLivePacket(f.path, f.env),/live_authorization_required/);
  f.packet.authorized=true; f.packet.source_files['scripts/genie-worlds/worker.mjs']='0'.repeat(64); f.save();
  assert.throws(()=>loadLivePacket(f.path, f.env),/live_source_changed/);
});
test('one Google attempt cannot be repeated even after a settled terminal receipt', t => {
  const f=fixture(t); let l=new Ledger(f.root);
  const p=projection(),r=l.review(p,POLICY,15,'google'),id=randomUUID();
  l.admit(id,p,r.id,'google'); l.terminal(id,{event_type:'interaction.completed',usage:{video_output_tokens:0,input_tokens:0}});
  l.close(); l=new Ledger(f.root);
  try {
    assert.equal(l.admit(id,p,r.id,'google').newly_created,false);
    const r2=l.review(p,POLICY,15,'google');
    assert.throws(()=>l.admit(randomUUID(),p,r2.id,'google'),/single_attempt_consumed/);
  } finally {l.close();}
});

test('review covers every runtime module, viewer asset and fixture, including local imports', () => {
  const base=resolve('scripts/genie-worlds'), names=new Set(LIVE_SOURCE_FILES);
  function inspect(dir) {
    for (const entry of readdirSync(dir,{withFileTypes:true})) {
      if (['node_modules','__pycache__'].includes(entry.name)) continue;
      const path=join(dir,entry.name), name=relative(process.cwd(),path);
      if (entry.isDirectory()) { inspect(path); continue; }
      if (path.endsWith('.mjs') || path.startsWith(join(base,'viewer')+'/') || path.startsWith(join(base,'fixtures')+'/')) {
        assert.ok(names.has(name),`unreviewed runtime file: ${name}`);
      }
      if (!path.endsWith('.mjs')) continue;
      const source=readFileSync(path,'utf8');
      // Static import/export-from and literal dynamic imports; no computed import allowed.
      assert.doesNotMatch(source,/\bimport\s*\(\s*[^'"\s]/);
      for (const match of source.matchAll(/(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)["'](\.[^"']+)["']/g)) {
        const dependency=relative(process.cwd(),resolve(dirname(path),match[1]));
        assert.ok(names.has(dependency),`unreviewed import: ${dependency}`);
      }
    }
  }
  inspect(base);
});

async function copiedSource(t) {
  const f=fixture(t), checkout=join(f.root,'checkout');
  for (const name of LIVE_SOURCE_FILES) {
    const target=join(checkout,name); mkdirSync(dirname(target),{recursive:true}); copyFileSync(name,target);
  }
  const module=await import(pathToFileURL(join(checkout,'scripts/genie-worlds/live-packet.mjs')));
  return {...f,checkout,load:path => module.loadLivePacket(path, f.env)};
}
test('campaign accounting and world-design bytes require a refreshed exact source review', async t => {
  const f = await copiedSource(t);
  for (const name of ['campaign-budget.mjs', 'world-designs.mjs']) {
    const path = join(f.checkout, 'scripts/genie-worlds', name), original = readFileSync(path);
    try {
      writeFileSync(path, Buffer.concat([original, Buffer.from('\n// changed reviewed source\n')]));
      assert.throws(() => f.load(f.path), /live_source_changed/, name);
    } finally { writeFileSync(path, original); }
  }
});
test('each retained viewer dependency invalidates a reviewed packet when its bytes change', async t => {
  const f=await copiedSource(t); assert.equal(f.load(f.path).attempts,1);
  for (const name of ['network-graph.mjs','selection.mjs','index.html','viewer.mjs','viewer.css']) {
    const path=join(f.checkout,'scripts/genie-worlds/viewer',name), original=readFileSync(path);
    try { writeFileSync(path,Buffer.concat([original,Buffer.from('\nchanged')])); assert.throws(()=>f.load(f.path),/live_source_changed/,name); }
    finally { writeFileSync(path,original); }
  }
});
test('new runtime modules and served assets cannot be omitted from source review', async t => {
  const f=await copiedSource(t);
  for (const name of ['extra.mjs','viewer/extra.svg','nested/helper.mjs']) {
    const path=join(f.checkout,'scripts/genie-worlds',name);mkdirSync(dirname(path),{recursive:true});writeFileSync(path,'synthetic');
    try { assert.throws(()=>f.load(f.path),/source_closure_changed/,name); }
    finally { rmSync(path); }
  }
});
test('legacy manifests and asset symlinks fail closed before credential access', async t => {
  const f=await copiedSource(t);
  delete f.packet.source_files['scripts/genie-worlds/viewer/network-graph.mjs'];f.save();
  assert.throws(()=>f.load(f.path),/source_manifest_required/);
  const path=join(f.checkout,'scripts/genie-worlds/viewer/network-graph.mjs');
  f.packet.source_files['scripts/genie-worlds/viewer/network-graph.mjs']=createHash('sha256').update(readFileSync(path)).digest('hex');f.save();
  const target=join(f.root,'unchanged-asset.mjs');copyFileSync(path,target);rmSync(path);symlinkSync(target,path);
  rmSync(f.credential);
  assert.throws(()=>f.load(f.path),/source_closure_symlink/);
});

test('live packet cannot select, omit or change the trusted campaign authority', t => {
  const f = fixture(t);
  assert.equal(loadCampaignAuthority(f.env).campaign_id, 'synthetic-campaign');
  assert.throws(() => loadLivePacket(f.path, {}), /campaign_pin_required/);
  f.packet.campaign_authority_sha256 = '0'.repeat(64); f.save();
  assert.throws(() => loadLivePacket(f.path, f.env), /campaign_packet_mismatch/);
  writeFileSync(f.authorityPath, JSON.stringify({...f.authority, campaign_id:'alternate-account'}));
  assert.throws(() => loadCampaignAuthority(f.env), /campaign_pin_changed/);
});

test('missing, replaced or symlinked authority fails without bootstrapping or credential access', t => {
  const f = fixture(t), db = join(f.authority.authority_root, 'campaign-budget.sqlite');
  rmSync(f.credential);
  renameSync(db, db + '.retained');
  assert.throws(() => loadLivePacket(f.path, f.env), /ENOENT/);
  copyFileSync(db + '.retained', db);
  assert.throws(() => loadLivePacket(f.path, f.env), /campaign_identity_changed/);
  rmSync(db); symlinkSync(db + '.retained', db);
  assert.throws(() => loadCampaignAuthority(f.env), /campaign_identity_changed/);
});

test('shared campaign survives reopen and alternate session roots retain the same authority', t => {
  const f = fixture(t), a = loadCampaignAuthority(f.env);
  const budget = new CampaignBudget(a.authority_root, a.campaign_id), id = randomUUID();
  budget.reserve({operation_id:id, world_number:1, review_sha256:'a'.repeat(64),
    service_bound_sha256:'b'.repeat(64), target_seconds:120, input_text_bound_microusd:404000});
  budget.close();
  for (const name of ['session-a', 'account-alias']) {
    f.packet.state_root = join(f.root, name); f.save();
    assert.equal(loadLivePacket(f.path, f.env).campaign_authority_sha256, a.sha256);
    const reopened = new CampaignBudget(a.authority_root, a.campaign_id);
    try { assert.equal(reopened.totals().unresolved, 1); }
    finally { reopened.close(); }
  }
});

function reviewedEvidence(t) {
  const f = fixture(t), path = join(f.root, 'synthetic-evidence.json');
  const bytes = Buffer.from('{"synthetic":true,"claim":"not provider evidence"}');
  writeFileSync(path, bytes, {mode:0o600});
  const st = lstatSync(path);
  return {...f, bytes, reference:{path, dev:st.dev, ino:st.ino, size_bytes:st.size,
    sha256:createHash('sha256').update(bytes).digest('hex')}};
}
function campaignEvidence(t) {
  const f = fixture(t);
  const retain = (name, value) => {
    const path = join(f.root, name + '.json'), bytes = JSON.stringify(value);
    writeFileSync(path, bytes, {mode:0o600});
    const st = lstatSync(path);
    return {path, dev:st.dev, ino:st.ino, size_bytes:st.size,
      sha256:createHash('sha256').update(bytes).digest('hex')};
  };
  const common = {schema:1, campaign_id:f.authority.campaign_id,
    campaign_authority_sha256:f.packet.campaign_authority_sha256,
    source_manifest_sha256:hash(f.packet.source_files), projection_sha256:projection().sha256,
    policy_sha256:hash(CAMPAIGN_POLICY), model:'genie-4', currency:'USD', world_number:1, target_seconds:120};
  const evidence = retain('synthetic-contract', {synthetic:true, note:'TEST ONLY; no provider proof'});
  const service = {...common, kind:'service_bound', enforcement:'provider', max_seconds:120,
    video_bound_microusd:12_096_000, evidence};
  const input = {...common, kind:'input_text_bound', enforcement:'provider',
    max_input_tokens:1000, max_output_text_tokens:1000,
    input_price_microusd_per_million:1_000_000, output_text_price_microusd_per_million:1_000_000,
    bound_microusd:404000, evidence};
  const review = {...common, kind:'campaign_review', expires_at:f.packet.expires_at,
    reservation_microusd:12_500_000};
  const save = () => retain('review', {...review, service_bound:retain('service', service), input_text_bound:retain('input', input)});
  const context = {world_number:1, source_files:f.packet.source_files, projection:projection()};
  return {...f, retain, service, input, review, save, context};
}
test('typed campaign evidence binds exact source, synthetic projection and reopened authority', t => {
  const f = campaignEvidence(t), ref = f.save();
  for (let i=0;i<2;i++) {
    const result = loadCampaignReview(ref, f.context, f.env);
    assert.equal(result.input_text_bound_microusd, 404000);
    assert.equal(result.review_sha256, ref.sha256);
    assert.equal(result.target_seconds, 120);
  }
  assert.throws(()=>loadCampaignReview(ref,{...f.context,world_number:2},f.env),/review_binding_mismatch/);
  assert.throws(()=>loadCampaignReview(ref,{...f.context,projection:{...projection(),classification:'private'}},f.env),/private_or_modified_projection/);
  f.context.source_files['scripts/genie-worlds/worker.mjs']='0'.repeat(64);
  assert.throws(()=>loadCampaignReview(ref,f.context,f.env),/live_source_changed/);
});
test('typed evidence rejects claimed timer caps, underfunding, expired and mismatched artifacts', t => {
  const f=campaignEvidence(t);
  const cases = [
    [f.service,'enforcement','client_timer'], [f.service,'max_seconds',121],
    [f.service,'video_bound_microusd',1], [f.service,'projection_sha256','0'.repeat(64)],
    [f.input,'enforcement','estimate'], [f.input,'bound_microusd',1],
    [f.input,'max_input_tokens',Number.MAX_SAFE_INTEGER], [f.input,'max_output_text_tokens',-1],
    [f.input,'campaign_id','alternate-account'], [f.review,'reservation_microusd',12_096_000],
    [f.review,'expires_at','2000-01-01T00:00:00Z'], [f.review,'unexpected',true],
  ];
  for (const [object,key,value] of cases) {
    const old=object[key]; object[key]=value;
    assert.throws(()=>loadCampaignReview(f.save(),f.context,f.env),key);
    if(old===undefined) delete object[key]; else object[key]=old;
  }
});
test('reviewed contract tampering and duplicate JSON keys fail closed', t => {
  const f=campaignEvidence(t), ref=f.save();
  writeFileSync(f.service.evidence.path, 'tampered');
  assert.throws(()=>loadCampaignReview(ref,f.context,f.env),/artifact_identity_changed|artifact_content_changed/);
  const bytes=readFileSync(ref.path,'utf8').replace('{','{"schema":2,');
  writeFileSync(ref.path,bytes);
  const st=lstatSync(ref.path), duplicate={...ref,size_bytes:st.size,sha256:createHash('sha256').update(bytes).digest('hex')};
  assert.throws(()=>loadCampaignReview(duplicate,f.context,f.env),/artifact_json_encoding/);
});
test('reviewed evidence retains exact bytes and refuses changed contents at the same identity', t => {
  const f = reviewedEvidence(t);
  assert.deepEqual(readReviewedArtifact(f.reference), f.bytes);
  const changed = Buffer.from(f.bytes); changed[0] = 0x5b;
  writeFileSync(f.reference.path, changed);
  assert.throws(() => readReviewedArtifact(f.reference), /artifact_content_changed/);
});
test('byte-identical replacement requires a new identity review', t => {
  const f = reviewedEvidence(t), path = f.reference.path;
  renameSync(path, path + '.retained');
  writeFileSync(path, f.bytes, {mode:0o600});
  assert.throws(() => readReviewedArtifact(f.reference), /artifact_identity_changed/);
});
test('reviewed artifacts reject hardlinks, symlinks and public permissions', t => {
  const f = reviewedEvidence(t), r = f.reference;
  linkSync(r.path, r.path + '.link');
  assert.throws(() => readReviewedArtifact(r), /private_file_required/);
  rmSync(r.path + '.link');
  chmodSync(r.path, 0o644);
  assert.throws(() => readReviewedArtifact(r), /private_file_required/);
  chmodSync(r.path, 0o600);
  renameSync(r.path, r.path + '.retained'); symlinkSync(r.path + '.retained', r.path);
  assert.throws(() => readReviewedArtifact(r), /private_path_symlink/);
  const alias = join(f.root, 'alias'); symlinkSync(f.root, alias);
  assert.throws(() => readReviewedArtifact({...r, path:join(alias, 'synthetic-evidence.json.retained')}), /private_path_symlink/);
});
test('artifact references require bounded bytes, exact metadata and closed fields', t => {
  const f = reviewedEvidence(t), r = f.reference;
  for (const update of [{sha256:'x'}, {dev:-1}, {ino:1.5}, {size_bytes:NaN}, {unexpected:true}])
    assert.throws(() => readReviewedArtifact({...r,...update}));
  assert.throws(() => readReviewedArtifact({...r,size_bytes:r.size_bytes + 1}), /artifact_identity_changed/);
  writeFileSync(r.path, Buffer.alloc(1024 * 1024 + 1));
  assert.throws(() => readReviewedArtifact(r), /private_file_size/);
  writeFileSync(r.path, '');
  assert.throws(() => readReviewedArtifact(r), /private_file_size/);
});
test('live packet and authority loading reject hardlinked private inputs', t => {
  const f = fixture(t);
  linkSync(f.authorityPath, f.authorityPath + '.link');
  assert.throws(() => loadLivePacket(f.path, f.env), /private_file_required/);
  rmSync(f.authorityPath + '.link');
  linkSync(f.path, f.path + '.link');
  assert.throws(() => loadLivePacket(f.path, f.env), /private_file_required/);
});

function pinnedAdmission(t) {
  const f = campaignEvidence(t), reference = f.save();
  const launch = {schema:1, world_number:1, source_files:f.packet.source_files, review:reference};
  const descriptor = f.retain('launch', launch);
  Object.assign(f.env, {NETCLAW_GENIE_CAMPAIGN_REVIEW:descriptor.path,
    NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256:descriptor.sha256});
  const ledger = new Ledger(join(f.root, 'session'));
  t.after(() => ledger.close());
  const review = ledger.review(projection(), CAMPAIGN_SESSION_POLICY, 12.5, 'google');
  const input = {operation_id:randomUUID(), projection:projection(), review_id:review.id};
  const totals = () => {
    const budget = new CampaignBudget(f.authority.authority_root, f.authority.campaign_id);
    try { return budget.totals(); } finally { budget.close(); }
  };
  return {...f, reference, launch, descriptor, ledger, input, totals};
}
function campaignPacket(t) {
  const f = pinnedAdmission(t);
  Object.assign(f.packet, {schema:2, policy_sha256:hash(CAMPAIGN_SESSION_POLICY),
    world_number:1, reservation_microusd:12_500_000, allowance_usd:12.5,
    campaign_review_sha256:f.reference.sha256});
  const savePacket = () => writeFileSync(f.path, JSON.stringify(f.packet), {mode:0o600});
  savePacket(); return {...f, savePacket};
}
async function withCampaignManager(t, f, audit, run) {
  // Keep evidence filenames distinct from manager-owned service.json.
  f.packet.state_root=join(f.root,'manager');
  writeFileSync(f.path,JSON.stringify(f.packet),{mode:0o600});
  const launches = [];
  // Intercept process creation itself: synthetic authority can never reach SDK
  // transport, even if an expected refusal regresses.
  const mocked = t.mock.method(childProcess, 'fork', (file, args, options) => {
    const child = new EventEmitter();
    child.stderr = new EventEmitter(); child.connected = true;
    child.send = message => { if (message.type === 'stop') child.emit('exit', 0); };
    child.kill = () => child.emit('exit', null, 'SIGKILL');
    launches.push({file, args, options}); return child;
  });
  syncBuiltinESMExports();
  let m;
  try {
    m = await createManager({root:f.packet.state_root, livePacketPath:f.path, campaignEnv:f.env, audit});
    const post = async (path, body) => {
      const response = await fetch(m.origin + path, {method:'POST',
        headers:{Authorization:`Bearer ${m.owner}`, 'Content-Type':'application/json'},
        body:JSON.stringify(body)});
      return {status:response.status, body:await response.json()};
    };
    await run(m, post, launches);
  } finally {
    if (m) await m.close();
    mocked.mock.restore(); syncBuiltinESMExports();
  }
}
test('manager uses campaign review/admission and frozen four-pin worker environment; original IDs do not replay', async t => {
  const f=campaignPacket(t), pins={...f.env}; let audits=0;
  await withCampaignManager(t, f, async () => {
    audits++; for (const key of Object.keys(f.env)) f.env[key]='changed-after-launch';
    return {commit:'synthetic-audit'};
  }, async (m, post, launches) => {
    const draft=await (await fetch(m.origin+'/v1/draft',{headers:{Authorization:`Bearer ${m.owner}`}})).json();
    assert.deepEqual(draft.session_bounds, {
      accounting_mode:'campaign-v1', policy:CAMPAIGN_SESSION_POLICY,
      estimated_usd:12.5, estimated_video_usd:12.096, reservation_usd:12.5,
      campaign_limits:{soft_stop_usd:100,hard_stop_usd:100},
    });
    const review=await post('/v1/reviews',{projection_sha256:projection().sha256,provider:'google'});
    assert.equal(review.status,200,JSON.stringify(review.body)); assert.equal(review.body.accounting_version,'campaign-v1');
    assert.equal(review.body.allowance_usd,12.5);
    assert.equal(review.body.policy_sha256,hash(CAMPAIGN_SESSION_POLICY));
    const input={request_id:randomUUID(),review_ref:review.body.id};
    const admitted=await post('/v1/sessions',input);
    assert.equal(admitted.status,200,JSON.stringify(admitted.body));
    assert.equal(admitted.body.reserved_microusd,12_500_000);
    assert.deepEqual(admitted.body.session_bounds,draft.session_bounds);
    assert.equal(f.totals().exposure_microusd,12_500_000);
    assert.equal(launches.length,1);
    assert.deepEqual(launches[0].options.env,{PATH:process.env.PATH,...pins});
    const before=m.ledger.db.prepare('SELECT body FROM sessions WHERE id=?').get(input.request_id).body;
    writeFileSync(f.path,'invalidated packet');
    const retry=await post('/v1/sessions',input);
    assert.equal(retry.status,200); assert.equal(audits,1); assert.equal(launches.length,1);
    assert.equal(m.ledger.db.prepare('SELECT body FROM sessions WHERE id=?').get(input.request_id).body,before);
    assert.equal((await post('/v1/sessions',{...input,review_ref:randomUUID()})).status,409);
  });
});
for (const change of ['packet','evidence','descriptor','expiry']) {
  test(`manager rejects ${change} tampering during audit await before reservation or worker`, async t => {
    const f=campaignPacket(t);
    await withCampaignManager(t,f,async () => {
      await Promise.resolve();
      if (change==='evidence') writeFileSync(f.service.evidence.path,'tampered');
      else if (change==='descriptor') writeFileSync(f.descriptor.path,'tampered');
      else {
        if (change==='expiry') f.packet.expires_at='2000-01-01T00:00:00Z';
        else f.packet.authorization_ref='changed otherwise-valid packet';
        f.savePacket();
      }
      return {commit:'synthetic-audit'};
    },async (m,post,launches) => {
      const review=await post('/v1/reviews',{projection_sha256:projection().sha256,provider:'google'});
      assert.equal(review.status,200,JSON.stringify(review.body));
      const result=await post('/v1/sessions',{request_id:randomUUID(),review_ref:review.body.id});
      assert.notEqual(result.status,200);
      assert.equal(m.ledger.list().length,0); assert.equal(launches.length,0);
      assert.equal(f.totals().exposure_microusd,0);
      assert.equal(m.ledger.db.prepare('SELECT used FROM reviews WHERE id=?').get(review.body.id).used,null);
    });
  });
}
test('manager refuses historical packets and every missing launch pin without workers', async t => {
  for (const key of [null,'NETCLAW_GENIE_CAMPAIGN_AUTHORITY','NETCLAW_GENIE_CAMPAIGN_AUTHORITY_SHA256',
    'NETCLAW_GENIE_CAMPAIGN_REVIEW','NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256']) {
    const f=key ? campaignPacket(t) : fixture(t);
    if (key) delete f.env[key];
    await assert.rejects(withCampaignManager(t,f,async()=>({commit:'synthetic'}),()=>assert.fail('started')),
      /campaign_packet_required|campaign_pin_required|campaign_review_pin_required/);
    assert.equal(readFileSync(f.path,'utf8'),JSON.stringify(f.packet));
  }
});
test('manager original-ID lookup preserves historical session and review bytes without renewed authority', async t => {
  const f=campaignPacket(t); let audits=0;
  await withCampaignManager(t,f,async()=>{ audits++; return {commit:'synthetic'}; },async(m,post,launches)=>{
    const review=m.ledger.review(projection(),POLICY,15,'google'), id=randomUUID();
    m.ledger.admit(id,projection(),review.id,'google');
    const session=m.ledger.db.prepare('SELECT body FROM sessions WHERE id=?').get(id).body;
    const originalReview=m.ledger.db.prepare('SELECT body FROM reviews WHERE id=?').get(review.id).body;
    writeFileSync(f.descriptor.path,'authority no longer available');
    const result=await post('/v1/sessions',{request_id:id,review_ref:review.id});
    assert.equal(result.status,200); assert.equal(result.body.accounting_version,undefined);
    assert.deepEqual(result.body.session_bounds,{accounting_mode:'legacy',policy:POLICY,
      estimated_usd:2.016,estimated_video_usd:null,reservation_usd:15});
    assert.equal(m.ledger.db.prepare('SELECT body FROM sessions WHERE id=?').get(id).body,session);
    assert.equal(m.ledger.db.prepare('SELECT body FROM reviews WHERE id=?').get(review.id).body,originalReview);
    assert.equal(audits,0); assert.equal(launches.length,0); assert.equal(f.totals().exposure_microusd,0);
  });
});
test('schema2 packet binds full-duration policy and exact reviewed amount without admission', t => {
  const f=campaignPacket(t), before=readFileSync(f.path);
  const loaded=loadLivePacket(f.path,f.env);
  assert.equal(loaded.policy_sha256,hash(CAMPAIGN_SESSION_POLICY));
  assert.equal(loaded.reservation_microusd,12_500_000);
  assert.deepEqual(readFileSync(f.path),before);
  assert.equal(f.totals().exposure_microusd,0);
  assert.equal(f.ledger.list().length,0);
});
test('campaign packet refuses policy downgrade and mismatched amount, world or review', t => {
  const f=campaignPacket(t);
  for (const [key,value] of [['policy_sha256',hash(POLICY)],['allowance_usd',15],
    ['reservation_microusd',12_500_001],['reservation_microusd',12_500_000.5],
    ['world_number',2],['campaign_review_sha256','0'.repeat(64)]]) {
    const old=f.packet[key];f.packet[key]=value;f.savePacket();
    assert.throws(()=>loadLivePacket(f.path,f.env),/live_packet_mismatch|campaign_packet_mismatch/);
    f.packet[key]=old;
  }
  assert.equal(f.totals().exposure_microusd,0);
  assert.equal(f.ledger.list().length,0);
});
test('schema2 reloads operator pins and evidence before credential access', t => {
  const f=campaignPacket(t);
  f.packet.credential_file=join(f.root,'missing-credential');f.savePacket();
  const pin=f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256;
  delete f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256;
  assert.throws(()=>loadLivePacket(f.path,f.env),/campaign_review_pin_required/);
  f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256=pin;
  writeFileSync(f.service.evidence.path,'changed');
  assert.throws(()=>loadLivePacket(f.path,f.env),/artifact_identity_changed|artifact_content_changed/);
  assert.equal(f.totals().exposure_microusd,0);
});
test('legacy packet stays byte-identical and cannot silently adopt campaign policy', t => {
  const f=fixture(t), before=readFileSync(f.path);
  assert.equal(loadLivePacket(f.path,f.env).schema,1);
  assert.deepEqual(readFileSync(f.path),before);
  f.packet.policy_sha256=hash(CAMPAIGN_SESSION_POLICY);f.save();
  assert.throws(()=>loadLivePacket(f.path,f.env),/live_packet_mismatch/);
  f.packet.schema=3;f.save();
  assert.throws(()=>loadLivePacket(f.path,f.env),/live_authorization_required/);
});
test('operator-pinned review reserves before session admission and reopens original ID', t => {
  const f=pinnedAdmission(t);
  assert.equal(admitReviewedCampaign(f.ledger,f.input,f.env).newly_created,true);
  assert.equal(f.totals().reserved_microusd,12_500_000);
  assert.equal(admitReviewedCampaign(f.ledger,f.input,f.env).newly_created,false);
  assert.equal(f.totals().unresolved,1);
  assert.throws(()=>admitReviewedCampaign(f.ledger,{...f.input,budget_review:{}},f.env),/invalid_input/);
});
test('absent and changed launch pins fail before reservation or session marker', t => {
  const f=pinnedAdmission(t);
  const pin=f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256;
  delete f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256;
  assert.throws(()=>admitReviewedCampaign(f.ledger,f.input,f.env),/campaign_review_pin_required/);
  f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256=pin;
  writeFileSync(f.descriptor.path,JSON.stringify({...f.launch,world_number:2}));
  assert.throws(()=>admitReviewedCampaign(f.ledger,f.input,f.env),/campaign_review_pin_changed/);
  assert.equal(f.totals().exposure_microusd,0);
  assert.equal(f.ledger.list().length,0);
});
test('reviewed artifact and authority changes fail before reservation or marker', t => {
  const f=pinnedAdmission(t), original=readFileSync(f.service.evidence.path);
  writeFileSync(f.service.evidence.path,'changed');
  assert.throws(()=>admitReviewedCampaign(f.ledger,f.input,f.env),/artifact_identity_changed|artifact_content_changed/);
  writeFileSync(f.service.evidence.path,original);
  f.env.NETCLAW_GENIE_CAMPAIGN_AUTHORITY_SHA256='0'.repeat(64);
  assert.throws(()=>admitReviewedCampaign(f.ledger,f.input,f.env),/campaign_pin_changed/);
  assert.equal(f.totals().exposure_microusd,0);
  assert.equal(f.ledger.list().length,0);
});
test('even a pinned descriptor cannot override reviewed world or source bindings', t => {
  const f=pinnedAdmission(t);
  for (const changed of [{...f.launch,world_number:2},
    {...f.launch,source_files:{...f.launch.source_files,'scripts/genie-worlds/worker.mjs':'0'.repeat(64)}}]) {
    const descriptor=f.retain('launch',changed);
    f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256=descriptor.sha256;
    assert.throws(()=>admitReviewedCampaign(f.ledger,f.input,f.env),/review_binding_mismatch|live_source_changed/);
    assert.equal(f.totals().exposure_microusd,0);
    assert.equal(f.ledger.list().length,0);
  }
});

test("adapter records ID before connect, never returns a receipt from complete", async t => {
  let creates = 0;
  const f=pinnedAdmission(t);
  admitReviewedCampaign(f.ledger,f.input,f.env);
  const ledger=f.ledger, id=f.input.operation_id;
  const client = {
    interactions: {
      create: async (body, options) => {
        creates++;
        assert.equal(body.automatic_continuation, false);
        assert.deepEqual(options.retries, { strategy: "none" });
        return { id: "observed-id" };
      },
      connect: async (id) => {
        assert.equal(ledger.get(f.input.operation_id).provider_id, id);
        return {
          send: async () => {},
          complete: async () => {},
          cancel: async () => {},
          receive: async function* () {
            yield { event_type: "interaction.completed" };
          },
        };
      },
    },
  };
  const s = await openGoogle({ ledger, id, apiKey: "fake", client, env:f.env });
  assert.equal(creates, 1);
  assert.equal(await s.complete(), undefined);
  assert.equal(
    (await s.receive().next()).value.event_type,
    "interaction.completed",
  );
});
test("actual pinned SDK does not retry create after HTTP503 or connection loss", async t => {
  const original = globalThis.fetch;
  try {
    for (const mode of ["503", "reset"]) {
      const f=pinnedAdmission(t);
      admitReviewedCampaign(f.ledger,f.input,f.env);
      let sends = 0;
      globalThis.fetch = async () => {
        sends++;
        if (mode === "reset") throw new TypeError("transport reset");
        return new Response(
          JSON.stringify({
            error: { message: "fixture", code: 503, status: "UNAVAILABLE" },
          }),
          { status: 503, headers: { "content-type": "application/json" } },
        );
      };
      await assert.rejects(
        openGoogle({ ledger:f.ledger, id:f.input.operation_id, env:f.env, apiKey: "fixture-not-a-real-key" }),
      );
      assert.equal(sends, 1, mode);
    }
  } finally {
    globalThis.fetch = original;
  }
});

test('provider create claim excludes concurrent opens across ledger connections', {timeout:3000}, async t => {
  const f=pinnedAdmission(t), id=f.input.operation_id;
  admitReviewedCampaign(f.ledger,f.input,f.env);
  const other=new Ledger(f.ledger.root);
  let resolveCreate, creates=0;
  const pending=new Promise(resolve => { resolveCreate=resolve; });
  const client={interactions:{create:()=>{ creates++; return pending; }, connect:async()=>({})}};
  const first=openGoogle({ledger:f.ledger,id,env:f.env,apiKey:'synthetic',client});
  try {
    await assert.rejects(openGoogle({ledger:other,id,env:f.env,apiKey:'synthetic',client}),/provider_create_claimed/);
    assert.equal(creates,1);
  } finally { resolveCreate({id:'synthetic-original'}); await first; other.close(); }
  assert.equal(f.ledger.get(id).provider_id,'synthetic-original');
  assert.equal(f.totals().unresolved,1);
});

test('durable create claim survives restart even before an observable transport result', async t => {
  const f=pinnedAdmission(t), id=f.input.operation_id;
  admitReviewedCampaign(f.ledger,f.input,f.env);
  const original=f.ledger.get(id), totals=f.totals();
  const before=new Ledger(f.ledger.root);
  before.claimProviderCreate(id,original);
  before.close();
  const restarted=new Ledger(f.ledger.root);
  let creates=0;
  try {
    assert.throws(()=>restarted.transition(id,'failed_pre_send',{reason:'deadline_before_transport'}),
      /provider_create_may_have_sent/);
    await assert.rejects(openGoogle({ledger:restarted,id,env:f.env,apiKey:'synthetic',
      client:{interactions:{create:async()=>{creates++;}}}}),/provider_create_claimed/);
    assert.equal(creates,0);
    assert.deepEqual(restarted.get(id),original);
    assert.deepEqual(f.totals(),totals);
  } finally { restarted.close(); }
});

test('ambiguous create or connect preserves unknown and reservation without replay', async t => {
  for (const fault of ['create','missing-id','connect']) {
    const f=pinnedAdmission(t), id=f.input.operation_id;
    admitReviewedCampaign(f.ledger,f.input,f.env);
    const totals=f.totals(); let creates=0;
    const client={interactions:{
      create:async()=>{ creates++; if(fault==='create') throw new Error('synthetic transport loss');
        return fault==='missing-id' ? {} : {id:'synthetic-original'}; },
      connect:async()=>{throw new Error('synthetic connection loss');},
    }};
    await assert.rejects(openGoogle({ledger:f.ledger,id,env:f.env,apiKey:'synthetic',client}));
    const restarted=new Ledger(f.ledger.root);
    try {
      assert.equal(restarted.get(id).state,'unknown',fault);
      assert.equal(restarted.get(id).usage_state,'reserved',fault);
      assert.equal(restarted.get(id).provider_id,fault==='connect'?'synthetic-original':null);
      await assert.rejects(openGoogle({ledger:restarted,id,env:f.env,apiKey:'synthetic',client}),/paid_admission_required/);
      assert.equal(creates,1,fault);
      assert.deepEqual(f.totals(),totals,fault);
    } finally { restarted.close(); }
  }
});

test('late create and connect retain original ID after worker cleanup without setup or settlement', {timeout:15000}, async t => {
  for (const delayed of ['create','connect']) {
    const f=pinnedAdmission(t), id=f.input.operation_id;
    admitReviewedCampaign(f.ledger,f.input,f.env);
    const totals=f.totals();
    let resolveLate, entered, opening, creates=0, connects=0, cancels=0, sends=0, receives=0;
    const pending=new Promise(resolve=>{resolveLate=resolve;});
    const started=new Promise(resolve=>{entered=resolve;});
    const transport={
      send:()=>{sends++;}, complete:()=>{},
      cancel:()=>{cancels++; return new Promise(()=>{});},
      receive:()=>{receives++; return {next:()=>new Promise(()=>{})};},
    };
    const client={interactions:{
      create:()=>{creates++; if(delayed==='create'){entered(); return pending;} return {id:'synthetic-late-original'};},
      connect:(providerId)=>{connects++; assert.equal(providerId,'synthetic-late-original');
        if(delayed==='connect'){entered(); return pending;} return transport;},
    }};
    const worker=createSessionWorker({ledger:f.ledger,id,
      open:()=>opening=openGoogle({ledger:f.ledger,id,env:f.env,apiKey:'synthetic',client})});
    const running=worker.run();
    await started;
    await worker.stop('synthetic-local-cleanup');
    await running;
    f.ledger.close();
    resolveLate(delayed==='create'?{id:'synthetic-late-original'}:transport);
    await opening;
    await new Promise(resolve=>setImmediate(resolve));
    assert.throws(()=>f.ledger.get(id),/database is not open/);
    const reopened=new Ledger(f.ledger.root);
    try {
      assert.equal(reopened.get(id).provider_id,'synthetic-late-original',delayed);
      assert.equal(reopened.get(id).state,'unknown',delayed);
      assert.equal(reopened.get(id).usage_state,'reserved',delayed);
      assert.deepEqual(f.totals(),totals,delayed);
      assert.deepEqual({creates,connects,cancels,sends,receives},
        {creates:1,connects:1,cancels:1,sends:0,receives:0},delayed);
    } finally {reopened.close();}
  }
});

test('late create and connect rejection preserve original error and release retained ledger', async t => {
  for (const delayed of ['create','connect']) {
    const f=pinnedAdmission(t), id=f.input.operation_id;
    admitReviewedCampaign(f.ledger,f.input,f.env);
    const totals=f.totals();
    let rejectLate, entered;
    const pending=new Promise((resolve,reject)=>{rejectLate=reject;});
    const started=new Promise(resolve=>{entered=resolve;});
    const client={interactions:{
      create:()=>{if(delayed==='create'){entered();return pending;} return {id:'synthetic-original'};},
      connect:()=>{entered();return pending;},
    }};
    const opening=openGoogle({ledger:f.ledger,id,env:f.env,apiKey:'synthetic',client});
    await started;
    f.ledger.transition(id,'unknown',{reason:'synthetic-local-cleanup'});
    f.ledger.close();
    const error=new Error('synthetic late transport rejection');
    const rejected=assert.rejects(opening,e=>e===error);
    rejectLate(error);
    await rejected;
    assert.throws(()=>f.ledger.get(id),/database is not open/);
    const reopened=new Ledger(f.ledger.root);
    try {
      assert.equal(reopened.get(id).state,'unknown');
      assert.equal(reopened.get(id).provider_id,delayed==='connect'?'synthetic-original':null);
      assert.deepEqual(f.totals(),totals);
    } finally {reopened.close();}
  }
});

test('native worker CLI drains original opens and bounds stuck transport cleanup', {timeout:40000}, async t => {
  for (const mode of ['late-create', 'late-connect-stuck-cancel', 'never-create']) {
    const f=campaignPacket(t), id=f.input.operation_id;
    admitReviewedCampaign(f.ledger,f.input,f.env);
    f.packet.state_root=f.ledger.root; f.savePacket();
    const totals=f.totals(), trace=join(f.root,'transport.jsonl');
    const stub=`import {appendFileSync} from 'node:fs';
      const mode=${JSON.stringify(mode)}, trace=${JSON.stringify(trace)};
      const mark=phase=>{appendFileSync(trace,JSON.stringify({phase})+'\\n',{mode:0o600}); process.send({fixture_phase:phase});};
      const late=value=>new Promise(resolve=>process.on('message',m=>{if(m.fixture_release)resolve(value);}));
      const transport={send:()=>mark('send'), complete:()=>mark('complete'),
        cancel:()=>{mark('cancel');return mode.includes('stuck')?new Promise(()=>{}):Promise.resolve();},
        receive:()=>{mark('receive');throw Error('unexpected media receive');}};
      export class GoogleGenAI { interactions={
        create:()=>{mark('create');return mode==='never-create'?new Promise(()=>{}):mode==='late-create'?late({id:'synthetic-cli-original'}):{id:'synthetic-cli-original'};},
        connect:()=>{mark('connect');return mode.startsWith('late-connect')?late(transport):transport;}
      };}`;
    const preload=join(f.root,'synthetic-sdk.mjs');
    writeFileSync(preload,`import {registerHooks} from 'node:module';
      globalThis.fetch=()=>{throw Error('network forbidden in synthetic subprocess');};
      registerHooks({resolve(specifier,context,next){return specifier==='@google/genai'
        ?{url:${JSON.stringify('data:text/javascript,'+encodeURIComponent(stub))},shortCircuit:true}:next(specifier,context);}});`,{mode:0o600});
    const child=childProcess.fork(resolve('scripts/genie-worlds/worker.mjs'),
      [f.ledger.root,id,'google',f.path],{execPath:process.execPath,
        execArgv:['--import',preload],env:{...f.env,PATH:process.env.PATH},silent:true});
    t.after(()=>{if(child.exitCode===null)child.kill('SIGKILL');});
    let doneAt=null, stderr='';
    child.stderr.on('data',data=>{stderr+=data;});
    child.on('message',m=>{
      if(m.fixture_phase===(mode.startsWith('late-connect')?'connect':'create'))child.send({type:'stop'});
      if(m.type==='done'){doneAt=Date.now(); if(mode!=='never-create')child.send({fixture_release:true});}
    });
    const result=await new Promise((resolve,reject)=>{
      child.once('error',reject);child.once('exit',(code,signal)=>resolve({code,signal}));
    });
    assert.deepEqual(result,{code:0,signal:null},stderr);
    assert.ok(doneAt!==null);
    const phases=readFileSync(trace,'utf8').trim().split('\n').map(row=>JSON.parse(row).phase);
    assert.deepEqual(phases,mode==='never-create'?['create']:['create','connect','cancel']);
    assert.equal(f.ledger.get(id).provider_id,mode==='never-create'?null:'synthetic-cli-original');
    assert.equal(f.ledger.get(id).state,'unknown');
    assert.equal(f.ledger.get(id).usage_state,'reserved');
    assert.deepEqual(f.totals(),totals);
    const drain=f.ledger.db.prepare("SELECT body FROM audit WHERE json_extract(body,'$.type')='worker_shutdown_drain'").get();
    assert.equal(JSON.parse(drain.body).outcome,mode==='late-create'?'drained':'deadline');
    if(mode!=='late-create')assert.ok(Date.now()-doneAt>=4900);
    assert.ok(Date.now()-doneAt<7500,'bounded local shutdown');
    let replayCreates=0;
    await assert.rejects(openGoogle({ledger:f.ledger,id,env:f.env,apiKey:'synthetic',
      client:{interactions:{create:()=>{replayCreates++;}}}}),/paid_admission_required/);
    assert.equal(replayCreates,0);
  }
});

test('provider boundary reloads review pins and never creates or repairs reservations on refusal', async t => {
  for (const fault of ['missing-pin','changed-evidence','missing-reservation','settled','provider-id','expired','binding','credential']) {
    const f=pinnedAdmission(t), id=f.input.operation_id;
    admitReviewedCampaign(f.ledger,f.input,f.env);
    const before=f.ledger.get(id);
    let creates=0;
    const client={interactions:{create:async()=>{creates++;}}};
    let apiKey='synthetic';
    if (fault==='missing-pin') delete f.env.NETCLAW_GENIE_CAMPAIGN_REVIEW_SHA256;
    if (fault==='changed-evidence') writeFileSync(f.service.evidence.path,'changed');
    if (['missing-reservation','settled'].includes(fault)) {
      const budget=new CampaignBudget(f.authority.authority_root,f.authority.campaign_id);
      try {
        if (fault==='missing-reservation') budget.db.prepare('DELETE FROM reservations WHERE id=?').run(id);
        else budget.settle(id,{charged_microusd:1,terminal_sha256:'a'.repeat(64),billing_sha256:'b'.repeat(64)});
      } finally {budget.close();}
    }
    if (['provider-id','expired','binding'].includes(fault)) {
      const body={...before};
      if (fault==='provider-id') body.provider_id='already-sent';
      if (fault==='expired') {
        body.send_marked_at=new Date(Date.now()-200000).toISOString();
        body.deadline_at=new Date(Date.now()-70000).toISOString();
      }
      if (fault==='binding') body.review_id=randomUUID();
      f.ledger.db.prepare('UPDATE sessions SET body=? WHERE id=?').run(JSON.stringify(body),id);
    }
    if (fault==='credential') apiKey='';
    const totals=f.totals(), record=f.ledger.get(id);
    await assert.rejects(openGoogle({ledger:f.ledger,id,env:f.env,apiKey,client}),
      /campaign_review_pin_required|artifact_identity_changed|artifact_content_changed|campaign_reservation_required|campaign_reservation_settled|paid_admission_required|campaign_send_expired|credential_missing/,fault);
    assert.equal(creates,0,fault);
    assert.deepEqual(f.totals(),totals,fault);
    assert.deepEqual(f.ledger.get(id),record,fault);
  }
});

test('manager shutdown preserves late original worker results before bounded reap', {timeout:45000}, async t => {
  for (const mode of ['late-create', 'late-connect-stuck-cancel', 'frozen-create']) {
    const f=campaignPacket(t), id=randomUUID();
    f.packet.state_root=join(f.root,'manager'); f.savePacket();
    const trace=join(f.root,'shutdown-transport.jsonl');
    const stub=`import {appendFileSync} from 'node:fs';
      const mode=${JSON.stringify(mode)}, trace=${JSON.stringify(trace)};
      const mark=phase=>{appendFileSync(trace,JSON.stringify({phase})+'\\n',{mode:0o600});process.send({fixture_phase:phase});};
      const late=value=>new Promise(resolve=>process.on('message',m=>{if(m.fixture_release)resolve(value);}));
      const transport={send:()=>mark('send'),complete:()=>mark('complete'),
        cancel:()=>{mark('cancel');return mode.includes('stuck')?new Promise(()=>{}):Promise.resolve();},
        receive:()=>{mark('receive');throw Error('unexpected receive');}};
      export class GoogleGenAI { interactions={
        create:()=>{mark('create');return mode==='late-connect-stuck-cancel'?{id:'synthetic-manager-original'}:late({id:'synthetic-manager-original'});},
        connect:()=>{mark('connect');return mode==='late-connect-stuck-cancel'?late(transport):transport;}
      };}`;
    const preload=join(f.root,'synthetic-shutdown-sdk.mjs');
    writeFileSync(preload,`import {registerHooks} from 'node:module';
      globalThis.fetch=()=>{throw Error('network forbidden in synthetic subprocess');};
      registerHooks({resolve(s,c,next){return s==='@google/genai'?{url:${JSON.stringify('data:text/javascript,'+encodeURIComponent(stub))},shortCircuit:true}:next(s,c);}});`,{mode:0o600});
    const originalFork=childProcess.fork;
    let child, exited, ready, releaseTimer, stderr='';
    const started=new Promise(resolve=>{ready=resolve;});
    const mocked=t.mock.method(childProcess,'fork',(file,args,options)=>{
      child=originalFork(file,args,{...options,execArgv:['--import',preload]});
      exited=new Promise(resolve=>child.once('exit',(code,signal)=>resolve({code,signal})));
      child.stderr.on('data',data=>{stderr+=data;});
      child.on('message',m=>{
        if(m.fixture_phase===(mode.startsWith('late-connect')?'connect':'create'))ready();
        // Deliberately return AFTER the old manager 6.5s grace has expired.
        if(m.type==='done') releaseTimer=setTimeout(()=>{
          if(child.connected)child.send({fixture_release:true},()=>{});
        },2500);
      });
      return child;
    });
    syncBuiltinESMExports();
    let manager;
    try {
      manager=await createManager({root:f.packet.state_root,livePacketPath:f.path,campaignEnv:f.env,
        audit:async()=>({commit:'synthetic-audit'})});
      const review=manager.ledger.review(projection(),CAMPAIGN_SESSION_POLICY,12.5,'google');
      const response=await fetch(manager.origin+'/v1/sessions',{method:'POST',
        headers:{Authorization:`Bearer ${manager.owner}`,'Content-Type':'application/json'},
        body:JSON.stringify({request_id:id,review_ref:review.id})});
      assert.equal(response.status,200);
      await started;
      const totals=f.totals();
      if(mode==='frozen-create')assert.equal(child.kill('SIGSTOP'),true);
      const at=Date.now();
      await manager.close();
      assert.ok(Date.now()-at<15000,'bounded manager child reap');
      assert.deepEqual(await exited,mode==='frozen-create'?{code:null,signal:'SIGKILL'}:{code:0,signal:null},stderr);
      assert.equal(manager.workers.size,0);
      assert.throws(()=>process.kill(child.pid,0),/ESRCH/);
      const retained=new Ledger(f.packet.state_root);
      try {
        const row=retained.get(id);
        assert.equal(row.state,'unknown'); assert.equal(row.usage_state,'reserved');
        assert.equal(row.terminal_receipt,null);
        assert.equal(row.provider_id,mode==='frozen-create'?null:'synthetic-manager-original');
        assert.deepEqual(f.totals(),totals);
        assert.equal(totals.exposure_microusd,12_500_000);
        const phases=readFileSync(trace,'utf8').trim().split('\n').map(line=>JSON.parse(line).phase);
        assert.deepEqual(phases,mode==='frozen-create'?['create']:['create','connect','cancel']);
        const drain=retained.db.prepare("SELECT body FROM audit WHERE json_extract(body,'$.type')='worker_shutdown_drain'").get();
        if(mode!=='frozen-create')assert.equal(JSON.parse(drain.body).outcome,mode==='late-create'?'drained':'deadline');
        else assert.equal(row.reason,'manager_cleanup_expired');
        let replayCreates=0;
        await assert.rejects(openGoogle({ledger:retained,id,env:f.env,apiKey:'synthetic',
          client:{interactions:{create:()=>{replayCreates++;}}}}),/paid_admission_required/);
        assert.equal(replayCreates,0);
      } finally {retained.close();}
      const reopened=await createManager({root:f.packet.state_root});
      await reopened.close(); // lock released only after the old child is gone
    } finally {
      clearTimeout(releaseTimer);
      if(child?.exitCode===null && child?.signalCode===null)child.kill('SIGKILL');
      if(manager)await manager.close();
      mocked.mock.restore();syncBuiltinESMExports();
    }
  }
});
