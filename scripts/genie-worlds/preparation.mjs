import { readFileSync, lstatSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { closed, need, UUID, hash, projection } from './model.mjs';
import { loadOfflineSnapshot } from './offline-snapshot.mjs';
import { buildWorldDesigns } from './world-designs.mjs';

export function loadSnapshotBindings(path) {
  if (!path) return {};
  need(resolve(path) === path, 'private_path_required');
  for (let p = path; p !== dirname(p); p = dirname(p))
    need(!lstatSync(p).isSymbolicLink(), 'private_path_symlink');
  const s = lstatSync(path);
  need(s.isFile() && s.uid === process.getuid() && !(s.mode & 0o077) && s.size < 16384, 'private_file_required');
  const config = JSON.parse(readFileSync(path, 'utf8'));
  closed(config, ['schema', 'snapshots']);
  need(config.schema === 1 && Array.isArray(config.snapshots) && config.snapshots.length <= 5, 'snapshot_registry_invalid');
  const bindings = {};
  for (const entry of config.snapshots) {
    closed(entry, ['ref', 'path', 'manifest_sha256']);
    need(typeof entry.ref === 'string' && /^[a-z0-9][a-z0-9-]{0,95}$/.test(entry.ref) && !Object.hasOwn(bindings, entry.ref), 'snapshot_ref_invalid');
    bindings[entry.ref] = loadOfflineSnapshot(entry.path, entry.manifest_sha256);
  }
  return Object.freeze(bindings);
}

export class Preparations {
  constructor(ledger, bindings = {}) {
    this.ledger = ledger; this.bindings = bindings;
    ledger.db.exec('CREATE TABLE IF NOT EXISTS drafts(id TEXT PRIMARY KEY,digest TEXT NOT NULL,ref TEXT UNIQUE NOT NULL,body TEXT NOT NULL)');
  }
  prepare(input) {
    closed(input, ['request_id', 'synthetic_fixture_id', 'private_snapshot_ref']);
    need(UUID.test(input.request_id), 'invalid_request_id');
    need(Object.hasOwn(input, 'synthetic_fixture_id') !== Object.hasOwn(input, 'private_snapshot_ref'), 'exactly_one_source_required');
    const digest = hash(input);
    return this.ledger.tx(() => {
      const old = this.ledger.db.prepare('SELECT * FROM drafts WHERE id=?').get(input.request_id);
      if (old) { need(old.digest === digest, 'request_conflict'); return JSON.parse(old.body); }
      need(this.ledger.db.prepare('SELECT count(*) AS n FROM drafts').get().n < 256, 'draft_limit');
      let summary;
      if (Object.hasOwn(input, 'synthetic_fixture_id')) {
        const p = projection(input.synthetic_fixture_id);
        summary = { classification: 'synthetic', projection_sha256: p.sha256, hosted_eligible: true, review_required: true, event_id: p.event_id };
      } else {
        need(typeof input.private_snapshot_ref === 'string' && Object.hasOwn(this.bindings, input.private_snapshot_ref), 'unknown_snapshot');
        summary = { ...this.bindings[input.private_snapshot_ref].summary, snapshot_ref: input.private_snapshot_ref };
        const selected=projection();
        if(selected.classification==='private_derived'&&selected.snapshot_ref===input.private_snapshot_ref&&selected.manifest_sha256===summary.manifest_sha256)
          summary={...summary,classification:'private_derived',projection_sha256:selected.sha256,hosted_eligible:true,review_required:true,event_id:selected.event_id};
      }
      const result = { schema_version: 1, request_id: input.request_id, status: 'ok', projection_ref: randomUUID(), ...summary };
      this.ledger.db.prepare('INSERT INTO drafts VALUES(?,?,?,?)').run(input.request_id, digest, result.projection_ref, JSON.stringify(result));
      this.ledger.audit('prepared', { request_id: input.request_id, projection_ref: result.projection_ref, classification: result.classification });
      return result;
    });
  }
  get(ref) {
    need(UUID.test(ref), 'invalid_projection_ref');
    const row = this.ledger.db.prepare('SELECT body FROM drafts WHERE ref=?').get(ref);
    need(row, 'unknown_projection');
    return JSON.parse(row.body);
  }
  eligible(ref) {
    const d = this.get(ref);
    need(d.classification === projection().classification && d.hosted_eligible && d.projection_sha256 === projection().sha256, 'private_projection');
    return projection();
  }
  localFacts(ref) {
    const d = this.get(ref);
    need(['private','private_derived'].includes(d.classification) && Object.hasOwn(this.bindings, d.snapshot_ref), 'unknown_snapshot');
    return { summary: this.bindings[d.snapshot_ref].summary, facts: this.bindings[d.snapshot_ref].localFacts(), coverage: this.bindings[d.snapshot_ref].localCoverage() };
  }
  localDesigns(ref) {
    const d = this.get(ref);
    need(['private','private_derived'].includes(d.classification) && Object.hasOwn(this.bindings, d.snapshot_ref), 'unknown_snapshot');
    return buildWorldDesigns(this.bindings[d.snapshot_ref]);
  }
}
