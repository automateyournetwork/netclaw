import express from 'express';
import { strictJson, ProtectedError } from './protected-client.js';
import { ENROLLMENT_ROUTE as BASE, enrollmentInfo, enrollmentRecord, enrollmentNonce } from '../shared/mobile-enrollment.js';

const once = (req, name) => req.rawHeaders.filter((v,i) => i % 2 === 0 && v.toLowerCase() === name).length === 1;
const exact = (v, keys) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v,k));
const isRoute = req => req.path === BASE || req.path.startsWith(BASE + '/');

/** Only the three device-enrollment methods are reachable through this router. */
export function mountMobileEnrollment(app, { installation, client, config = {} }) {
  const router = express.Router({ caseSensitive: true, strict: true });
  router.use((req,res,next) => {
    res.set({'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'});
    if (!once(req,'x-netclaw-installation') || req.headers['x-netclaw-installation'] !== installation.installationId) return res.status(409).json({code:'installation_changed'});
    const origin = req.headers.origin;
    if (req.headers['sec-fetch-site'] === 'cross-site' || origin !== undefined && (!once(req,'origin') || !config.origins?.includes(origin)) || req.method !== 'GET' && origin === undefined) return res.status(403).json({code:'origin_refused'});
    if (req.url.includes('?') || !['GET','POST'].includes(req.method)) return res.status(400).json({code:'invalid_argument'});
    if (!config.enabled) {
      if (req.method === 'GET' && req.path === BASE) return res.json({schema:1,installation_id:installation.installationId,available:false,reason:config.reason || 'enrollment_unavailable'});
      return res.status(404).json({code:'enrollment_unavailable'});
    }
    next();
  });
  router.use(express.text({type:'application/json',limit:'2kb'}));
  const wrap = fn => (req,res,next) => Promise.resolve(fn(req,res)).catch(next);
  const authority = () => ({installation_id:installation.installationId, ...(config.access?.mode === 'open-lab' ? {auth_context:{access_mode:'open-lab',installation_id:installation.installationId,...(config.cluster ? {cluster_id:config.cluster.cluster_id,generation:config.cluster.generation} : {})}} : {})});
  router.get(BASE, wrap(async (_req,res) => {
    const value = await client.call('mobile.enrollment.info',authority());
    res.json(enrollmentInfo(value,installation.installationId));
  }));
  router.get(BASE + '/:nonce', wrap(async (req,res) => {
    if (!enrollmentNonce(req.params.nonce)) throw new ProtectedError('invalid_argument',400);
    const value = await client.call('mobile.enrollment.status',{...authority(),client_nonce:req.params.nonce});
    res.json(enrollmentRecord(value,installation.installationId,req.params.nonce));
  }));
  router.post(BASE, wrap(async (req,res) => {
    let body; try { if (typeof req.body !== 'string' || !req.is('application/json')) throw Error(); body = strictJson(req.body); } catch { throw new ProtectedError('invalid_json',400); }
    if (!exact(body,['client_nonce','replace_client_nonce']) || !enrollmentNonce(body.client_nonce) || !(body.replace_client_nonce === null || enrollmentNonce(body.replace_client_nonce)) || body.client_nonce === body.replace_client_nonce) throw new ProtectedError('invalid_argument',400);
    // Once forwarded, even a timeout may follow durable minting. Never retry.
    req.enrollmentForwarded = true;
    const value = await client.call('mobile.enrollment.issue',{...body,...authority()});
    res.json(enrollmentRecord(value,installation.installationId,body.client_nonce,true));
  }));
  router.use((_req,res) => res.status(404).json({code:'route_unavailable'}));
  router.use((error,req,res,_next) => {
    const status = error?.type === 'entity.too.large' ? 413 : error instanceof ProtectedError ? error.status : 503;
    res.status(status).json({code:error instanceof ProtectedError ? error.code : 'enrollment_unavailable', ...(req.method === 'POST' && !req.enrollmentForwarded ? {admission:'not_submitted'} : {}),error:'Enrollment status is unavailable. Check the original request; no request was retried.'});
  });
  app.use((req,res,next) => isRoute(req) ? router(req,res,next) : next());
  return {enabled:config.enabled === true};
}

/** Ordinary local Borders use fixed loopback daemon routes, never a proxy API. */
export function createLocalEnrollmentClient(installation, endpoint, fetcher = fetch) {
  return {async call(method, params) {
    const base = typeof endpoint === 'function' ? endpoint() : endpoint;
    if (!/^http:\/\/(127\.0\.0\.1|localhost|\[::1\]):[1-9][0-9]{0,4}$/.test(base) || new URL(base).port > 65535 || params.installation_id !== installation.installationId) throw new ProtectedError('bridge_unavailable');
    const issue = method === 'mobile.enrollment.issue', read = method === 'mobile.enrollment.info', status = method === 'mobile.enrollment.status';
    if (!issue && !read && !status || status && !enrollmentNonce(params.client_nonce)) throw new ProtectedError('invalid_method',400);
    const target = '/n2n/mobile/enrollment' + (status ? '/' + params.client_nonce : '');
    const response = await fetcher(base + target + (issue ? '' : '?installation_id=' + encodeURIComponent(installation.installationId)),{method:issue?'POST':'GET',redirect:'error',headers:{'Content-Type':'application/json','X-NetClaw-Installation':installation.installationId},...(issue?{body:JSON.stringify(params)}:{}),signal:AbortSignal.timeout(15000)});
    let size=0; const chunks=[];
    for await (const chunk of response.body || []) { size += chunk.length; if (size>256*1024) throw new ProtectedError('bridge_unavailable'); chunks.push(chunk); }
    const value = strictJson(Buffer.concat(chunks).toString('utf8'));
    if (!response.ok) throw new ProtectedError(/^[a-z][a-z0-9_]{0,79}$/.test(value?.code)?value.code:'bridge_unavailable',[400,403,404,409,429].includes(response.status)?response.status:503);
    return read ? enrollmentInfo(value,installation.installationId) : enrollmentRecord(value,installation.installationId,params.client_nonce,issue);
  }};
}
