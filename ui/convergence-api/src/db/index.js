'use strict';

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

/**
 * Postgres backs the event diary and operator triage only. Everything else —
 * health, WAN, Wi-Fi, devices, alerts — is served from Prometheus and
 * VictoriaMetrics and needs no database.
 *
 * So Postgres is optional. Requiring it made trying Convergence a
 * stand-up-a-database exercise, which is a poor first impression for a feature
 * most of the dashboard does not use.
 *
 * Set CONVERGENCE_DB=off to disable explicitly. Otherwise the pool is created
 * and probed once; if it cannot connect, diary and triage report themselves
 * unavailable and the rest of the dashboard is unaffected.
 */

const DISABLED = String(process.env.CONVERGENCE_DB || '').toLowerCase() === 'off';

/** Thrown by query() when there is no usable database. Callers degrade on this. */
class DbUnavailableError extends Error {
  constructor(reason) {
    super(reason || 'database unavailable');
    this.name = 'DbUnavailableError';
    this.code = 'DB_UNAVAILABLE';
  }
}

/**
 * How long to keep short-circuiting after a connection failure before allowing
 * one probe through. Without this the breaker latches open and the diary stays
 * dead until the API is restarted, even after Postgres comes back.
 */
const RETRY_AFTER_MS = 15000;

const state = {
  /** null = not probed yet, true/false = probe result */
  available: DISABLED ? false : null,
  reason: DISABLED ? 'disabled by CONVERGENCE_DB=off' : null,
  lastFailureAt: 0,
};

const pool = DISABLED ? null : new Pool({
  host: process.env.PGHOST || 'guardian-postgres',
  port: parseInt(process.env.PGPORT, 10) || 5432,
  database: process.env.PGDATABASE || 'guardian',
  user: process.env.PGUSER || 'guardian',
  password: process.env.PGPASSWORD || '',
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

// An idle-client error must not take the process down. Without this, a Postgres
// restart crashes the API even though the API can serve most routes without it.
if (pool) {
  pool.on('error', (err) => {
    console.warn('Postgres pool error (diary/triage degraded):', err.message);
    state.available = false;
    state.reason = err.message;
    state.lastFailureAt = Date.now();
  });
}

/**
 * Initialize the schema. Safe to call repeatedly — the schema uses IF NOT EXISTS.
 * Doubles as the connectivity probe: success here means the diary is usable.
 */
async function initDB() {
  if (DISABLED) {
    console.log('Postgres disabled (CONVERGENCE_DB=off) — diary and triage will report unavailable');
    return false;
  }
  const schemaPath = path.join(__dirname, 'schema.sql');
  const schema = fs.readFileSync(schemaPath, 'utf-8');
  try {
    await pool.query(schema);
    state.available = true;
    state.reason = null;
    console.log('Database schema initialized — diary and triage enabled');
    return true;
  } catch (err) {
    state.available = false;
    state.reason = err.message;
    state.lastFailureAt = Date.now();
    console.warn(
      `Postgres unavailable (${err.message}) — diary and triage will report `
      + 'unavailable; health, WAN, Wi-Fi and devices are unaffected',
    );
    return false;
  }
}

/** Current availability, without probing. */
function dbStatus() {
  const retryIn = state.available === false && !DISABLED
    ? Math.max(0, RETRY_AFTER_MS - (Date.now() - state.lastFailureAt))
    : 0;
  return {
    enabled: !DISABLED,
    available: state.available === true,
    reason: state.reason,
    retryInMs: retryIn || undefined,
  };
}

/**
 * Query helper.
 *
 * Throws DbUnavailableError when there is no usable database, so routes can
 * degrade deliberately rather than surfacing a driver error as a 500. A failed
 * query also flips availability, so one outage does not produce a slow error per
 * request for every subsequent call.
 */
async function query(text, params) {
  if (DISABLED) throw new DbUnavailableError(state.reason);
  // Half-open: once marked down, short-circuit for RETRY_AFTER_MS, then let one
  // query through to test recovery. Postgres coming back must not require an API
  // restart, but nor should every request pay a connection timeout.
  if (state.available === false && Date.now() - state.lastFailureAt < RETRY_AFTER_MS) {
    throw new DbUnavailableError(state.reason);
  }
  try {
    const result = await pool.query(text, params);
    if (state.available !== true) {
      console.log('Postgres reachable again — diary and triage re-enabled');
    }
    state.available = true;
    state.reason = null;
    return result;
  } catch (err) {
    // Connection-level failures mean the database is gone; statement errors are
    // the caller's problem and must still surface as real errors.
    const connectionish = /ECONNREFUSED|ENOTFOUND|ETIMEDOUT|EHOSTUNREACH|terminating connection|server closed|Connection terminated/i
      .test(err.message || '');
    if (connectionish) {
      state.available = false;
      state.reason = err.message;
      state.lastFailureAt = Date.now();
      throw new DbUnavailableError(err.message);
    }
    console.error('DB query error:', err.message, '\nQuery:', String(text).slice(0, 100));
    throw err;
  }
}

module.exports = {
  pool, query, initDB, dbStatus, DbUnavailableError,
};
