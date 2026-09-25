#!/usr/bin/env node
// Regenerates figma-paragon-map.{json,md} and paragon-unmapped.md from the normalized
// catalog in sources/<sourceId>.json against an installed @openedx/paragon. Zero
// dependencies; only reads files and parses text. Never executes Paragon's own code.
//
// Usage:
//   node generate.mjs [--paragon <dir-or-project-root>] [--theme light] [--source <id>] [--check]
//
// --paragon defaults to walking up from this script's own repo checkout to find a sibling
// frontend-app-authoring/node_modules/@openedx/paragon (the v0 pilot target); pass it
// explicitly for any other repo. --check regenerates into memory and exits 1 if the
// committed files would change, instead of writing them (used by CI and the golden test).
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadParagonTokens, findParagonDir } from './lib/paragon-css.mjs';
import { loadParagonExports, resolveComponentName } from './lib/paragon-exports.mjs';
import { resolveVariable, resolveColorStyle, resolveEffectStyle, COLLECTION_FAMILY } from './lib/join.mjs';
import { resolveTextTarget, compareTextStyle } from './lib/text-styles.mjs';
import { normalizeColor } from './lib/normalize.mjs';
import { writeJson, writeMarkdownTable } from './lib/emit.mjs';
import { buildTierWords, isTierEligible } from './lib/tier.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const DESIGN_SYSTEM_DIR = join(HERE, '..');
const GENERATOR_VERSION = '0.1.0';

function parseArgs(argv) {
  const args = { theme: 'light', source: 'unicon-copy-2026-09', check: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--paragon') args.paragon = argv[++i];
    else if (argv[i] === '--theme') args.theme = argv[++i];
    else if (argv[i] === '--source') args.source = argv[++i];
    else if (argv[i] === '--source-file') args.sourceFile = argv[++i]; // test/fixture use only; bypasses sources/<id>.json
    else if (argv[i] === '--out-dir') args.outDir = argv[++i]; // test/fixture use only; default writes into design-system/
    else if (argv[i] === '--check') args.check = true;
  }
  return args;
}

function defaultParagonDir() {
  // Walk up from this repo's own checkout to find a sibling frontend-app-authoring; this
  // is the v0 pilot target only (see figmaToCodeWorkflow.md). A real project points
  // --paragon at its own repo instead of relying on this default.
  const candidates = [
    join(DESIGN_SYSTEM_DIR, '../../../frontend-app-authoring'),
    join(DESIGN_SYSTEM_DIR, '../../../../frontend-app-authoring'),
  ];
  for (const c of candidates) {
    const found = findParagonDir(c);
    if (found) return found;
  }
  return null;
}

function loadJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function checkOverridesFresh(overrides, tokens) {
  for (const o of overrides.overrides ?? []) {
    if (o.token == null) continue;
    if (!tokens.has(o.token)) {
      throw new Error(`overrides.json: "${o.figma}" points at "${o.token}", which doesn't exist in this Paragon install.`);
    }
    if (o.expect != null) {
      const actual = tokens.get(o.token).resolved;
      const same = normalizeColor(o.expect) != null
        ? normalizeColor(o.expect) === normalizeColor(actual)
        : String(o.expect) === String(actual);
      if (!same) {
        throw new Error(`overrides.json: "${o.figma}" -> "${o.token}" expected ${o.expect}, but it now resolves to ${actual}. Review and update \`expect\`, or the override may no longer be correct.`);
      }
    }
  }
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const paragonDir = args.paragon ? findParagonDir(args.paragon) ?? args.paragon : defaultParagonDir();
  if (!paragonDir || !existsSync(join(paragonDir, 'package.json'))) {
    console.error('Could not find an installed @openedx/paragon. Pass --paragon <project-or-package-dir>.');
    process.exit(2);
  }

  const rules = loadJson(join(DESIGN_SYSTEM_DIR, 'rules.json'));
  const overrides = loadJson(join(DESIGN_SYSTEM_DIR, 'overrides.json'));
  const source = loadJson(args.sourceFile ?? join(DESIGN_SYSTEM_DIR, `sources/${args.source}.json`));
  const outDir = args.outDir ?? DESIGN_SYSTEM_DIR;

  const { names: tokens, version: paragonVersion } = loadParagonTokens(paragonDir, { theme: args.theme });
  checkOverridesFresh(overrides, tokens);
  const paragonExports = loadParagonExports(paragonDir);
  const tierWords = buildTierWords(source.variables, COLLECTION_FAMILY);

  // --- Variables ---
  const variableEntries = source.variables.map((v) => resolveVariable(v, { tokens, rules, overrides: overrides.overrides, tierWords }));

  // --- Styles: split by kind. Text styles use the typography-target resolver directly
  // (it needs the raw Font(...) values, not just a token/value pair). ---
  const paintStyleEntries = [];
  const textStyleEntries = [];
  const effectStyleEntries = [];
  for (const style of source.styles) {
    if (style.kind === 'paint') {
      paintStyleEntries.push(resolveColorStyle(style, { tokens, overrides: overrides.overrides, tierWords }));
    } else if (style.kind === 'effect') {
      effectStyleEntries.push(resolveEffectStyle(style, tokens));
    } else if (style.kind === 'text') {
      const resolved = resolveTextTarget(style.name, tokens);
      const cmp = compareTextStyle(style.value, resolved);
      const allEqual = Object.values(cmp).every((v) => v === 'equal' || v === 'rounded' || v === 'unavailable');
      textStyleEntries.push({
        style, target: resolved.target, cssRef: resolved.cssRef, note: resolved.note,
        status: !resolved.matched ? 'figma-only' : allEqual ? 'exact' : 'value-differs',
        comparison: cmp, figmaValue: style.value,
        codeValue: resolved.matched ? { fontSizePx: resolved.fontSizePx, lineHeightPx: resolved.lineHeightPx, fontWeight: resolved.fontWeight, fontFamilyKind: resolved.fontFamilyKind } : null,
      });
    }
  }

  // --- Components ---
  const componentEntries = [];
  for (const category of source.components) {
    const names = String(category.value).split(',').map((s) => s.trim()).filter(Boolean);
    for (const name of names) componentEntries.push({ category: category.name, ...resolveComponentName(name, paragonExports) });
  }

  // --- Reverse index: global/alias-tier tokens no Figma variable maps to. ---
  const mappedTokens = new Set();
  for (const e of variableEntries) if (e.token) mappedTokens.add(e.token);
  for (const e of paintStyleEntries) if (e.token) mappedTokens.add(e.token);
  const unmapped = [];
  for (const [name, entry] of tokens) {
    if (!isTierEligible(name, tierWords)) continue; // component-scoped; not interesting here
    if (/^--pgn-[a-z]+-action-/.test(name)) continue;
    if (!mappedTokens.has(name)) unmapped.push({ token: name, value: entry.resolved, description: entry.description ?? '' });
  }
  unmapped.sort((a, b) => a.token.localeCompare(b.token));

  const counts = tally(variableEntries, textStyleEntries, paintStyleEntries, effectStyleEntries);

  const header = {
    generatorVersion: GENERATOR_VERSION,
    sourceId: source.sourceId,
    figmaFileName: source.provenance?.figmaFileName,
    variablesCapturedAt: source.provenance?.variablesCapturedAt,
    stylesCapturedAt: source.provenance?.stylesCapturedAt,
    stylesCaptureScope: source.provenance?.stylesCaptureScope,
    paragonVersion,
    theme: args.theme,
    counts,
  };

  const mapJson = {
    ...header,
    variables: variableEntries.map(serializeVariableEntry).sort(byFigmaName),
    textStyles: textStyleEntries.map(serializeTextStyleEntry).sort(byStyleName),
    paintStyles: paintStyleEntries.map(serializePaintStyleEntry).sort(byStyleName),
    effectStyles: effectStyleEntries.map(serializeEffectStyleEntry).sort(byStyleName),
    components: componentEntries.sort((a, b) => a.name.localeCompare(b.name)),
  };

  const outMap = join(outDir, 'figma-paragon-map.json');
  const outMd = join(outDir, 'figma-paragon-map.md');
  const outUnmapped = join(outDir, 'paragon-unmapped.md');

  const mdRows = [
    ...mapJson.variables.map((v) => ({
      Collection: v.collection, 'Figma name': v.figmaName, Status: v.status,
      'Code token / class': v.token ?? (v.fallback ? `→ ${v.fallback}` : (v.candidates?.[0]?.token ? `? ${v.candidates[0].token}` : '')),
      'Figma value': v.figmaValue, 'Code value': v.codeValue ?? '', Note: v.reason ?? v.note ?? '',
    })),
    ...mapJson.textStyles.map((s) => ({
      Collection: 'Text style', 'Figma name': s.figmaName, Status: s.status,
      'Code token / class': s.cssRef ?? '', 'Figma value': s.figmaValue, 'Code value': s.codeValue ?? '', Note: s.note ?? '',
    })),
    ...mapJson.paintStyles.map((s) => ({
      Collection: s.legacyLibraryStyle ? 'Paint style (library)' : 'Paint style (local)', 'Figma name': s.figmaName, Status: s.status,
      'Code token / class': s.token ?? (s.candidates?.[0]?.token ? `? ${s.candidates[0].token}` : ''),
      'Figma value': s.figmaValue, 'Code value': s.codeValue ?? '', Note: s.reason ?? s.note ?? '',
    })),
    ...mapJson.effectStyles.map((s) => ({
      Collection: 'Effect style', 'Figma name': s.figmaName, Status: s.status,
      'Code token / class': (s.candidates ?? []).map((c) => c.token).join(', '), 'Figma value': '(ordered shadow layers)', 'Code value': '',
      Note: (s.candidates ?? []).some((c) => c.layerOrder === 'reversed') ? 'layer order reversed vs Figma (same layers, same paint result; see policy.md)' : '',
    })),
  ];

  const mdHeaderLines = [
    `Generator ${GENERATOR_VERSION} · catalog \`${source.sourceId}\` (${source.provenance?.figmaFileName}, variables captured ${source.provenance?.variablesCapturedAt}, styles captured ${source.provenance?.stylesCapturedAt} — ${source.provenance?.stylesCaptureScope}) · Paragon ${paragonVersion} (${args.theme} theme)`,
    '',
    '**Use the Code token / class column. Never derive a `--pgn-*` name from a Figma name. When a Figma value and the code value differ, the code value wins** (see policy.md).',
    '',
    `Counts: ${Object.entries(counts).map(([k, v]) => `${k} ${v}`).join(' · ')}`,
  ];

  const unmappedRows = unmapped.map((u) => ({ Token: u.token, Value: u.value, Description: u.description }));

  const files = {
    [outMap]: mapJson,
    [outMd]: () => renderMarkdown('Figma → Paragon map', mdHeaderLines, ['Collection', 'Figma name', 'Status', 'Code token / class', 'Figma value', 'Code value', 'Note'], mdRows),
    [outUnmapped]: () => renderMarkdown(
      'Paragon tokens with no Figma variable',
      [`Generator ${GENERATOR_VERSION} · catalog \`${source.sourceId}\` · Paragon ${paragonVersion} (${args.theme} theme)`, '', 'Global and alias-tier tokens only (component-scoped tokens and `action-*` hover shades are excluded). For Phil and the Paragon WG: candidates for new Figma variables.'],
      ['Token', 'Value', 'Description'],
      unmappedRows,
    ),
  };

  if (args.check) {
    let changed = false;
    for (const [path, content] of Object.entries(files)) {
      const rendered = typeof content === 'function' ? content() : `${JSON.stringify(content, null, 2)}\n`;
      const existing = existsSync(path) ? readFileSync(path, 'utf8') : null;
      if (existing !== rendered) {
        console.error(`STALE: ${path} would change. Run \`node generate.mjs\` and commit the result.`);
        changed = true;
      }
    }
    if (changed) process.exit(1);
    console.log('figma-paragon-map is up to date.');
    return;
  }

  writeJson(outMap, mapJson);
  writeMarkdownTable(outMd, { title: 'Figma → Paragon map', headerLines: mdHeaderLines, columns: ['Collection', 'Figma name', 'Status', 'Code token / class', 'Figma value', 'Code value', 'Note'], rows: mdRows });
  writeMarkdownTable(outUnmapped, {
    title: 'Paragon tokens with no Figma variable',
    headerLines: [`Generator ${GENERATOR_VERSION} · catalog \`${source.sourceId}\` · Paragon ${paragonVersion} (${args.theme} theme)`, '', 'Global and alias-tier tokens only (component-scoped tokens and `action-*` hover shades are excluded). For Phil and the Paragon WG: candidates for new Figma variables.'],
    columns: ['Token', 'Value', 'Description'],
    rows: unmappedRows,
  });

  console.log(`Wrote ${outMap}, ${outMd}, ${outUnmapped}`);
  console.log('Counts:', counts);
}

function renderMarkdown(title, headerLines, columns, rows) {
  const esc = (c) => String(c ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
  const lines = [`# ${title}`, '', ...headerLines, '', `| ${columns.join(' | ')} |`, `|${columns.map(() => '---').join('|')}|`];
  for (const row of rows) lines.push(`| ${columns.map((c) => esc(row[c])).join(' | ')} |`);
  lines.push('');
  return lines.join('\n');
}

function tally(variableEntries, textStyleEntries, paintStyleEntries, effectStyleEntries) {
  const counts = {};
  const bump = (s) => { counts[s] = (counts[s] ?? 0) + 1; };
  for (const e of variableEntries) bump(e.status);
  for (const e of textStyleEntries) bump(`text-${e.status}`);
  for (const e of paintStyleEntries) bump(`paint-${e.status}`);
  for (const e of effectStyleEntries) bump(`effect-${e.status}`);
  return counts;
}

function serializeVariableEntry(e) {
  return {
    figmaName: e.figma.name, collection: e.figma.collection, type: e.figma.type,
    figmaValue: e.figma.value ?? (e.figma.aliasOf ? `→ ${e.figma.aliasOf}` : ''),
    status: e.status, token: e.token ?? null, codeValue: e.codeValue ?? null,
    valueMatch: e.valueMatch ?? null, delta: e.delta ?? null, context: e.context ?? null,
    fallback: e.fallback ?? null, via: e.via ?? null,
    candidates: (e.candidates ?? []).map((c) => c.token),
    reason: e.reason ?? null, reviewer: e.reviewer ?? null, rule: e.rule ?? null,
  };
}
function serializeTextStyleEntry(e) {
  return { figmaName: e.style.name, legacyLibraryStyle: e.style.legacyLibraryStyle, target: e.target, cssRef: e.cssRef, note: e.note ?? null, status: e.status, comparison: e.comparison, figmaValue: `${e.figmaValue.fontSize}px/${e.figmaValue.lineHeight} ${e.figmaValue.fontWeight} ${e.figmaValue.fontFamily}`, codeValue: e.codeValue ? `${e.codeValue.fontSizePx}px/${e.codeValue.lineHeightPx} ${e.codeValue.fontWeight} ${e.codeValue.fontFamilyKind}` : null };
}
function serializePaintStyleEntry(e) {
  return { figmaName: e.style.name, legacyLibraryStyle: e.style.legacyLibraryStyle, local: e.style.local, status: e.status, token: e.token ?? null, codeValue: e.codeValue ?? null, figmaValue: e.style.value.hex, valueMatch: e.valueMatch ?? null, candidates: (e.candidates ?? []).map((c) => c.token), reason: e.reason ?? null, note: e.note ?? null };
}
function serializeEffectStyleEntry(e) {
  return { figmaName: e.style.name, status: e.status, candidates: (e.candidates ?? []).map((c) => ({ token: c.token, layerOrder: c.layerOrder })), layers: e.style.value.effects };
}
function byFigmaName(a, b) { return a.figmaName.localeCompare(b.figmaName); }
function byStyleName(a, b) { return a.figmaName.localeCompare(b.figmaName); }

main();
