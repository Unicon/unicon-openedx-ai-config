import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCRIPT = join(HERE, '../generate.mjs');
const FIXTURE_PARAGON = join(HERE, 'fixtures/paragon');
const FIXTURE_SOURCE = join(HERE, 'fixtures/source-sample.json');

function run(outDir) {
  return spawnSync('node', [SCRIPT, '--paragon', FIXTURE_PARAGON, '--source-file', FIXTURE_SOURCE, '--out-dir', outDir], { encoding: 'utf8' });
}

test('generate: produces the expected status for each fixture variable and style', () => {
  const outDir = mkdtempSync(join(tmpdir(), 'design-system-golden-'));
  const r = run(outDir);
  assert.equal(r.status, 0, r.stderr);

  const map = JSON.parse(readFileSync(join(outDir, 'figma-paragon-map.json'), 'utf8'));
  const byName = Object.fromEntries(map.variables.map((v) => [v.figmaName, v]));

  assert.equal(byName['white'].status, 'exact');
  assert.equal(byName['primary/base'].status, 'exact');
  assert.equal(byName['primary/500'].status, 'exact');
  assert.equal(byName['brand/500'].status, 'figma-only'); // alias hop, candidate only (no --pgn-color-brand-500 token exists)
  assert.equal(byName['brand/500'].fallback, '--pgn-color-primary-base');
  assert.equal(byName['theme/bg/base'].status, 'renamed'); // hits the real, committed rename rule
  assert.equal(byName['theme/bg/base'].token, '--pgn-color-bg-base');
  assert.equal(byName['spacer/1-5'].status, 'exact');
  assert.equal(byName['border-radius/pill'].status, 'renamed');
  assert.equal(byName['border-radius/pill'].token, '--pgn-size-rounded-pill');

  const heading = map.textStyles.find((s) => s.figmaName === 'Heading/H1');
  assert.equal(heading.status, 'exact');

  // "Extras/Black" doesn't mechanically match (its name isn't "black"), so it resolves by
  // value match instead — a candidate, not an auto-picked token (see join.test.mjs).
  const black = map.paintStyles.find((s) => s.figmaName === 'Extras/Black');
  assert.ok(black.status === 'value-only' || black.status === 'ambiguous');
  assert.ok(black.candidates.includes('--pgn-color-black')); // serialized candidates are plain token-name strings
  assert.equal(black.token, null);

  const level1 = map.effectStyles.find((s) => s.figmaName === 'Level 1');
  assert.ok(level1.status === 'value-only' || level1.status === 'ambiguous');

  const navBar = map.components.find((c) => c.name === 'NavBar');
  assert.equal(navBar.status, 'renamed');
  const multiselect = map.components.find((c) => c.name === 'Multiselect');
  assert.equal(multiselect.status, 'no-equivalent');
  const button = map.components.find((c) => c.name === 'Button');
  assert.equal(button.status, 'exact');
});

test('generate: two runs against the same inputs produce byte-identical output (no timestamps)', () => {
  const dir1 = mkdtempSync(join(tmpdir(), 'design-system-det-1-'));
  const dir2 = mkdtempSync(join(tmpdir(), 'design-system-det-2-'));
  assert.equal(run(dir1).status, 0);
  assert.equal(run(dir2).status, 0);
  assert.equal(readFileSync(join(dir1, 'figma-paragon-map.json'), 'utf8'), readFileSync(join(dir2, 'figma-paragon-map.json'), 'utf8'));
  assert.equal(readFileSync(join(dir1, 'figma-paragon-map.md'), 'utf8'), readFileSync(join(dir2, 'figma-paragon-map.md'), 'utf8'));
});

test('generate --check: passes when nothing changed, fails when the committed file is stale', () => {
  const outDir = mkdtempSync(join(tmpdir(), 'design-system-check-'));
  assert.equal(run(outDir).status, 0);
  const check1 = spawnSync('node', [SCRIPT, '--paragon', FIXTURE_PARAGON, '--source-file', FIXTURE_SOURCE, '--out-dir', outDir, '--check'], { encoding: 'utf8' });
  assert.equal(check1.status, 0);

  const path = join(outDir, 'figma-paragon-map.json');
  const original = readFileSync(path, 'utf8');
  writeFileSync(path, original.replace('"exact"', '"tampered"'));
  const check2 = spawnSync('node', [SCRIPT, '--paragon', FIXTURE_PARAGON, '--source-file', FIXTURE_SOURCE, '--out-dir', outDir, '--check'], { encoding: 'utf8' });
  assert.equal(check2.status, 1);
  assert.match(check2.stderr, /STALE/);
});
