// Reads an installed @openedx/paragon package's compiled token CSS and resolves every
// --pgn-* custom property to a literal value, following var() chains and evaluating the
// scalar calc() expressions Paragon's own build emits. Never executes package code: this
// only reads and parses text files.
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { evalSimpleCalc } from './normalize.mjs';

const DECL_RE = /(--pgn-[a-zA-Z0-9-]+)\s*:\s*([^;]+);(?:\s*\/\*\*\s*([^*]*?)\s*\*\/)?/g;

/** Parse one CSS file's top-level --pgn-* declarations. Later declarations in the same
 * file win over earlier ones with the same name (last-in-source-order approximation of
 * the cascade), matching how Paragon's own theme files re-declare a handful of core
 * properties. */
function parseCssFile(path) {
  const text = readFileSync(path, 'utf8');
  const out = new Map();
  for (const m of text.matchAll(DECL_RE)) {
    const [, name, rawValue, description] = m;
    out.set(name, { raw: rawValue.trim(), description: description?.trim() || undefined, file: path });
  }
  return out;
}

/** Locate an installed @openedx/paragon package given either its own directory or a
 * project directory above it (walks up looking for node_modules/@openedx/paragon). */
export function findParagonDir(startDir) {
  let dir = startDir;
  for (let i = 0; i < 8; i++) {
    const direct = join(dir, 'package.json');
    if (existsSync(direct)) {
      try {
        const pkg = JSON.parse(readFileSync(direct, 'utf8'));
        if (pkg.name === '@openedx/paragon') return dir;
      } catch { /* not JSON, keep walking */ }
    }
    const nested = join(dir, 'node_modules', '@openedx', 'paragon');
    if (existsSync(join(nested, 'package.json'))) return nested;
    const parent = join(dir, '..');
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

/** Load and resolve every --pgn-* custom property for one Paragon install + theme.
 * Returns { version, names: Map<name, {raw, resolved, resolvedNumeric?, description, chain, family}> }. */
export function loadParagonTokens(paragonDir, { theme = 'light' } = {}) {
  const pkgPath = join(paragonDir, 'package.json');
  const version = existsSync(pkgPath) ? JSON.parse(readFileSync(pkgPath, 'utf8')).version : null;

  const files = [
    join(paragonDir, 'styles/css/core/variables.css'),
    join(paragonDir, 'styles/css/core/abstraction-variables.css'),
    join(paragonDir, 'styles/css/themes', theme, 'variables.css'),
    join(paragonDir, 'styles/css/themes', theme, 'abstraction-variables.css'),
  ].filter(existsSync);
  if (files.length === 0) {
    throw new Error(`No Paragon token CSS found under ${paragonDir} (looked for styles/css/core and styles/css/themes/${theme})`);
  }

  const raw = new Map(); // name -> {raw, description, file}
  for (const f of files) for (const [name, entry] of parseCssFile(f)) raw.set(name, entry);

  const resolved = new Map();
  const resolving = new Set();

  function substituteVars(value, chain) {
    // Replace every var(--pgn-x[, fallback]) with its resolved value (or the fallback).
    return value.replace(/var\(\s*(--pgn-[a-zA-Z0-9-]+)\s*(?:,\s*([^)]+))?\)/g, (whole, refName, fallback) => {
      const r = resolveOne(refName, chain);
      if (r.resolved != null) return String(r.resolved);
      return fallback != null ? fallback.trim() : whole;
    });
  }

  function resolveOne(name, chainSoFar = []) {
    if (resolved.has(name)) return resolved.get(name);
    const entry = raw.get(name);
    if (!entry) {
      const missing = { raw: null, resolved: null, description: undefined, chain: chainSoFar, missing: true };
      resolved.set(name, missing);
      return missing;
    }
    if (resolving.has(name)) {
      const cyc = { raw: entry.raw, resolved: null, description: entry.description, chain: chainSoFar, cycle: true };
      resolved.set(name, cyc);
      return cyc;
    }
    resolving.add(name);
    const chain = [...chainSoFar, name];

    let value = entry.raw;
    if (/var\(/.test(value)) {
      value = substituteVars(value, chain);
    }
    if (/^calc\(/.test(value.trim())) {
      const evaluated = evalSimpleCalc(value.trim());
      if (evaluated != null) value = evaluated;
      // else: leave as the calc() string with vars already substituted to literals; still
      // useful for a human reading the map, just not directly comparable numerically.
    }

    resolving.delete(name);
    const out = { raw: entry.raw, resolved: value, description: entry.description, chain, family: familyOf(name) };
    resolved.set(name, out);
    return out;
  }

  for (const name of raw.keys()) resolveOne(name);

  return { version, theme, names: resolved, rawByName: raw };
}

/** The `--pgn-<family>-...` prefix, used by the mechanical-name join rule. */
export function familyOf(tokenName) {
  const m = /^--pgn-([a-z]+)-/.exec(tokenName);
  return m ? m[1] : null;
}
