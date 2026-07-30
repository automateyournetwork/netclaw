'use strict';

const express = require('express');
const router = express.Router();

/**
 * The diary and triage are the only Postgres-backed features; Postgres is
 * optional (see src/db/index.js). Reads degrade to an empty list carrying
 * `unavailable` so the UI can say "diary unavailable" rather than showing an
 * empty diary, which looks identical to "nothing has happened yet". Writes
 * cannot degrade, so they answer 503.
 */
function isDbDown(err) {
  return err instanceof DbUnavailableError || err?.code === 'DB_UNAVAILABLE';
}

function emptyWithReason(res, site, err) {
  const down = isDbDown(err);
  return res.json({
    site,
    events: [],
    unavailable: down || undefined,
    reason: down ? (dbStatus().reason || 'database unavailable') : undefined,
  });
}

function writeUnavailable(res, err, what) {
  if (isDbDown(err)) {
    return res.status(503).json({
      error: `${what} requires the event database, which is unavailable`,
      reason: dbStatus().reason || undefined,
      hint: 'Start Postgres, or unset CONVERGENCE_DB=off. Health, WAN, Wi-Fi and devices work without it.',
    });
  }
  return null;
}
const { query, DbUnavailableError, dbStatus } = require('../db');

/**
 * Ensure a site row exists so event POSTs never FK-500 on unknown site_id.
 * Concurrent POSTs are safe: INSERT … ON CONFLICT DO NOTHING.
 */
async function ensureSite(siteId) {
  if (!siteId) return;
  await query(
    `INSERT INTO sites (id, name) VALUES ($1, $2)
     ON CONFLICT (id) DO NOTHING`,
    [siteId, siteId]
  );
}

/**
 * GET /api/events?site=X&limit=20&status=X&fingerprint=Y
 * Returns curated event diary entries for the customer/operator view.
 */
router.get('/', async (req, res) => {
  const site = req.site;
  const limit = Math.min(parseInt(req.query.limit) || 20, 100);
  const status = req.query.status; // optional: filter by status
  const fingerprint = req.query.fingerprint; // optional: alertmanager fingerprint

  try {
    let sql = `SELECT id, timestamp, message, severity, category, source, status,
               alert_name, alert_fingerprint, root_cause, investigation_notes,
               expert_feedback, feedback_quality, rag_document_id
               FROM events WHERE site_id = $1`;
    const params = [site];

    if (status) {
      sql += ` AND status = $${params.length + 1}`;
      params.push(status);
    }
    if (fingerprint) {
      sql += ` AND alert_fingerprint = $${params.length + 1}`;
      params.push(fingerprint);
    }

    sql += ` ORDER BY timestamp DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await query(sql, params);
    res.json({ site, events: result.rows });
  } catch (err) {
    if (!isDbDown(err)) console.error('Events GET error:', err.message);
    emptyWithReason(res, site, err);
  }
});

/**
 * POST /api/events
 * Create a new event entry.
 * Used by: NetClaw (investigation results), Alertmanager (webhook), operators.
 */
router.post('/', async (req, res) => {
  const site = req.site;
  const {
    message, severity, category, source,
    alert_name, alert_fingerprint,
    investigation_notes, root_cause, status,
    rag_document_id, expert_feedback, feedback_quality,
  } = req.body;

  if (!message) {
    return res.status(400).json({ error: 'message is required' });
  }
  if (!site) {
    return res.status(400).json({ error: 'site query param is required' });
  }

  try {
    // Stage 6: never 500 on missing site_id — auto-seed the row.
    await ensureSite(site);

    const st = status || 'logged';
    const ragId = rag_document_id || null;
    const result = await query(
      `INSERT INTO events (site_id, message, severity, category, source,
        alert_name, alert_fingerprint, investigation_notes, root_cause, status,
        rag_document_id, expert_feedback, feedback_quality,
        escalated_at, rag_snapshotted_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
       RETURNING id, timestamp, message, severity, status, alert_name, alert_fingerprint,
                 rag_document_id, escalated_at`,
      [
        site,
        message,
        severity || 'info',
        category || null,
        source || 'system',
        alert_name || null,
        alert_fingerprint || null,
        investigation_notes || null,
        root_cause || null,
        st,
        ragId,
        expert_feedback || null,
        feedback_quality || null,
        st === 'escalated' ? new Date().toISOString() : null,
        ragId ? new Date().toISOString() : null,
      ]
    );

    res.status(201).json(result.rows[0]);
  } catch (err) {
    if (writeUnavailable(res, err, 'Recording an event')) return;
    console.error('Events POST error:', err.message);
    // FK / validation → 400 so callers can distinguish retryable 500s
    if (err.code === '23503' || err.code === '23514' || err.code === '23502') {
      return res.status(400).json({ error: 'Invalid event payload', detail: err.message });
    }
    res.status(500).json({ error: 'Failed to create event' });
  }
});

/**
 * PATCH /api/events/:id
 * Update an event — used for:
 *  - NetClaw adding investigation results
 *  - Operator providing expert feedback
 *  - Marking as escalated/resolved
 *  - Recording RAG snapshot
 */
router.patch('/:id', async (req, res) => {
  const { id } = req.params;
  const {
    status, severity, message,
    investigation_notes, root_cause,
    expert_feedback, feedback_quality,
    rag_document_id
  } = req.body;

  const updates = [];
  const params = [];
  let paramIdx = 1;

  if (status) {
    updates.push(`status = $${paramIdx++}`);
    params.push(status);
    // Set timestamps based on status transitions
    if (status === 'investigating') updates.push(`investigation_started_at = NOW()`);
    if (status === 'resolved') updates.push(`investigation_completed_at = NOW()`);
    if (status === 'escalated') updates.push(`escalated_at = NOW()`);
  }
  if (severity) {
    updates.push(`severity = $${paramIdx++}`);
    params.push(severity);
  }
  if (message) {
    updates.push(`message = $${paramIdx++}`);
    params.push(message);
  }
  if (investigation_notes) {
    updates.push(`investigation_notes = $${paramIdx++}`);
    params.push(investigation_notes);
  }
  if (root_cause) {
    updates.push(`root_cause = $${paramIdx++}`);
    params.push(root_cause);
  }
  if (expert_feedback) {
    updates.push(`expert_feedback = $${paramIdx++}`);
    params.push(expert_feedback);
    updates.push(`feedback_provided_at = NOW()`);
  }
  if (feedback_quality) {
    updates.push(`feedback_quality = $${paramIdx++}`);
    params.push(feedback_quality);
  }
  if (rag_document_id) {
    updates.push(`rag_document_id = $${paramIdx++}`);
    params.push(rag_document_id);
    updates.push(`rag_snapshotted_at = NOW()`);
  }

  if (updates.length === 0) {
    return res.status(400).json({ error: 'No fields to update' });
  }

  params.push(id);
  const sql = `UPDATE events SET ${updates.join(', ')} WHERE id = $${paramIdx} RETURNING *`;

  try {
    const result = await query(sql, params);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }
    res.json(result.rows[0]);
  } catch (err) {
    if (writeUnavailable(res, err, 'Updating an event')) return;
    console.error('Events PATCH error:', err.message);
    res.status(500).json({ error: 'Failed to update event' });
  }
});

/**
 * GET /api/events/escalated?site=X
 * Returns events awaiting expert review (the operator triage panel).
 * Registered before /:id so path is not swallowed.
 */
router.get('/escalated', async (req, res) => {
  const site = req.site;

  try {
    const result = await query(
      `SELECT id, site_id, timestamp, message, severity, category, source, status,
              alert_name, alert_fingerprint, root_cause, investigation_notes,
              expert_feedback, feedback_quality, rag_document_id, rag_snapshotted_at,
              escalated_at, investigation_started_at, investigation_completed_at,
              feedback_provided_at, created_at, updated_at
       FROM events
       WHERE site_id = $1 AND status = 'escalated'
       ORDER BY escalated_at DESC NULLS LAST, timestamp DESC`,
      [site]
    );
    res.json({ site, events: result.rows });
  } catch (err) {
    if (!isDbDown(err)) console.error('Escalated events error:', err.message);
    emptyWithReason(res, site, err);
  }
});

/**
 * GET /api/events/:id?site=X
 * Single event (for triage detail / RAG id display).
 */
router.get('/:id', async (req, res) => {
  const { id } = req.params;
  try {
    const result = await query(`SELECT * FROM events WHERE id = $1`, [id]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }
    res.json(result.rows[0]);
  } catch (err) {
    if (writeUnavailable(res, err, 'Reading an event')) return;
    console.error('Event GET error:', err.message);
    res.status(500).json({ error: 'Failed to fetch event' });
  }
});

/**
 * POST /api/events/:id/reinvestigate
 * Operator "Need More" — mark needs_more_context, re-open as investigating,
 * optionally forward to host alert-receiver /reinvestigate (hooks guardian-claw).
 *
 * Body: { expert_feedback?: string, site?: string }
 * Query: ?site=home (preferred for multi-tenant)
 */
router.post('/:id/reinvestigate', async (req, res) => {
  const { id } = req.params;
  const site = req.site || req.body?.site || req.query?.site || 'home';
  const expert_feedback = String(req.body?.expert_feedback || '').trim();

  try {
    const existing = await query(`SELECT * FROM events WHERE id = $1`, [id]);
    if (existing.rows.length === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }
    const prev = existing.rows[0];
    const noteAppend = expert_feedback
      ? `\n\n[operator:needs_more_context] ${expert_feedback}`
      : '\n\n[operator:needs_more_context] Operator requested deeper investigation.';
    const notes = ((prev.investigation_notes || '') + noteAppend).trim();

    const updated = await query(
      `UPDATE events SET
         status = 'investigating',
         investigation_started_at = COALESCE(investigation_started_at, NOW()),
         investigation_notes = $1,
         expert_feedback = $2,
         feedback_quality = 'needs_more_context',
         feedback_provided_at = NOW()
       WHERE id = $3
       RETURNING *`,
      [
        notes,
        expert_feedback || prev.expert_feedback || 'Operator requested more context',
        id,
      ]
    );

    // Forward to host alert-receiver when configured (same contract as pilot)
    let reinvestigate = { status: 'skipped', reason: 'ALERT_RECEIVER_URL not set' };
    const receiverBase = (process.env.ALERT_RECEIVER_URL || '')
      .replace(/\/webhook\/?$/, '')
      .replace(/\/$/, '');
    if (receiverBase) {
      try {
        const r = await fetch(`${receiverBase}/reinvestigate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({
            event_id: id,
            site,
            expert_feedback: expert_feedback || undefined,
          }),
          signal: AbortSignal.timeout(25000),
        });
        const text = await r.text();
        let body = null;
        try {
          body = text ? JSON.parse(text) : null;
        } catch {
          body = { raw: text };
        }
        reinvestigate = {
          status: r.ok ? (body?.status || 'accepted') : 'error',
          http: r.status,
          detail: body,
        };
      } catch (err) {
        reinvestigate = { status: 'error', reason: err.message };
      }
    }

    res.json({
      event: updated.rows[0],
      reinvestigate,
      site,
    });
  } catch (err) {
    if (writeUnavailable(res, err, 'Re-investigating an event')) return;
    console.error('Reinvestigate error:', err.message);
    res.status(500).json({ error: 'Failed to reinvestigate', detail: err.message });
  }
});

module.exports = router;
