import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(HERE, '../check-tokens.mjs');
const FIXTURE_SRC = join(HERE, 'fixtures/sample-src');
const FIXTURE_PARAGON = join(HERE, 'fixtures/paragon');

test('check-tokens: exits 1 and reports an unknown var() reference plus a hardcoded hex', () => {
  const r = spawnSync('node', [SCRIPT, '--json', '--paragon', FIXTURE_PARAGON, FIXTURE_SRC], { encoding: 'utf8' });
  assert.equal(r.status, 1);
  const out = JSON.parse(r.stdout);
  const unknown = out.findings.find((f) => f.rule === 'unknown-token');
  assert.ok(unknown, 'expected an unknown-token finding');
  assert.equal(unknown.level, 'error');
  assert.match(unknown.detail, /does-not-exist-in-fixture/);

  const hardcoded = out.findings.find((f) => f.rule === 'hardcoded-color');
  assert.ok(hardcoded, 'expected a hardcoded-color finding');
  assert.equal(hardcoded.level, 'warning'); // warning by default, not --strict
});

test('check-tokens: --strict promotes hardcoded-color to an error', () => {
  const r = spawnSync('node', [SCRIPT, '--json', '--strict', '--paragon', FIXTURE_PARAGON, FIXTURE_SRC], { encoding: 'utf8' });
  const out = JSON.parse(r.stdout);
  const hardcoded = out.findings.find((f) => f.rule === 'hardcoded-color');
  assert.equal(hardcoded.level, 'error');
});

test('check-tokens: a valid var() reference produces no unknown-token finding', () => {
  const r = spawnSync('node', [SCRIPT, '--json', '--paragon', FIXTURE_PARAGON, FIXTURE_SRC], { encoding: 'utf8' });
  const out = JSON.parse(r.stdout);
  assert.ok(!out.findings.some((f) => f.rule === 'unknown-token' && f.detail.includes('--pgn-color-white')));
});
