// Distinguishes global/alias-tier Paragon tokens (candidates worth offering for a value
// match, and worth listing in the reverse index) from the ~1,800 component-scoped tokens
// (--pgn-color-btn-text-primary, --pgn-color-badge-focus-dark, ...), which happen to share
// literal values with primitives constantly (white/black especially) and would otherwise
// flood every ambiguous-color report.
//
// The "first segment after the family prefix" of every global/alias/semantic word is
// derived straight from the catalog's own Primitives/Semantic/Spacing/Typography/Sizing
// variable names (e.g. "primary/500" -> "primary", "theme/bg/base" -> "theme"), since
// Paragon's own token convention always puts the semantic word first for a global token and
// the component name first for a component token ("btn-text-primary", never
// "primary-btn-text"). A small extra allowlist covers semantic tokens that exist in code but
// aren't literal Figma variables (bg-base, body-base, text-muted, ...). This is a v0
// heuristic, not a structural read of tokens/src's core/global vs core/components
// directories (see generate.mjs's note); it is good enough for every case in the current
// catalog and documented as a known simplification to revisit.
const EXTRA_WORDS = {
  color: ['bg', 'body', 'headings', 'text', 'yiq', 'link', 'disabled', 'focus', 'border', 'active'],
  spacing: ['spacer', 'grid'],
  typography: ['font', 'line'],
  size: ['border', 'rounded', 'container', 'icon', 'avatar'],
};

export function buildTierWords(catalogVariables, collectionToFamily) {
  const byFamily = {};
  for (const v of catalogVariables) {
    const family = collectionToFamily[v.collection];
    if (!family) continue;
    const firstSegment = v.name.split('/')[0];
    (byFamily[family] ??= new Set()).add(firstSegment);
  }
  for (const [family, words] of Object.entries(EXTRA_WORDS)) {
    for (const w of words) (byFamily[family] ??= new Set()).add(w);
  }
  return byFamily;
}

export function isTierEligible(tokenName, tierWords) {
  const m = /^--pgn-([a-z]+)-(.+)$/.exec(tokenName);
  if (!m) return false;
  const [, family, rest] = m;
  const words = tierWords[family];
  if (!words) return false;
  return words.has(rest.split('-')[0]) || words.has(rest);
}
