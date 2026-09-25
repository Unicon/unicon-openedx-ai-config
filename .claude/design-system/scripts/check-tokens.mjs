#!/usr/bin/env node
// Read-only: scans SCSS/CSS/JS/TS(X) files (or a diff) for `var(--pgn-*)` references that
// don't exist in the installed Paragon, and for hardcoded colors that could be tokens.
// Never edits anything; only prints findings and sets its exit code.
//
// Usage:
//   node check-tokens.mjs [--diff <base-ref>] [--strict] [--json] [paths...]
//
// --diff checks only added lines in `git diff -U0 <base-ref>` (run from inside the target
// repo). Without --diff, pass one or more file/dir paths to scan every line of every
// matching file under them. --strict makes a hardcoded color an error instead of a warning.
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { join, extname } from 'node:path';
import { findParagonDir, loadParagonTokens } from './lib/paragon-css.mjs';
import { normalizeColor } from './lib/normalize.mjs';

const CODE_EXT = new Set(['.scss', '.css', '.js', '.jsx', '.ts', '.tsx']);
const VAR_REF_RE = /var\(\s*(--pgn-[a-zA-Z0-9-]+)/g;
const HEX_RE = /#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3}(?:[0-9a-fA-F]{2})?)?\b/g;
const RGB_RE = /\brgba?\([^)]*\)/g;

function parseArgs(argv) {
  const args = { strict: false, json: false, paths: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--diff') args.diffBase = argv[++i];
    else if (argv[i] === '--strict') args.strict = true;
    else if (argv[i] === '--json') args.json = true;
    else if (argv[i] === '--paragon') args.paragon = argv[++i]; // explicit override; default infers from the scanned path
    else args.paths.push(argv[i]);
  }
  return args;
}

function walk(path, out = []) {
  const st = statSync(path);
  if (st.isDirectory()) {
    if (/node_modules|\.git$/.test(path)) return out;
    for (const child of readdirSync(path)) walk(join(path, child), out);
  } else if (CODE_EXT.has(extname(path))) {
    out.push(path);
  }
  return out;
}

/** Lines added by `git diff -U0 <base>` in the current repo, as { file, line, text }. */
function addedLinesFromDiff(base) {
  const raw = execSync(`git diff -U0 ${JSON.stringify(base)}`, { encoding: 'utf8', maxBuffer: 1024 * 1024 * 64 });
  const results = [];
  let file = null;
  let nextLine = null;
  for (const rawLine of raw.split('\n')) {
    if (rawLine.startsWith('+++ b/')) { file = rawLine.slice(6); continue; }
    if (rawLine.startsWith('+++ /dev/null')) { file = null; continue; }
    const hunk = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(rawLine);
    if (hunk) { nextLine = Number(hunk[1]); continue; }
    if (rawLine.startsWith('+') && !rawLine.startsWith('+++')) {
      if (file && nextLine != null && CODE_EXT.has(extname(file))) {
        results.push({ file, line: nextLine, text: rawLine.slice(1) });
      }
      if (nextLine != null) nextLine++;
    } else if (!rawLine.startsWith('-') && nextLine != null) {
      nextLine++;
    }
  }
  return results;
}

function linesFromPaths(paths) {
  const out = [];
  for (const p of paths) {
    for (const file of walk(p)) {
      const text = readFileSync(file, 'utf8').split('\n');
      text.forEach((line, i) => out.push({ file, line: i + 1, text: line }));
    }
  }
  return out;
}

function nearestTokenName(missing, tokenNames) {
  const target = missing.toLowerCase();
  let best = null, bestScore = -1;
  for (const name of tokenNames) {
    const n = name.toLowerCase();
    let score = 0;
    const minLen = Math.min(n.length, target.length);
    for (let i = 0; i < minLen; i++) if (n[i] === target[i]) score++; else break;
    if (score > bestScore) { bestScore = score; best = name; }
  }
  return bestScore >= 10 ? best : null; // require a reasonably long shared prefix
}

function sameValueTokens(hexOrRgb, tokens, limit = 3) {
  const normalized = normalizeColor(hexOrRgb);
  if (!normalized) return [];
  const out = [];
  for (const [name, entry] of tokens) {
    if (out.length >= limit) break;
    if (normalizeColor(entry.resolved) === normalized) out.push(name);
  }
  return out;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const startDir = args.paths[0] ?? process.cwd();
  const paragonDir = args.paragon ? findParagonDir(args.paragon) : findParagonDir(startDir);
  if (!paragonDir) {
    console.error(`No installed @openedx/paragon found from ${args.paragon ?? startDir}.`);
    process.exit(2);
  }
  const { names: tokens, version } = loadParagonTokens(paragonDir, { theme: 'light' });
  const tokenNames = [...tokens.keys()];

  const lines = args.diffBase ? addedLinesFromDiff(args.diffBase) : linesFromPaths(args.paths.length ? args.paths : [process.cwd()]);

  const findings = [];
  for (const { file, line, text } of lines) {
    if (/^\s*(\/\/|\*|\/\*)/.test(text)) continue; // skip whole-line comments

    for (const m of text.matchAll(VAR_REF_RE)) {
      const name = m[1];
      if (!tokens.has(name)) {
        const suggestion = nearestTokenName(name, tokenNames);
        findings.push({ level: 'error', rule: 'unknown-token', file, line, detail: `${name} is not defined in @openedx/paragon ${version}${suggestion ? `; did you mean ${suggestion}?` : ''}` });
      }
    }

    for (const m of text.matchAll(HEX_RE)) {
      const suggestions = sameValueTokens(m[0], tokens);
      findings.push({ level: args.strict ? 'error' : 'warning', rule: 'hardcoded-color', file, line, detail: `literal color ${m[0]}${suggestions.length ? `; matches ${suggestions.join(', ')}` : ' (no matching Paragon token found by value)'}` });
    }
    for (const m of text.matchAll(RGB_RE)) {
      const suggestions = sameValueTokens(m[0], tokens);
      findings.push({ level: args.strict ? 'error' : 'warning', rule: 'hardcoded-color', file, line, detail: `literal color ${m[0]}${suggestions.length ? `; matches ${suggestions.join(', ')}` : ' (no matching Paragon token found by value)'}` });
    }
  }

  if (args.json) {
    console.log(JSON.stringify({ paragonVersion: version, findings }, null, 2));
  } else {
    if (findings.length === 0) {
      console.log(`check-tokens: clean (Paragon ${version}, ${lines.length} line(s) checked).`);
    } else {
      for (const f of findings) console.log(`${f.file}:${f.line} ${f.level} ${f.rule} ${f.detail}`);
      console.log(`\n${findings.length} finding(s) against Paragon ${version} (${findings.filter((f) => f.level === 'error').length} error(s)).`);
    }
  }

  const hasErrors = findings.some((f) => f.level === 'error');
  process.exit(hasErrors ? 1 : 0);
}

main();
