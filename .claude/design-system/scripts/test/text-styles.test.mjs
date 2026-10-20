import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { loadParagonTokens } from '../lib/paragon-css.mjs';
import { resolveTextTarget, compareTextStyle } from '../lib/text-styles.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE_DIR = join(HERE, 'fixtures/paragon');
const { names: tokens } = loadParagonTokens(FIXTURE_DIR, { theme: 'light' });

test('resolveTextTarget: heading line-height is a ratio of its OWN font-size, not the body font-size', () => {
  // headings-line-height 1.25 x font-size-h1-base (2.5rem = 40px) = 50px, not 1.25 x body (18px).
  const r = resolveTextTarget('Heading/H1', tokens);
  assert.equal(r.matched, true);
  assert.equal(r.fontSizePx, 40);
  assert.equal(r.lineHeightPx, 50);
});

test('resolveTextTarget: h5 vs an unrelated size is a real fontSize mismatch (heading-level drift stays visible)', () => {
  const r = resolveTextTarget('Heading/H5', tokens);
  const cmp = compareTextStyle({ fontSize: 20, lineHeight: 25, fontWeight: 700, fontFamily: 'Fixture Sans' }, r);
  assert.equal(cmp.fontSize, 'differs'); // fixture h5-base is 14px, Figma says 20px
});

test('resolveTextTarget: an unrecognized style name reports unmatched rather than guessing a target', () => {
  const r = resolveTextTarget('Something/Unknown', tokens);
  assert.equal(r.matched, false);
});

test('compareTextStyle: font-family kind compares mono vs sans, not exact family name', () => {
  const r = resolveTextTarget('Heading/H1', tokens); // headings-font-family: inherit -> font-family-base (sans)
  const cmp = compareTextStyle({ fontSize: 40, lineHeight: 50, fontWeight: 700, fontFamily: 'Inter' }, r);
  assert.equal(cmp.fontFamily, 'equal'); // both sans-serif-kind, despite different literal family names
});
