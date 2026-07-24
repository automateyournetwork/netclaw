'use strict';

const express = require('express');
const router = express.Router();
const { query } = require('../db');

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
    console.error('Events GET error:', err.message);
    // Fallback: return empty (DB might not be ready yet)
    res.json({ site, events: [] });
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
    investigation_notes, root_cause, status
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

    const result = await query(
      `INSERT INTO events (site_id, message, severity, category, source,
        alert_name, alert_fingerprint, investigation_notes, root_cause, status)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING id, timestamp, message, severity, status, alert_name, alert_fingerprint`,
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
        status || 'logged'
      ]
    );

    res.status(201).json(result.rows[0]);
  } catch (err) {
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
    console.error('Events PATCH error:', err.message);
    res.status(500).json({ error: 'Failed to update event' });
  }
});

/**
 * GET /api/events/escalated?site=X
 * Returns events awaiting expert review (the operator triage panel).
 */
router.get('/escalated', async (req, res) => {
  const site = req.site;

  try {
    const result = await query(
      `SELECT * FROM events
       WHERE site_id = $1 AND status = 'escalated'
       ORDER BY escalated_at DESC`,
      [site]
    );
    res.json({ site, events: result.rows });
  } catch (err) {
    console.error('Escalated events error:', err.message);
    res.json({ site, events: [] });
  }
});

module.exports = router;
