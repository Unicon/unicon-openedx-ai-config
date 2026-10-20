#!/usr/bin/env node
// Checks a live Figma MCP `get_variable_defs` capture against the committed
// figma-paragon-map.json: every name in the capture should already be in the map, with the
// same resolved status. A name the map doesn't know about, or a value that no longer
// matches, is catalog drift — reported, never silently resolved. Read-only.
//
// Usage: node map-figma.mjs <path-to-get_variable_defs.json>
//   (the file is the raw MCP tool result: { variables: { "<name>": "<value>", ... } })
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseVariableDefs } from './lib/adapters/mcp-variable-defs.mjs';
import { normalizeColor } from './lib/normalize.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const DESIGN_SYSTEM_DIR = join(HERE, '..');

function loadMap() {
  const path = join(DESIGN_SYSTEM_DIR, 'figma-paragon-map.json');
  if (!existsSync(path)) {
    console.error('figma-paragon-map.json not found. Run generate.mjs first.');
    process.exit(2);
  }
  return JSON.parse(readFileSync(path, 'utf8'));
}

function main() {
  const [captureFile] = process.argv.slice(2);
  if (!captureFile) {
    console.error('Usage: node map-figma.mjs <path-to-get_variable_defs.json>');
    process.exit(2);
  }
  const capture = JSON.parse(readFileSync(captureFile, 'utf8'));
  const map = loadMap();

  const knownVariableNames = new Set(map.variables.map((v) => v.figmaName));
  const { confirmations, styles } = parseVariableDefs(capture.variables, knownVariableNames);

  const results = { consistent: [], valueDrift: [], notInMap: [] };

  for (const { name, value } of confirmations) {
    const entry = map.variables.find((v) => v.figmaName === name);
    if (!entry) { results.notInMap.push({ kind: 'variable', name }); continue; }
    const live = normalizeColor(value) ?? String(value);
    const catalogValue = typeof entry.figmaValue === 'string' && !entry.figmaValue.startsWith('→ ')
      ? (normalizeColor(entry.figmaValue) ?? entry.figmaValue) : null;
    if (catalogValue && live !== catalogValue) {
      results.valueDrift.push({ kind: 'variable', name, catalogValue, liveValue: live, status: entry.status });
    } else {
      results.consistent.push({ kind: 'variable', name, status: entry.status });
    }
  }

  for (const style of styles) {
    const pools = style.kind === 'text' ? map.textStyles : style.kind === 'effect' ? map.effectStyles : map.paintStyles;
    const entry = pools.find((s) => s.figmaName === style.name && (s.legacyLibraryStyle ?? false) === style.legacyLibraryStyle);
    if (!entry) {
      results.notInMap.push({ kind: `${style.kind} style`, name: style.rawName });
      continue;
    }
    if (style.kind === 'paint') {
      const live = normalizeColor(style.value.hex);
      const catalogValue = normalizeColor(entry.figmaValue);
      if (catalogValue && live !== catalogValue) {
        results.valueDrift.push({ kind: 'paint style', name: style.rawName, catalogValue: entry.figmaValue, liveValue: style.value.hex, status: entry.status });
        continue;
      }
    }
    results.consistent.push({ kind: `${style.kind} style`, name: style.rawName, status: entry.status });
  }

  console.log(`map-figma: ${results.consistent.length} consistent, ${results.valueDrift.length} value drift, ${results.notInMap.length} not in map (catalog needs a refresh; see policy.md "Catalog freshness").`);
  for (const d of results.valueDrift) console.log(`  DRIFT   ${d.kind} "${d.name}": catalog=${d.catalogValue} live=${d.liveValue} (map status was ${d.status})`);
  for (const n of results.notInMap) console.log(`  UNKNOWN ${n.kind} "${n.name}" is not in the committed map`);

  process.exit(results.valueDrift.length || results.notInMap.length ? 1 : 0);
}

main();
