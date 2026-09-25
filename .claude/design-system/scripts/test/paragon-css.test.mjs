import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadParagonTokens, findParagonDir, familyOf } from '../lib/paragon-css.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE_DIR = join(HERE, 'fixtures/paragon');

test('findParagonDir: resolves a package.json named @openedx/paragon directly', () => {
  assert.equal(findParagonDir(FIXTURE_DIR), FIXTURE_DIR);
});

test('loadParagonTokens: theme file overrides core for the same property (cascade order)', () => {
  const { names } = loadParagonTokens(FIXTURE_DIR, { theme: 'light' });
  assert.equal(names.get('--pgn-size-border-radius-base').resolved, '0.4rem'); // theme wins over core's 0.375rem
});

test('loadParagonTokens: resolves a var() chain and a calc() expression to literals', () => {
  const { names } = loadParagonTokens(FIXTURE_DIR, { theme: 'light' });
  assert.equal(names.get('--pgn-color-primary-500').resolved, '#112233FF'); // 1-hop alias
  assert.equal(names.get('--pgn-color-bg-base').resolved, '#FFFFFFFF'); // theme-declared alias to a core primitive
  assert.equal(names.get('--pgn-spacing-spacer-1-5').resolved, '0.375rem'); // calc(1rem * .375)
});

test('loadParagonTokens: reads the description comment and the package version', () => {
  const { names, version } = loadParagonTokens(FIXTURE_DIR, { theme: 'light' });
  assert.equal(version, '9.9.9');
  assert.equal(names.get('--pgn-color-primary-base').description, 'Basic primary color.');
});

test('familyOf: extracts the --pgn-<family>- prefix', () => {
  assert.equal(familyOf('--pgn-color-primary-base'), 'color');
  assert.equal(familyOf('--pgn-typography-font-size-base'), 'typography');
  assert.equal(familyOf('not-a-pgn-var'), null);
});
