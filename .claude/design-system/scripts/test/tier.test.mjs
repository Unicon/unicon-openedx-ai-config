import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildTierWords, isTierEligible } from '../lib/tier.mjs';

const catalogVariables = [
  { name: 'primary/base', collection: 'Primitives' },
  { name: 'gray/700', collection: 'Primitives' },
  { name: 'theme/bg/base', collection: 'Semantic' },
];
const collectionToFamily = { Primitives: 'color', Semantic: 'color' };

test('isTierEligible: a primitive/semantic-shaped token is eligible', () => {
  const words = buildTierWords(catalogVariables, collectionToFamily);
  assert.equal(isTierEligible('--pgn-color-primary-500', words), true);
  assert.equal(isTierEligible('--pgn-color-gray-700', words), true);
  assert.equal(isTierEligible('--pgn-color-theme-hover-primary', words), true);
  assert.equal(isTierEligible('--pgn-color-bg-base', words), true); // extra allowlist word "bg"
});

test('isTierEligible: a component-scoped token is excluded even though it shares the color family', () => {
  const words = buildTierWords(catalogVariables, collectionToFamily);
  assert.equal(isTierEligible('--pgn-color-btn-text-primary', words), false);
  assert.equal(isTierEligible('--pgn-color-badge-focus-dark', words), false);
});

test('isTierEligible: an unknown family (no catalog variables of that family) is excluded', () => {
  const words = buildTierWords(catalogVariables, collectionToFamily);
  assert.equal(isTierEligible('--pgn-elevation-box-shadow-1', words), false);
});
