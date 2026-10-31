import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';
const directory=new URL('.',import.meta.url).pathname;
const output=await build({stdin:{contents:`import React from 'react';import {createRoot} from 'react-dom/client';import Avatar from './PalAvatar.jsx';const root=createRoot(document.getElementById('root'));window.showAvatar=props=>root.render(<Avatar {...props}/>);window.removeAvatar=()=>root.unmount();`,loader:'jsx',resolveDir:directory},bundle:true,write:false,format:'iife',define:{'process.env.NODE_ENV':'"production"'},plugins:[{
  name:'avatar-renderer-fixture',setup(b){
    b.onResolve({filter:/^three$/},()=>({path:'three',namespace:'fixture'}));
    b.onLoad({filter:/.*/,namespace:'fixture'},()=>({contents:`export * from ${JSON.stringify(new URL('../../node_modules/three/build/three.module.js',import.meta.url).pathname)};export const WebGLRenderer=window.TestRenderer;`,resolveDir:directory}));
    b.onResolve({filter:/GLTFLoader\.js$/},()=>({path:'loader',namespace:'loader'}));
    b.onLoad({filter:/.*/,namespace:'loader'},()=>({contents:`import {Group} from 'three';export class GLTFLoader{load(url,ready){window.loadedAvatars.push(url);const scene=new Group();for(const name of ['pal_head','pal_mouth','pal_eye_left','pal_eye_right']){const node=new Group();node.name=name;scene.add(node);}ready({scene});}}`,resolveDir:directory}));
  },
}]});
const settle=()=>new Promise(resolve=>setTimeout(resolve,25));

async function until(predicate) {
  const deadline=Date.now()+3000;
  while(!predicate()) {
    if(Date.now()>deadline)assert.fail('Pal fixture did not become ready');
    await new Promise(resolve=>setTimeout(resolve,5));
  }
}

test('avatar suspends offscreen, recovers context loss and releases render resources',async t=>{
  const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost:3000',runScripts:'outside-only',pretendToBeVisual:true});
  t.after(()=>dom.window.close());const w=dom.window;
  let renders=0,disposed=0,lost=0,nextFrame=0;const frames=new Map();let observe;
  w.requestAnimationFrame=callback=>{frames.set(++nextFrame,callback);return nextFrame;};w.cancelAnimationFrame=id=>frames.delete(id);
  const frame=now=>{const callbacks=[...frames.values()];frames.clear();callbacks.forEach(callback=>callback(now));};
  w.WebGL2RenderingContext=function(){};w.loadedAvatars=[];
  w.ResizeObserver=class{observe(){}disconnect(){}};
  w.IntersectionObserver=class{constructor(callback){observe=callback;}observe(){}disconnect(){}};
  w.TestRenderer=class{
    domElement=w.document.createElement('canvas');
    setPixelRatio(){}setSize(){}render(){renders++;}dispose(){disposed++;}forceContextLoss(){lost++;}
  };
  w.eval(output.outputFiles[0].text);w.showAvatar({avatar:'john'});await until(()=>w.loadedAvatars.length===1);
  assert.deepEqual([...w.loadedAvatars],['/pal/john.glb']);frame(100);assert.equal(renders,1);
  observe([{isIntersecting:false}]);assert.equal(frames.size,0);
  observe([{isIntersecting:true}]);frame(200);assert.equal(renders,2);
  w.showAvatar({avatar:'john',active:false});await settle();assert.equal(frames.size,0);
  w.showAvatar({avatar:'john',active:true});await settle();frame(300);assert.equal(renders,3);
  const canvas=w.document.querySelector('canvas');
  canvas.dispatchEvent(new w.Event('webglcontextlost',{cancelable:true}));await settle();assert.equal(frames.size,0);
  assert.match(w.document.body.textContent,/3D paused/);
  [...w.document.querySelectorAll('button')].find(button=>button.textContent==='Retry 3D').click();await settle();
  assert.equal(disposed,1);assert.equal(lost,1);assert.notEqual(w.document.querySelector('canvas'),canvas);
  assert.equal(w.loadedAvatars.length,2);
  w.removeAvatar();assert.equal(disposed,2);assert.equal(lost,2);assert.equal(frames.size,0);
});
