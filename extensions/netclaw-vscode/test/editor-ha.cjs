/** Coordinator-only actual Code1.109 qualification. Never seeds profile/reference state. */
const vscode=require('vscode'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
exports.run=async()=>{
 const h=await import(pathToFileURL(path.resolve(__dirname,'../../../labs/ha/client_evidence.mjs')).href);
 const context=await h.loadQualification(process.env.NETCLAW_CLOUD_CONFIG,'editor'),{config,bundle,node}=context;
 assert.equal(path.resolve(process.env.NETCLAW_CLOUD_EDITOR_USER),config.profile_directory,'Selected isolated native profile changed');
 assert.match(vscode.version,/^1\.109\./,'Use the isolated qualified Code1.109 binary');
 const extension=vscode.extensions.getExtension('NetClaw.netclaw');assert.ok(extension);
 assert.equal(h.sha256(fs.readFileSync(path.join(extension.extensionPath,'dist/extension.cjs'))),config.extension_sha256,'Built source closure changed');
 const api=await extension.activate(),before=api.profiles.list(),run=String(Date.now()),out=config.evidence_directory;
 const report={schema_version:1,classification:'REAL',surface:'editor',phase:config.phase,source_commit:config.source_commit,editor:vscode.version,extension:extension.packageJSON.version,record_sha256:config.record_sha256,complete:false,checks:[],requests:[],artifacts:[]};
 const {chromium}=require(process.env.NETCLAW_TEST_PLAYWRIGHT),browser=await chromium.connectOverCDP('http://127.0.0.1:'+process.env.NETCLAW_TEST_CDP_PORT);
 const page=browser.contexts().flatMap(c=>c.pages()).find(p=>p.url().includes('workbench'));assert.ok(page);page.setDefaultTimeout(20000);
 const quick=()=>page.locator('.quick-input-widget input').first(),select=async text=>{const row=page.locator('.quick-input-list .monaco-list-row').filter({hasText:text});assert.equal(await row.count(),1);await row.click();};
 const original=['original_once','prepare_review'].includes(config.phase);let prepareNonce,prepared,decisionReady=false,prepareSent=false,decisionSent=false;
 const originalFetch=globalThis.fetch;
 // Observe and fence the same native transport; never synthesize a response or relax TLS.
 globalThis.fetch=async(url,init={})=>{
  const u=new URL(url),method=init.method||'GET';
  if(u.origin===config.origin||bundle.descriptor.manifest.manifest.nodes.some(n=>new URL(n.endpoints.https).origin===u.origin)){
   report.requests.push({method,origin:u.origin,path:u.pathname});
   if(method!=='GET'){
    assert.equal(original,true,'Recovery phase must not mutate');const body=JSON.parse(init.body);
    if(u.pathname==='/api/hud/operations'&&!prepareSent){assert.deepEqual(Object.fromEntries(Object.entries(body).filter(([k])=>k!=='client_nonce')),bundle.selection);prepareSent=true;prepareNonce=body.client_nonce;report.artifacts.push(h.writeArtifact(out,run+'-before-prepare.json',body));}
    else if(decisionReady&&!decisionSent&&u.pathname==='/api/hud/operations/'+prepared.operation_id+'/decision'){assert.deepEqual(body,{revision:prepared.revision,review_digest:prepared.review_digest,decision:'approve'});decisionSent=true;report.artifacts.push(h.writeArtifact(out,run+'-before-decision.json',{operation_id:prepared.operation_id,client_nonce:prepared.client_nonce,...body,decision_sent:true}));}
    else throw Error('Unexpected or repeated mutation refused');
   }
   assert.equal(init.redirect,'error');
  }
  return originalFetch(url,init);
 };
 try{
  let profile=before.find(p=>p.id===config.profile_id);
  if(original){
   h.claimOriginal(context);assert.equal(profile,undefined,'Original phase starts a fresh dedicated connection');
   const adding=vscode.commands.executeCommand('netclaw.addConnection');
   await page.locator('.quick-input-list .monaco-list-row').filter({hasText:'Cloud Border'}).first().click();
   await quick().waitFor({state:'visible'});await quick().fill('R08 actual HA qualification');await quick().press('Enter');
   await quick().waitFor({state:'visible'});await quick().fill(config.origin);await quick().press('Enter');
   const trust=page.getByRole('button',{name:'Trust cluster',exact:true});await trust.waitFor({state:'visible'});
   assert.ok((await page.locator('.monaco-dialog-box').innerText()).includes(bundle.pin.anchor_key_id));
   report.artifacts.push(h.writeArtifact(out,run+'-anchor-review.png',await page.screenshot()));await trust.click();await adding;
   profile=api.connection.profile;assert.ok(profile?.cluster);assert.equal(profile.cluster.pin.anchor_key_id,bundle.pin.anchor_key_id);
  }else{
   assert.ok(profile?.cluster,'Recovery requires the original retained native profile');
   assert.equal(profile.cluster.pin.cluster_id,bundle.pin.cluster_id);assert.equal(profile.cluster.pin.generation,bundle.pin.generation);
   if(config.phase==='endpoint_recovery'){
    const replacing=vscode.commands.executeCommand('netclaw.replaceCloudEndpoint');await select(profile.label);await quick().waitFor({state:'visible'});await quick().fill(config.origin);await quick().press('Enter');
    const confirm=page.getByRole('button',{name:'Replace endpoint',exact:true});await confirm.waitFor({state:'visible'});const text=await page.locator('.monaco-dialog-box').innerText();assert.ok(text.includes(profile.installationId)&&text.includes(node.installation_id)&&text.includes(bundle.pin.cluster_id));report.artifacts.push(h.writeArtifact(out,run+'-endpoint-review.png',await page.screenshot()));await confirm.click();await replacing;
    assert.equal(api.connection.profile.id,profile.id);profile=api.connection.profile;
   }else{assert.equal(profile.url,config.origin);await api.connection.connect(profile);}
  }
  assert.equal(api.connection.owner.expectedId,node.installation_id);assert.ok(api.connection.owner.cluster);await api.ownerWorkflow.overview();
  report.authority=api.connection.owner.cluster.descriptor.authority;report.profile_id=profile.id;
  report.artifacts.push(h.writeArtifact(out,run+'-authority.png',await page.screenshot()));
  if(config.phase==='no_quorum')assert.equal(report.authority.state,'no_quorum');
  if(original){
   const catalog=await api.connection.owner.catalog(),choices=[];for(const row of catalog.members)for(const model of row.model_profiles)for(const tool of row.tools)choices.push({catalog_revision:catalog.revision,member_id:row.member.member_id,model_profile_id:model.profile_id,tool:tool.tool,arguments:tool.arguments});
   const index=choices.findIndex(v=>h.canonical(v)===h.canonical(bundle.selection));assert.ok(index>=0);
   const pending=api.ownerWorkflow.prepare();await page.locator('.quick-input-list .monaco-list-row').nth(index).click();
   const review=page.getByRole('button',{name:'Review decision',exact:true});await review.waitFor({state:'visible'});
   const document=vscode.workspace.textDocuments.find(d=>d.uri.scheme==='netclaw-owner'&&d.getText().includes('review_digest'));assert.ok(document);const display=JSON.parse(document.getText());
   // Fetch original status once to bind state/counters in addition to the displayed immutable review.
   prepared=await api.connection.owner.status({operation_id:display.operation_id,client_nonce:prepareNonce});
   assert.equal(prepared.review_digest,display.review_digest);assert.deepEqual(prepared.review,display.review);h.assertExactReview(prepared,context);
   report.artifacts.push(h.writeArtifact(out,run+'-original-review.json',prepared));
   if(config.phase==='prepare_review'){report.reference={operation_id:prepared.operation_id,client_nonce:prepared.client_nonce};report.acceptance_complete=false;report.checks.push('Actual Code originated pending exact review; no decision sent');report.complete=true;return;}
   await review.click();
   const approve=page.getByRole('button',{name:'Approve once',exact:true});await approve.waitFor({state:'visible'});const text=await page.locator('.monaco-dialog-box').innerText();assert.ok(text.includes(prepared.operation_id)&&text.includes(prepared.review_digest));report.artifacts.push(h.writeArtifact(out,run+'-exact-native-review.png',await page.screenshot()));
   decisionReady=true;await approve.click();try{report.operation=await pending;}catch(error){report.decision_error=String(error.message||error);report.outcome_unknown=!error.status;if(error.status)throw error;}
   assert.equal(prepareSent,true);assert.equal(decisionSent,true);report.reference={operation_id:prepared.operation_id,client_nonce:prepared.client_nonce,decision_sent:true};report.acceptance_complete=false;
   report.checks.push('Actual Code prepared and approved the complete exact original review once; identifiers persisted before sending; signed-result acceptance remains a later phase');
  }else{
   const expected=config.phase==='stale_review'?bundle.stale:bundle.completed;
   if(config.phase==='stale_review')assert.equal(api.connection.owner.canDecide({review:expected.review}),false);
   const pending=api.ownerWorkflow.recover();await select(expected.reference.operation_id);
   // Never accept a Review decision or Reconcile prompt in this recovery-only phase.
   const operation=await Promise.race([pending,new Promise((_,reject)=>setTimeout(()=>reject(Error('Native recovery requested a decision/reconcile or did not complete')),25000))]);h.assertOriginal(operation,expected,config.phase==='stale_review'?undefined:context.receipt.digest);
   report.operation=operation;report.reference=expected.reference;h.unchangedCounters(context);assert.ok(report.requests.every(r=>r.method==='GET'));
   report.checks.push('Native retained original reference recovered; signed result/ACK correlated; cumulative actual runtime counters unchanged');
  }
  report.artifacts.push(h.writeArtifact(out,run+'-native-result.png',await page.screenshot()));
  assert.deepEqual(api.profiles.list().filter(p=>p.id!==profile.id),before.filter(p=>p.id!==profile.id));report.complete=true;
 }catch(error){report.error=String(error.message||error);try{report.artifacts.push(h.writeArtifact(out,run+'-failure.png',await page.screenshot()));}catch{}}
 finally{globalThis.fetch=originalFetch;await browser.close();h.writeArtifact(out,run+'-editor-report.json',report);fs.writeFileSync(process.env.NETCLAW_TEST_REPORT,JSON.stringify(report,null,2),{mode:0o600});}
};
