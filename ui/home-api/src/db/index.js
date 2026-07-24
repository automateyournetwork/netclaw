'use strict';

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

const pool = new Pool({
  host: process.env.PGHOST || 'guardian-postgres',
  port: parseInt(process.env.PGPORT) || 5432,
  database: process.env.PGDATABASE || 'guardian',
  user: process.env.PGUSER || 'guardian',
  password: process.env.PGPASSWORD || '',
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000
});

/**
 * Initialize the database schema.
 * Safe to call repeatedly — uses IF NOT EXISTS.
 */
async function initDB() {
  const schemaPath = path.join(__dirname, 'schema.sql');
  const schema = fs.readFileSync(schemaPath, 'utf-8');

  try {
    await pool.query(schema);
    console.log('Database schema initialized');
  } catch (err) {
    console.error('Database schema init failed:', err.message);
    // Non-fatal — app can still serve dashboard from Prometheus
  }
}

/**
 * Query helper with error logging.
 */
async function query(text, params) {
  try {
    return await pool.query(text, params);
  } catch (err) {
    console.error('DB query error:', err.message, '\nQuery:', text.slice(0, 100));
    throw err;
  }
}

module.exports = { pool, query, initDB };
