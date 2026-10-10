import { cookieFrom, projectAssessment } from './bindings.js';
export function mountAssessmentRoutes(app, { bindings, readAssessment, audit = async () => ({ status: "unavailable" }) }) {
  let activeReads = 0;
  app.post('/api/hud/session', (req, res) => {
    res.set('Cache-Control', 'no-store');
    try {
      let cookie = cookieFrom(req);
      try { bindings.read(cookie); } catch { cookie = bindings.create(); }
      res.set('Set-Cookie', `${bindings.cookieName || 'nc_hud'}=${cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000`);
      res.json({ authenticated: true });
    } catch { res.status(503).json({ error: 'Private session storage unavailable' }); }
  });
  app.post('/api/hud/session/revoke', (req, res) => {
    try { bindings.revoke(cookieFrom(req)); } catch { /* no existence information */ }
    res.set('Set-Cookie', `${bindings.cookieName || 'nc_hud'}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0`).set('Cache-Control', 'no-store').json({ revoked: true });
  });
  app.get('/api/hud/tasks/:taskRef/assessments/:assessmentId', async (req, res) => {
    res.set('Cache-Control', 'no-store');
    const cookie = cookieFrom(req); let owned;
    try { bindings.read(cookie); } catch { return res.status(401).json({ error: 'Authentication required' }); }
    try { owned = bindings.authorize(cookie, req.params.taskRef, req.params.assessmentId); } catch { return res.status(404).json({ error: 'Assessment unavailable' }); }
    if (activeReads >= 4) return res.status(429).json({ error: 'Assessment reader busy; retry later' });
    activeReads++;
    try {
      const record = await readAssessment(owned.ref.assessmentId, owned.ref.ledgerTask);
      if (!record || record.assessment_id !== owned.ref.assessmentId || record.reconsideration_of !== owned.ref.parent) throw Error('Unavailable');
      const records = [];
      if (record.reconsideration_of) {
        const parent = bindings.authorize(cookie, owned.task.id, record.reconsideration_of);
        if (parent.ref.ledgerTask !== owned.ref.ledgerTask || parent.ref.parent) throw Error('Unavailable');
        const original = await readAssessment(parent.ref.assessmentId, parent.ref.ledgerTask);
        if (original?.assessment_id !== parent.ref.assessmentId || original.reconsideration_of) throw Error('Unavailable');
        records.push({ ...projectAssessment(original), influence: parent.ref.influence || null, budget_scope: parent.ref.ledgerTask === 'unscoped' ? 'Shared conservative budget case' : 'Operator-bound case' });
      }
      records.push({ ...projectAssessment(record), influence: owned.ref.influence || null, budget_scope: owned.ref.ledgerTask === 'unscoped' ? 'Shared conservative budget case' : 'Operator-bound case' });
      // Recheck expiry/revocation after asynchronous reads.
      bindings.authorize(cookie, owned.task.id, owned.ref.assessmentId);
      const auditResult = await audit({ taskRef: owned.task.id, assessmentId: owned.ref.assessmentId });
      bindings.authorize(cookie, owned.task.id, owned.ref.assessmentId);
      res.json({ binding: 'bound', records, audit: auditResult });
    } catch { res.status(503).json({ error: 'Authorized assessment source unavailable' }); }
    finally { activeReads--; }
  });
}
