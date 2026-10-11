import React, { useEffect, useId, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { safePalId, PAL_PROFILES } from './local-pal-audio.js';
import { mouthEnvelope, replyNod, avatarKeyAction } from './pal-motion.js';

function disposeModel(model) {
  const resources=new Set();
  model?.traverse(node=>{
    if(node.geometry)resources.add(node.geometry);
    for(const material of (Array.isArray(node.material)?node.material:node.material?[node.material]:[])){
      resources.add(material);for(const value of Object.values(material))if(value?.isTexture)resources.add(value);
    }
  });
  resources.forEach(resource=>resource.dispose());
}
export default function PalAvatar({avatar='john',state='idle',replyId,player,active=true,assetBase='/pal',fallbackDetail='Your chat and local voice still work.'}) {
  const host=useRef(null),controlsRef=useRef(null),latest=useRef({state,player,active});latest.current={state,player,active};
  const lastReply=useRef(replyId),replyAt=useRef(-Infinity);
  useEffect(()=>{if(replyId && replyId!==lastReply.current)replyAt.current=performance.now();lastReply.current=replyId;},[replyId]);
  const [error,setError]=useState(''),[loading,setLoading]=useState(true);
  const [retry,setRetry]=useState(0);
  const helpId=useId();
  const id=safePalId(avatar);
  useEffect(()=>{controlsRef.current?.wake();},[active]);
  useEffect(()=>{
    setError('');setLoading(true);
    const element=host.current;
    let renderer,model,frame,observer,intersection,controls,disposed=false,visible=true,failed=false;
    const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(34,1,.1,50);
    camera.position.set(0,1.4,5.45);camera.lookAt(0,1.22,0);
    const hemisphere=new THREE.HemisphereLight(0xe8f1ff,0x647267,2.2);scene.add(hemisphere);
    const key=new THREE.DirectionalLight(0xffedda,3.2);key.position.set(-3,4,5);scene.add(key);
    const rim=new THREE.DirectionalLight(0x79d9e8,2.4);rim.position.set(3,3,-2);scene.add(rim);
    const motion=window.matchMedia?.('(prefers-reduced-motion: reduce)');
    let reduced=motion?.matches;
    const motionChange=event=>{reduced=event.matches;};motion?.addEventListener?.('change',motionChange);
    let head,mouth,jaw,eyes=[],hands=[],baseMouth=1,openness=0,lastFrame;
    const render=now=>{
      if(disposed || failed || document.hidden || !visible || !latest.current.active)return;
      const t=now/1000,level=latest.current.player?.level()||0;
      const replyAge=(now-replyAt.current)/1000;
      const nod=replyNod(replyAge,reduced);
      openness=mouthEnvelope(openness,level,lastFrame===undefined?1/60:(now-lastFrame)/1000);lastFrame=now;
      if(model){
        model.position.y=reduced?0:Math.sin(t*1.6)*.012;
        if(head){head.rotation.y=reduced?0:Math.sin(t*.52)*.055;head.rotation.x=reduced?0:Math.sin(t*.83)*.017+(latest.current.state==='thinking'?.035:0)+nod;}
        if(mouth)mouth.scale.y=baseMouth*(1+openness*3.8);
        if(jaw)jaw.position.y=jaw.userData.restY-openness*.035;
        // Slow unsynchronised blinks, with no random state updates in React.
        const blink=reduced?1:Math.abs(Math.sin(t*.47))<.044?.12:1;
        for(const eye of eyes)eye.scale.y=blink;
        hands.forEach((hand,index)=>{hand.rotation.z=reduced?0:Math.sin(t*1.1+index)*.035+level*(index?-.05:.05);});
      }
      controls?.update();renderer.render(scene,camera);frame=requestAnimationFrame(render);
    };
    const visibility=()=>{cancelAnimationFrame(frame);if(!disposed && !failed && !document.hidden && visible && latest.current.active && renderer)frame=requestAnimationFrame(render);};
    const loss=event=>{event.preventDefault();failed=true;cancelAnimationFrame(frame);setError(`3D paused. ${fallbackDetail}`);};
    try {
      if(!window.WebGL2RenderingContext)throw Error('webgl-unavailable');
      renderer=new THREE.WebGLRenderer({alpha:true,antialias:true});renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
      renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;
      element.appendChild(renderer.domElement);renderer.domElement.setAttribute('aria-label',`${PAL_PROFILES[id].name} animated avatar`);
      controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,1.22,0);controls.enableDamping=true;
      controls.minDistance=2;controls.maxDistance=10;controls.minPolarAngle=.15;controls.maxPolarAngle=Math.PI-.15;
      controls.update();controls.saveState();controlsRef.current={controls,camera,wake:visibility};
      renderer.domElement.addEventListener('webglcontextlost',loss);
      const resize=()=>{const width=Math.max(1,element.clientWidth),height=Math.max(1,element.clientHeight);renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();};
      observer=new ResizeObserver(resize);observer.observe(element);resize();
      if(window.IntersectionObserver){intersection=new IntersectionObserver(entries=>{visible=entries.some(entry=>entry.isIntersecting);visibility();});intersection.observe(element);}
      new GLTFLoader().load(`${assetBase}/${id}.glb`,gltf=>{
        if(disposed){disposeModel(gltf.scene);return;}
        model=gltf.scene;scene.add(model);
        head=model.getObjectByName('pal_head');mouth=model.getObjectByName('pal_mouth');jaw=model.getObjectByName('pal_jaw');
        eyes=['pal_eye_left','pal_eye_right'].map(name=>model.getObjectByName(name)).filter(Boolean);
        hands=['pal_hand_left','pal_hand_right'].map(name=>model.getObjectByName(name)).filter(Boolean);
        if(jaw)jaw.userData.restY=jaw.position.y;
        if(mouth)baseMouth=mouth.scale.y;
        setLoading(false);
      },undefined,()=>{if(!disposed){failed=true;cancelAnimationFrame(frame);setLoading(false);setError(`The avatar could not load. ${fallbackDetail}`);}});
      document.addEventListener('visibilitychange',visibility);frame=requestAnimationFrame(render);
    }catch{setLoading(false);setError(`3D is unavailable in this browser. ${fallbackDetail}`);}
    return()=>{disposed=true;cancelAnimationFrame(frame);motion?.removeEventListener?.('change',motionChange);document.removeEventListener('visibilitychange',visibility);observer?.disconnect();intersection?.disconnect();renderer?.domElement.removeEventListener('webglcontextlost',loss);controls?.dispose();controlsRef.current=null;disposeModel(model);renderer?.dispose();renderer?.forceContextLoss();renderer?.domElement.remove();};
  },[id,retry,assetBase,fallbackDetail]);
  function adjust(action) {
    const value=controlsRef.current;if(!value)return;
    const {controls,camera}=value;
    if(action==='reset'){controls.reset();return;}
    const offset=camera.position.clone().sub(controls.target);
    if(action==='left'||action==='right')offset.applyAxisAngle(new THREE.Vector3(0,1,0),action==='left'?Math.PI/12:-Math.PI/12);
    else if(action==='up'||action==='down'){
      const sphere=new THREE.Spherical().setFromVector3(offset);
      sphere.phi=THREE.MathUtils.clamp(sphere.phi+(action==='up'?-.15:.15),controls.minPolarAngle,controls.maxPolarAngle);
      offset.setFromSpherical(sphere);
    }else if(action.startsWith('pan-')){
      const horizontal=action==='pan-left'||action==='pan-right';
      const vector=new THREE.Vector3().setFromMatrixColumn(camera.matrix,horizontal?0:1).multiplyScalar(['pan-left','pan-down'].includes(action)?-.15:.15);
      const next=controls.target.clone().add(vector).clampScalar(-3,3);
      camera.position.add(next.clone().sub(controls.target));controls.target.copy(next);controls.update();return;
    }
    else offset.setLength(THREE.MathUtils.clamp(offset.length()*(action==='in'?.82:1.22),controls.minDistance,controls.maxDistance));
    camera.position.copy(controls.target).add(offset);controls.update();
  }
  return <div className="local-pal-stage"><div ref={host} className="local-pal-canvas" hidden={!!error} tabIndex={error?-1:0} role="group" aria-label={`${PAL_PROFILES[id].name} 3D view`} aria-describedby={helpId} onKeyDown={event=>{const action=avatarKeyAction(event);if(action && !loading && !error){event.preventDefault();adjust(action);}}}/>{error&&<div className="local-pal-fallback"><img src={`${assetBase}/${id}.png`} alt={PAL_PROFILES[id].description}/><p role="status">{error}</p><button onClick={()=>setRetry(value=>value+1)}>Retry 3D</button></div>}{loading&&!error&&<span className="local-pal-loading" role="status">Loading {PAL_PROFILES[id].name}…</span>}<div className="local-pal-view-controls" role="group" aria-label="Avatar camera controls">{[['left','↶','Rotate left'],['right','↷','Rotate right'],['in','+','Zoom in'],['out','−','Zoom out'],['reset','Reset','Reset view']].map(([action,label,title])=><button key={action} aria-label={title} title={title} disabled={!!error||loading} onClick={()=>adjust(action)}>{label}</button>)}</div><span className="local-pal-stage-caption">Drag to rotate · scroll to zoom · right-drag to move<br/>{PAL_PROFILES[id].description}</span><span id={helpId} className="sr-only">Arrow keys rotate. Shift and arrows move. Plus and minus zoom. Home resets the view.</span></div>;
}
