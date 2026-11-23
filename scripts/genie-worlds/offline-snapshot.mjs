import { constants, openSync, closeSync, fstatSync, readFileSync, lstatSync, readdirSync } from 'node:fs';
import { resolve, dirname, join, relative, isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';
import { need } from './model.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const digest = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const MAX_FILES = 2048, MAX_BYTES = 32 * 1024 * 1024, MAX_FILE = 8 * 1024 * 1024;

function privatePath(path, directory = false) {
  for (let p = path; p !== dirname(p); p = dirname(p))
    need(!lstatSync(p).isSymbolicLink(), 'snapshot_symlink');
  const s = lstatSync(path);
  need(s.uid === process.getuid() && !(s.mode & 0o077), 'snapshot_private_ownership');
  need(directory ? s.isDirectory() : s.isFile(), 'snapshot_file_type');
}

function read(path, limit = MAX_FILE) {
  privatePath(path);
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const s = fstatSync(fd);
    need(s.isFile() && s.uid === process.getuid() && !(s.mode & 0o077) && s.size <= limit, 'snapshot_file_bound');
    const bytes = readFileSync(fd);
    need(bytes.length === s.size, 'snapshot_changed_during_read');
    return bytes;
  } finally { closeSync(fd); }
}

function member(root, name) {
  need(typeof name === 'string' && name.length <= 512 && /^[\w./-]+$/.test(name), 'snapshot_member_name');
  need(!isAbsolute(name) && !name.split('/').some(x => !x || x === '.' || x === '..'), 'snapshot_member_escape');
  const p = resolve(root, name);
  need(relative(root, p) === name, 'snapshot_member_escape');
  return p;
}

// This module has no transport/runtime/provider dependency. Paths and the trusted
// manifest digest come from operator-owned member setup, never MCP arguments.
export function loadOfflineSnapshot(path, expectedManifestSha256) {
  need(typeof path === 'string' && isAbsolute(path) && digest(expectedManifestSha256), 'snapshot_binding_required');
  const root = resolve(path); privatePath(root, true);
  const manifestBytes = read(join(root, 'SHA256SUMS.json'), 1024 * 1024);
  need(sha(manifestBytes) === expectedManifestSha256, 'snapshot_manifest_changed');
  const manifest = JSON.parse(manifestBytes);
  need(manifest && typeof manifest === 'object' && !Array.isArray(manifest), 'snapshot_manifest_invalid');
  const entries = Object.entries(manifest);
  need(entries.length > 0 && entries.length <= MAX_FILES, 'snapshot_file_count');
  let bytes = 0;
  const captured = new Map();
  for (const [name, hash] of entries) {
    need(digest(hash), 'snapshot_digest_invalid');
    const data = read(member(root, name)); bytes += data.length;
    need(bytes <= MAX_BYTES, 'snapshot_total_bound');
    need(sha(data) === hash, 'snapshot_artifact_changed');
    if (['world-facts.json', 'coverage.json'].includes(name)) captured.set(name, data);
  }
  const actual = [];
  function walk(dir) {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      need(!e.isSymbolicLink(), 'snapshot_symlink');
      const p = join(dir, e.name);
      if (e.isDirectory()) { privatePath(p, true); walk(p); }
      else { need(e.isFile(), 'snapshot_file_type'); actual.push(relative(root, p)); }
      need(actual.length <= MAX_FILES + 2, 'snapshot_file_count');
    }
  }
  walk(root);
  need(actual.every(n => n in manifest || ['SHA256SUMS.json', 'SEAL.json'].includes(n)), 'snapshot_unmanifested_file');
  const seal = JSON.parse(read(join(root, 'SEAL.json'), 16384));
  need(seal.manifest_sha256 === expectedManifestSha256, 'snapshot_seal_changed');
  need(captured.has('world-facts.json') && captured.has('coverage.json'), 'snapshot_facts_missing');
  const facts = JSON.parse(captured.get('world-facts.json'));
  const coverage = JSON.parse(captured.get('coverage.json'));
  need(facts.schema === 1 && facts.classification === 'private' && facts.mode === 'frozen_historical_snapshot', 'snapshot_classification');
  need(facts.snapshot_id === seal.snapshot_id && facts.google_export_authorized === false, 'snapshot_authority');
  need(Array.isArray(facts.devices) && facts.devices.length > 0 && facts.devices.length <= 4, 'snapshot_device_bound');
  const ids = facts.devices.map(d => d.id);
  need(ids.every(x => typeof x === 'string' && /^[\w.-]{1,128}$/.test(x)) && new Set(ids).size === ids.length, 'snapshot_device_identity');
  need(Array.isArray(facts.physical_links) && facts.physical_links.length <= 64, 'snapshot_link_bound');
  for (const link of facts.physical_links)
    need(Array.isArray(link.endpoints) && link.endpoints.length === 2 && link.endpoints.every(e => ids.includes(e.device)), 'snapshot_link_identity');
  need(Array.isArray(facts.coverage_limits) && facts.coverage_limits.length <= 32, 'snapshot_coverage');
  const summary = Object.freeze({
    snapshot_ref: facts.snapshot_id, classification: 'private', historical: true,
    manifest_sha256: expectedManifestSha256, files_verified: entries.length,
    devices: ids.length, physical_links: facts.physical_links.length,
    verified_baseline_window: facts.verified_baseline_window,
    enrichment_window: facts.enrichment_window,
    coverage_outcomes: coverage.outcomes, coverage_limit_count: facts.coverage_limits.length,
    network_required: false, hosted_eligible: false,
  });
  return Object.freeze({ summary, localFacts: () => structuredClone(facts), localCoverage: () => structuredClone(coverage) });
}
