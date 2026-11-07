// Temporary recovery helper: refresh one stale lockfile integrity value from the
// authoritative npm packument. Used only while repairing `npm ci`; records the
// package/version so the change can be audited. Not part of the release pipeline.
import fs from 'node:fs';

const REGISTRY = 'https://registry.npmjs.org';
const lockPath = 'package-lock.json';
const lock = JSON.parse(fs.readFileSync(lockPath, 'utf8'));

const wanted = process.argv[2];
if (!wanted) {
  console.error('usage: node sync-integrity.mjs <sha512-base64-or-full-integrity>');
  process.exit(2);
}
const full = wanted.startsWith('sha512-') ? wanted : `sha512-${wanted}`;

const matches = Object.entries(lock.packages).filter(([, v]) => v.integrity === full);
if (matches.length === 0) {
  console.error(`no lockfile entry with integrity ${full}`);
  process.exit(3);
}

let changed = 0;
for (const [key, entry] of matches) {
  const name = key.replace(/^node_modules\//, '');
  const res = await fetch(`${REGISTRY}/${encodeURIComponent(name)}/${entry.version}`);
  if (!res.ok) {
    console.error(`packument fetch failed for ${name}@${entry.version}: HTTP ${res.status}`);
    process.exit(4);
  }
  const doc = await res.json();
  const authoritative = doc?.dist?.integrity;
  if (!authoritative || !authoritative.startsWith('sha512-')) {
    console.error(`packument has no sha512 integrity for ${name}@${entry.version}`);
    process.exit(5);
  }
  if (authoritative === entry.integrity) {
    console.error(`${name}@${entry.version}: registry agrees with lockfile; no safe repair`);
    process.exit(6);
  }
  console.log(`repair ${name}@${entry.version}`);
  console.log(`  from: ${entry.integrity}`);
  console.log(`  to:   ${authoritative}`);
  entry.integrity = authoritative;
  changed += 1;
}

fs.writeFileSync(lockPath, `${JSON.stringify(lock, null, 2)}\n`);
console.log(`updated ${changed} entr${changed === 1 ? 'y' : 'ies'}`);
