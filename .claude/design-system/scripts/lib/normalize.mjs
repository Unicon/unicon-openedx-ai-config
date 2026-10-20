// Zero-dependency value normalization: colors, lengths, and tolerance comparisons.
// Used by join.mjs to decide whether a Figma value and a Paragon token's resolved
// value are the same design decision, not just textually identical.

const ROOT_PX = 16; // Paragon's rem root.

/**
 * Normalize any CSS color-ish string to lowercase 8-digit hex (#rrggbbaa).
 * Returns null if the input isn't a recognized color (e.g. "inherit", "transparent",
 * "none", or a var()/calc() we didn't resolve).
 */
export function normalizeColor(input) {
  if (input == null) return null;
  const s = String(input).trim();

  let m = /^#([0-9a-fA-F]{8})$/.exec(s);
  if (m) return `#${m[1].toLowerCase()}`;

  m = /^#([0-9a-fA-F]{6})$/.exec(s);
  if (m) return `#${m[1].toLowerCase()}ff`;

  m = /^#([0-9a-fA-F]{3})$/.exec(s);
  if (m) {
    const [r, g, b] = m[1];
    return `#${r}${r}${g}${g}${b}${b}ff`.toLowerCase();
  }

  m = /^#([0-9a-fA-F]{4})$/.exec(s);
  if (m) {
    const [r, g, b, a] = m[1];
    return `#${r}${r}${g}${g}${b}${b}${a}${a}`.toLowerCase();
  }

  m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(s);
  if (m) {
    const [, r, g, b, a] = m;
    const hex = (n) => Math.round(Math.max(0, Math.min(255, Number(n)))).toString(16).padStart(2, '0');
    const alpha = a === undefined ? 255 : Math.round(Math.max(0, Math.min(1, Number(a))) * 255);
    return `#${hex(r)}${hex(g)}${hex(b)}${hex(alpha.toString(16).padStart(2, '0') !== undefined ? 0 : 0)}`
      .slice(0, 7) + alpha.toString(16).padStart(2, '0');
  }

  return null;
}

/** Parse a CSS length/number into { value: <px or unitless number>, unit }. Returns null if unparsable. */
export function parseLength(input) {
  if (input == null) return null;
  const s = String(input).trim();
  if (s === '') return null;

  let m = /^(-?[\d.]+)rem$/.exec(s);
  if (m) return { px: Number(m[1]) * ROOT_PX, unit: 'rem', raw: Number(m[1]) };

  m = /^(-?[\d.]+)em$/.exec(s);
  if (m) return { px: Number(m[1]) * ROOT_PX, unit: 'em', raw: Number(m[1]) };

  m = /^(-?[\d.]+)px$/.exec(s);
  if (m) return { px: Number(m[1]), unit: 'px', raw: Number(m[1]) };

  m = /^(-?[\d.]+)%$/.exec(s);
  if (m) return { px: null, unit: '%', raw: Number(m[1]) }; // relative; caller supplies a base

  // Bare number: could be a unitless line-height ratio or a plain FLOAT (spacer count, etc).
  m = /^-?[\d.]+$/.exec(s);
  if (m) return { px: null, unit: 'number', raw: Number(s) };

  return null;
}

/**
 * Compare a Figma FLOAT (raw px/number from the catalog) against a Paragon token's
 * resolved value, which may be expressed in rem, %, or a unitless ratio. `context`
 * says which assumption bridged them (the generator records this on the map entry).
 *
 * `basePx` is the font-size the comparison should treat "100%" or "ratio × " as relative
 * to (Paragon's body font-size for typography, or null when not applicable).
 */
export function compareLengths(figmaPx, codeValue, { basePx = null, tolerance = 0.05, roundTolerance = 0.5 } = {}) {
  const code = parseLength(codeValue);
  if (code == null || figmaPx == null) return { match: 'unparsable', codePx: null, context: null };

  let codePx = code.px;
  let context = null;

  if (codePx == null && code.unit === '%') {
    if (basePx == null) return { match: 'unparsable', codePx: null, context: 'percent-needs-base' };
    codePx = (code.raw / 100) * basePx;
    context = `${code.raw}% of ${basePx}px base`;
  } else if (codePx == null && code.unit === 'number') {
    if (basePx == null) {
      // A bare number with no base to scale against: compare as a plain number (e.g. a spacer count).
      codePx = code.raw;
    } else {
      codePx = code.raw * basePx;
      context = `ratio ${code.raw} × ${basePx}px base`;
    }
  }

  const delta = Math.abs(codePx - figmaPx);
  const match = delta <= tolerance ? 'equal' : delta <= roundTolerance ? 'rounded' : 'differs';
  return { match, codePx, delta, context };
}

/** Two colors: 'equal' or 'differs'. Colors are never "rounded". */
export function compareColors(figmaValue, codeValue) {
  const a = normalizeColor(figmaValue);
  const b = normalizeColor(codeValue);
  if (a == null || b == null) return { match: 'unparsable', a, b };
  return { match: a === b ? 'equal' : 'differs', a, b };
}

/** Evaluate a Paragon `calc(var(--x) * N)` / `calc(var(--x) + var(--y))` expression once every
 * var() inside has already been substituted with its resolved literal (by paragon-css.mjs). Only
 * handles scalar * and +/-, which is the entirety of what Paragon's own token CSS uses. Returns
 * null (never throws) on anything more complex, so the caller falls back to the raw string. */
export function evalSimpleCalc(expr) {
  const inner = /^calc\((.+)\)$/.exec(expr.trim());
  if (!inner) return null;
  const body = inner[1].trim();

  let m = /^([\d.]+(?:rem|px|em)?)\s*([*+-])\s*([\d.]+(?:rem|px|em)?)$/.exec(body);
  if (!m) return null;
  const [, leftRaw, op, rightRaw] = m;
  const left = parseLength(leftRaw) ?? { px: Number(leftRaw), unit: 'number', raw: Number(leftRaw) };
  const right = parseLength(rightRaw) ?? { px: Number(rightRaw), unit: 'number', raw: Number(rightRaw) };
  if (left.px == null && left.unit !== 'number') return null;

  if (op === '*') {
    const basePx = left.unit === 'number' ? right.px : left.px;
    const factor = left.unit === 'number' ? left.raw : right.raw;
    if (basePx == null) return null;
    const resultPx = basePx * factor;
    // Re-express in the same unit as the non-number operand, since that's how Paragon writes it.
    const unit = left.unit !== 'number' ? left.unit : right.unit;
    if (unit === 'rem') return `${round(resultPx / ROOT_PX)}rem`;
    if (unit === 'em') return `${round(resultPx / ROOT_PX)}em`;
    return `${round(resultPx)}px`;
  }
  if (op === '+' || op === '-') {
    if (left.px == null || right.px == null) return null;
    const resultPx = op === '+' ? left.px + right.px : left.px - right.px;
    const unit = left.unit !== 'number' ? left.unit : right.unit;
    if (unit === 'rem') return `${round(resultPx / ROOT_PX)}rem`;
    if (unit === 'em') return `${round(resultPx / ROOT_PX)}em`;
    return `${round(resultPx)}px`;
  }
  return null;
}

function round(n, places = 6) {
  const f = 10 ** places;
  return Math.round(n * f) / f;
}

export const ROOT_PX_DEFAULT = ROOT_PX;
