#!/usr/bin/env node
// Prints ready-to-run `use_figma` code for paragon-design-check's sync-to-code mode: one of
// the committed scripts in scripts/figma/, with only its INPUT block filled in. Paste the
// output as the `code` argument of the Figma MCP's `use_figma` tool.
//
// Usage:
//   node figma-script.mjs audit <node-id>
//   node figma-script.mjs apply <plan.json> --approve P1,P3 [--pick P2=gray/700]...
//                                [--style-key "💎 - Body/Small=<key>"]...
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { buildApplyInput, injectInput, normalizeNodeId } from './lib/figma-inject.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const script = (name) => readFileSync(join(HERE, 'figma', name), 'utf8');

function collect(args, flag) {
  const values = [];
  for (let i = 0; i < args.length; i++) if (args[i] === flag && args[i + 1] != null) values.push(args[++i]);
  return values;
}

function pairs(values, flag) {
  const out = {};
  for (const v of values) {
    const at = v.lastIndexOf('=');
    if (at <= 0) throw new Error(`${flag} "${v}" should look like name=value.`);
    out[v.slice(0, at)] = v.slice(at + 1);
  }
  return out;
}

function main() {
  const [command, target, ...rest] = process.argv.slice(2);
  try {
    if (command === 'audit' && target) {
      process.stdout.write(injectInput(script('audit-frame.figma.js'), { rootId: normalizeNodeId(target) }));
    } else if (command === 'apply' && target) {
      const plan = JSON.parse(readFileSync(target, 'utf8'));
      const approve = collect(rest, '--approve').flatMap((v) => v.split(',')).map((s) => s.trim()).filter(Boolean);
      const input = buildApplyInput(plan, {
        approve,
        picks: pairs(collect(rest, '--pick'), '--pick'),
        styleKeys: pairs(collect(rest, '--style-key'), '--style-key'),
      });
      process.stdout.write(injectInput(script('apply-sync.figma.js'), input));
    } else {
      console.error('Usage: node figma-script.mjs audit <node-id>\n       node figma-script.mjs apply <plan.json> --approve P1,P3 [--pick P2=<variable>] [--style-key "<style name>=<key>"]');
      process.exit(2);
    }
  } catch (e) {
    console.error(`figma-script: ${e.message}`);
    process.exit(1);
  }
}

main();
