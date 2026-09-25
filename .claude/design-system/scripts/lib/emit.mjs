// Deterministic writers: no timestamps in generated output, so two runs against the same
// inputs produce byte-identical files (checked by generate.mjs --check and the golden test).
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

function ensureDir(path) {
  mkdirSync(dirname(path), { recursive: true });
}

export function writeJson(path, value) {
  ensureDir(path);
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function esc(cell) {
  return String(cell ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

export function writeMarkdownTable(path, { title, headerLines, columns, rows }) {
  ensureDir(path);
  const lines = [`# ${title}`, ''];
  for (const h of headerLines) lines.push(h);
  lines.push('', `| ${columns.join(' | ')} |`, `|${columns.map(() => '---').join('|')}|`);
  for (const row of rows) lines.push(`| ${columns.map((c) => esc(row[c])).join(' | ')} |`);
  lines.push('');
  writeFileSync(path, lines.join('\n'), 'utf8');
}
