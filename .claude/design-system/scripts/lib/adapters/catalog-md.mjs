// Adapter for the "DESIGN.md variables export" format: a Markdown file with one
// "### Collection: <Name>  ·  N variables  ·  modes: <modes>" section per Figma variable
// collection, each followed by a "| Variable | Type | <mode columns...> |" table.
//
// This is the bootstrap adapter (source of the v0 catalog). It is frozen once a real
// native DTCG export or use_figma export exists to replace it; see figma-dtcg.mjs /
// use-figma-json.mjs, not built yet.
import { readFileSync } from 'node:fs';

const COLLECTION_RE = /^### Collection: (.+?)\s+·\s+(\d+) variables?\s+·\s+modes: (.+)$/;

/** Parse one Markdown table row into cells, unescaping the leading/trailing pipes. */
function splitRow(line) {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  return trimmed.split('|').map((c) => c.trim());
}

/**
 * Parse a DESIGN.md variables export into a flat list of variable records:
 * { name, collection, type, mode, value, aliasOf }.
 * A cell of the form "→ var:foo/bar" becomes { aliasOf: "foo/bar" } instead of a value.
 * A `\`literal\`` cell has its backticks stripped. A bare quoted string (STRING type,
 * e.g. the Paragon Categories collection) keeps its content without the quotes.
 */
export function parseCatalogMd(filePath) {
  const text = readFileSync(filePath, 'utf8');
  const lines = text.split('\n');
  const variables = [];
  const collections = [];

  let current = null; // { name, count, modes: [] }
  let headerModes = null; // column names for the current table, after the fixed Variable/Type columns

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const collMatch = COLLECTION_RE.exec(line.trim());
    if (collMatch) {
      const [, name, count, modesStr] = collMatch;
      current = { name: name.trim(), count: Number(count), modes: modesStr.split(',').map((m) => m.trim()) };
      collections.push(current);
      headerModes = null;
      continue;
    }
    if (!current) continue;
    if (!line.trim().startsWith('|')) continue;

    const cells = splitRow(line);
    if (cells[0] === 'Variable') {
      headerModes = cells.slice(2); // everything after "Variable", "Type"
      continue;
    }
    if (/^-+$/.test(cells[0]?.replace(/[:\s]/g, '') ?? '')) continue; // the "|---|---|" separator row
    if (headerModes == null) continue;

    const [rawName, rawType, ...valueCells] = cells;
    if (!rawName) continue;
    const type = rawType.trim();

    valueCells.forEach((rawValue, idx) => {
      const mode = headerModes[idx] ?? current.modes[idx] ?? current.modes[0];
      const value = rawValue.trim();
      if (value === '' || value === '—') return;

      const aliasMatch = /^→\s*var:(.+)$/.exec(value);
      const record = { name: rawName.trim(), collection: current.name, type, mode };
      if (aliasMatch) {
        record.aliasOf = aliasMatch[1].trim();
      } else {
        const literal = /^`(.*)`$/.exec(value);
        const quoted = /^"(.*)"$/.exec(value);
        record.value = literal ? literal[1] : quoted ? quoted[1] : value;
        if (type === 'FLOAT' && record.value !== undefined) {
          const n = Number(record.value);
          if (!Number.isNaN(n)) record.value = n;
        }
      }
      variables.push(record);
    });
  }

  return { collections, variables };
}
