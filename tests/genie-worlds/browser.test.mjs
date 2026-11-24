import test from "node:test";
import assert from "node:assert/strict";
import {
  mkdirSync,
  writeFileSync,
  readFileSync,
} from "node:fs";
import { join } from "node:path";
import { createBrowserFixture } from './browser-fixture.mjs';
import { POLICY, CAMPAIGN_SESSION_POLICY } from "../../scripts/genie-worlds/model.mjs";
const enabled = Boolean(process.env.NETCLAW_BROWSER_EXECUTABLE);
test('actual Chrome movement identity survives modifier changes, repeats and release guards',
  { skip: !enabled, timeout: 15000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'keyboard-identity-');
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const active = { state: 'active', event_state: 'planned', session_bounds: {
      accounting_mode: 'fixture', policy: POLICY, estimated_usd: 0, reservation_usd: 0 },
      terminal_confirmed: false, usage_state: 'unknown' };
    const messages = [], events = [], errors = []; let socket, onControl;
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => {
      window.keyWitness = [];
      for (const type of ['keydown', 'keyup']) window.addEventListener(type, e =>
        window.keyWitness.push({ type, key: e.key, code: e.code, repeat: e.repeat,
          defaultPrevented: e.defaultPrevented }));
    });
    await page.routeWebSocket('**/v1/view/**', ws => { socket = ws; ws.onMessage(v => { const message = JSON.parse(v); messages.push(message); onControl?.(message); }); });
    await page.route('**/v1/**', async route => {
      const path = new URL(route.request().url()).pathname;
      if (route.request().method() === 'POST' && path !== '/v1/bootstrap')
        return route.fulfill({ json: path === '/v1/reviews' ? { id: 'synthetic-review' } : path === '/v1/sessions' ? active : {} });
      return route.continue();
    });
    await page.goto(m.origin + '/#' + m.bootstrap); await page.locator('#start').click();
    await page.waitForFunction(() => document.activeElement?.id === 'world');
    socket.send(JSON.stringify({ type: 'frame_meta', sequence: 1 }));
    socket.send(readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg', import.meta.url)));
    await page.waitForFunction(() => !document.querySelector('#event').disabled);
    const observe = async (action, predicate) => {
      const received = new Promise(resolve => { onControl = message => { if (predicate(message)) resolve(); }; });
      await action(); await received; onControl = undefined;
    };
    const barrier = () => observe(
      () => page.evaluate(() => document.querySelector('#world').dispatchEvent(new Event('blur'))),
      message => message.type === 'release');
    await page.keyboard.down('w'); await page.keyboard.down('Shift');
    await page.keyboard.down('W'); await page.keyboard.up('W'); await page.keyboard.up('Shift');
    await barrier();
    const first = messages.filter(v => v.type === 'key');
    const witness = await page.evaluate(() => window.keyWitness);
    if (process.env.NETCLAW_BROWSER_EVIDENCE) writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE, 'keyboard-reproduction.json'),
      JSON.stringify({ synthetic: true, witness, controls: messages, provider_calls: 0 }, null, 2), { mode: 0o600 });
    assert.ok(witness.some(e => e.type === 'keyup' && e.key === 'W' && e.code === 'KeyW'));
    assert.deepEqual(first.map(({ key, down }) => ({ key, down })), [{ key: 'w', down: true }, { key: 'w', down: false }]);
    for (const key of ['a', 's', 'd']) {
      await page.keyboard.down('Shift'); await page.keyboard.down(key.toUpperCase());
      await page.keyboard.up('Shift'); await page.keyboard.up(key); await barrier();
      assert.deepEqual(messages.filter(v => v.type === 'key' && v.key === key).map(v => v.down), [true, false]);
    }
    await page.keyboard.down('ArrowLeft'); await page.keyboard.down('ArrowLeft'); await page.keyboard.up('ArrowLeft'); await barrier();
    assert.deepEqual(messages.filter(v => v.type === 'key' && v.key === 'arrow_left').map(v => v.down), [true, false]);
    // Native repeated keydown must remain a viewer control, not a page-scroll
    // command. Observe both browser defaults and ordered transport packets.
    await page.evaluate(() => window.scrollTo(0, 0));
    const scrollBefore = await page.evaluate(() => window.scrollY);
    await page.keyboard.down('ArrowDown');
    for (let i = 0; i < 8; i++) await page.keyboard.down('ArrowDown');
    await page.keyboard.up('ArrowDown'); await barrier();
    await page.waitForTimeout(300); // Allow native scroll animation to settle.
    const repeatEvidence = await page.evaluate(() => ({ scrollAfter: window.scrollY,
      keys: window.keyWitness.filter(e => e.key === 'ArrowDown') }));
    repeatEvidence.scrollBefore = scrollBefore;
    repeatEvidence.controls = messages.filter(v => v.type === 'key' && v.key === 'arrow_down');
    if (process.env.NETCLAW_BROWSER_EVIDENCE) {
      writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE, 'arrow-repeat.json'),
        JSON.stringify({ synthetic: true, provider_calls: 0, ...repeatEvidence }, null, 2), { mode: 0o600 });
      await page.screenshot({ path: join(process.env.NETCLAW_BROWSER_EVIDENCE, 'arrow-repeat.png'), fullPage: true });
    }
    assert.ok(repeatEvidence.keys.some(e => e.repeat), 'native repeated keydown observed');
    assert.ok(repeatEvidence.keys.filter(e => e.type === 'keydown').every(e => e.defaultPrevented),
      'all active movement keydowns suppress browser scrolling');
    assert.equal(repeatEvidence.scrollAfter, scrollBefore);
    assert.deepEqual(repeatEvidence.controls.map(v => v.down), [true, false]);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => window.keyWitness.findLast(e => e.key === 'Tab' && e.type === 'keydown').defaultPrevented), false,
      'unrelated focus navigation remains native');
    for (const guard of ['escape', 'canvas-blur', 'window-blur', 'terminal']) {
      await page.locator('canvas').focus();
      await observe(() => page.keyboard.down('w'), message => message.type === 'key' && message.down);
      const before = messages.filter(v => v.type === 'key').length;
      if (guard === 'escape') await page.keyboard.press('Escape');
      else if (guard === 'canvas-blur') await page.locator('#evidence').focus();
      else if (guard === 'window-blur') await page.evaluate(() => window.dispatchEvent(new Event('blur')));
      else {
        socket.send(JSON.stringify({ type: 'status', session: { ...active, state: 'terminal', terminal_confirmed: true } }));
        await page.waitForFunction(() => document.querySelector('#status').textContent.startsWith('terminal'));
      }
      await page.keyboard.up('w'); await barrier();
      assert.equal(messages.filter(v => v.type === 'key').length, before, guard + ' clears held identity');
      assert.equal(messages.filter(v => ['key', 'release'].includes(v.type)).at(-1).type, 'release');
      events.push({ guard, released: true });
    }
    const count = messages.filter(v => v.type === 'key').length;
    await page.locator('canvas').focus(); await page.keyboard.press('Shift+W'); await barrier();
    assert.equal(messages.filter(v => v.type === 'key').length, count);
    assert.equal(messages.filter(v => v.type === 'event').length, 0);
    assert.equal(m.ledger.list().length, 0); assert.deepEqual(errors, []);
    if (process.env.NETCLAW_BROWSER_EVIDENCE) {
      await page.screenshot({ path: join(process.env.NETCLAW_BROWSER_EVIDENCE, 'keyboard-released.png'), fullPage: true });
      writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE, 'keyboard-guards.json'),
        JSON.stringify({ synthetic: true, controls: messages, guards: events, provider_calls: 0 }, null, 2), { mode: 0o600 });
    }
  });
test('actual Chrome late status cannot regress ended state and original receipts can reconcile',
  { skip: !enabled, timeout: 15000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'status-order-');
    const active={state:'active',event_state:'planned',session_bounds:{accounting_mode:'fixture',policy:POLICY,estimated_usd:0,reservation_usd:0},terminal_confirmed:false,usage_state:'unknown'};
    const context=await browser.newContext(), results=[];
    for(const endState of ['unknown','terminal','failed_pre_send']) {
      const page=await context.newPage({viewport:{width:1280,height:900}});
      let socket; const requests=[],errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.routeWebSocket('**/v1/view/**',ws=>{socket=ws;});
      await page.route('**/v1/**',async route=>{
        const path=new URL(route.request().url()).pathname;
        if(route.request().method()==='POST' && path!=='/v1/bootstrap') {
          requests.push(path);
          return route.fulfill({json:path==='/v1/reviews'?{id:'synthetic-review'}:path==='/v1/sessions'?active:{}});
        }
        if(path.endsWith('/evidence'))return route.fulfill({json:{synthetic:true,operation_id:path.split('/')[3]}});
        return route.continue();
      });
      await page.goto(m.origin+(results.length?'':'/#'+m.bootstrap));await page.locator('#start').click();
      await page.waitForFunction(()=>document.activeElement?.id==='world');
      const original=await page.evaluate(()=>sessionStorage.getItem('genie_last_operation'));
      const status=async fields=>{
        socket.send(JSON.stringify({type:'status',session:{...active,...fields}}));
        // Round-trip marker on the same socket guarantees the status was handled.
        socket.send(JSON.stringify({type:'error',code:'status-barrier'}));
        await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('status-barrier'));
        socket.send(JSON.stringify({type:'status',session:{...active,...fields}}));
        await page.waitForFunction(()=>!document.querySelector('#status').textContent.includes('status-barrier'));
      };
      await status({state:endState,terminal_confirmed:endState==='terminal',usage_state:'unsettled'});
      const ended=await page.locator('#status').innerText();
      await status({state:'active'});
      assert.equal(await page.locator('#status').innerText(),ended,'late active cannot overwrite ended lifecycle');
      if(endState!=='failed_pre_send') {
        await status({state:'terminal',terminal_confirmed:true,usage_state:'unsettled'});
        assert.match(await page.locator('#status').innerText(),/terminal · provider receipt retained · usage unsettled/);
        await status({state:'terminal',terminal_confirmed:true,usage_state:'reconciled'});
        await status({state:'unknown'});
        await status({state:'terminal',terminal_confirmed:false,usage_state:'unsettled'});
        assert.match(await page.locator('#status').innerText(),/terminal · provider receipt retained · usage reconciled/);
      }
      for(const id of ['stop','event','navshot','eventshot'])assert.equal(await page.locator('#'+id).isEnabled(),false);
      await page.locator('#evidence').click();
      await page.waitForFunction(()=>document.querySelector('#result').textContent.includes('operation_id'));
      assert.equal(JSON.parse(await page.locator('#result').innerText()).operation_id,original);
      assert.equal(requests.filter(p=>p==='/v1/sessions').length,1);
      assert.equal(requests.filter(p=>p.endsWith('/stop')).length,0);
      assert.deepEqual(errors,[]);
      results.push({endState,status:await page.locator('#status').innerText(),original_operation_retained:true,synthetic:true});
      if(process.env.NETCLAW_BROWSER_EVIDENCE && endState==='unknown')await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,'status-reconciled.png'),fullPage:true});
      await page.close();
    }
    assert.equal(m.ledger.list().length,0);
    if(process.env.NETCLAW_BROWSER_EVIDENCE)writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,'status-order.json'),JSON.stringify({results,provider_calls:0,sessions:0},null,2),{mode:0o600});
  });
test('actual Chrome baseline timeout preserves ambiguity and original-session stop without replay',
  { skip: !enabled, timeout: 30000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'baseline-timeout-');
    const active={state:'active',event_state:'planned',session_bounds:{accounting_mode:'fixture',policy:POLICY,estimated_usd:0,reservation_usd:0},terminal_confirmed:false,usage_state:'unknown'};
    const jpeg=readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg',import.meta.url));
    const context=await browser.newContext(),results=[];
    for(const scenario of ['hanging','lost-reply','stop-pending','late-success']) {
      const page=await context.newPage({viewport:{width:1280,height:900}});
      const requests=[],errors=[],messages=[];let socket,settle;
      const pending=new Promise(resolve=>{settle=resolve;});t.after(settle);
      page.on('pageerror',e=>errors.push(e.message));
      await page.routeWebSocket('**/v1/view/**',ws=>{socket=ws;ws.onMessage(v=>messages.push(JSON.parse(v)));});
      await page.route('**/v1/**',async route=>{
        const path=new URL(route.request().url()).pathname;
        if(path.endsWith('/evidence')) return route.fulfill({json:{synthetic:true,operation_id:path.split('/')[3],baseline:'inspect original receipt'}});
        if(route.request().method()==='POST' && path!=='/v1/bootstrap') {
          requests.push({path,name:path.endsWith('/checkpoint')?route.request().postDataJSON().name:undefined});
          if(path.endsWith('/checkpoint')) {
            await pending;
            if(['lost-reply','hanging'].includes(scenario)) return route.abort('failed');
          }
          return route.fulfill({json:path==='/v1/reviews'?{id:'synthetic-review'}:path==='/v1/sessions'?active:path.endsWith('/stop')?{...active,state:'terminal',terminal_confirmed:true}:{}});
        }
        return route.continue();
      });
      await page.goto(m.origin+(results.length?'':'/#'+m.bootstrap));await page.locator('#start').click();
      await page.waitForFunction(()=>document.activeElement?.id==='world');
      const original=await page.evaluate(()=>sessionStorage.getItem('genie_last_operation'));
      const frame=n=>{socket.send(JSON.stringify({type:'frame_meta',sequence:n}));socket.send(jpeg);};
      frame(1);
      await page.waitForFunction(()=>document.querySelector('#mode').textContent.includes('FRAME DECODED'));
      if(scenario==='stop-pending') await page.locator('#stop').click();
      if(scenario==='lost-reply') settle();
      await page.waitForFunction(()=>document.querySelector('#capture-status').textContent.includes('Baseline: Unconfirmed'),null,{timeout:4500});
      assert.match(await page.locator('#capture-status').innerText(),/original session evidence.*Do not repeat/);
      await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('terminal'));
      settle();frame(2);socket.send(JSON.stringify({type:'status',session:active}));
      await page.waitForTimeout(100);
      await page.evaluate(()=>{document.querySelector('#navshot').onclick();document.querySelector('#eventshot').onclick();document.querySelector('#event').onclick();});
      await page.locator('canvas').focus();await page.keyboard.press('w');
      for(const id of ['event','navshot','eventshot'])assert.equal(await page.locator('#'+id).isEnabled(),false);
      assert.equal(requests.filter(v=>v.name==='baseline').length,1);
      assert.equal(requests.filter(v=>v.path==='/v1/sessions').length,1);
      assert.ok(requests.some(v=>v.path===`/v1/sessions/${original}/stop`));
      assert.equal(messages.filter(v=>['key','event'].includes(v.type)).length,0);
      assert.equal(await page.evaluate(()=>sessionStorage.getItem('genie_last_operation')),original);
      await page.locator('#evidence').click();
      await page.waitForFunction(()=>document.querySelector('#result').textContent.includes('inspect original receipt'));
      assert.equal(JSON.parse(await page.locator('#result').innerText()).operation_id,original);
      assert.match(await page.locator('#capture-status').innerText(),/Baseline: Unconfirmed/);
      assert.deepEqual(errors,[]);results.push({scenario,synthetic:true,baseline_requests:1,status:await page.locator('#capture-status').innerText(),original_session_retained:true});
      if(process.env.NETCLAW_BROWSER_EVIDENCE && scenario==='hanging')await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,'baseline-unconfirmed.png'),fullPage:true});
      await page.close();
    }
    assert.equal(m.ledger.list().length,0);
    if(process.env.NETCLAW_BROWSER_EVIDENCE)writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,'baseline-timeout.json'),JSON.stringify({results,provider_calls:0,sessions:0},null,2),{mode:0o600});
  });
test(
  "actual isolated Chrome fixture playback,controls,event,recording,stop",
  { skip: !enabled, timeout: 30000 },
  async (t) => {
    const { m, browser } = await createBrowserFixture(t, 'browser-');
    const page = await browser.newPage({
      viewport: { width: 1280, height: 900 },
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(m.origin + "/#" + m.bootstrap);
    await page.waitForFunction(() => document.querySelector('#bounds').textContent.includes('Offline fixture'));
    assert.match(await page.locator('#bounds').innerText(), /20-second target · 30-second local deadline/);
    assert.match(await page.locator('#cost').innerText(), /Fixture cost US\$0.00 · reservation US\$0.00/);
    assert.match(await page.locator('#mode').innerText(), /OFFLINE TRANSPORT FIXTURE.*No frame decoded/);
    await page
      .getByRole("button", { name: "Review and start fixture" })
      .click();
    await page.waitForFunction(() =>
      /^(active|unknown)/.test(document.querySelector("#status").textContent),
    );
    assert(
      (await page.locator("#status").textContent()).startsWith("active"),
      JSON.stringify(m.ledger.list()),
    );
    await page.locator("canvas").focus();
    await page.keyboard.down("w");
    await page.waitForTimeout(500);
    await page.keyboard.up("w");
    await page
      .getByRole("button", { name: "Capture navigation checkpoint" })
      .click();
    await page
      .getByRole("button", { name: "Target visible: dim corridor" })
      .click();
    await page.waitForTimeout(500);
    await page
      .getByRole("button", { name: "Capture event checkpoint" })
      .click();
    await page
      .getByRole("button", { name: "Stop session", exact: true })
      .click();
    await page.waitForFunction(() =>
      document.querySelector("#status").textContent.startsWith("terminal"),
    );
    await page.waitForTimeout(300);
    await page.getByRole("button", { name: "View evidence" }).click();
    await page.waitForFunction(() =>
      document
        .querySelector("#result")
        .textContent.includes("live_world_proven"),
    );
    const evidence = JSON.parse(await page.locator("#result").innerText());
    assert.equal(evidence.live_world_proven, false);
    assert.equal(evidence.session.terminal_confirmed, true);
    assert.match(await page.locator('#mode').innerText(), /OFFLINE TRANSPORT FIXTURE.*VIEWING ENDED.*Last decoded frame retained/);
    assert.match(await page.locator('#cost').innerText(), /Fixture cost US\$0.00/);
    assert.equal(evidence.session.event_state, "sent");
    assert.equal(evidence.event_checkpoint.state, 'correlated');
    assert.equal(evidence.event_checkpoint.receipt.operation_id, evidence.session.operation_id);
    assert.equal(evidence.event_checkpoint.receipt.visible_effect, 'unassessed');
    assert.equal(evidence.manifest.length, 4);
    assert(
      evidence.manifest.find((x) => x.mime === "video/webm").size_bytes > 0,
    );
    assert.deepEqual(errors, []);
    if (process.env.NETCLAW_BROWSER_EVIDENCE) {
      const out = process.env.NETCLAW_BROWSER_EVIDENCE;
      mkdirSync(out, { recursive: true, mode: 0o700 });
      await page.screenshot({
        path: join(out, "fixture-viewer.png"),
        fullPage: true,
      });
      writeFileSync(
        join(out, "result.json"),
        JSON.stringify(evidence, null, 2),
        { mode: 0o600 },
      );
    }
  },
);

test('actual Chrome renders immutable synthetic campaign and legacy budget packets without admission',
  { skip: !enabled, timeout: 30000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'budget-viewer-');
    const context=await browser.newContext();
    const page=await context.newPage({viewport:{width:1280,height:900}});
    // Display-only synthetic responses. The actual manager stays fixture-only;
    // no review, authorization, session, credential or provider call is created.
    const packets=Object.freeze([
      Object.freeze({accounting_mode:'campaign-v1',policy:CAMPAIGN_SESSION_POLICY,
        estimated_usd:12.567891,estimated_video_usd:12.096,reservation_usd:12.567891,
        campaign_limits:Object.freeze({soft_stop_usd:25,hard_stop_usd:50})}),
      Object.freeze({accounting_mode:'legacy',policy:POLICY,
        estimated_usd:2.016,estimated_video_usd:null,reservation_usd:15}),
    ]);
    let packet=packets[0], forbidden=0;
    await page.route('**/v1/**',async route=>{
      const path=new URL(route.request().url()).pathname;
      if (route.request().method()==='POST' && path!=='/v1/bootstrap') {
        forbidden++; return route.abort();
      }
      const response=await route.fetch(), data=await response.json();
      if (['/v1/bootstrap','/v1/client'].includes(path)) data.mode='google';
      if (path==='/v1/draft') data.session_bounds=packet;
      await route.fulfill({response,json:data});
    });
    const results=[];
    for (let i=0;i<packets.length;i++) {
      packet=packets[i];
      await page.goto(m.origin+(i?'':'/#'+m.bootstrap));
      await page.waitForFunction(()=>!document.querySelector('#start').disabled);
      assert.match(await page.locator('#mode').innerText(), /GOOGLE MODE · AWAITING MEDIA · No frame decoded/);
      assert.doesNotMatch(await page.locator('#mode').innerText(), /GOOGLE GENERATED/);
      const bounds=await page.locator('#bounds').innerText(), cost=await page.locator('#cost').innerText();
      if (!i) {
        assert.match(bounds,/Campaign session · 120-second target · 130-second local deadline/);
        assert.match(cost,/Video estimate US\$12.096; total estimate US\$12.567891; reservation US\$12.567891/);
        assert.match(cost,/soft admission stop US\$25.00; hard ceiling US\$50.00/);
        assert.doesNotMatch(cost,/US\$2.02|US\$15/);
      } else {
        assert.match(bounds,/Legacy session · 20-second target · 30-second local deadline/);
        assert.match(cost,/total estimate US\$2.016; reservation US\$15.00/);
        assert.doesNotMatch(cost,/Campaign|soft admission|hard ceiling/);
      }
      assert.match(cost,/not billed usage/);assert.match(cost,/not a provider spending cap/);
      results.push({synthetic:true,bounds,cost});
      if (process.env.NETCLAW_BROWSER_EVIDENCE) {
        mkdirSync(process.env.NETCLAW_BROWSER_EVIDENCE,{recursive:true,mode:0o700});
        await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,`budget-${packet.accounting_mode}.png`),fullPage:true});
      }
    }
    assert.equal(forbidden,0);assert.equal(m.ledger.list().length,0);
    if (process.env.NETCLAW_BROWSER_EVIDENCE) writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,'budget-display.json'),JSON.stringify({results,provider_calls:0,sessions:0},null,2),{mode:0o600});
  });

test('actual Chrome distinguishes synthetic media arrival, failure, disconnect and no-frame termination',
  { skip: !enabled, timeout: 30000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'media-viewer-');
    const bounds=Object.freeze({accounting_mode:'fixture',policy:POLICY,estimated_usd:0,reservation_usd:0});
    const active=Object.freeze({state:'active',session_bounds:bounds,terminal_confirmed:false,usage_state:'unknown'});
    const ended=Object.freeze({...active,state:'terminal',terminal_confirmed:true});
    const jpeg=readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg',import.meta.url));
    const results=[];
    const context=await browser.newContext();
    for (const scenario of ['terminal-empty','disconnect-empty','decode-error','decoded-terminal','decoded-error','decoded-disconnect','baseline-failure','baseline-pending','late-decode']) {
      const page=await context.newPage();
      await page.setViewportSize({width:1280,height:900});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      const controls = () => page.evaluate(() => Object.fromEntries(['event','navshot','eventshot'].map(id => [id, !document.getElementById(id).disabled])));
      const disabled = {event:false,navshot:false,eventshot:false};
      let socket, baselineCount=0, releaseBaseline;
      const messages=[];
      let keyPairResolve;
      const keyPair=new Promise(resolve=>{keyPairResolve=resolve;});
      if (scenario==='late-decode') await page.addInitScript(() => {
        const decode=window.createImageBitmap;
        window.createImageBitmap=async (...args) => {
          const bitmap=await decode(...args);
          window.decodeWaiting=true;
          await new Promise(resolve=>{window.releaseDecode=resolve;});
          return bitmap;
        };
      });
      await page.routeWebSocket('**/v1/view/**',ws=>{socket=ws;ws.onMessage(message=>{messages.push(JSON.parse(message));if(messages.filter(m=>m.type==='key').length===2)keyPairResolve();});});
      // Immutable synthetic statuses and a labeled transport JPEG exercise only
      // browser display. POSTs never reach the fixture manager or any provider.
      await page.route('**/v1/**',async route=>{
        const path=new URL(route.request().url()).pathname;
        if (route.request().method()==='POST' && path!=='/v1/bootstrap') {
          if (path.endsWith('/checkpoint') && route.request().postDataJSON().name==='baseline') {
            baselineCount++;
            if(scenario==='baseline-failure') return route.fulfill({status:500,json:{error:'synthetic_checkpoint_failure'}});
            if(scenario==='baseline-pending') await new Promise(resolve=>{releaseBaseline=resolve;});
          }
          const data=path==='/v1/reviews'?{id:'synthetic-review'}:path==='/v1/sessions'?active:path.endsWith('/stop')?ended:{};
          return route.fulfill({json:data});
        }
        const response=await route.fetch(),data=await response.json();
        if (['/v1/bootstrap','/v1/client'].includes(path)) data.mode='google';
        await route.fulfill({response,json:data});
      });
      await page.goto(m.origin+(results.length?'':'/#'+m.bootstrap));
      await page.waitForFunction(()=>!document.querySelector('#start').disabled);
      assert.match(await page.locator('#mode').innerText(),/AWAITING MEDIA · No frame decoded/);
      await page.locator('#start').click();
      await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('active'));
      await page.waitForFunction(()=>document.activeElement?.id==='world');
      assert.ok(socket);
      assert.match(await page.locator('#mode').innerText(),/AWAITING MEDIA · No frame decoded/);
      const pre_frame_controls=await controls();
      assert.deepEqual(pre_frame_controls,disabled);
      await page.keyboard.press('w');
      assert.equal(messages.filter(m=>m.type==='key').length,0);
      assert.equal(await page.locator('#stop').isEnabled(),true);
      assert.equal(await page.locator('#evidence').isEnabled(),true);
      if (scenario==='terminal-empty' && process.env.NETCLAW_BROWSER_EVIDENCE) {
        mkdirSync(process.env.NETCLAW_BROWSER_EVIDENCE,{recursive:true,mode:0o700});
        await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,'media-awaiting-active.png'),fullPage:true});
      }
      if (scenario.startsWith('decoded') || scenario.startsWith('baseline') || scenario==='late-decode') {
        socket.send(JSON.stringify({type:'frame_meta',sequence:1}));socket.send(jpeg);
        if(scenario==='late-decode') await page.waitForFunction(()=>window.decodeWaiting);
        else if(scenario==='baseline-failure') await page.waitForFunction(()=>document.querySelector('#mode').textContent.includes('MEDIA / CAPTURE FAILURE'));
        else {
          await page.waitForFunction(()=>document.querySelector('#mode').textContent.includes('ILLUSTRATION FRAME DECODED'));
          assert.match(await page.locator('#mode').innerText(),/Visual quality unreviewed/);
          if(scenario==='baseline-pending') {
            await page.waitForTimeout(100);
            assert.deepEqual(await controls(),disabled);
            socket.send(JSON.stringify({type:'frame_meta',sequence:2}));socket.send(jpeg);
            await page.waitForTimeout(100);
            assert.equal(baselineCount,1);
          } else {
            await page.waitForFunction(()=>!document.querySelector('#event').disabled);
            assert.deepEqual(await controls(),{event:true,navshot:false,eventshot:false});
            socket.send(JSON.stringify({type:'frame_meta',sequence:2}));socket.send(jpeg);
            await page.waitForFunction(()=>!document.querySelector('#navshot').disabled);
            await page.keyboard.press('w');
            await keyPair;
            assert.equal(messages.filter(m=>m.type==='key').length,2);
            if(scenario==='decoded-terminal') {
              await page.locator('#event').click();await page.locator('#navshot').click();
              await page.waitForFunction(()=>document.querySelector('#navshot').disabled);
              socket.send(JSON.stringify({type:'frame_meta',sequence:2}));socket.send(jpeg);
              socket.send(JSON.stringify({type:'status',session:active}));
              await page.waitForTimeout(100);
              assert.deepEqual(await controls(),{event:false,navshot:false,eventshot:false});
            }
          }
        }
      }
      if (scenario.includes('error')) {
        socket.send(JSON.stringify({type:'frame_meta',sequence:2}));socket.send(Buffer.from('invalid synthetic JPEG'));
      } else if (scenario.includes('disconnect')) socket.close();
      else socket.send(JSON.stringify({type:'status',session:ended}));
      if(scenario==='baseline-pending') releaseBaseline();
      if(scenario==='late-decode') await page.evaluate(()=>window.releaseDecode());
      const expected=scenario.includes('error') || scenario==='baseline-failure'?'MEDIA / CAPTURE FAILURE':scenario.includes('disconnect')?'DISCONNECTED':'VIEWING ENDED';
      await page.waitForFunction(expected=>document.querySelector('#mode').textContent.includes(expected),expected);
      const banner=await page.locator('#mode').innerText();
      assert.match(banner,scenario.startsWith('decoded') || scenario.startsWith('baseline')?/Last decoded frame retained/:/No frame decoded/);
      await page.waitForTimeout(100);
      assert.deepEqual(await controls(),disabled);
      if(scenario==='late-decode') assert.equal(baselineCount,0);
      const keysBefore=messages.filter(m=>m.type==='key').length;
      await page.locator('canvas').focus();await page.keyboard.press('w');
      assert.equal(messages.filter(m=>m.type==='key').length,keysBefore);
      assert.equal(await page.locator('#evidence').isEnabled(),true);
      assert.doesNotMatch(banner,/GOOGLE GENERATED/);assert.deepEqual(errors,[]);
      results.push({scenario,banner,synthetic:true,pre_frame_controls,final_controls:await controls(),baseline_requests:baselineCount,key_messages:messages.filter(m=>m.type==='key').length});
      if(process.env.NETCLAW_BROWSER_EVIDENCE){
        mkdirSync(process.env.NETCLAW_BROWSER_EVIDENCE,{recursive:true,mode:0o700});
        await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,`media-${scenario}.png`),fullPage:true});
      }
      await page.close();
    }
    assert.equal(m.ledger.list().length,0);
    if(process.env.NETCLAW_BROWSER_EVIDENCE)writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,'media-display.json'),JSON.stringify({results,provider_calls:0,sessions:0},null,2),{mode:0o600});
  });


test('actual Chrome event capture requires send acknowledgement and subsequent decoded media',
  { skip: !enabled, timeout: 30000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'event-order-');
    const bounds={accounting_mode:'fixture',policy:POLICY,estimated_usd:0,reservation_usd:0};
    const active={state:'active',event_state:'planned',session_bounds:bounds,terminal_confirmed:false,usage_state:'unknown'};
    const jpeg=readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg',import.meta.url));
    const results=[];
    const context=await browser.newContext();
    for (const scenario of ['delayed','refused','unknown','member-sent','inflight-decode']) {
      const page=await context.newPage({viewport:{width:1280,height:900}});
      const messages=[], checkpoints=[], errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      let socket;
      await page.addInitScript(() => {
        const decode=window.createImageBitmap;
        window.createImageBitmap=async (...args) => {
          const bitmap=await decode(...args);
          if(window.holdDecode) {
            window.decodeWaiting=true;
            await new Promise(resolve=>{window.releaseDecode=resolve;});
          }
          return bitmap;
        };
      });
      await page.routeWebSocket('**/v1/view/**',ws=>{socket=ws;ws.onMessage(value=>messages.push(JSON.parse(value)));});
      await page.route('**/v1/**',async route=>{
        const path=new URL(route.request().url()).pathname;
        if(route.request().method()==='POST' && path!=='/v1/bootstrap') {
          if(path.endsWith('/checkpoint')) checkpoints.push(route.request().postDataJSON().name);
          return route.fulfill({json:path==='/v1/reviews'?{id:'synthetic-review'}:path==='/v1/sessions'?active:{}});
        }
        return route.continue();
      });
      await page.goto(m.origin+(results.length?'':'/#'+m.bootstrap));
      await page.locator('#start').click();
      await page.waitForFunction(()=>document.activeElement?.id==='world');
      const frame=n=>{socket.send(JSON.stringify({type:'frame_meta',sequence:n}));socket.send(jpeg);};
      const status=session=>socket.send(JSON.stringify({type:'status',session}));
      frame(1);
      await page.waitForFunction(()=>!document.querySelector('#event').disabled);
      assert.equal(await page.locator('#eventshot').isEnabled(),false,'baseline is not an event checkpoint');
      // Calling the handler directly must retain the same guard as the disabled UI.
      await page.evaluate(()=>document.querySelector('#eventshot').onclick());
      assert.deepEqual(checkpoints,['baseline']);
      if(scenario!=='member-sent') await page.locator('#event').click();
      if(scenario==='inflight-decode') {
        await page.evaluate(()=>{window.holdDecode=true;});frame(2);
        await page.waitForFunction(()=>window.decodeWaiting);
      } else { frame(2); await page.waitForTimeout(80); }
      assert.equal(await page.locator('#eventshot').isEnabled(),false);
      if(scenario==='refused') {
        socket.send(JSON.stringify({type:'error',code:'event_target_not_ready'}));status(active);frame(3);
      } else if(scenario==='unknown') {
        status({...active,state:'unknown',event_state:'send_marked'});frame(3);
      } else {
        status({...active,event_state:'sent'});
        await page.waitForFunction(()=>document.querySelector('#event-status').textContent.includes('Send acknowledged'));
        assert.equal(await page.locator('#eventshot').isEnabled(),false,'send return is not a new frame');
        if(scenario==='inflight-decode') {
          await page.evaluate(()=>{window.holdDecode=false;window.releaseDecode();});
          await page.waitForTimeout(80);
          assert.equal(await page.locator('#eventshot').isEnabled(),false,'pre-ack media finishing decode is not post-ack media');
        }
        frame(3);
        await page.waitForFunction(()=>!document.querySelector('#eventshot').disabled);
        assert.match(await page.locator('#event-status').innerText(),/visible effect unassessed/i);
        await page.locator('#eventshot').click();
        await page.waitForFunction(()=>document.querySelector('#eventshot').disabled);
        frame(4);status({...active,event_state:'sent'});
      }
      await page.waitForTimeout(100);
      assert.equal(await page.locator('#eventshot').isEnabled(),false);
      assert.equal(await page.locator('#event').isEnabled(),false);
      assert.deepEqual(checkpoints, ['refused','unknown'].includes(scenario)?['baseline']:['baseline','event']);
      const sends=messages.filter(v=>v.type==='event');
      assert.equal(sends.length,scenario==='member-sent'?0:1);
      assert.ok(sends.every(v=>v.event_id==='north-corridor-dim-v1'));
      assert.deepEqual(errors,[]);
      results.push({scenario,synthetic:true,checkpoints,event_sends:sends.length,event_status:await page.locator('#event-status').innerText()});
      if(process.env.NETCLAW_BROWSER_EVIDENCE) await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,`event-${scenario}.png`),fullPage:true});
      await page.close();
    }
    assert.equal(m.ledger.list().length,0);
    if(process.env.NETCLAW_BROWSER_EVIDENCE)writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,'event-order.json'),JSON.stringify({results,provider_calls:0,sessions:0},null,2),{mode:0o600});
  });

test('actual Chrome checkpoint persistence is single-flight and response loss never replays captures',
  { skip: !enabled, timeout: 30000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'checkpoint-flight-');
    const bounds={accounting_mode:'fixture',policy:POLICY,estimated_usd:0,reservation_usd:0};
    const active={state:'active',event_state:'sent',session_bounds:bounds,terminal_confirmed:false,usage_state:'unknown'};
    const jpeg=readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg',import.meta.url));
    const context=await browser.newContext(), results=[];
    for (const name of ['navigation','event']) for (const outcome of ['saved','failed','lost','timeout','stop-pending']) {
      const page=await context.newPage({viewport:{width:1280,height:900}});
      const requests=[],messages=[],errors=[];
      let socket,settle;
      const pending=new Promise(resolve=>{settle=resolve;});
      t.after(()=>settle());
      page.on('pageerror',e=>errors.push(e.message));
      await page.routeWebSocket('**/v1/view/**',ws=>{socket=ws;ws.onMessage(v=>messages.push(JSON.parse(v)));});
      await page.route('**/v1/**',async route=>{
        const path=new URL(route.request().url()).pathname;
        if(route.request().method()==='POST' && path!=='/v1/bootstrap') {
          if(path.endsWith('/checkpoint')) {
            const body=route.request().postDataJSON();requests.push({name:body.name,path});
            if(body.name===name) {
              await pending;
              if(['lost','timeout'].includes(outcome)) return route.abort('failed');
              if(outcome==='failed') return route.fulfill({status:500,json:{error:'synthetic_save_failure'}});
            }
          }
          return route.fulfill({json:path==='/v1/reviews'?{id:'synthetic-review'}:path==='/v1/sessions'?active:path.endsWith('/stop')?{...active,state:'terminal',terminal_confirmed:true}:{}});
        }
        return route.continue();
      });
      await page.goto(m.origin+(results.length?'':'/#'+m.bootstrap));
      await page.locator('#start').click();
      await page.waitForFunction(()=>document.activeElement?.id==='world');
      const frame=n=>{socket.send(JSON.stringify({type:'frame_meta',sequence:n}));socket.send(jpeg);};
      frame(1);
      await page.waitForFunction(()=>document.querySelector('#capture-status').textContent.includes('Navigation: Waiting'));
      frame(2);
      const id=name==='event'?'eventshot':'navshot';
      await page.waitForFunction(id=>!document.getElementById(id).disabled,id);
      await page.evaluate(id=>{document.getElementById(id).onclick();document.getElementById(id).onclick();},id);
      assert.equal(await page.locator('#'+id).isEnabled(),false,'pending capture must disable immediately');
      await page.waitForFunction(()=>document.querySelector('#capture-status').textContent.includes('Saving'));
      socket.send(JSON.stringify({type:'status',session:active}));frame(2);
      await page.waitForTimeout(60);
      await page.evaluate(id=>document.getElementById(id).onclick(),id);
      assert.equal(requests.filter(v=>v.name===name).length,1,'status/media/direct invocation cannot duplicate pending POST');
      if(outcome==='stop-pending') {
        await page.locator('#stop').click();
        await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('terminal'));
      }
      if(outcome==='timeout') await page.waitForFunction(()=>document.querySelector('#capture-status').textContent.includes('Unconfirmed'));
      settle();
      await page.waitForFunction(()=>/Saved|Unconfirmed/.test(document.querySelector('#capture-status').textContent));
      assert.match(await page.locator('#capture-status').innerText(),['failed','lost','timeout'].includes(outcome)?/Unconfirmed.*original.*evidence/i:/Saved/);
      await page.evaluate(id=>document.getElementById(id).onclick(),id);
      frame(3);await page.waitForTimeout(60);
      assert.equal(await page.locator('#'+id).isEnabled(),false);
      assert.equal(requests.filter(v=>v.name===name).length,1);
      assert.equal(messages.filter(v=>v.type==='event').length,0,'capture never resends an event');
      assert.deepEqual(errors,[]);
      results.push({name,outcome,synthetic:true,requests,status:await page.locator('#capture-status').innerText()});
      if(process.env.NETCLAW_BROWSER_EVIDENCE && outcome==='lost') await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,`capture-${name}-lost.png`),fullPage:true});
      await page.close();
    }
    assert.equal(m.ledger.list().length,0);
    if(process.env.NETCLAW_BROWSER_EVIDENCE)writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,'checkpoint-flight.json'),JSON.stringify({results,provider_calls:0,sessions:0},null,2),{mode:0o600});
  });


test('actual Chrome navigation capture waits for post-baseline acknowledgement media',
  { skip: !enabled, timeout: 30000 }, async t => {
    const { m, browser } = await createBrowserFixture(t, 'navigation-order-');
    const active={state:'active',event_state:'planned',session_bounds:{accounting_mode:'fixture',policy:POLICY,estimated_usd:0,reservation_usd:0},terminal_confirmed:false,usage_state:'unknown'};
    const jpeg=readFileSync(new URL('../../scripts/genie-worlds/fixtures/baseline.jpg',import.meta.url));
    const context=await browser.newContext(),results=[];
    for(const scenario of ['delayed-baseline','inflight-decode','terminal-before-decode']) {
      const page=await context.newPage({viewport:{width:1280,height:900}});
      const requests=[],errors=[];let socket,releaseBaseline;
      const pending=new Promise(resolve=>{releaseBaseline=resolve;});t.after(releaseBaseline);
      page.on('pageerror',e=>errors.push(e.message));
      await page.addInitScript(()=>{
        const decode=window.createImageBitmap;
        window.createImageBitmap=async (...args)=>{
          const bitmap=await decode(...args);
          if(window.holdDecode){window.decodeWaiting=true;await new Promise(resolve=>{window.releaseDecode=resolve;});}
          return bitmap;
        };
      });
      await page.routeWebSocket('**/v1/view/**',ws=>{socket=ws;});
      await page.route('**/v1/**',async route=>{
        const path=new URL(route.request().url()).pathname;
        if(route.request().method()==='POST' && path!=='/v1/bootstrap') {
          if(path.endsWith('/checkpoint')) {
            const body=route.request().postDataJSON();requests.push(body.name);
            if(body.name==='baseline')await pending;
          }
          return route.fulfill({json:path==='/v1/reviews'?{id:'synthetic-review'}:path==='/v1/sessions'?active:{}});
        }
        return route.continue();
      });
      await page.goto(m.origin+(results.length?'':'/#'+m.bootstrap));await page.locator('#start').click();
      await page.waitForFunction(()=>document.activeElement?.id==='world');
      const frame=n=>{socket.send(JSON.stringify({type:'frame_meta',sequence:n}));socket.send(jpeg);};
      frame(1);await page.waitForFunction(()=>document.querySelector('#mode').textContent.includes('FRAME DECODED'));
      if(scenario==='inflight-decode') {
        await page.evaluate(()=>{window.holdDecode=true;});frame(2);
        await page.waitForFunction(()=>window.decodeWaiting);
      } else {frame(2);await page.waitForTimeout(80);}
      await page.evaluate(()=>document.querySelector('#navshot').onclick());
      assert.deepEqual(requests,['baseline']);
      releaseBaseline();await page.waitForFunction(()=>!document.querySelector('#event').disabled);
      assert.equal(await page.locator('#navshot').isEnabled(),false,'baseline ACK alone must not enable capture');
      assert.match(await page.locator('#capture-status').innerText(),/Navigation: Waiting for subsequent media/);
      if(scenario==='inflight-decode') {
        await page.evaluate(()=>{window.holdDecode=false;window.releaseDecode();});await page.waitForTimeout(80);
        assert.equal(await page.locator('#navshot').isEnabled(),false,'pre-ACK decode cannot enable capture');
      }
      frame(2);await page.waitForTimeout(80);
      assert.equal(await page.locator('#navshot').isEnabled(),false,'old frame cannot enable capture');
      await page.evaluate(()=>document.querySelector('#navshot').onclick());assert.deepEqual(requests,['baseline']);
      if(process.env.NETCLAW_BROWSER_EVIDENCE && scenario==='inflight-decode')await page.screenshot({path:join(process.env.NETCLAW_BROWSER_EVIDENCE,'navigation-waiting.png'),fullPage:true});
      await page.evaluate(()=>{window.holdDecode=true;window.decodeWaiting=false;});frame(3);
      await page.waitForFunction(()=>window.decodeWaiting);
      assert.equal(await page.locator('#navshot').isEnabled(),false,'received frame must finish decoding');
      if(scenario==='terminal-before-decode') {
        socket.send(JSON.stringify({type:'status',session:{...active,state:'terminal',terminal_confirmed:true}}));
        await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('terminal'));
      }
      await page.evaluate(()=>{window.holdDecode=false;window.releaseDecode();});
      if(scenario!=='terminal-before-decode') {
        await page.waitForFunction(()=>!document.querySelector('#navshot').disabled);
        await page.locator('#navshot').click();
        await page.waitForFunction(()=>document.querySelector('#capture-status').textContent.includes('Saved'));
      } else await page.waitForTimeout(80);
      assert.equal(await page.locator('#navshot').isEnabled(),false);
      assert.deepEqual(requests,scenario==='terminal-before-decode'?['baseline']:['baseline','navigation']);
      assert.deepEqual(errors,[]);results.push({scenario,requests,status:await page.locator('#capture-status').innerText(),synthetic:true});
      await page.close();
    }
    assert.equal(m.ledger.list().length,0);
    if(process.env.NETCLAW_BROWSER_EVIDENCE)writeFileSync(join(process.env.NETCLAW_BROWSER_EVIDENCE,'navigation-order.json'),JSON.stringify({results,provider_calls:0,sessions:0},null,2),{mode:0o600});
  });
