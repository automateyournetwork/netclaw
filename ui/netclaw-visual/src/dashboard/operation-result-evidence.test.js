import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
import { authoritativeToolFacts, unverifiedModelCommentary, verifiedResultSummary } from '../shared/protected-operation-references.js';
const fixtures = JSON.parse(fs.readFileSync(new URL('../shared/operation-evidence.fixture.json', import.meta.url)));
const built = await build({ stdin: { contents: `import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import View from './OperationResultEvidence.jsx';window.render=operation=>renderToStaticMarkup(<View operation={operation}/>);`, resolveDir: new URL('.', import.meta.url).pathname, loader: 'jsx' }, bundle: true, write: false, format: 'iife', define: { 'process.env.NODE_ENV': '"production"' } });
for (const [index, summary] of ['192.0.2.0/26 · 62 usable hosts', '2001:db8::/48 · 1208925819614629174706176 addresses'].entries()) {
  test(`IPv${fixtures[index].result.evidence.output.tool.output.family} native facts and unverified prose render separately without receipt mutation`, () => {
    const op = structuredClone(fixtures[index]), before = JSON.stringify(op);
    assert.equal(verifiedResultSummary(op), summary);
    assert.deepEqual(authoritativeToolFacts(op), op.result.evidence.output.tool.output);
    const dom = new JSDOM('', { runScripts: 'outside-only' });
    dom.window.eval(built.outputFiles[0].text);dom.window.document.body.innerHTML=dom.window.render(op);
    const get=label=>dom.window.document.querySelector(`[aria-label="${label}"]`).textContent;
    assert.equal(get('Verified native summary'), summary);
    assert.doesNotMatch(get('Authoritative tool facts'), /model_answer|64 usable addresses|Unverified IPv6 model prose/);
    assert.equal(get('Unverified model commentary'), op.result.evidence.output.model_answer);
    assert.match(get('Signed receipt and audit references'), /model_answer/);
    assert.equal(JSON.stringify(op), before);dom.window.close();
  });
}
test('normalized facts require independent verification and bound native fields; model text never supplies missing facts', () => {
  for (const mutate of [op=>op.result.verified=false,op=>op.result.evidence.output.tool.independent_verification=false,op=>op.result.evidence.output.tool.output.usable_count='64',op=>op.result.evidence.output.tool.arguments.cidr='198.51.100.0/26']) {
    const op=structuredClone(fixtures[0]);mutate(op);assert.equal(authoritativeToolFacts(op),null);assert.equal(verifiedResultSummary(op),'Unavailable');
  }
  assert.equal(unverifiedModelCommentary(fixtures[0]),'The subnet has 64 usable addresses.');
});
