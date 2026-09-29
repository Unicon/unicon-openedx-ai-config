// Builds paragon-design-check's sync-to-code proposal for one Figma node from a read-only
// audit (scripts/figma/audit-frame.figma.js). Every proposed change is decided by lookup in
// the committed map and catalog (policy.md §1), never by guessing:
//   - an unbound color or spacing/radius value is linked to the library variable with the
//     same value, only when exactly one confirmed variable has it;
//   - a text style whose value differs from code is switched to the style the map says
//     matches code for the same CSS target.
// Anything else is reported with where it goes (upstream gap, open design question, catalog
// refresh), never changed.
import { normalizeColor } from './normalize.mjs';

// Mirrors adapters/mcp-variable-defs.mjs: the Paragon library's older styles carry this prefix.
const LEGACY_PREFIX_RE = /^💎\s*-\s*/;
const LEGACY_PREFIX = '💎 - ';

// policy.md §1's confirmed tier. value-differs stays eligible: the variable's identity is
// real, so linking to it means the frame picks up the fix when the library is corrected.
const CONFIRMED = new Set(['exact', 'renamed', 'override', 'value-differs']);

const SPACING_FIELDS = new Set(['itemSpacing', 'counterAxisSpacing', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft']);
const RADIUS_FIELDS = new Set(['topLeftRadius', 'topRightRadius', 'bottomLeftRadius', 'bottomRightRadius']);
const FLOAT_TOLERANCE = 0.01;

function sixDigitHex(value) {
  const n = normalizeColor(value);
  return n ? n.slice(0, 7) : null;
}

function indexCatalog(catalog, mapByName) {
  const byName = new Map(catalog.variables.map((v) => [v.name, v]));
  const confirmed = (name) => CONFIRMED.has(mapByName.get(name)?.status);

  const terminal = (name, seen = new Set()) => {
    const v = byName.get(name);
    if (!v || seen.has(name)) return null;
    seen.add(name);
    return v.aliasOf ? terminal(v.aliasOf, seen) : v;
  };

  const primitivesByHex = new Map();
  const semanticByPrimitive = new Map();
  const floats = [];
  for (const v of catalog.variables) {
    if (v.type === 'COLOR' && v.collection === 'Primitives' && v.value != null && confirmed(v.name)) {
      const hex = sixDigitHex(v.value);
      if (hex) (primitivesByHex.get(hex) ?? primitivesByHex.set(hex, []).get(hex)).push(v.name);
    }
    if (v.type === 'COLOR' && v.collection === 'Semantic' && v.aliasOf && confirmed(v.name)) {
      const t = terminal(v.name);
      if (t) (semanticByPrimitive.get(t.name) ?? semanticByPrimitive.set(t.name, []).get(t.name)).push(v.name);
    }
    if (v.type === 'FLOAT' && typeof v.value === 'number' && confirmed(v.name)) floats.push(v);
  }
  return { primitivesByHex, semanticByPrimitive, floats };
}

function numberCandidates(floats, field, value) {
  const pool = SPACING_FIELDS.has(field)
    ? floats.filter((v) => v.collection === 'Spacing')
    : RADIUS_FIELDS.has(field)
      ? floats.filter((v) => v.collection === 'Sizing' && v.name.startsWith('border-radius/'))
      : [];
  return pool.filter((v) => Math.abs(v.value - value) <= FLOAT_TOLERANCE).map((v) => v.name);
}

function parseFont(figmaValue) {
  // Map textStyles figmaValue looks like "15.800000190734863px/24.5 400 Inter".
  const m = /^\S+\s+(\d+)\s+(.+)$/.exec(figmaValue ?? '');
  return m ? { weight: Number(m[1]), family: m[2] } : null;
}

function group(list, keyOf, init) {
  const groups = new Map();
  for (const entry of list) {
    const key = keyOf(entry);
    if (!groups.has(key)) groups.set(key, { ...init(entry), targets: [] });
    groups.get(key).targets.push(entry.target);
  }
  return [...groups.values()];
}

/**
 * Build a sync-to-code plan.
 *
 * :param audit: the object audit-frame.figma.js returns.
 * :param map: figma-paragon-map.json.
 * :param catalog: sources/<map.sourceId>.json.
 * :returns: ``{ schema, rootId, rootName, source, items, notes, summary }``. ``items`` are the
 *   only changes apply-sync.figma.js may make; each has a stable ``id`` (P1, P2, ...) and a
 *   ``status`` of ``proposed`` (one candidate) or ``ambiguous`` (the designer picks).
 */
export function buildSyncPlan(audit, { map, catalog }) {
  const mapByName = new Map(map.variables.map((v) => [v.figmaName, v]));
  const { primitivesByHex, semanticByPrimitive, floats } = indexCatalog(catalog, mapByName);
  const items = [];
  const notes = [];
  const target = (e, extra = {}) => ({ nodeId: e.nodeId, nodeName: e.nodeName, ...extra });

  // Colors
  const opaque = [];
  for (const p of audit.paints ?? []) {
    const hex = sixDigitHex(p.hex);
    if (!hex) continue;
    if ((p.opacity ?? 1) < 1) {
      notes.push({ kind: 'translucent-color', from: hex, target: target(p, { field: p.field, index: p.index }) });
      continue;
    }
    opaque.push({ hex, target: target(p, { field: p.field, index: p.index }) });
  }
  for (const g of group(opaque, (e) => e.hex, (e) => ({ from: e.hex }))) {
    const candidates = primitivesByHex.get(g.from) ?? [];
    if (candidates.length === 0) {
      notes.push({ kind: 'off-system-color', from: g.from, targets: g.targets });
      continue;
    }
    const alsoPossible = candidates.flatMap((c) => semanticByPrimitive.get(c) ?? []);
    items.push({
      kind: 'bind-color', from: g.from,
      status: candidates.length === 1 ? 'proposed' : 'ambiguous',
      to: candidates.length === 1 ? candidates[0] : null,
      candidates, alsoPossible, targets: g.targets,
    });
  }

  // Spacing and corner radii
  const numbers = (audit.numbers ?? [])
    .filter((n) => SPACING_FIELDS.has(n.field) || RADIUS_FIELDS.has(n.field))
    .map((n) => ({ ...n, groupName: SPACING_FIELDS.has(n.field) ? 'spacing' : 'radius', target: target(n, { field: n.field }) }));
  for (const g of group(numbers, (e) => `${e.groupName}|${e.value}`, (e) => ({ group: e.groupName, from: e.value, sampleField: e.field }))) {
    const candidates = numberCandidates(floats, g.sampleField, g.from);
    const { sampleField, ...rest } = g;
    if (candidates.length === 0) {
      notes.push({ kind: 'number-no-variable', ...rest });
      continue;
    }
    items.push({
      kind: 'bind-number', ...rest,
      status: candidates.length === 1 ? 'proposed' : 'ambiguous',
      to: candidates.length === 1 ? candidates[0] : null,
      candidates,
    });
  }

  // Text styles
  const swaps = [];
  for (const t of audit.textStyles ?? []) {
    const tgt = target(t);
    if (t.mixed) { notes.push({ kind: 'mixed-text-styles', target: tgt }); continue; }
    if (!t.styleName) { notes.push({ kind: 'unstyled-text', target: tgt }); continue; }
    const legacy = LEGACY_PREFIX_RE.test(t.styleName);
    const name = t.styleName.replace(LEGACY_PREFIX_RE, '').trim();
    const entry = map.textStyles.find((s) => s.figmaName === name && (s.legacyLibraryStyle ?? false) === legacy);
    if (!entry) { notes.push({ kind: 'text-style-not-in-map', from: t.styleName, target: tgt }); continue; }
    if (entry.status === 'exact') continue;
    const match = entry.status === 'value-differs'
      ? map.textStyles.find((s) => s.target === entry.target && s.status === 'exact')
      : null;
    if (!match) {
      notes.push({ kind: 'text-style-differs-no-match', from: t.styleName, figmaValue: entry.figmaValue, codeValue: entry.codeValue, target: tgt });
      continue;
    }
    swaps.push({
      from: t.styleName,
      to: match.legacyLibraryStyle ? `${LEGACY_PREFIX}${match.figmaName}` : match.figmaName,
      toFont: parseFont(match.figmaValue),
      cssRef: entry.cssRef, fromValue: entry.figmaValue, codeValue: entry.codeValue, toValue: match.figmaValue,
      target: tgt,
    });
  }
  for (const g of group(swaps, (e) => `${e.from}|${e.to}`, ({ target: _, ...rest }) => rest)) {
    items.push({ kind: 'swap-text-style', status: 'proposed', ...g });
  }

  // Paint styles and bound variables: reported only; nothing in a frame can fix them.
  for (const s of audit.paintStyles ?? []) {
    const legacy = LEGACY_PREFIX_RE.test(s.styleName);
    const name = s.styleName.replace(LEGACY_PREFIX_RE, '').trim();
    const entry = map.paintStyles.find((x) => x.figmaName === name && (x.legacyLibraryStyle ?? false) === legacy);
    if (!entry) notes.push({ kind: 'paint-style-not-in-map', from: s.styleName, target: target(s, { field: s.field }) });
    else if (entry.status !== 'exact') notes.push({ kind: `paint-style-${entry.status}`, from: s.styleName, target: target(s, { field: s.field }) });
  }
  for (const b of audit.boundVariables ?? []) {
    const entry = mapByName.get(b.variableName);
    const tgt = target(b, { field: b.field });
    if (!entry) notes.push({ kind: 'bound-variable-not-in-map', from: b.variableName, target: tgt });
    else if (entry.status === 'value-differs') notes.push({ kind: 'bound-variable-value-differs', from: b.variableName, figmaValue: entry.figmaValue, codeValue: entry.codeValue, token: entry.token, target: tgt });
    else if (!CONFIRMED.has(entry.status)) notes.push({ kind: `bound-variable-${entry.status}`, from: b.variableName, target: tgt });
  }

  items.forEach((item, i) => { item.id = `P${i + 1}`; });

  const noteGroups = new Map();
  for (const { target: one, targets: many, ...rest } of notes) {
    const key = `${rest.kind}|${rest.from ?? ''}`;
    if (!noteGroups.has(key)) noteGroups.set(key, { ...rest, targets: [] });
    noteGroups.get(key).targets.push(...(many ?? [one]));
  }
  const groupedNotes = [...noteGroups.values()];

  return {
    schema: 'unicon.sync-plan/1',
    rootId: audit.rootId,
    rootName: audit.rootName,
    source: { map: map.sourceId, paragonVersion: map.paragonVersion },
    items,
    notes: groupedNotes,
    summary: {
      proposed: items.filter((i) => i.status === 'proposed').length,
      ambiguous: items.filter((i) => i.status === 'ambiguous').length,
      layersAffected: items.reduce((n, i) => n + i.targets.length, 0),
      reported: groupedNotes.length,
      instancesNotAudited: audit.skipped?.instances ?? 0,
    },
  };
}

const NOTE_ROUTING = {
  'off-system-color': ['No Paragon variable has this color.', 'Figma issue (code wins): pick a Paragon color or ask the designer why it differs.'],
  'translucent-color': ['A color with opacity below 100%; opacity is not a token.', 'Designer: confirm the intent; Paragon usually uses a separate color instead.'],
  'number-no-variable': ['No Paragon spacing or radius variable has this value.', 'Figma issue (code wins): snap to a Paragon step, or record why not.'],
  'unstyled-text': ['Text with no text style.', 'Designer: apply the Paragon style that matches code.'],
  'mixed-text-styles': ['One text layer uses several text styles.', 'Designer: check each run; this mode only swaps whole-layer styles.'],
  'text-style-not-in-map': ['This text style is not in the catalog (styles were captured from one frame only).', 'Unverified: refresh the catalog before trusting it either way.'],
  'text-style-differs-no-match': ['This style differs from code, and no style in the catalog matches code.', 'Upstream: add a row to paragon-gaps.md.'],
  'bound-variable-not-in-map': ['A variable that is not in the committed map.', 'Catalog drift, or a local variable: refresh the catalog, or replace it with a Paragon variable.'],
  'bound-variable-value-differs': ["The library variable's own value differs from code.", 'Upstream: the Paragon Figma library needs the fix (paragon-gaps.md), not this frame.'],
  'bound-variable-figma-only': ['A Figma-only variable with no Paragon token.', 'Open design question (policy.md §1).'],
  'bound-variable-ambiguous': ['A variable the map matches to more than one Paragon token.', 'Open design question: the designer confirms the intended token.'],
  'bound-variable-value-only': ['A variable the map matches to a Paragon token by value only.', 'Open design question: the designer confirms the token.'],
  'paint-style-not-in-map': ['A paint style that is not in the catalog.', 'Unverified: refresh the catalog.'],
  'paint-style-ambiguous': ['A paint style that matches more than one Paragon token.', 'Open design question: the designer picks the intended token, then replaces the style with that variable.'],
  'paint-style-value-only': ['A paint style that matches a Paragon token by value only.', 'Open design question: the designer confirms the token.'],
  'paint-style-value-differs': ["A paint style whose value differs from code.", 'Upstream if it is a library style (paragon-gaps.md); otherwise replace it with the Paragon variable.'],
  'paint-style-figma-only': ['A paint style with no Paragon token.', 'Open design question (policy.md §1).'],
};

// Map values carry raw float noise from Figma and computed CSS (24.500700000000002).
const tidy = (s) => String(s ?? '').replace(/\d+\.\d{3,}/g, (m) => String(Number(Number(m).toFixed(2))));

function describeItem(item) {
  if (item.kind === 'bind-color') {
    const also = item.alsoPossible.length ? ` Semantic names for the same value: ${item.alsoPossible.map((n) => `\`${n}\``).join(', ')}.` : '';
    return item.status === 'proposed'
      ? [`Link ${item.from} to \`${item.to}\``, `Same value as the library variable, so nothing changes visually; the layer follows Paragon from now on.${also}`]
      : [`Pick one: link ${item.from} to ${item.candidates.map((c) => `\`${c}\``).join(' or ')}`, `Several library variables have exactly this value, so the plan can't choose.${also}`];
  }
  if (item.kind === 'bind-number') {
    return item.status === 'proposed'
      ? [`Link ${item.group} ${item.from} to \`${item.to}\``, 'Same value as the library variable, so nothing changes visually.']
      : [`Pick one: link ${item.group} ${item.from} to ${item.candidates.map((c) => `\`${c}\``).join(' or ')}`, 'Several library variables have exactly this value.'];
  }
  return [
    `Switch text style \`${item.from}\` to \`${item.to}\``,
    `\`${item.from}\` is ${tidy(item.fromValue)}, but code's \`${item.cssRef}\` is ${tidy(item.codeValue)}. \`${item.to}\` (${tidy(item.toValue)}) matches code. **This changes how the text looks.**`,
  ];
}

/** Render a plan as the Markdown table the designer approves from. */
export function renderPlanMarkdown(plan) {
  const lines = [
    `## sync-to-code proposal: ${plan.rootName} (\`${plan.rootId}\`)`,
    '',
    `Map \`${plan.source.map}\`, Paragon ${plan.source.paragonVersion}. Nothing below has been applied yet.`,
    `${plan.summary.proposed} proposed and ${plan.summary.ambiguous} needing a pick, across ${plan.summary.layersAffected} layers. ${plan.summary.instancesNotAudited} component instances were not audited (their internals belong to the library component).`,
    '',
    '### Changes you can approve',
    '',
  ];
  if (plan.items.length === 0) lines.push('None.');
  else {
    lines.push('| ID | Change | Layers | Why |', '|---|---|---|---|');
    for (const item of plan.items) {
      const [change, why] = describeItem(item);
      lines.push(`| ${item.id} | ${change} | ${item.targets.length} | ${why} |`);
    }
  }
  lines.push('', '### Reported, not changed', '');
  if (plan.notes.length === 0) lines.push('None.');
  else {
    lines.push('| Finding | Value | Layers | Where it goes |', '|---|---|---|---|');
    for (const n of plan.notes) {
      const [what, where] = NOTE_ROUTING[n.kind] ?? [`${n.kind}.`, 'Review by hand.'];
      const value = n.kind === 'bound-variable-value-differs' ? `\`${n.from}\`: Figma ${tidy(n.figmaValue)}, code ${tidy(n.codeValue)}` : n.from != null ? `\`${n.from}\`` : '';
      lines.push(`| ${what} | ${value} | ${n.targets.length} | ${where} |`);
    }
  }
  return lines.join('\n');
}
