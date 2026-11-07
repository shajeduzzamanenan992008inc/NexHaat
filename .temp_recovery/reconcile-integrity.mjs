// Temporary recovery helper: reconcile lockfile integrity values with the
// authoritative npm packuments for this registry. Every change is logged with
// package, version, old and new value. Only entries the registry contradicts
// are touched; names, versions and resolved URLs are never changed.
import fs from 'node:fs';

const REGISTRY = 'https://registry.npmjs.org';
const lockPath = 'package-lock.json';
const lock = JSON.parse(fs.readFileSync(lockPath, 'utf8'));

const entries = Object.entries(lock.packages).filter(
  ([key, v]) => key !== '' && v.version && v.integrity && v.resolved?.startsWith(REGISTRY),
);

const changes = [];
const failures = [];
let cursor = 0;
const CONCURRENCY = 12;

async function fetchPackument(name, version) {
  const url = `${REGISTRY}/${name.startsWith('@') ? name.replace('/', '%2f') : encodeURIComponent(name)}/${version}`;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 20000);
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timer);
      if (res.status === 404) return { missing: true };
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      if (attempt === 2) throw err;
    }
  }
  throw new Error('unreachable');
}

async function worker() {
  while (cursor < entries.length) {
    const index = cursor++;
    const [key, entry] = entries[index];
    const name = key.slice(key.lastIndexOf('node_modules/') + 'node_modules/'.length);
    try {
      const doc = await fetchPackument(name, entry.version);
      if (doc?.missing) {
        failures.push(`${name}@${entry.version}: not found in registry`);
        continue;
      }
      const authoritative = doc?.dist?.integrity;
      if (typeof authoritative === 'string' && authoritative.startsWith('sha512-') && authoritative !== entry.integrity) {
        changes.push({ key, name, version: entry.version, from: entry.integrity, to: authoritative });
        entry.integrity = authoritative;
      }
    } catch (err) {
      failures.push(`${name}@${entry.version}: ${err.message}`);
    }
  }
}

await Promise.all(Array.from({ length: CONCURRENCY }, worker));

changes.sort((a, b) => a.key.localeCompare(b.key));
const lines = [
  `# lockfile integrity reconciliation ${new Date().toISOString()}`,
  `# entries checked: ${entries.length}`,
  `# entries changed: ${changes.length}`,
  `# lookup failures: ${failures.length}`,
  ...changes.map((c) => `CHANGED ${c.name}@${c.version}\n  from ${c.from}\n  to   ${c.to}`),
  ...failures.map((f) => `FAILED ${f}`),
  '',
];
fs.writeFileSync('.temp_recovery/integrity-reconcile.log', lines.join('\n'));
fs.writeFileSync(lockPath, `${JSON.stringify(lock, null, 2)}\n`);
console.log(`checked=${entries.length} changed=${changes.length} failures=${failures.length}`);
for (const c of changes) console.log(`changed ${c.name}@${c.version}`);
for (const f of failures.slice(0, 15)) console.log(`failed ${f}`);
