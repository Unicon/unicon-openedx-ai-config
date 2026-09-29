import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { buildSyncPlan, renderPlanMarkdown } from '../lib/sync-plan.mjs';
import { buildApplyInput, injectInput, normalizeNodeId } from '../lib/figma-inject.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIGMA_DIR = join(HERE, '../figma');
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;

const v = (name, collection, type, value) => ({ name, collection, type, mode: 'Mode 1', value });
const alias = (name, aliasOf) => ({ name, collection: 'Semantic', type: 'COLOR', mode: 'Mode 1', aliasOf });
const catalog = {
  variables: [
    v('white', 'Primitives', 'COLOR', '#ffffff'),
    v('gray/700', 'Primitives', 'COLOR', '#454545'),
    v('secondary/base', 'Primitives', 'COLOR', '#454545'),
    v('light/400', 'Primitives', 'COLOR', '#e9e6e4'),
    alias('text/primary', 'gray/700'),
    alias('text/on-dark', 'white'),
    v('spacer/2', 'Spacing', 'FLOAT', 8),
    v('spacer/3', 'Spacing', 'FLOAT', 16),
    v('border/width', 'Sizing', 'FLOAT', 1),
    v('border-radius/base', 'Sizing', 'FLOAT', 6),
    v('font-weight/bolder', 'Typography', 'FLOAT', 800),
  ],
};
const status = (figmaName, s, extra = {}) => ({ figmaName, status: s, ...extra });
const map = {
  sourceId: 'fixture', paragonVersion: '23.23.0',
  variables: [
    status('white', 'exact'), status('gray/700', 'exact'), status('secondary/base', 'exact'), status('light/400', 'exact'),
    status('text/primary', 'override'), status('text/on-dark', 'figma-only'),
    status('spacer/2', 'exact'), status('spacer/3', 'exact'), status('border/width', 'exact'), status('border-radius/base', 'exact'),
    status('font-weight/bolder', 'value-differs', { figmaValue: 800, codeValue: 'bolder', token: '--pgn-typography-font-weight-bolder' }),
  ],
  textStyles: [
    { figmaName: 'Body/Small', legacyLibraryStyle: true, status: 'exact', target: 'small', cssRef: '.small', figmaValue: '15.8px/24.5 400 Inter', codeValue: '15.75px/24.5 400 sans-serif' },
    { figmaName: 'Body/Small', legacyLibraryStyle: false, status: 'value-differs', target: 'small', cssRef: '.small', figmaValue: '14px/24 400 Inter', codeValue: '15.75px/24.500700000000002 400 sans-serif' },
    { figmaName: 'Heading/H5', legacyLibraryStyle: true, status: 'value-differs', target: 'h5', cssRef: '.h5', figmaValue: '20px/25 700 Inter', codeValue: '14px/17.5 700 sans-serif' },
  ],
  paintStyles: [],
};
const paint = (nodeId, hex, opacity = 1) => ({ nodeId, nodeName: `n${nodeId}`, field: 'fills', index: 0, hex, opacity });
const audit = (parts) => ({ schema: 'unicon.figma-audit/1', rootId: '1:1', rootName: 'Frame', skipped: { instances: 3 }, paints: [], numbers: [], textStyles: [], paintStyles: [], boundVariables: [], ...parts });
const plan = (parts) => buildSyncPlan(audit(parts), { map, catalog });

test('bind-color: a color with exactly one confirmed primitive is proposed, grouped across layers', () => {
  const p = plan({ paints: [paint('1:2', '#e9e6e4'), paint('1:3', '#E9E6E4')] });
  assert.equal(p.items.length, 1);
  assert.deepEqual({ id: p.items[0].id, kind: p.items[0].kind, status: p.items[0].status, to: p.items[0].to }, { id: 'P1', kind: 'bind-color', status: 'proposed', to: 'light/400' });
  assert.equal(p.items[0].targets.length, 2);
});

test('bind-color: two primitives with the same value make the item ambiguous; confirmed semantic aliases are offered, Figma-only ones are not', () => {
  const p = plan({ paints: [paint('1:2', '#454545'), paint('1:3', '#ffffff')] });
  const gray = p.items.find((i) => i.from === '#454545');
  assert.equal(gray.status, 'ambiguous');
  assert.equal(gray.to, null);
  assert.deepEqual(gray.candidates, ['gray/700', 'secondary/base']);
  assert.deepEqual(gray.alsoPossible, ['text/primary']);
  const white = p.items.find((i) => i.from === '#ffffff');
  assert.deepEqual(white.alsoPossible, []);
});

test('colors with no Paragon variable, or with opacity, are reported and never proposed', () => {
  const p = plan({ paints: [paint('1:2', '#123456'), paint('1:3', '#e9e6e4', 0.5)] });
  assert.equal(p.items.length, 0);
  assert.deepEqual(p.notes.map((n) => n.kind).sort(), ['off-system-color', 'translucent-color']);
});

test('bind-number: spacing matches Spacing variables and radii match only border-radius variables', () => {
  const p = plan({ numbers: [
    { nodeId: '1:2', nodeName: 'a', field: 'paddingLeft', value: 16 },
    { nodeId: '1:2', nodeName: 'a', field: 'itemSpacing', value: 16 },
    { nodeId: '1:3', nodeName: 'b', field: 'topLeftRadius', value: 6 },
    { nodeId: '1:4', nodeName: 'c', field: 'topLeftRadius', value: 16 },
  ] });
  const spacing = p.items.find((i) => i.group === 'spacing');
  assert.equal(spacing.to, 'spacer/3');
  assert.equal(spacing.targets.length, 2);
  assert.equal(p.items.find((i) => i.group === 'radius').to, 'border-radius/base');
  assert.ok(p.notes.some((n) => n.kind === 'number-no-variable' && n.from === 16 && n.group === 'radius'));
});

test('swap-text-style: a style that differs from code is switched to the style that matches code, even an older prefixed one', () => {
  const p = plan({ textStyles: [{ nodeId: '1:5', nodeName: 't', styleName: 'Body/Small' }, { nodeId: '1:6', nodeName: 'u', styleName: '💎 - Body/Small' }] });
  assert.equal(p.items.length, 1);
  const swap = p.items[0];
  assert.equal(swap.kind, 'swap-text-style');
  assert.equal(swap.from, 'Body/Small');
  assert.equal(swap.to, '💎 - Body/Small');
  assert.deepEqual(swap.toFont, { weight: 400, family: 'Inter' });
  assert.equal(swap.targets.length, 1);
});

test('text styles the plan cannot fix are reported with the reason', () => {
  const p = plan({ textStyles: [
    { nodeId: '1:5', nodeName: 't', styleName: '💎 - Heading/H5' },
    { nodeId: '1:6', nodeName: 'u', styleName: 'Heading/H9' },
    { nodeId: '1:7', nodeName: 'w', styleName: null },
    { nodeId: '1:8', nodeName: 'x', mixed: true },
  ] });
  assert.equal(p.items.length, 0);
  assert.deepEqual(p.notes.map((n) => n.kind).sort(), ['mixed-text-styles', 'text-style-differs-no-match', 'text-style-not-in-map', 'unstyled-text']);
});

test('bound variables are reported by map status; confirmed ones are left alone', () => {
  const b = (nodeId, variableName) => ({ nodeId, nodeName: 'n', field: 'fills[0]', variableName });
  const p = plan({ boundVariables: [b('1:2', 'gray/700'), b('1:3', 'font-weight/bolder'), b('1:4', 'text/on-dark'), b('1:5', 'local/thing')] });
  assert.equal(p.items.length, 0);
  assert.deepEqual(p.notes.map((n) => n.kind).sort(), ['bound-variable-figma-only', 'bound-variable-not-in-map', 'bound-variable-value-differs']);
  assert.equal(p.summary.instancesNotAudited, 3);
});

test('renderPlanMarkdown: approvable items and reported findings get separate tables, and text swaps are flagged as visible changes', () => {
  const md = renderPlanMarkdown(plan({
    paints: [paint('1:2', '#e9e6e4'), paint('1:3', '#123456')],
    textStyles: [{ nodeId: '1:5', nodeName: 't', styleName: 'Body/Small' }],
  }));
  assert.match(md, /\| P1 \| Link #e9e6e4 to `light\/400` \| 1 \|/);
  assert.match(md, /\| P2 \| Switch text style `Body\/Small` to `💎 - Body\/Small`/);
  assert.match(md, /This changes how the text looks/);
  assert.match(md, /code's `\.small` is 15\.75px\/24\.5 400/);
  assert.doesNotMatch(md, /24\.5007/);
  assert.match(md, /### Reported, not changed[\s\S]*No Paragon variable has this color/);
});

test('buildApplyInput: carries only approved items, with the designer\'s pick for an ambiguous one', () => {
  const p = plan({ paints: [paint('1:2', '#e9e6e4'), paint('1:3', '#454545')] });
  const input = buildApplyInput(p, { approve: ['P2'], picks: { P2: 'gray/700' } });
  assert.equal(input.rootId, '1:1');
  assert.equal(input.changes.length, 1);
  assert.deepEqual(input.changes[0], { id: 'P2', kind: 'bind-color', from: '#454545', to: 'gray/700', targets: [{ nodeId: '1:3', field: 'fills', index: 0 }] });
});

test('buildApplyInput: refuses unknown ids, missing or invalid picks, and swaps without a style key', () => {
  const p = plan({ paints: [paint('1:3', '#454545')], textStyles: [{ nodeId: '1:5', nodeName: 't', styleName: 'Body/Small' }] });
  assert.throws(() => buildApplyInput(p, { approve: [] }), /Nothing approved/);
  assert.throws(() => buildApplyInput(p, { approve: ['P9'] }), /P9 is not in this plan/);
  assert.throws(() => buildApplyInput(p, { approve: ['P1'] }), /P1 needs --pick/);
  assert.throws(() => buildApplyInput(p, { approve: ['P1'], picks: { P1: 'white' } }), /isn't one of/);
  assert.throws(() => buildApplyInput(p, { approve: ['P2'] }), /P2 needs --style-key/);
  assert.throws(() => buildApplyInput(p, { approve: ['P2'], styleKeys: { '💎 - Body/Small': 'nope' } }), /doesn't look like a Figma style key/);
  const ok = buildApplyInput(p, { approve: ['P2'], styleKeys: { '💎 - Body/Small': '0123456789abcdef0123456789abcdef01234567' } });
  assert.equal(ok.changes[0].toKey, '0123456789abcdef0123456789abcdef01234567');
});

test('buildApplyInput and normalizeNodeId: instance sublayer ids are refused', () => {
  assert.equal(normalizeNodeId('123-456'), '123:456');
  assert.throws(() => normalizeNodeId('I2972:1;2:3'), /not a plain Figma node id/);
  const p = plan({ paints: [{ ...paint('I9:9;1:2', '#e9e6e4') }] });
  assert.throws(() => buildApplyInput(p, { approve: ['P1'] }), /not a plain Figma node id/);
});

test('both committed Figma scripts still parse after their INPUT block is filled in', () => {
  const auditCode = injectInput(readFileSync(join(FIGMA_DIR, 'audit-frame.figma.js'), 'utf8'), { rootId: '1:1' });
  const applyCode = injectInput(readFileSync(join(FIGMA_DIR, 'apply-sync.figma.js'), 'utf8'), { rootId: '1:1', changes: [] });
  assert.match(auditCode, /const INPUT = \{"rootId":"1:1"\};/);
  assert.doesNotThrow(() => new AsyncFunction('figma', auditCode));
  assert.doesNotThrow(() => new AsyncFunction('figma', applyCode));
  assert.throws(() => injectInput('const x = 1;', {}), /no "\/\/ @inject-start/);
});

test('figma-script.mjs audit: prints the committed audit script with the node id filled in', () => {
  const r = spawnSync('node', [join(HERE, '../figma-script.mjs'), 'audit', '123-456'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /const INPUT = \{"rootId":"123:456"\};/);
  assert.match(r.stdout, /Read-only audit of one Figma node/);
});
