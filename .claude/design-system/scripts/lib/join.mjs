// The resolver: for every Figma catalog variable and style, decides a map entry per the
// two-tier contract in policy.md. Join order: override -> rename rule -> mechanical name
// -> alias hop (candidate only) -> value match (candidate only) -> none. A "legacy SCSS
// name" hop is documented in policy.md as a later join step; it is not implemented in v0
// because no entry in the current catalog needs it to resolve (see generator essentials in
// the plan) and reproducing Paragon's own composite-token expansion to build that map
// safely, without executing package code, is real work with zero effect on today's output.
import { compareColors, compareLengths, parseLength } from './normalize.mjs';
import { isTierEligible } from './tier.mjs';

const COLLECTION_FAMILY = {
  Primitives: 'color',
  Semantic: 'color',
  Spacing: 'spacing',
  Typography: 'typography',
  Sizing: 'size',
};

export { COLLECTION_FAMILY };

const BODY_FONT_SIZE_TOKEN = '--pgn-typography-font-size-base';

function mechanicalTokenName(family, figmaName) {
  return `--pgn-${family}-${figmaName.replace(/\//g, '-')}`;
}

/** Resolve a font-size-family token to a px number, following one %-of-base hop if needed
 * (font-size-sm/xs are themselves declared as a percentage of font-size-base). Never scales
 * further than that one hop, which is all Paragon's own tokens need. */
function resolveFontSizePx(tokens, tokenName) {
  const entry = tokens.get(tokenName);
  if (!entry) return null;
  const parsed = parseLength(entry.resolved);
  if (!parsed) return null;
  if (parsed.px != null) return parsed.px;
  if (parsed.unit === '%') {
    const base = resolveFontSizePx(tokens, BODY_FONT_SIZE_TOKEN);
    return base != null ? (parsed.raw / 100) * base : null;
  }
  return null;
}

/** The px a Typography-collection FLOAT variable's code counterpart should be interpreted
 * relative to, when that counterpart is a bare unitless number (a line-height ratio) or a
 * percentage. Returns null for anything that isn't relative (font-weight, rem/px tokens,
 * font-size/h*, display sizes): those compare as literals with no scaling. */
function typographyBasisPx(figmaVar, tokens) {
  if (figmaVar.collection !== 'Typography') return null;
  if (/^font-weight\//.test(figmaVar.name)) return null; // never a ratio; handled as a literal below
  if (/^line-height\/lg$/.test(figmaVar.name)) return resolveFontSizePx(tokens, '--pgn-typography-font-size-lg');
  if (/^line-height\/sm$/.test(figmaVar.name)) return resolveFontSizePx(tokens, '--pgn-typography-font-size-sm');
  if (/^line-height\//.test(figmaVar.name)) return resolveFontSizePx(tokens, BODY_FONT_SIZE_TOKEN); // base, micro
  if (/^font-size\/(sm|xs)$/.test(figmaVar.name)) return resolveFontSizePx(tokens, BODY_FONT_SIZE_TOKEN);
  return null;
}

const FONT_WEIGHT_KEYWORDS = { lighter: 200, bolder: 800, normal: 400, bold: 700 };

function compareValue(figmaVar, resolvedValue, tokens) {
  if (figmaVar.type === 'COLOR') return compareColors(figmaVar.value, resolvedValue);
  if (figmaVar.type !== 'FLOAT') return { match: 'unparsable' };

  if (/^font-weight\//.test(figmaVar.name)) {
    const asNumber = Number.parseFloat(resolvedValue);
    const codeNumber = Number.isNaN(asNumber) ? FONT_WEIGHT_KEYWORDS[String(resolvedValue).trim()] : asNumber;
    if (codeNumber == null) return { match: 'unparsable', codePx: null };
    // A CSS keyword (lighter/bolder/normal/bold) is a different design decision than a
    // literal Figma number even when the keyword's usual meaning is the same number: it
    // computes relative to the parent's weight, not a fixed value. Never call it 'equal'.
    if (!Number.isNaN(asNumber)) {
      return { match: codeNumber === figmaVar.value ? 'equal' : 'differs', codePx: codeNumber };
    }
    return { match: 'differs', codePx: codeNumber, context: `code uses the CSS keyword "${resolvedValue}"` };
  }

  const basePx = typographyBasisPx(figmaVar, tokens);
  const result = compareLengths(figmaVar.value, resolvedValue, { basePx });
  // A code value that couldn't be parsed at all (unrelated string) is never silently "fine".
  if (result.match === 'unparsable') return { ...result, match: 'differs' };
  return result;
}

function buildConfirmed(figmaVar, tokenName, tokens, baseStatus, extra = {}) {
  const entry = tokens.get(tokenName);
  const cmp = compareValue(figmaVar, entry.resolved, tokens);
  const status = cmp.match === 'differs' ? 'value-differs' : baseStatus;
  return {
    figma: figmaVar, status, token: tokenName,
    codeValue: entry.resolved, valueMatch: cmp.match, delta: cmp.delta ?? null, context: cmp.context ?? null,
    ...extra,
  };
}

/** Rank alias/value-match candidates: prefer a token whose own name shares a word with the
 * Figma name (a weak proxy for "semantic twin"), then a shorter chain, then a shorter name. */
function rankCandidates(figmaName, candidates) {
  const words = figmaName.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  return candidates
    .map((c) => ({
      ...c,
      score: words.filter((w) => c.token.toLowerCase().includes(w)).length,
    }))
    .sort((a, b) => b.score - a.score || (a.chainLength ?? 0) - (b.chainLength ?? 0) || a.token.length - b.token.length);
}

/** Resolve one Figma variable record ({name, collection, type, value|aliasOf}) into a map entry. */
export function resolveVariable(figmaVar, { tokens, rules, overrides, tierWords }) {
  const overrideEntry = overrides.find((o) => o.kind === 'variable' && o.figma === figmaVar.name);
  if (overrideEntry) {
    if (overrideEntry.token === null) {
      return { figma: figmaVar, status: 'figma-only', override: true, reason: overrideEntry.reason, candidates: [] };
    }
    if (!tokens.has(overrideEntry.token)) {
      throw new Error(`overrides.json: "${figmaVar.name}" -> "${overrideEntry.token}" but that token doesn't exist in the installed Paragon`);
    }
    return buildConfirmed(figmaVar, overrideEntry.token, tokens, 'override', { reason: overrideEntry.reason, reviewer: overrideEntry.reviewer });
  }

  for (const rule of rules.renameRules ?? []) {
    const re = new RegExp(rule.pattern);
    if (!re.test(figmaVar.name)) continue;
    const tokenName = figmaVar.name.replace(re, rule.template);
    if (!tokens.has(tokenName)) {
      throw new Error(`rules.json rename rule "${rule.pattern}" matched "${figmaVar.name}" but target token "${tokenName}" doesn't exist`);
    }
    return buildConfirmed(figmaVar, tokenName, tokens, 'renamed', { rule: rule.pattern });
  }

  const family = COLLECTION_FAMILY[figmaVar.collection];
  if (family) {
    const mechanical = mechanicalTokenName(family, figmaVar.name);
    if (tokens.has(mechanical)) return buildConfirmed(figmaVar, mechanical, tokens, 'exact');
  }

  // Alias hop: candidate only, status stays figma-only. The fallback is what an agent
  // should actually use (see policy.md's runtime contract) when nothing else resolves it.
  if (figmaVar.aliasOf && family) {
    const aliasToken = mechanicalTokenName(family, figmaVar.aliasOf);
    if (tokens.has(aliasToken)) {
      const semanticCandidates = valueMatchCandidates(figmaVar, tokens, family, tierWords, { excludeToken: aliasToken });
      return {
        figma: figmaVar, status: 'figma-only', via: 'alias-hop', fallback: aliasToken,
        candidates: rankCandidates(figmaVar.name, semanticCandidates),
      };
    }
  }

  const candidates = rankCandidates(figmaVar.name, valueMatchCandidates(figmaVar, tokens, family, tierWords));
  if (candidates.length === 1) return { figma: figmaVar, status: 'value-only', candidates };
  if (candidates.length > 1) return { figma: figmaVar, status: 'ambiguous', candidates };
  return { figma: figmaVar, status: 'figma-only', candidates: [] };
}

/** Global/alias-tier tokens (never the ~1,800 component-scoped ones) whose resolved value
 * exactly equals the Figma value, restricted to the same family when known. Component tier
 * is excluded via `tierWords` (see tier.mjs), and `action-*` derived hover shades are
 * excluded because they're generated by Paragon's `modify` transform, not a design decision
 * to point at. */
function valueMatchCandidates(figmaVar, tokens, family, tierWords, { excludeToken } = {}) {
  const out = [];
  for (const [name, entry] of tokens) {
    if (name === excludeToken) continue;
    if (family && !name.startsWith(`--pgn-${family}-`)) continue;
    if (/^--pgn-[a-z]+-action-/.test(name)) continue;
    if (tierWords && !isTierEligible(name, tierWords)) continue;
    const cmp = compareValue(figmaVar, entry.resolved, tokens);
    if (cmp.match === 'equal') out.push({ token: name, chainLength: entry.chain?.length ?? 1 });
  }
  return out;
}

/** Resolve one style record from mcp-variable-defs.mjs (paint/text/effect) analogously to a
 * variable: strip the legacy prefix, try the variable-resolution path by treating the
 * stripped name as if it were a catalog color variable (this is exactly how a library
 * "💎 -" color style is meant to read: as a renamed pointer at the same primitive/semantic
 * variable), then fall back to value match against elevation/color tokens. Text styles are
 * resolved by resolveTextTarget/compareTextStyle instead (see generate.mjs). */
export function resolveColorStyle(style, { tokens, overrides, tierWords }) {
  const overrideEntry = overrides.find((o) => o.kind === 'style' && o.figma === style.rawName);
  if (overrideEntry) {
    if (overrideEntry.token === null) return { style, status: 'figma-only', override: true, reason: overrideEntry.reason, candidates: [] };
    return { style, status: 'override', token: overrideEntry.token, codeValue: tokens.get(overrideEntry.token)?.resolved, reason: overrideEntry.reason };
  }

  // A local/legacy style's name isn't confirmed to be the library style of the same name
  // (that needs the use_figma audit script's id/key check, not built in v0), so every local
  // result carries `note` regardless of status: an 'exact' name+value match here is strong
  // evidence, not proof, and 'value-differs' is a real, useful stale-color finding either way.
  const localNote = style.local
    ? 'local/legacy style name; not confirmed to be the library style of the same name (needs the use_figma audit script, not built in v0)'
    : undefined;

  const asVariable = { name: style.name.toLowerCase(), type: 'COLOR', value: style.value.hex, collection: 'Primitives' };
  const mechanical = mechanicalTokenName('color', asVariable.name);
  if (tokens.has(mechanical)) return { style, ...buildConfirmed(asVariable, mechanical, tokens, 'exact', { note: localNote }) };

  const candidates = rankCandidates(style.name, valueMatchCandidates(asVariable, tokens, 'color', tierWords));
  if (candidates.length >= 1) {
    return { style, status: candidates.length === 1 ? 'value-only' : 'ambiguous', candidates, note: localNote };
  }
  return { style, status: 'figma-only', candidates: [], note: localNote ?? 'no Paragon color matches this value' };
}

/** Effect (shadow) styles: compare the ordered layer list against `--pgn-elevation-box-shadow-*`
 * tokens, which Paragon documents as literal multi-layer box-shadow strings. Order is never
 * ignored: Figma effect order and CSS box-shadow order both paint first-declared-first
 * within a layer stack, so this compares layers positionally, not as a set. */
export function resolveEffectStyle(style, tokens) {
  const candidates = [];
  for (const [name, entry] of tokens) {
    if (!name.startsWith('--pgn-elevation-box-shadow-')) continue;
    const layers = parseCssBoxShadowLayers(entry.resolved);
    if (!layers) continue;
    if (layersMatch(style.value.effects, layers)) {
      candidates.push({ token: name, chainLength: entry.chain?.length ?? 1, layerOrder: 'same' });
    } else if (layers.length > 1 && layersMatch(style.value.effects, [...layers].reverse())) {
      // Paragon's own elevation tokens list shadow layers smallest-blur-first; Figma lists
      // this same effect largest-first. Both paint the identical set of non-overlapping,
      // same-color layers, so this is a real match, not a coincidence — but it's recorded
      // explicitly (never silently treated the same as an in-order match) per policy.md.
      candidates.push({ token: name, chainLength: entry.chain?.length ?? 1, layerOrder: 'reversed' });
    }
  }
  const ranked = rankCandidates(style.name, candidates);
  if (ranked.length === 1) return { style, status: 'value-only', candidates: ranked };
  if (ranked.length > 1) return { style, status: 'ambiguous', candidates: ranked };
  return { style, status: 'figma-only', candidates: [] };
}

const REM_PX = 16;

/** Parse one whitespace-separated length token ("0", "0.125rem", "4px") to px. Bare "0"
 * with no unit is valid CSS for a zero length and is the only unitless case that occurs. */
function lengthTokenToPx(tok) {
  if (tok === '0') return 0;
  const m = /^(-?[\d.]+)(px|rem)$/.exec(tok);
  if (!m) return null;
  return Number.parseFloat(m[1]) * (m[2] === 'rem' ? REM_PX : 1);
}

/** Paragon's box-shadow tokens resolve across several source lines (one var() per
 * component), so whitespace between components includes newlines; collapse it before
 * splitting a layer into tokens. Each layer is `x y blur [spread] color`, in that order,
 * with the color always last and spread always optional (never mistaken for a length: it is
 * whatever comes before the color once x/y/blur are accounted for). */
function parseCssBoxShadowLayers(value) {
  if (!value || typeof value !== 'string') return null;
  const layers = [];
  for (const part of splitTopLevelCommas(value)) {
    const tokens = part.trim().replace(/\s+/g, ' ').split(' ').filter(Boolean);
    const colorIdx = tokens.findIndex((t) => /^(rgba?\(|#[0-9a-fA-F]{3,8}$)/.test(t));
    if (colorIdx < 3) return null; // need at least x, y, blur before the color
    const color = tokens.slice(colorIdx).join(' '); // rgba(...) may itself contain spaces
    const lengths = tokens.slice(0, colorIdx).map(lengthTokenToPx);
    if (lengths.some((n) => n == null)) return null;
    const [offsetX, offsetY, radius, spread = 0] = lengths;
    layers.push({ offsetX, offsetY, radius, spread, color });
  }
  return layers.length ? layers : null;
}

function splitTopLevelCommas(value) {
  const parts = [];
  let depth = 0, start = 0;
  for (let i = 0; i < value.length; i++) {
    if (value[i] === '(') depth++;
    else if (value[i] === ')') depth--;
    else if (value[i] === ',' && depth === 0) { parts.push(value.slice(start, i)); start = i + 1; }
  }
  parts.push(value.slice(start));
  return parts;
}

function layersMatch(figmaLayers, cssLayers) {
  if (figmaLayers.length !== cssLayers.length) return false;
  return figmaLayers.every((f, i) => {
    const c = cssLayers[i];
    const near = (a, b) => Math.abs(a - b) <= 0.5;
    return near(f.offsetX, c.offsetX) && near(f.offsetY, c.offsetY) && near(f.radius, c.radius) && near(f.spread ?? 0, c.spread ?? 0);
  });
}
