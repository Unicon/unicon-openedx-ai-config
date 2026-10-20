#!/usr/bin/env node
// Turns a read-only Figma audit (the JSON that scripts/figma/audit-frame.figma.js returns)
// into paragon-design-check's sync-to-code proposal, using the committed map and catalog.
// Prints the proposal as Markdown for the designer to approve from. Changes nothing.
//
// Usage: node sync-plan.mjs <audit.json> [--out <plan.json>] [--json]
//   --out   also writes the plan as JSON; figma-script.mjs apply reads that file.
//   --json  prints the plan as JSON instead of Markdown.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { buildSyncPlan, renderPlanMarkdown } from './lib/sync-plan.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const DESIGN_SYSTEM_DIR = join(HERE, '..');

function readJson(path, what) {
  if (!existsSync(path)) {
    console.error(`${what} not found at ${path}.`);
    process.exit(2);
  }
  return JSON.parse(readFileSync(path, 'utf8'));
}

function main() {
  const args = process.argv.slice(2);
  let auditFile = null;
  let outFile = null;
  let asJson = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out') outFile = args[++i];
    else if (args[i] === '--json') asJson = true;
    else auditFile ??= args[i];
  }
  if (!auditFile) {
    console.error('Usage: node sync-plan.mjs <audit.json> [--out <plan.json>] [--json]');
    process.exit(2);
  }

  const audit = readJson(auditFile, 'Audit file');
  if (audit.schema !== 'unicon.figma-audit/1') {
    console.error(`${auditFile} isn't an audit-frame.figma.js result (schema "${audit.schema}").`);
    process.exit(2);
  }
  const map = readJson(join(DESIGN_SYSTEM_DIR, 'figma-paragon-map.json'), 'figma-paragon-map.json');
  const catalog = readJson(join(DESIGN_SYSTEM_DIR, 'sources', `${map.sourceId}.json`), `Catalog ${map.sourceId}`);

  const plan = buildSyncPlan(audit, { map, catalog });
  if (outFile) writeFileSync(outFile, `${JSON.stringify(plan, null, 2)}\n`);
  console.log(asJson ? JSON.stringify(plan, null, 2) : renderPlanMarkdown(plan));
}

main();
