/** Actual browser recovery driver. Runs only on explicit CLI invocation with private REAL inputs. */
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
import {loadQualification,writeArtifact,assertOriginal,unchangedCounters,canonical,sha256,claimOriginal,assertExactReview,awaitBudgetClaim,readBudgetClaim} from './client_evidence.mjs';
import {verifyClusterRuntime,clusterCanDecide,clusterStatusText} from '../../ui/netclaw-visual/src/shared/cluster-binding.js';
export async function runBrowser(configFile) {
 const context=await loadQualification(configFile,'browser'),{config,bundle,node}=context;
 assert.ok(path.isAbsolute(config.playwright_module));if(!config.browser_cdp_url)assert.ok(path.isAbsolute(config.browser_executable));else assert.match(config.browser_cdp_url,/^http:\/\/127\.0\.0\.1:[0-9]{1,5}$/);
 const {chromium}=await import(pathToFileURL(config.playwright_module).href);
 const report={schema_version:1,classification:'REAL',surface:'browser',phase:config.phase,source_commit:config.source_commit,record_sha256:config.record_sha256,complete:false,checks:[],requests:[],artifacts:[]};
 const run=String(Date.now()),out=config.evidence_directory;
 const original=['original_once','prepare_review'].includes(config.phase);if(original)claimOriginal(context);
 // Persistent, dedicated profile preserves this origin's own monotone sent markers.
 const connected=config.browser_cdp_url?await chromium.connectOverCDP(config.browser_cdp_url):null;
 const browser=connected?connected.contexts()[0]:await chromium.launchPersistentContext(config.profile_directory,{executablePath:config.browser_executable,headless:config.headless!==false,viewport:{width:1440,height:1100},ignoreHTTPSErrors:false,args:['--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run']});
 assert.ok(browser);const page=browser.pages().find(p=>p.url().startsWith(config.origin+'/'))||await browser.newPage();page.setDefaultTimeout(20000);
 const expected=config.phase==='stale_review'?bundle.stale:bundle.completed;let observed,prepared,decisionReady=false,prepareSent=false,decisionSent=false;
 try {
  report.browser=browser.browser()?.version();
  const origins=new Set(bundle.descriptor.manifest.manifest.nodes.map(n=>new URL(n.endpoints.https).origin));
  await browser.route('**/*',route=>{const r=route.request(),u=new URL(r.url());
    if(original&&u.origin===config.origin&&r.method()==='POST'){
      const body=r.postDataJSON();
      if(u.pathname==='/api/hud/operations'&&!prepareSent){assert.deepEqual(Object.fromEntries(Object.entries(body).filter(([k])=>k!=='client_nonce')),bundle.selection);prepareSent=true;report.artifacts.push(writeArtifact(out,run+'-before-prepare.json',body));report.requests.push({method:'POST',path:u.pathname,client_nonce:body.client_nonce});return route.continue();}
      if(decisionReady&&!decisionSent&&u.pathname==='/api/hud/operations/'+prepared.operation_id+'/decision'){assert.deepEqual(readBudgetClaim(context,prepared),report.budget_claim);assert.deepEqual(body,{revision:prepared.revision,review_digest:prepared.review_digest,decision:'approve'});decisionSent=true;report.artifacts.push(writeArtifact(out,run+'-before-decision.json',{operation_id:prepared.operation_id,client_nonce:prepared.client_nonce,...body,decision_sent:true,budget_claim:report.budget_claim}));report.requests.push({method:'POST',path:u.pathname});return route.continue();}
    }
    if(!origins.has(u.origin)||r.method()!=='GET'){report.requests.push({method:r.method(),path:u.pathname,blocked:true});return route.abort('blockedbyclient');}report.requests.push({method:r.method(),origin:u.origin,path:u.pathname});return route.continue();});
  page.on('response',async response=>{try{const u=new URL(response.url());if(original&&u.pathname==='/api/hud/operations'&&response.request().method()==='POST'&&response.ok())prepared=await response.json();else if(expected&&u.pathname==='/api/hud/operations/'+expected.reference.operation_id&&response.ok())observed=await response.json();}catch{}});
  await page.goto(config.origin,{waitUntil:'domcontentloaded'});
  const runtime=await page.evaluate(async()=>{const r=await fetch('/api/runtime',{redirect:'error',cache:'no-store'});if(!r.ok)throw Error('runtime unavailable');return r.json();});
  const verified=await verifyClusterRuntime(runtime,{pin:bundle.pin,origin:config.origin});assert.equal(verified.descriptor.installation_id,node.installation_id);report.authority=runtime.cluster.authority;
  const trust=page.getByRole('button',{name:'Trust cluster',exact:true});
  if(await trust.count()){await trust.waitFor({state:'visible'});await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Trust cluster'&&!b.disabled));await trust.click();report.checks.push('Explicit native browser trust accepted only after offline pinned manifest verification');}
  await page.locator('[aria-label="Cluster authority"]').waitFor();
  if(original){
    const catalog=await page.evaluate(async c=>(await fetch('/api/hud/operations/catalog',{headers:{'X-NetClaw-Installation':c.installation_id,'X-NetClaw-Cluster-ID':c.cluster_id,'X-NetClaw-Cluster-Generation':c.generation},redirect:'error'})).json(),runtime.cluster);
    const m=catalog.members.findIndex(row=>row.member.member_id===bundle.selection.member_id);assert.ok(m>=0);const row=catalog.members[m];
    const model=row.model_profiles.findIndex(p=>p.profile_id===bundle.selection.model_profile_id),tool=row.tools.findIndex(t=>t.tool===bundle.selection.tool&&canonical(t.arguments)===canonical(bundle.selection.arguments));assert.ok(model>=0&&tool>=0);
    await page.getByLabel('Member',{exact:true}).selectOption(String(m));await page.getByLabel('Model profile',{exact:true}).selectOption(String(model));await page.getByLabel('Read-only call',{exact:true}).selectOption(String(tool));
    await page.getByRole('button',{name:'Prepare review',exact:true}).click();await page.getByRole('button',{name:'Approve once',exact:true}).waitFor();
    assert.ok(prepared);assertExactReview(prepared,context);report.artifacts.push(writeArtifact(out,run+'-original-review.json',prepared));report.artifacts.push(writeArtifact(out,run+'-review.png',await page.screenshot({fullPage:true})));
    if(config.phase==='prepare_review'){report.reference={operation_id:prepared.operation_id,client_nonce:prepared.client_nonce};report.acceptance_complete=false;report.checks.push('Actual browser originated one pending review; no decision sent');report.complete=true;return report;}
    report.budget_claim=await awaitBudgetClaim(context,prepared);assertExactReview(prepared,context);report.artifacts.push(writeArtifact(out,run+'-budget-claim.json',report.budget_claim));
    const confirmation=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/hud/operations/'+prepared.operation_id+'/decision',{timeout:40000}).then(async r=>({status:r.status(),operation:await r.json()})).catch(()=>({outcome_unknown:true}));
    assert.deepEqual(readBudgetClaim(context,prepared),report.budget_claim);decisionReady=true;await page.getByRole('button',{name:'Approve once',exact:true}).click();report.confirmation=await confirmation;
    assert.equal(prepareSent,true);assert.equal(decisionSent,true);assert.ok(report.requests.every(r=>!r.blocked));if(report.confirmation.status)assert.equal(report.confirmation.status,200,'Original decision was refused; preserve the one-shot state');report.reference={operation_id:prepared.operation_id,client_nonce:prepared.client_nonce,decision_sent:true};report.acceptance_complete=false;report.checks.push('Actual browser originated one prepare and one exact approval; original IDs persisted before network; REAL result correlation remains required');report.complete=true;
    return report;
  }
  const authority=runtime.cluster.authority;report.authority=authority;report.checks.push(clusterStatusText(runtime.cluster));
  if(config.phase==='no_quorum'){assert.equal(authority.state,'no_quorum');const prepare=page.getByRole('button',{name:'Prepare review',exact:true});if(await prepare.count())assert.equal(await prepare.isDisabled(),true);}
  if(config.phase==='stale_review')assert.equal(clusterCanDecide(runtime.cluster,{review:expected.review}),false);
  const retained=await page.evaluate(()=>Object.keys(sessionStorage).filter(k=>k.endsWith('.operations.v2')).flatMap(k=>JSON.parse(sessionStorage.getItem(k)||'[]')));
  if(config.phase==='cold_recovery'){assert.ok(retained.some(r=>r.operation_id===expected.reference.operation_id&&r.decision_sent===true),'Cold recovery must retain a previously sent reference in this same profile/origin');}
  const inspect=page.getByRole('button',{name:'Inspect operation '+expected.reference.operation_id,exact:true});
  if(await inspect.count()){await inspect.click();await page.getByRole('button',{name:'Check status',exact:true}).click();}
  else {assert.notEqual(config.phase,'cold_recovery');await page.getByLabel('Recovery reference type').selectOption('operation_id');await page.getByLabel('Recover retained reference',{exact:true}).fill(expected.reference.operation_id);await page.getByRole('button',{name:'Recover existing operation',exact:true}).click();}
  await page.waitForFunction(id=>document.querySelector('[aria-label="Immutable operation review"]')?.textContent.includes(id),expected.review.border.installation_id);
  const deadline=Date.now()+20000;while(!observed&&Date.now()<deadline)await new Promise(r=>setTimeout(r,50));assert.ok(observed,'Original owned status must be readable');
  assertOriginal(observed,expected,config.phase==='stale_review'?undefined:context.receipt.digest);
  const approve=page.getByRole('button',{name:'Approve once',exact:true});if(await approve.count())assert.equal(await approve.isDisabled(),true,'Recovery-only refs and stale reviews cannot enable approval');
  if(observed.observation?.kind==='retained')await page.getByText(/Retained status last observed/).waitFor();
  if(!observed.result&&observed.result_reference)await page.getByRole('heading',{name:'Original result retained',exact:true}).waitFor();
  const screenshot=await page.screenshot({fullPage:true});report.artifacts.push(writeArtifact(out,run+'-'+config.phase+'.png',screenshot));
  report.artifacts.push(writeArtifact(out,run+'-original-status.json',observed));
  report.rendered_sha256=sha256(await page.locator('body').innerText());
  report.reference=expected.reference;report.result_digest=context.receipt.digest;
  unchangedCounters(context);assert.ok(report.requests.every(r=>r.method==='GET'&&!r.blocked),'No mutation, untrusted navigation or redirect target was attempted');
  report.checks.push('Original signed result/ACK correlated; actual cumulative counters unchanged; status-only requests');report.complete=true;
 }catch(error){report.error=String(error.message||error);try{report.artifacts.push(writeArtifact(out,run+'-failure.png',await page.screenshot({fullPage:true})));}catch{}}
 finally{if(connected)await connected.close();else await browser.close();writeArtifact(out,run+'-browser-report.json',report);}
 return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){const result=await runBrowser(process.argv[2]);console.log(JSON.stringify({complete:result.complete,phase:result.phase}));if(!result.complete)process.exitCode=1;}
