import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeColor, parseLength, compareLengths, compareColors, evalSimpleCalc } from '../lib/normalize.mjs';

test('normalizeColor: hex3/hex6/hex8 all fold to the same lowercase 8-digit form', () => {
  assert.equal(normalizeColor('#FFF'), '#ffffffff');
  assert.equal(normalizeColor('#ffffff'), '#ffffffff');
  assert.equal(normalizeColor('#FFFFFFFF'), '#ffffffff');
});

test('normalizeColor: rgba() converts alpha to a hex byte', () => {
  assert.equal(normalizeColor('rgba(0, 0, 0, 0.5)'), '#00000080');
  assert.equal(normalizeColor('rgb(255, 0, 0)'), '#ff0000ff');
});

test('normalizeColor: unrecognized input returns null, never a guess', () => {
  assert.equal(normalizeColor('inherit'), null);
  assert.equal(normalizeColor('var(--pgn-color-x)'), null);
});

test('parseLength: rem/px/em convert to px at the 16px root; % and bare numbers stay relative', () => {
  assert.equal(parseLength('1rem').px, 16);
  assert.equal(parseLength('0.375rem').px, 6);
  assert.equal(parseLength('24px').px, 24);
  assert.equal(parseLength('1em').px, 16);
  assert.equal(parseLength('87.5%').unit, '%');
  assert.equal(parseLength('87.5%').px, null);
  assert.equal(parseLength('1.5').unit, 'number');
});

test('compareLengths: equal within tolerance, rounded within the wider band, otherwise differs', () => {
  assert.equal(compareLengths(6, '0.375rem').match, 'equal');
  assert.equal(compareLengths(24, '1.5', { basePx: 15.75 }).match, 'rounded'); // 1.5*15.75=23.625, delta 0.375
  assert.equal(compareLengths(40, '32px').match, 'differs');
});

test('compareColors: equal ignores hex length/case; differs on a real value difference', () => {
  assert.equal(compareColors('#0a3055', '#0A3055FF').match, 'equal');
  assert.equal(compareColors('#00262b', '#0A3055FF').match, 'differs');
});

test('evalSimpleCalc: scalar multiplication and addition, re-expressed in the operand unit', () => {
  assert.equal(evalSimpleCalc('calc(1rem * .375)'), '0.375rem');
  assert.equal(evalSimpleCalc('calc(4px + 2px)'), '6px');
  assert.equal(evalSimpleCalc('calc(1rem / 2)'), null); // division isn't in Paragon's own calc()s; not implemented
});
