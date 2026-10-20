import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadParagonTokens } from '../lib/paragon-css.mjs';
import { resolveVariable, resolveColorStyle, resolveEffectStyle, COLLECTION_FAMILY } from '../lib/join.mjs';
import { buildTierWords } from '../lib/tier.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE_DIR = join(HERE, 'fixtures/paragon');

const { names: tokens } = loadParagonTokens(FIXTURE_DIR, { theme: 'light' });
const rules = { renameRules: [{ pattern: '^theme/bg/base$', template: '--pgn-color-bg-base' }] };
const catalogVariables = [
  { name: 'white', collection: 'Primitives' }, { name: 'primary/base', collection: 'Primitives' },
  { name: 'primary/500', collection: 'Primitives' }, { name: 'theme/bg/base', collection: 'Semantic' },
];
const tierWords = buildTierWords(catalogVariables, COLLECTION_FAMILY);

test('resolveVariable: mechanical name match is exact when the value also matches', () => {
  const v = { name: 'white', collection: 'Primitives', type: 'COLOR', value: '#ffffff' };
  const r = resolveVariable(v, { tokens, rules: { renameRules: [] }, overrides: [], tierWords });
  assert.equal(r.status, 'exact');
  assert.equal(r.token, '--pgn-color-white');
});

test('resolveVariable: mechanical name match with a differing value is value-differs, not silently exact', () => {
  const v = { name: 'primary/base', collection: 'Primitives', type: 'COLOR', value: '#000000' }; // wrong on purpose
  const r = resolveVariable(v, { tokens, rules: { renameRules: [] }, overrides: [], tierWords });
  assert.equal(r.status, 'value-differs');
  assert.equal(r.token, '--pgn-color-primary-base');
});

test('resolveVariable: a matching rename rule resolves to its target token', () => {
  const v = { name: 'theme/bg/base', collection: 'Semantic', type: 'COLOR', value: '#ffffff' };
  const r = resolveVariable(v, { tokens, rules, overrides: [], tierWords });
  assert.equal(r.status, 'renamed');
  assert.equal(r.token, '--pgn-color-bg-base');
});

test('resolveVariable: a rename rule whose target token does not exist fails loudly, never silently skips', () => {
  const badRules = { renameRules: [{ pattern: '^white$', template: '--pgn-color-does-not-exist' }] };
  const v = { name: 'white', collection: 'Primitives', type: 'COLOR', value: '#ffffff' };
  assert.throws(() => resolveVariable(v, { tokens, rules: badRules, overrides: [], tierWords }), /does-not-exist/);
});

test('resolveVariable: an override always wins, and a token: null override confirms figma-only', () => {
  const v = { name: 'text/secondary', collection: 'Semantic', type: 'COLOR', value: '#707070' };
  const overrides = [{ kind: 'variable', figma: 'text/secondary', token: null, reason: 'no equivalent' }];
  const r = resolveVariable(v, { tokens, rules: { renameRules: [] }, overrides, tierWords });
  assert.equal(r.status, 'figma-only');
  assert.equal(r.override, true);
});

test('resolveVariable: an alias whose target mechanically resolves reports figma-only with a fallback, never auto-picks', () => {
  // brand/500 has no --pgn-color-brand-500 token of its own in the fixture (unlike
  // primary/500, which does and is covered by the mechanical-match test above), so this
  // exercises the alias-hop path specifically.
  const v = { name: 'brand/500', collection: 'Primitives', type: 'COLOR', aliasOf: 'primary/base' };
  const r = resolveVariable(v, { tokens, rules: { renameRules: [] }, overrides: [], tierWords });
  assert.equal(r.status, 'figma-only');
  assert.equal(r.fallback, '--pgn-color-primary-base');
});

test('resolveVariable: a same-family value match with no name hit is value-only (one candidate) or ambiguous (several), never auto-resolved', () => {
  const v = { name: 'text/on-dark', collection: 'Semantic', type: 'COLOR', value: '#ffffff' };
  const r = resolveVariable(v, { tokens, rules: { renameRules: [] }, overrides: [], tierWords });
  assert.ok(r.status === 'value-only' || r.status === 'ambiguous');
  assert.ok(r.candidates.some((c) => c.token === '--pgn-color-white'));
  assert.equal(r.token, undefined); // never silently confirmed
});

test('resolveVariable: value match candidates exclude component-scoped tokens via tierWords', () => {
  const v = { name: 'text/on-dark', collection: 'Semantic', type: 'COLOR', value: '#ffffff' };
  const r = resolveVariable(v, { tokens, rules: { renameRules: [] }, overrides: [], tierWords });
  assert.ok(!r.candidates.some((c) => c.token === '--pgn-color-btn-text-primary'));
  assert.ok(!r.candidates.some((c) => c.token === '--pgn-color-badge-focus-dark'));
});

test('resolveVariable: action-* derived tokens are never offered as candidates', () => {
  const v = { name: 'primary/700', collection: 'Primitives', type: 'COLOR', value: '#0e2a44' };
  const r = resolveVariable(v, { tokens, rules: { renameRules: [] }, overrides: [], tierWords });
  assert.ok(!(r.candidates ?? []).some((c) => c.token.includes('action')));
});

test('resolveColorStyle: an exact-value local style is exact, not forced value-differs, but still carries the unconfirmed-identity note', () => {
  const style = { name: 'Gray/700', rawName: 'Gray/700', kind: 'paint', legacyLibraryStyle: false, local: true, value: { hex: '#454545' } };
  const r = resolveColorStyle(style, { tokens, overrides: [], tierWords });
  assert.equal(r.status, 'exact');
  assert.ok(r.note && /unconfirmed|not confirmed/.test(r.note));
});

test('resolveColorStyle: a stale local style with a different value is value-differs', () => {
  const style = { name: 'Primary/500', rawName: 'Primary/500', kind: 'paint', legacyLibraryStyle: false, local: true, value: { hex: '#00262b' } };
  const r = resolveColorStyle(style, { tokens, overrides: [], tierWords });
  assert.equal(r.status, 'value-differs');
});

test('resolveEffectStyle: matches a same-value shadow even when layer order is reversed, and records that explicitly', () => {
  const style = {
    name: 'Level 1', value: { effects: [
      { radius: 4, offsetX: 0, offsetY: 0, spread: 0, color: '#00000026' },
      { radius: 2, offsetX: 0, offsetY: 0, spread: 0, color: '#00000026' },
    ] },
  };
  const r = resolveEffectStyle(style, tokens);
  assert.ok(r.status === 'value-only' || r.status === 'ambiguous');
  const hit = r.candidates.find((c) => c.token === '--pgn-elevation-box-shadow-centered-1');
  assert.ok(hit);
  assert.equal(hit.layerOrder, 'reversed');
});

test('resolveEffectStyle: a shadow with no matching layer set is figma-only', () => {
  const style = { name: 'Nope', value: { effects: [{ radius: 99, offsetX: 0, offsetY: 0, spread: 0, color: '#00000026' }] } };
  const r = resolveEffectStyle(style, tokens);
  assert.equal(r.status, 'figma-only');
});
