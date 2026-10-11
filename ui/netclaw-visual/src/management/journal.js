import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { createHash, randomUUID } from 'node:crypto';
import { ownedDirectory, ownedFile, readOwned } from './files.js';
import { invariant, fail } from './errors.js';

export function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().filter(k => value[k] !== undefined).map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
export const digest = value => createHash('sha256').update(canonical(value)).digest('hex');
export const ownerKey = owner => canonical([owner.principalId, owner.grantId ?? null, owner.generation ?? 0]);
const terminal = new Set(['succeeded','failed','rolled-back','rollback-failed','cancelled','denied','expired']);
const transitions = {
  admitted: ['preparing','running','denied','failed','cancelled'],
  preparing: ['waiting-approval','succeeded','failed','denied'],
  'waiting-approval': ['running','denied','expired','failed'],
  running: ['succeeded','failed','rolled-back','rollback-failed','unknown','cancellation-requested'],
  'cancellation-requested': ['cancelled','succeeded','failed','unknown'],
  unknown: [],
};

/** One database per stable installation. Never garbage-collect admission tombstones. */
export class Journal {
  constructor(directory, installationId) {
    ownedDirectory(path.dirname(directory)); ownedDirectory(directory, { create: true });
    this.directory = directory; this.installationId = installationId;
    const file = path.join(directory, 'operations.sqlite');
    if (!fs.existsSync(file)) { const fd = fs.openSync(file, 'wx', 0o600); fs.closeSync(fd); }
    ownedFile(file);
    this.db = new DatabaseSync(file);
    try {
      const version = this.db.prepare('PRAGMA user_version').get().user_version;
      invariant(version <= 1, 'INCOMPATIBLE');
      this.db.exec('PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON;');
      if (version === 0) this.transaction(() => {
        this.db.exec(`
          CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS operations (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, nonce TEXT NOT NULL, digest TEXT NOT NULL,
            kind TEXT NOT NULL, state TEXT NOT NULL, input TEXT NOT NULL, admitted INTEGER NOT NULL,
            sequence INTEGER NOT NULL DEFAULT 0, lease TEXT, lease_until INTEGER, worker TEXT,
            external_reference TEXT, result TEXT, UNIQUE(owner, nonce));
          CREATE TABLE IF NOT EXISTS events (operation TEXT NOT NULL REFERENCES operations(id), sequence INTEGER NOT NULL,
            type TEXT NOT NULL, data TEXT NOT NULL, observed INTEGER NOT NULL, PRIMARY KEY(operation, sequence));
          CREATE TABLE IF NOT EXISTS locks (resource TEXT PRIMARY KEY, token TEXT NOT NULL, owner TEXT NOT NULL, expires INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS revisions (digest TEXT PRIMARY KEY, revision TEXT NOT NULL UNIQUE);
          CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL, owner TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(kind,id));
          PRAGMA user_version=1;
        `);
        this.db.prepare('INSERT OR IGNORE INTO metadata VALUES (?,?)').run('installationId', installationId);
      });
      invariant(this.db.prepare('SELECT value FROM metadata WHERE key=?').get('installationId')?.value === installationId, 'IDENTITY_CHANGED');
      this.db.exec('PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;');
    } catch (error) { this.db.close(); throw error; }
  }
  close() { if (this.db.isOpen) this.db.close(); }
  transaction(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const value = fn(); this.db.exec('COMMIT'); return value; }
    catch (error) { this.db.exec('ROLLBACK'); throw error; }
  }
  view(row) {
    return { operationId: row.id, kind: row.kind, state: row.state, sequence: row.sequence,
      admittedAt: new Date(row.admitted).toISOString(), ...(row.result ? { result: JSON.parse(row.result) } : {}),
      ...(row.external_reference ? { externalReference: row.external_reference } : {}) };
  }
  _row(id) { const row = this.db.prepare('SELECT * FROM operations WHERE id=?').get(id); invariant(row, 'DENIED'); return row; }
  _owned(owner, row) { invariant(row && (row.owner === ownerKey(owner) || owner.surface === 'operator'), 'DENIED'); return row; }
  get(owner, id) { return this.view(this._owned(owner, this._row(id))); }
  byNonce(owner, nonce) {
    const row = this.db.prepare('SELECT * FROM operations WHERE owner=? AND nonce=?').get(ownerKey(owner), nonce);
    return row ? this.view(row) : null;
  }
  list(owner, { limit = 100 } = {}) {
    const rows = owner.surface === 'operator'
      ? this.db.prepare('SELECT * FROM operations ORDER BY admitted DESC LIMIT ?').all(limit)
      : this.db.prepare('SELECT * FROM operations WHERE owner=? ORDER BY admitted DESC LIMIT ?').all(ownerKey(owner), limit);
    return rows.map(row => this.view(row));
  }
  conversationOperations(owner, conversationId) {
    return this.db.prepare("SELECT * FROM operations WHERE kind='conversation-request' AND json_extract(input,'$.conversationId')=? ORDER BY admitted DESC").all(conversationId)
      .filter(row=>row.owner===ownerKey(owner)||owner.surface==='operator').map(row=>this.view(row));
  }
  admit(owner, nonce, kind, input, now = Date.now()) {
    invariant(typeof nonce === 'string' && /^\d{13}:[a-f\d-]{36}$/.test(nonce));
    const body = canonical({ kind, input }), hash = digest({ kind, input });
    invariant(Buffer.byteLength(body) <= 1024 * 1024);
    return this.transaction(() => {
      const prior = this.db.prepare('SELECT * FROM operations WHERE owner=? AND nonce=?').get(ownerKey(owner), nonce);
      if (prior) { invariant(prior.digest === hash, 'NONCE_CONFLICT'); return this.view(prior); }
      const issued = Number(nonce.split(':')[0]);
      invariant(now - issued <= 86400000 && issued <= now + 300000, 'EXPIRED');
      const id = randomUUID();
      this.db.prepare('INSERT INTO operations(id,owner,nonce,digest,kind,state,input,admitted) VALUES (?,?,?,?,?,?,?,?)')
        .run(id, ownerKey(owner), nonce, hash, kind, 'admitted', canonical(input), now);
      this._event(id, 'admitted', { kind });
      return this.view(this._row(id));
    });
  }
  _event(id, type, data) {
    invariant(Buffer.byteLength(canonical(data)) <= 65536);
    this.db.prepare('UPDATE operations SET sequence=sequence+1 WHERE id=?').run(id);
    const sequence = this._row(id).sequence;
    this.db.prepare('INSERT INTO events VALUES (?,?,?,?,?)').run(id, sequence, type, canonical(data), Date.now());
    return sequence;
  }
  event(id, type, data) { return this.transaction(() => this._event(id, type, data)); }
  events(owner, id, after = 0, limit = 100) {
    this._owned(owner, this._row(id));
    return this.db.prepare('SELECT * FROM events WHERE operation=? AND sequence>? ORDER BY sequence LIMIT ?').all(id, after, Math.min(limit, 500))
      .map(row => ({ sequence: row.sequence, type: row.type, data: JSON.parse(row.data), observedAt: new Date(row.observed).toISOString() }));
  }
  transition(id, state, data = {}) {
    return this.transaction(() => {
      const row = this._row(id); invariant(transitions[row.state]?.includes(state), 'UNKNOWN_OUTCOME');
      this.db.prepare('UPDATE operations SET state=?,result=? WHERE id=?').run(state, Object.keys(data).length ? canonical(data) : row.result, id);
      this._event(id, state, data); return this.view(this._row(id));
    });
  }
  claim(id, worker, duration = 30000, now = Date.now()) {
    return this.transaction(() => {
      const row = this._row(id);
      if (row.state !== 'admitted') return null;
      const token = randomUUID();
      this.db.prepare('UPDATE operations SET state=?,lease=?,lease_until=?,worker=? WHERE id=?').run('running', token, now + duration, canonical(worker), id);
      this._event(id, 'running', {}); return token;
    });
  }
  renew(id, token, duration = 30000) {
    invariant(this.db.prepare("UPDATE operations SET lease_until=? WHERE id=? AND lease=? AND state IN ('running','cancellation-requested')").run(Date.now() + duration, id, token).changes === 1, 'UNKNOWN_OUTCOME');
  }
  finish(id, token, state, result) {
    return this.transaction(() => {
      const row = this._row(id);
      invariant(row.lease === token && transitions[row.state]?.includes(state), 'UNKNOWN_OUTCOME');
      this.db.prepare('UPDATE operations SET state=?,result=?,lease=NULL,lease_until=NULL WHERE id=?').run(state, canonical(result), id);
      this._event(id, state, result); return this.view(this._row(id));
    });
  }
  reconcileExpired(now = Date.now()) {
    return this.transaction(() => {
      const rows = this.db.prepare("SELECT id FROM operations WHERE state IN ('running','cancellation-requested') AND lease_until<?").all(now);
      for (const { id } of rows) {
        this.db.prepare("UPDATE operations SET state='unknown',lease=NULL,lease_until=NULL WHERE id=?").run(id);
        this._event(id, 'unknown', { reason: 'Worker lease expired. Authoritative reconciliation is required; no replay.' });
      }
      return rows.length;
    });
  }
  reconcile(id, reference, state, result) {
    invariant(reference && terminal.has(state));
    return this.transaction(() => {
      const row = this._row(id); invariant(row.state === 'unknown' && row.external_reference === reference, 'UNKNOWN_OUTCOME');
      this.db.prepare('UPDATE operations SET state=?,result=? WHERE id=?').run(state, canonical(result), id);
      this._event(id, 'reconciled', { state, source: 'authoritative-runtime' });
      return this.view(this._row(id));
    });
  }
  attachReference(id, token, reference) {
    invariant(this.db.prepare('UPDATE operations SET external_reference=? WHERE id=? AND lease=? AND external_reference IS NULL').run(reference, id, token).changes === 1, 'UNKNOWN_OUTCOME');
  }
  input(id, token) { const row = this._row(id); invariant(row.lease === token && row.state === 'running', 'DENIED'); return JSON.parse(row.input); }
  lock(resource, owner, duration = 30000) {
    return this.transaction(() => {
      // Expiry is evidence of interruption, never permission to race an old worker.
      if (this.db.prepare('SELECT 1 FROM locks WHERE resource=?').get(resource)) fail('BUSY');
      const token = randomUUID(); this.db.prepare('INSERT INTO locks VALUES (?,?,?,?)').run(resource, token, owner, Date.now() + duration); return token;
    });
  }
  unlock(resource, token) { invariant(this.db.prepare('DELETE FROM locks WHERE resource=? AND token=?').run(resource, token).changes === 1, 'DENIED'); }
  revision(files) {
    const hash = createHash('sha256');
    for (const file of files) { hash.update(file); const bytes = readOwned(file, { missing: true, limit: 4 * 1024 * 1024 }); hash.update(bytes === null ? 'missing' : bytes); }
    const fingerprint = hash.digest('hex');
    this.db.prepare('INSERT OR IGNORE INTO revisions VALUES (?,?)').run(fingerprint, randomUUID());
    return this.db.prepare('SELECT revision FROM revisions WHERE digest=?').get(fingerprint).revision;
  }
  put(kind, id, owner, value, { replace = false } = {}) {
    this.db.prepare(replace ? `INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET value=excluded.value ${owner.surface === 'operator' ? '' : 'WHERE records.owner=excluded.owner'}` : 'INSERT INTO records VALUES (?,?,?,?)')
      .run(kind, id, ownerKey(owner), canonical(value));
  }
  record(kind, id, owner) {
    const row = this.db.prepare('SELECT * FROM records WHERE kind=? AND id=?').get(kind, id);
    this._owned(owner, row); return JSON.parse(row.value);
  }
  records(kind, owner) {
    return this.db.prepare('SELECT * FROM records WHERE kind=?').all(kind).filter(row => row.owner === ownerKey(owner) || owner.surface === 'operator').map(row => ({ id: row.id, ...JSON.parse(row.value) }));
  }
}
