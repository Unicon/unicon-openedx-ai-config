import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { parseCatalogMd } from '../lib/adapters/catalog-md.mjs';
import { parseVariableDefs } from '../lib/adapters/mcp-variable-defs.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

test('catalog-md: parses collections, literal values, and alias pointers', () => {
  const { collections, variables } = parseCatalogMd(join(HERE, 'fixtures/catalog-sample.md'));
  assert.deepEqual(collections.map((c) => c.name), ['Primitives', 'Semantic', 'Spacing', 'Paragon Categories']);
  assert.equal(variables.length, 3 + 2 + 1 + 1);

  const white = variables.find((v) => v.name === 'white');
  assert.equal(white.value, '#ffffff');

  const themeBg = variables.find((v) => v.name === 'theme/bg/base');
  assert.equal(themeBg.aliasOf, 'white');
  assert.equal(themeBg.value, undefined);

  const spacer = variables.find((v) => v.name === 'spacer/1-5');
  assert.equal(spacer.value, 6); // FLOAT cells are coerced to a number
  assert.equal(typeof spacer.value, 'number');

  const actions = variables.find((v) => v.name === 'Actions');
  assert.equal(actions.type, 'STRING');
  assert.equal(actions.value, 'Button, Badge, NavBar, Multiselect');
});

test('mcp-variable-defs: classifies confirmations, legacy-prefixed, and local styles', () => {
  const known = new Set(['white', 'gray/700']);
  const { confirmations, styles } = parseVariableDefs({
    'white': '#ffffff', // exact-case match to a known variable -> confirmation, not a style
    '💎 - Primary/500': '#112233', // legacy-prefixed -> library style
    'Extras/Black': '#000000', // neither prefixed nor a known name -> local style
  }, known);

  assert.equal(confirmations.length, 1);
  assert.equal(confirmations[0].name, 'white');

  assert.equal(styles.length, 2);
  const primary500 = styles.find((s) => s.rawName === '💎 - Primary/500');
  assert.equal(primary500.name, 'Primary/500');
  assert.equal(primary500.legacyLibraryStyle, true);
  assert.equal(primary500.local, false);
  assert.equal(primary500.kind, 'paint');

  const black = styles.find((s) => s.rawName === 'Extras/Black');
  assert.equal(black.local, true);
  assert.equal(black.legacyLibraryStyle, false);
});

test('mcp-variable-defs: parses Font(...) as a text style and preserves Effect(...) layer order', () => {
  const { styles } = parseVariableDefs({
    'Heading/H2': 'Font(family: "Inter", style: Bold, size: 32, weight: 700, lineHeight: 36, letterSpacing: 0)',
    'Elevation/L1': 'Effect(type: DROP_SHADOW, color: #00000026, offset: (0, 0), radius: 16, spread: 0); Effect(type: DROP_SHADOW, color: #00000026, offset: (0, 0), radius: 10, spread: 0)',
  }, new Set());

  const heading = styles.find((s) => s.name === 'Heading/H2');
  assert.equal(heading.kind, 'text');
  assert.equal(heading.value.fontSize, 32);
  assert.equal(heading.value.lineHeight, 36);

  const elevation = styles.find((s) => s.name === 'Elevation/L1');
  assert.equal(elevation.kind, 'effect');
  assert.equal(elevation.value.effects.length, 2);
  assert.equal(elevation.value.effects[0].radius, 16); // order preserved, never reordered
  assert.equal(elevation.value.effects[1].radius, 10);
});
