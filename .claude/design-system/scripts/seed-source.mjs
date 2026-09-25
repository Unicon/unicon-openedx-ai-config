#!/usr/bin/env node
// One-time (repeatable) step: normalize the raw catalog exports under sources/raw/ into
// the common source schema generate.mjs consumes. Run this again whenever Phil re-exports
// the catalog in the same raw formats (a DESIGN.md variables table + an MCP
// get_variable_defs capture); see policy.md "Catalog freshness".
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseCatalogMd } from './lib/adapters/catalog-md.mjs';
import { parseVariableDefs } from './lib/adapters/mcp-variable-defs.mjs';
import { writeJson } from './lib/emit.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const DESIGN_SYSTEM_DIR = join(HERE, '..');

const SOURCE_ID = 'unicon-copy-2026-09';
const VARIABLES_MD = join(DESIGN_SYSTEM_DIR, 'sources/raw/unicon-copy-2026-09-variables.md');
const MCP_STYLES_JSON = join(DESIGN_SYSTEM_DIR, 'sources/raw/unicon-copy-2026-09-mcp-baseline-16-1245.json');
const OUT = join(DESIGN_SYSTEM_DIR, `sources/${SOURCE_ID}.json`);

const catalog = parseCatalogMd(VARIABLES_MD);
const variables = catalog.variables.filter((v) => v.type !== 'STRING');
const components = catalog.variables.filter((v) => v.type === 'STRING');

const mcpCapture = JSON.parse(readFileSync(MCP_STYLES_JSON, 'utf8'));
const knownVariableNames = new Set(variables.map((v) => v.name));
const { styles } = parseVariableDefs(mcpCapture.variables, knownVariableNames);

const source = {
  schema: 'unicon.design-system-source/1',
  sourceId: SOURCE_ID,
  provenance: {
    adapters: ['catalog-md', 'mcp-variable-defs'],
    rawFiles: [
      'sources/raw/unicon-copy-2026-09-variables.md',
      'sources/raw/unicon-copy-2026-09-mcp-baseline-16-1245.json',
    ],
    figmaFileName: 'Paragon Design System - Unicon Copy',
    variablesCapturedAt: '2026-09-24',
    // The style capture is a single frame's *used* variables and styles (see
    // mcp-variable-defs.mjs), not a full library export. It is the only style data we
    // have for v0; policy.md and paragon-gaps.md both flag this as a known gap to close
    // once the read-only use_figma audit script (Milestone 3) exports every local style.
    stylesCapturedAt: '2026-09-21',
    stylesCaptureScope: 'partial: styles used by node 16:1245 ("Apply Competencies") only, via get_variable_defs',
  },
  collections: catalog.collections.map((c) => ({ name: c.name, count: c.count, modes: c.modes })),
  variables,
  components,
  styles,
};

writeJson(OUT, source);
console.log(`Wrote ${OUT}`);
console.log(`  ${variables.length} variables, ${components.length} component-list entries, ${styles.length} styles`);
