// Maps a Figma text style name to a Paragon typography target (an element/class, never a
// bare token) and computes that target's effective font-size/line-height/font-weight/
// font-family-kind from the resolved token map, so a text style's *base* (non-mobile,
// non-RTL) rendered values can be compared against Figma's.
//
// This intentionally does not parse Paragon's compiled CSS class rules generically: v0
// encodes the known token names each typography class reads, verified against Paragon
// 23.23.0's dist/core.css. A future revision could derive this from the CSS instead; see
// the "generator essentials" note in the plan.
import { compareLengths, parseLength } from './normalize.mjs';

const MONO_HINTS = ['monospace', 'mono', 'consolas', 'courier'];

/** Name-pattern rules, in priority order. First match wins. `target` names a row in
 * TARGETS below. Capture group $1 (size suffix) is used for heading-label pairing. */
const NAME_RULES = [
  { re: /^Heading\/H([1-6])$/i, target: (m) => `h${m[1]}` },
  { re: /^Display\/([1-4])$/i, target: (m) => `display-${m[1]}` },
  { re: /^Body\/(Default|Regular)$/i, target: () => 'body' },
  { re: /^Body\/(Large|Lead)$/i, target: () => 'lead' },
  { re: /^Body\/Small$/i, target: () => 'small' },
  { re: /^Body\/Extra ?Small$/i, target: () => 'x-small' },
  { re: /^Micro$/i, target: () => 'micro' },
  { re: /^Heading Label\/(.+)$/i, target: (m) => `heading-label:${m[1].trim().toLowerCase()}` },
];

/** Resolve a target key to { fontSizeToken, lineHeightToken|lineHeightValue, fontWeightToken|fontWeightValue,
 * fontFamilyToken|null, note }. Heading-label pairs get their size from the paired size target. */
function targetSpec(target) {
  const hMatch = /^h([1-6])$/.exec(target);
  if (hMatch) {
    return {
      fontSizeToken: `--pgn-typography-font-size-h${hMatch[1]}-base`,
      lineHeightToken: '--pgn-typography-headings-line-height',
      lineHeightBasis: 'own-size', // ratio × this target's own font-size, not the body size
      fontWeightToken: '--pgn-typography-headings-font-weight',
      fontFamilyToken: '--pgn-typography-headings-font-family',
      cssRef: `h${hMatch[1]}, .h${hMatch[1]}`,
    };
  }
  const dMatch = /^display-([1-4])$/.exec(target);
  if (dMatch) {
    return {
      fontSizeToken: `--pgn-typography-font-size-display-${dMatch[1]}`,
      lineHeightToken: '--pgn-typography-line-height-display-base',
      lineHeightBasis: 'own-size',
      fontWeightToken: `--pgn-typography-font-weight-display-${dMatch[1]}`,
      fontFamilyToken: null, // inherits body
      cssRef: `.display-${dMatch[1]}`,
    };
  }
  switch (target) {
    case 'body':
      return {
        fontSizeToken: '--pgn-typography-font-size-base', fontSizeIsBase: true,
        lineHeightToken: '--pgn-typography-line-height-base', lineHeightBasis: 'body-size',
        fontWeightToken: '--pgn-typography-font-weight-base',
        fontFamilyToken: '--pgn-typography-font-family-base',
        cssRef: 'body (no class; the document default)',
      };
    case 'lead':
      return {
        fontSizeToken: '--pgn-typography-font-size-lg',
        // .lead sets no line-height of its own; a unitless line-height inherits as a ratio
        // and is re-applied to each element's OWN font-size, never the body's font-size.
        lineHeightToken: '--pgn-typography-line-height-base', lineHeightBasis: 'own-size', lineHeightInherited: true,
        fontWeightToken: '--pgn-typography-font-weight-lead',
        fontFamilyToken: null,
        cssRef: '.lead',
      };
    case 'small':
      return {
        fontSizeToken: '--pgn-typography-font-size-sm', fontSizeIsBase: true,
        lineHeightToken: '--pgn-typography-line-height-base', lineHeightBasis: 'own-size', lineHeightInherited: true,
        fontWeightToken: '--pgn-typography-font-weight-normal',
        fontFamilyToken: null,
        cssRef: 'small, .small',
      };
    case 'x-small':
      return {
        fontSizeToken: '--pgn-typography-font-size-xs', fontSizeIsBase: true,
        lineHeightToken: '--pgn-typography-line-height-base', lineHeightBasis: 'own-size', lineHeightInherited: true,
        fontWeightToken: null,
        fontFamilyToken: null,
        cssRef: '.x-small',
      };
    case 'micro':
      return {
        fontSizeToken: '--pgn-typography-font-size-micro', fontSizeIsBase: true,
        lineHeightToken: '--pgn-typography-line-height-micro', lineHeightBasis: 'own-size',
        fontWeightLiteral: 'normal',
        fontFamilyToken: null,
        cssRef: '.micro',
      };
    default: {
      const labelMatch = /^heading-label:(.+)$/.exec(target);
      if (labelMatch) {
        const sizeTarget = { 'extra small': 'x-small', small: 'small', large: 'lead' }[labelMatch[1]] ?? 'x-small';
        const size = targetSpec(sizeTarget);
        return {
          ...size,
          fontFamilyToken: '--pgn-typography-font-family-monospace',
          cssRef: `.heading-label.${sizeTarget}`,
          note: `.heading-label pairs with .${sizeTarget} for size; text-transform: uppercase (no Figma equivalent tracked)`,
        };
      }
      return null;
    }
  }
}

function familyKind(resolvedValue) {
  if (resolvedValue == null) return 'unknown';
  const v = resolvedValue.toLowerCase();
  return MONO_HINTS.some((h) => v.includes(h)) ? 'monospace' : 'sans-serif';
}

/** @param {Map} tokens - the `.names` map from loadParagonTokens(). */
export function resolveTextTarget(figmaStyleName, tokens) {
  for (const rule of NAME_RULES) {
    const m = rule.re.exec(figmaStyleName.trim());
    if (!m) continue;
    const target = rule.target(m);
    const spec = targetSpec(target);
    if (!spec) return { matched: false, target };

    const fontSizeEntry = tokens.get(spec.fontSizeToken);
    const fontSizePx = fontSizeEntry
      ? (spec.fontSizeIsBase ? resolvePercentOrRatio(fontSizeEntry.resolved, tokens) : parseLength(fontSizeEntry.resolved)?.px)
      : null;

    const lineHeightEntry = spec.lineHeightToken ? tokens.get(spec.lineHeightToken) : null;
    let lineHeightPx = null;
    if (lineHeightEntry) {
      const basis = spec.lineHeightBasis === 'own-size' ? fontSizePx : (tokens.get('--pgn-typography-font-size-base') && resolvePercentOrRatio('100%', tokens));
      const parsed = parseLength(lineHeightEntry.resolved);
      lineHeightPx = parsed?.px ?? (basis != null ? basis * Number(lineHeightEntry.resolved) : null);
    }

    const fontWeight = spec.fontWeightLiteral
      ?? (spec.fontWeightToken ? tokens.get(spec.fontWeightToken)?.resolved : null)
      ?? (tokens.get('--pgn-typography-font-weight-base')?.resolved);

    const fontFamilyResolved = spec.fontFamilyToken
      ? resolveFontFamily(spec.fontFamilyToken, tokens)
      : resolveFontFamily('--pgn-typography-font-family-base', tokens);

    return {
      matched: true, target, cssRef: spec.cssRef, note: spec.note,
      fontSizePx, lineHeightPx, fontWeight: fontWeight != null ? Number(fontWeight) || fontWeight : null,
      fontFamilyKind: familyKind(fontFamilyResolved),
      tokens: { fontSizeToken: spec.fontSizeToken, lineHeightToken: spec.lineHeightToken, fontWeightToken: spec.fontWeightToken, fontFamilyToken: spec.fontFamilyToken },
    };
  }
  return { matched: false, target: null };
}

function resolvePercentOrRatio(rawOrPercent, tokens) {
  const parsed = parseLength(rawOrPercent);
  if (!parsed) return null;
  if (parsed.unit === '%') {
    const base = tokens.get('--pgn-typography-font-size-base');
    const basePx = base ? parseLength(base.resolved)?.px : null;
    return basePx != null ? (parsed.raw / 100) * basePx : null;
  }
  return parsed.px;
}

function resolveFontFamily(tokenName, tokens, depth = 0) {
  if (depth > 4) return null;
  const entry = tokens.get(tokenName);
  if (!entry) return null;
  if (entry.resolved === 'inherit') {
    // Paragon's own inheritance chain for headings/lead/etc bottoms out at the body family.
    return resolveFontFamily('--pgn-typography-font-family-base', tokens, depth + 1);
  }
  return entry.resolved;
}

/** Compare a parsed Figma Font(...) value (from mcp-variable-defs.mjs) against a resolved
 * text target. Returns { fontSize, lineHeight, fontWeight, fontFamily } each 'equal' | 'rounded' | 'differs' | 'unavailable'. */
export function compareTextStyle(figmaFont, resolvedTarget) {
  if (!resolvedTarget.matched) {
    return { fontSize: 'unavailable', lineHeight: 'unavailable', fontWeight: 'unavailable', fontFamily: 'unavailable' };
  }
  const fontSize = resolvedTarget.fontSizePx != null
    ? compareLengths(figmaFont.fontSize, `${resolvedTarget.fontSizePx}px`).match : 'unavailable';
  const lineHeight = resolvedTarget.lineHeightPx != null
    ? compareLengths(figmaFont.lineHeight, `${resolvedTarget.lineHeightPx}px`).match : 'unavailable';
  const codeWeight = resolvedTarget.fontWeight;
  const weightNum = typeof codeWeight === 'number' ? codeWeight : { normal: 400, bold: 700, lighter: 200, bolder: 800 }[codeWeight];
  const fontWeight = weightNum != null ? (weightNum === figmaFont.fontWeight ? 'equal' : 'differs') : 'unavailable';
  const fontFamily = resolvedTarget.fontFamilyKind !== 'unknown'
    ? (MONO_HINTS.some((h) => figmaFont.fontFamily.toLowerCase().includes(h)) === (resolvedTarget.fontFamilyKind === 'monospace') ? 'equal' : 'differs')
    : 'unavailable';
  return { fontSize, lineHeight, fontWeight, fontFamily };
}
