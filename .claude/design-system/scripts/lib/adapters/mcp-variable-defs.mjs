// Adapter for the official Figma MCP `get_variable_defs` tool's output shape:
// { variables: { "<name>": "<resolved value string>", ... } }. Classifies each entry as
// either a confirmation of an already-known catalog variable's value, or a style (legacy
// "💎 -" library style, or a local/legacy name with neither prefix). Used both to seed the
// v0 catalog's style half from the one captured frame (05) and, unchanged, by
// map-figma.mjs to check a live capture against the generated map.
//
// The classification is name-shape only, because get_variable_defs never returns a
// variable/style id or a remote/key flag (see policy.md's evidence matrix) — so "local
// style shadowing a library style of the same name" can only be *suspected* here, never
// confirmed. Confirming it needs the read-only use_figma audit script (not built for v0).

const LEGACY_PREFIX_RE = /^💎\s*-\s*/;

function stripLegacyPrefix(name) {
  return name.replace(LEGACY_PREFIX_RE, '').trim();
}

/** Parse one Figma MCP `Font(family: "...", style: ..., size: N, weight: N, lineHeight: N,
 * letterSpacing: N)` value string. Returns null if it doesn't match. */
function parseFont(value) {
  const m = /^Font\(family:\s*"([^"]+)",\s*style:\s*([^,]+),\s*size:\s*([\d.]+),\s*weight:\s*([\d.]+),\s*lineHeight:\s*([\d.]+),\s*letterSpacing:\s*([\d.]+)\)$/.exec(value);
  if (!m) return null;
  const [, family, style, size, weight, lineHeight, letterSpacing] = m;
  return {
    fontFamily: family,
    fontStyle: style.trim(),
    fontSize: Number(size),
    fontWeight: Number(weight),
    lineHeight: Number(lineHeight),
    letterSpacing: Number(letterSpacing),
  };
}

/** Parse one or more semicolon-separated `Effect(type: ..., color: #.., offset: (x, y),
 * radius: N, spread: N)` layers, in the order given (== rendering order; never reordered). */
function parseEffects(value) {
  const layers = [];
  const layerRe = /Effect\(type:\s*([A-Z_]+),\s*color:\s*(#[0-9a-fA-F]{6,8}),\s*offset:\s*\(([-\d.]+),\s*([-\d.]+)\),\s*radius:\s*([\d.]+),\s*spread:\s*([-\d.]+)\)/g;
  for (const m of value.matchAll(layerRe)) {
    const [, type, color, x, y, radius, spread] = m;
    layers.push({ type, color, offsetX: Number(x), offsetY: Number(y), radius: Number(radius), spread: Number(spread) });
  }
  return layers.length ? layers : null;
}

/**
 * @param {Record<string, string>} variableDefs - the raw `variables` map from get_variable_defs.
 * @param {Set<string>} knownVariableNames - exact-case variable names already in the catalog
 *   (e.g. "primary/base", "text/on-dark"). An entry whose stripped name exactly matches one of
 *   these is treated as a value confirmation, not a style.
 * @returns {{ confirmations: Array<{name, value}>, styles: Array<StyleRecord> }}
 */
export function parseVariableDefs(variableDefs, knownVariableNames) {
  const confirmations = [];
  const styles = [];

  for (const [rawName, value] of Object.entries(variableDefs)) {
    const isLegacyPrefixed = LEGACY_PREFIX_RE.test(rawName);
    const stripped = isLegacyPrefixed ? stripLegacyPrefix(rawName) : rawName;

    if (!isLegacyPrefixed && knownVariableNames.has(rawName)) {
      confirmations.push({ name: rawName, value });
      continue;
    }

    const font = parseFont(value);
    const effects = font ? null : parseEffects(value);
    const kind = font ? 'text' : effects ? 'effect' : 'paint';

    styles.push({
      name: stripped,
      rawName,
      kind,
      legacyLibraryStyle: isLegacyPrefixed,
      // A style with neither the library prefix nor a known-variable-shaped name is a
      // local/legacy artifact: possibly stale, possibly shadowing a library style/variable
      // of a similar name. Flag it; never resolve it silently.
      local: !isLegacyPrefixed,
      value: font ?? (effects ? { effects } : { hex: value }),
    });
  }

  return { confirmations, styles };
}
