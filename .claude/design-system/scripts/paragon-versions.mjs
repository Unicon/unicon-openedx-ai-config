#!/usr/bin/env node
// Reports the declared vs installed @openedx/paragon version (and brand package) for one or
// more target repos, and compares each against the generated map's reference Paragon
// version. A major-version difference is a real risk (token names/values can change); a
// minor difference is usually fine, and check-tokens.mjs confirms names either way.
//
// Usage: node paragon-versions.mjs <repo-dir> [<repo-dir> ...]
//   With no args, scans this checkout's sibling directories for repos that declare
//   @openedx/paragon as a dependency (the v0 pilot convenience; pass paths explicitly for
//   anything else).
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { findParagonDir } from './lib/paragon-css.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const DESIGN_SYSTEM_DIR = join(HERE, '..');

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function reportFor(repoDir) {
  const pkgPath = join(repoDir, 'package.json');
  if (!existsSync(pkgPath)) return { repoDir, error: 'no package.json' };
  const pkg = readJson(pkgPath);
  const declared = pkg.dependencies?.['@openedx/paragon'] ?? pkg.devDependencies?.['@openedx/paragon'] ?? null;
  const paragonDir = findParagonDir(repoDir);
  const installed = paragonDir && existsSync(join(paragonDir, 'package.json')) ? readJson(join(paragonDir, 'package.json')).version : null;
  const brandDep = pkg.dependencies?.['@edx/brand'] ?? pkg.dependencies?.['@openedx/brand-openedx'] ?? null;
  let brandVersion = null;
  for (const candidate of ['@edx/brand', '@openedx/brand-openedx']) {
    const p = join(repoDir, 'node_modules', candidate, 'package.json');
    if (existsSync(p)) { brandVersion = readJson(p).version; break; }
  }
  return { repoDir, name: pkg.name, declared, installed, brandDep, brandVersion };
}

function findCandidateRepos() {
  // Convenience default for the v0 pilot: scan the workspace's sibling repo directories.
  const roots = [join(DESIGN_SYSTEM_DIR, '../../..'), join(DESIGN_SYSTEM_DIR, '../../../..')];
  const found = [];
  for (const root of roots) {
    if (!existsSync(root)) continue;
    for (const entry of readdirSync(root, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const pkgPath = join(root, entry.name, 'package.json');
      if (!existsSync(pkgPath)) continue;
      try {
        const pkg = readJson(pkgPath);
        if (pkg.dependencies?.['@openedx/paragon'] || pkg.devDependencies?.['@openedx/paragon']) found.push(join(root, entry.name));
      } catch { /* not readable JSON; skip */ }
    }
  }
  return [...new Set(found)];
}

function semverParts(v) {
  const m = /^(\d+)\.(\d+)\.(\d+)/.exec(String(v ?? '').replace(/^[\^~]/, ''));
  return m ? { major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3]) } : null;
}

function main() {
  const args = process.argv.slice(2);
  const repos = args.length ? args : findCandidateRepos();
  if (repos.length === 0) {
    console.error('No repos given and none found declaring @openedx/paragon nearby. Pass repo paths explicitly.');
    process.exit(2);
  }

  const mapPath = join(DESIGN_SYSTEM_DIR, 'figma-paragon-map.json');
  const referenceVersion = existsSync(mapPath) ? readJson(mapPath).paragonVersion : null;
  const reference = semverParts(referenceVersion);

  let hasMajorMismatch = false;
  for (const repoDir of repos) {
    const r = reportFor(repoDir);
    if (r.error) { console.log(`${repoDir}: ${r.error}`); continue; }
    const installedParts = semverParts(r.installed);
    let note = '';
    if (!r.installed) note = 'not installed (run npm install)';
    else if (reference && installedParts && installedParts.major !== reference.major) { note = `MAJOR MISMATCH vs map reference ${referenceVersion}`; hasMajorMismatch = true; }
    else if (reference && installedParts && installedParts.minor !== reference.minor) note = `minor difference vs map reference ${referenceVersion} (check-tokens will confirm names)`;
    else note = 'matches map reference';

    console.log(`${r.name ?? repoDir}`);
    console.log(`  declared: ${r.declared ?? '(not a dependency)'}   installed: ${r.installed ?? '—'}   ${note}`);
    if (r.brandDep) console.log(`  brand: ${r.brandDep}   installed: ${r.brandVersion ?? '—'}`);
  }

  process.exit(hasMajorMismatch ? 1 : 0);
}

main();
