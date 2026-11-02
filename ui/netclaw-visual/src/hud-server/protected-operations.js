import express from 'express';
import crypto from 'node:crypto';
import { createProtectedClient, ProtectedError, strictJson } from './protected-client.js';

const SESSION = '/api/hud/owner/session', OPERATIONS = '/api/hud/operations';
const token = value => typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
const identifier = value => typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,200}$/.test(value);
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const exact = (value, keys) => object(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const equal = (a, b) => typeof a === 'string' && typeof b === 'string' && a.length <= 256 && b.length <= 256 && Buffer.byteLength(a) === Buffer.byteLength(b) && crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));

export function protectedHudConfig(environment = process.env) {
  if (environment.N2N_PROTECTED_OPERATIONS !== '1') return { enabled: false, origins: [] };
  try {
    const origins = String(environment.NETCLAW_PROTECTED_HUD_ORIGINS || '').split(',').map(value => value.trim());
    if (!origins.length || origins.some(origin => {
      const url = new URL(origin);
      return origin !== url.origin || url.username || url.password || !(url.protocol === 'https:' || url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname));
    }) || new Set(origins.map(origin => new URL(origin).protocol)).size !== 1) throw Error();
    return { enabled: true, origins, secure: origins[0].startsWith('https:') };
  } catch { return { enabled: false, origins: [] }; }
}

export function protectedDocumentHeaders(enabled) {
  return (req, res, next) => {
    if (enabled && ['/', '/index.html'].includes(new URL(req.url, 'http://localhost').pathname)) {
      res.setHeader('X-Frame-Options', 'DENY');
      res.setHeader('Content-Security-Policy', "frame-ancestors 'none'");
      res.setHeader('Cache-Control', 'no-store');
    }
    next();
  };
}

export function mountProtectedOperations(app, { installation, config = protectedHudConfig(), client = createProtectedClient(installation), now = Date.now } = {}) {
  const cookieName = `${config.secure ? '__Host-' : ''}nc_owner_${installation.installationId}`;
  const cookiePairs = req => {
    const pairs = String(req.headers.cookie || '').split(';').map(row => row.trim()).filter(Boolean);
    const names = new Set(); let selected;
    for (const pair of pairs) {
      const index = pair.indexOf('='); if (index < 1) throw new ProtectedError('invalid_session', 401);
      const key = pair.slice(0, index); if (names.has(key)) throw new ProtectedError('invalid_session', 401); names.add(key);
      if (key === cookieName) selected = pair.slice(index + 1);
    }
    return selected;
  };
  const cookie = req => { const selected = cookiePairs(req); if (!token(selected)) throw new ProtectedError('owner_session_required', 401); return selected; };
  const headerOnce = (req, name) => {
    const count = req.rawHeaders.filter((_, i) => i % 2 === 0 && req.rawHeaders[i].toLowerCase() === name.toLowerCase()).length;
    return count === 1 && typeof req.headers[name.toLowerCase()] === 'string';
  };
  const router = express.Router();
  router.use((req, res, next) => {
    res.set({ 'Cache-Control': 'no-store', 'X-Frame-Options': 'DENY', 'Content-Security-Policy': "frame-ancestors 'none'", 'X-Content-Type-Options': 'nosniff' });
    if (!config.enabled) return res.status(404).json({ code: 'protected_operations_disabled', error: 'Protected operations are unavailable.' });
    if (!headerOnce(req, 'X-NetClaw-Installation') || req.headers['x-netclaw-installation'] !== installation.installationId) return res.status(409).json({ code: 'installation_changed', error: 'Reload the selected installation.' });
    const origin = req.headers.origin;
    if (req.headers['sec-fetch-site'] === 'cross-site' || origin !== undefined && (!headerOnce(req, 'Origin') || !config.origins.includes(origin)) || !['GET', 'HEAD'].includes(req.method) && origin === undefined) return res.status(403).json({ code: 'origin_refused', error: 'The configured HUD origin is required.' });
    next();
  });
  router.use(express.text({ type: 'application/json', limit: '72kb' }));
  router.use((req, _res, next) => {
    try {
      if (!['GET', 'HEAD'].includes(req.method)) {
        if (!req.is('application/json') || typeof req.body !== 'string') throw new ProtectedError('invalid_json', 400);
        req.body = strictJson(req.body);
      }
      next();
    } catch (error) { next(error instanceof ProtectedError ? error : new ProtectedError('invalid_json', 400)); }
  });
  const session = async raw => {
    const value = await client.call('owner.session', { cookie: raw });
    const principal = value?.principal;
    if (value?.installation_id !== installation.installationId || !token(value.csrf_token) || value.session_hash !== crypto.createHash('sha256').update(raw).digest('hex') || !exact(principal, ['issuer', 'subject', 'display_name', 'roles']) || principal.issuer !== 'local' || !identifier(principal.subject) || typeof principal.display_name !== 'string' || principal.display_name.length > 200 || !Array.isArray(principal.roles) || principal.roles.length !== 1 || principal.roles[0] !== 'owner' || !Number.isSafeInteger(value.auth_generation) || value.auth_generation < 1 || !Number.isSafeInteger(value.expires_ms) || value.expires_ms <= now()) throw new ProtectedError('invalid_session', 401);
    return value;
  };
  const publicSession = value => ({ authenticated: true, principal: value.principal, csrf_token: value.csrf_token, expires_ms: value.expires_ms, installation_id: value.installation_id });
  const wrap = fn => (req, res, next) => Promise.resolve(fn(req, res)).catch(next);
  const authenticate = async req => {
    const raw = cookie(req), state = await session(raw);
    if (!['GET', 'HEAD'].includes(req.method) && (!headerOnce(req, 'X-NetClaw-CSRF') || !equal(req.headers['x-netclaw-csrf'], state.csrf_token))) throw new ProtectedError('csrf_refused', 403);
    return { raw, state, auth_context: { principal: state.principal, auth_generation: state.auth_generation, session_hash: state.session_hash } };
  };
  const noQuery = req => { if (Object.keys(req.query).length) throw new ProtectedError('invalid_argument', 400); };
  const setCookie = (res, value, expires) => res.set('Set-Cookie', `${cookieName}=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${Math.max(0, Math.floor((expires - now()) / 1000))}${config.secure ? '; Secure' : ''}`);
  // This small process-local limiter complements the durable, one-use backend ticket.
  let loginWindow = 0, loginAttempts = 0;
  router.post(SESSION, wrap(async (req, res) => {
    noQuery(req);
    cookiePairs(req);
    if (!headerOnce(req, 'X-NetClaw-Owner-Bootstrap') || req.headers['x-netclaw-owner-bootstrap'] !== '1' || !exact(req.body, ['ticket']) || !token(req.body.ticket)) throw new ProtectedError('invalid_bootstrap', 400);
    if (now() - loginWindow >= 60000) { loginWindow = now(); loginAttempts = 0; }
    if (++loginAttempts > 10) throw new ProtectedError('bootstrap_rate_limited', 429);
    const login = await client.call('owner.login', { ticket: req.body.ticket });
    if (!token(login?.cookie)) throw new ProtectedError('invalid_session', 401);
    const state = await session(login.cookie); setCookie(res, login.cookie, state.expires_ms); res.json(publicSession(state));
  }));
  router.get(SESSION, wrap(async (req, res) => { noQuery(req); const auth = await authenticate(req); res.json(publicSession(auth.state)); }));
  router.delete(SESSION, wrap(async (req, res) => {
    noQuery(req); if (!exact(req.body, [])) throw new ProtectedError('invalid_argument', 400);
    const auth = await authenticate(req); await client.call('owner.logout', { cookie: auth.raw, csrf_token: auth.state.csrf_token });
    setCookie(res, '', 0); res.json({ authenticated: false });
  }));
  const operation = (method, parameters) => wrap(async (req, res) => {
    const params = parameters(req), auth = await authenticate(req);
    const result = await client.call(method, { ...params, auth_context: auth.auth_context });
    await session(auth.raw); // Revoked/expired sessions cannot receive late private output.
    res.json(result);
  });
  router.get(`${OPERATIONS}/catalog`, operation('catalog', req => { noQuery(req); return {}; }));
  router.post(OPERATIONS, operation('prepare', req => {
    noQuery(req);
    const body = req.body;
    if (!exact(body, ['client_nonce', 'catalog_revision', 'member_id', 'model_profile_id', 'tool', 'arguments']) || !['client_nonce', 'member_id', 'model_profile_id', 'tool'].every(key => identifier(body[key])) || !(identifier(body.catalog_revision) || Number.isSafeInteger(body.catalog_revision)) || !object(body.arguments) || Buffer.byteLength(JSON.stringify(body.arguments)) > 65536) throw new ProtectedError('invalid_argument', 400);
    return body;
  }));
  router.get(OPERATIONS, operation('status', req => {
    if (!exact(req.query, ['client_nonce']) || !identifier(req.query.client_nonce)) throw new ProtectedError('invalid_argument', 400);
    return { client_nonce: req.query.client_nonce };
  }));
  const operationId = req => { noQuery(req); if (!identifier(req.params.id)) throw new ProtectedError('invalid_argument', 400); return { operation_id: req.params.id }; };
  router.get(`${OPERATIONS}/:id`, operation('status', operationId));
  router.post(`${OPERATIONS}/:id/decision`, operation('decision', req => {
    const id = operationId(req), body = req.body;
    if (!exact(body, ['revision', 'review_digest', 'decision']) || !Number.isSafeInteger(body.revision) || body.revision < 0 || !/^[a-f0-9]{64}$/.test(body.review_digest) || !['approve', 'deny'].includes(body.decision)) throw new ProtectedError('invalid_argument', 400);
    return { ...id, ...body };
  }));
  for (const method of ['reconcile', 'revoke']) router.post(`${OPERATIONS}/:id/${method}`, operation(method, req => {
    const id = operationId(req); if (!exact(req.body, [])) throw new ProtectedError('invalid_argument', 400); return id;
  }));
  router.use((_req, res) => res.status(404).json({ code: 'protected_route_unavailable', error: 'The protected route is unavailable.' }));
  router.use((error, _req, res, _next) => {
    const status = error?.type === 'entity.too.large' ? 413 : error instanceof ProtectedError ? error.status : 503;
    const code = error?.type === 'entity.too.large' ? 'payload_too_large' : error instanceof ProtectedError ? error.code : 'protected_operations_unavailable';
    res.status(status).json({ code, error: status === 401 ? 'Owner session expired or is unavailable. Sign in again.' : status === 503 ? 'Status is unavailable. The operation may have been accepted; check the same operation before continuing.' : 'The protected request was refused.' });
  });
  // Must precede express.json and the legacy conversation cookie rewrite.
  app.use((req, res, next) => req.path === SESSION || req.path === OPERATIONS || req.path.startsWith(OPERATIONS + '/') ? router(req, res, next) : next());
  return { enabled: config.enabled, cookieName };
}
