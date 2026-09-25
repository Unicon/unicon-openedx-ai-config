// Reads the installed @openedx/paragon package's top-level export list from `src/index.ts`
// (shipped in the npm package, and the one file that lists every export, typed or not —
// dist/index.d.ts only covers the ~46 typed ones). Used to confirm a component name exists
// before recommending it, and to resolve the Figma "Paragon Categories" component lists
// against real exports.
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const EXPORT_BLOCK_RE = /export\s*\{([^}]+)\}\s*from\s*['"][^'"]+['"]/g;

/** @returns {Set<string>} every top-level named export from @openedx/paragon (e.g. "Button",
 * "IconButtonWithTooltip", "FormAutosuggest"). Dotted subcomponents (Form.Control) are not
 * separate exports in this list; see KNOWN_SUBCOMPONENTS below for those. */
export function loadParagonExports(paragonDir) {
  const path = join(paragonDir, 'src/index.ts');
  if (!existsSync(path)) return null; // older/newer Paragon that doesn't ship src/; caller falls back to dist/index.d.ts
  const text = readFileSync(path, 'utf8');
  const names = new Set();
  for (const m of text.matchAll(EXPORT_BLOCK_RE)) {
    for (const spec of m[1].split(',')) {
      const s = spec.trim();
      if (!s) continue;
      const asMatch = /\bas\s+([A-Za-z0-9_]+)/.exec(s);
      const name = asMatch ? asMatch[1] : /^([A-Za-z0-9_]+)/.exec(s)?.[1];
      if (name && /^[A-Z]/.test(name)) names.add(name); // skip lowercase helpers/hooks/consts
    }
  }
  return names;
}

/** Figma "Paragon Categories" component names that are exported under a different name, or
 * as a Form.* subcomponent rather than a top-level export. Curated from the Paragon
 * Categories variable list against Paragon 23.23.0's real exports (2026-09-25). */
export const COMPONENT_RENAMES = {
  NavBar: 'Navbar',
  Breadcrumbs: 'Breadcrumb',
  Autosuggest: 'FormAutosuggest',
  Checkbox: 'CheckboxControl, or FormCheck for one item in a set (via Form; see Form/README.md)',
  Radio: 'RadioControl, or FormRadio / FormRadioSet for a set (via Form)',
  Switch: 'SwitchControl, or FormSwitchSet for a set (via Form)',
  Modal: 'ModalDialog',
  'Input.Inline': 'FormControl inline variant (via Form)',
  Input: 'FormControl (via Form)',
  'Form.Control': 'FormControl (via Form)',
  'Form.Control.Feedback': 'FormControlFeedback (via Form)',
  'Form.Group': 'FormGroup (via Form)',
  'Form.Label': 'FormLabel (via Form)',
  'IconButton.Toggle': 'IconButtonToggle',
};

/** Figma component names with no Paragon equivalent at all, as of 23.23.0. Each should have
 * a matching row in paragon-gaps.md. */
export const COMPONENT_NO_EQUIVALENT = new Set(['Multiselect', 'ContentBlockEmpty', 'ContentBlockError']);

/** Resolve one Figma component name from the "Paragon Categories" lists to a status. */
export function resolveComponentName(figmaName, exportsSet) {
  if (exportsSet?.has(figmaName)) return { name: figmaName, status: 'exact' };
  if (COMPONENT_RENAMES[figmaName]) return { name: figmaName, status: 'renamed', resolvesTo: COMPONENT_RENAMES[figmaName] };
  if (COMPONENT_NO_EQUIVALENT.has(figmaName)) return { name: figmaName, status: 'no-equivalent' };
  return { name: figmaName, status: exportsSet ? 'unknown' : 'unverified' };
}
