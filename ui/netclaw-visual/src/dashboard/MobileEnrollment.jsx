import React, {useEffect,useRef,useState} from 'react';
import {runtimeInfo,verifyRuntime,workspaceFetch} from '../shared/runtime-client.js';
import {ENROLLMENT_ROUTE as BASE,enrollmentInfo,enrollmentRecord,enrollmentNonce,drawEnrollmentQr,enrollmentMessage} from '../shared/mobile-enrollment.js';

export default function MobileEnrollment({preview=false}) {
  const runtime=runtimeInfo(), id=runtime?.installationId;
  const [info,setInfo]=useState(null), [record,setRecord]=useState(null), [matrix,setMatrix]=useState(null), [busy,setBusy]=useState(false), [message,setMessage]=useState('Checking mobile enrollment…'), [now,setNow]=useState(Date.now());
  const live=useRef(true), locked=useRef(false), retained=useRef(null), canvas=useRef(null);
  const key=`netclaw.mobile-enrollment.${id}`;
  const read=async (route,body) => {
    await verifyRuntime();
    const response=await workspaceFetch(route,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-NetClaw-Installation':id},...(body?{body:JSON.stringify(body)}:{}),cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000)});
    if (!response.ok) throw Error(response.status === 409 ? 'Another code may still be active, or the selected Border changed. Check status before continuing.' : 'Enrollment is unavailable. Check the original request; nothing was retried.');
    const value=await response.json(); if(!live.current)throw Error('View closed.'); return value;
  };
  const applyRecord=value => {const {qr_matrix,...metadata}=value;retained.current=metadata;setRecord(metadata);setNow(Date.now());if(value.status!=='issued')setMatrix(null);setMessage(enrollmentMessage(value));};
  const recover=async () => {
    const nonce=retained.current?.client_nonce;
    if(!nonce)return;
    const value=enrollmentRecord(await read(BASE+'/'+nonce),id,nonce);
    applyRecord(value);return value;
  };
  const run=async fn => {
    if(locked.current)return; locked.current=true;setBusy(true);
    try{await fn();}catch(error){if(live.current){setMatrix(null);setMessage(error.message);}}finally{locked.current=false;if(live.current)setBusy(false);}
  };
  useEffect(()=>{
    live.current=true;
    if(preview){setMessage('Enrollment is unavailable in this preview. Select a running Border.');return()=>{live.current=false;};}
    if(!id){setMessage('Select a Border before enrolling a mobile device.');return()=>{live.current=false;};}
    void run(async()=>{
      const value=enrollmentInfo(await read(BASE),id);setInfo(value);
      const saved=sessionStorage.getItem(key);
      if(saved!==null){const data=JSON.parse(saved);if(Object.keys(data).join(',')!=='client_nonce'||!enrollmentNonce(data.client_nonce))throw Error('Saved enrollment reference is invalid.');retained.current={client_nonce:data.client_nonce,status:'unknown'};setRecord(retained.current);await recover();}
      else setMessage(value.available?enrollmentMessage(null):'Mobile enrollment is not ready on this Border. Check its trusted mobile listener setup.');
    });
    const tick=setInterval(()=>setNow(Date.now()),1000);
    const hide=()=>{if(document.hidden)setMatrix(null);};document.addEventListener('visibilitychange',hide);
    return()=>{live.current=false;clearInterval(tick);document.removeEventListener('visibilitychange',hide);};
  },[id,preview]);
  useEffect(()=>{if(matrix&&canvas.current)try{drawEnrollmentQr(canvas.current,matrix);}catch{setMatrix(null);setMessage('QR drawing is unavailable. Check the offer status before creating another code.');}},[matrix]);
  useEffect(()=>{if(record?.status!=='issued'||!record.expires_ms)return;if(now>=record.expires_ms){setMatrix(null);return;}const timer=setTimeout(()=>void run(recover),3000);return()=>clearTimeout(timer);},[record]);
  useEffect(()=>{if(matrix&&record?.expires_ms<=now)setMatrix(null);},[now,matrix,record?.expires_ms]);
  const generate=()=>void run(async()=>{
    if(!info?.available||retained.current?.status==='unknown')return;
    if(retained.current)await recover();
    const previous=retained.current,nonce=crypto.randomUUID();
    sessionStorage.setItem(key,JSON.stringify({client_nonce:nonce}));
    retained.current={client_nonce:nonce,status:'unknown'};setRecord(retained.current);setMatrix(null);setMessage('Generating a one-use code…');
    const value=enrollmentRecord(await read(BASE,{client_nonce:nonce,replace_client_nonce:previous?.status==='issued'?previous.client_nonce:null}),id,nonce,true);
    applyRecord(value);setMatrix(document.hidden?null:value.qr_matrix||null);
    if(value.status==='issued'&&!value.qr_matrix)setMessage('This offer was already issued. Its QR is not stored. Generate a new code deliberately to replace it.');
  });
  const known=record&&record.status!=='unknown', expired=record?.expires_ms<=now;
  return <section className="panel mobile-enrollment" aria-labelledby="mobile-enrollment-heading">
    <div className="section-heading"><div><span className="eyebrow">Connect your phone</span><h2 id="mobile-enrollment-heading">Enroll mobile device</h2></div><button onClick={generate} disabled={busy||!info?.available||record?.status==='unknown'}>{known?'Generate new QR code':'Generate QR code'}</button></div>
    <p>Open NetClaw Mobile, choose <strong>Scan QR code</strong>, and point your camera at the code below.</p>
    {info?.available&&<p className="mobile-destination"><strong>{info.endpoint.claw_domain}</strong> · {info.mode==='protected'?'Protected operations':'Local Border'}<br/><small>Selected installation: {id}</small></p>}
    <p role="status" aria-live="polite">{message}</p>
    {matrix&&<div className="mobile-qr"><canvas ref={canvas} aria-label="One-use mobile enrollment QR code"/><p>Expires in {Math.max(0,Math.ceil((record.expires_ms-now)/1000))} seconds</p></div>}
    {record?.status==='issued'&&!matrix&&<p>{expired?'This code has expired.':'The QR is no longer displayed. Check status, then deliberately generate a new code if needed.'}</p>}
    {record&&<button className="secondary" onClick={()=>void run(recover)} disabled={busy}>Check enrollment status</button>}
    {record?.member_id&&<p>Enrolled device: <code>{record.member_id}</code></p>}
    <p className="muted">A code enrolls one device and expires after two minutes. Existing enrolled phones reconnect with their saved key.</p>
  </section>;
}
