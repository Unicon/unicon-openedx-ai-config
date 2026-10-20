// Applies the changes a designer approved from a paragon-design-check sync-to-code plan.
// Runs through the Figma MCP `use_figma` tool; get the ready-to-run code from
// `node scripts/figma-script.mjs apply <plan.json> --approve ...`, which fills in the INPUT
// block below with only the approved changes.
//
// Every change is re-checked against the live file first and skipped, with a reason, when:
// the layer is gone or sits inside a component instance; it no longer holds the audited
// value (it was edited since the audit); the library variable can't be found by name, or its
// live value differs from the audited one; or the text style's key doesn't match its name.
// A skipped change never stops the others. Returns what was applied and what was skipped.
// @inject-start
const INPUT = { rootId: "", changes: [] };
// @inject-end

const root = await figma.getNodeByIdAsync(INPUT.rootId);
if (!root) throw new Error(`Node ${INPUT.rootId} was not found in this file.`);
let page = root;
while (page && page.type !== "PAGE") page = page.parent;
if (page) await figma.setCurrentPageAsync(page);

const hex = (c) => "#" + [c.r, c.g, c.b].map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
const applied = [];
const skipped = [];
const skip = (change, t, reason) => skipped.push({ id: change.id, nodeId: t?.nodeId ?? null, field: t?.field ?? null, reason });

const insideInstance = (node) => {
  for (let p = node.parent; p && p.type !== "PAGE"; p = p.parent) if (p.type === "INSTANCE") return true;
  return false;
};
const underRoot = (node) => {
  for (let n = node; n; n = n.parent) if (n.id === root.id) return true;
  return false;
};
const layer = async (change, t) => {
  const node = await figma.getNodeByIdAsync(t.nodeId);
  if (!node || node.removed) { skip(change, t, "layer not found"); return null; }
  if (!underRoot(node)) { skip(change, t, "layer is outside the audited node"); return null; }
  if (node.type === "INSTANCE" || insideInstance(node)) { skip(change, t, "layer is a component instance or inside one"); return null; }
  return node;
};

// Library variables by name, across every library attached to this file.
const byName = new Map();
if (INPUT.changes.some((c) => c.kind !== "swap-text-style")) {
  for (const col of await figma.teamLibrary.getAvailableLibraryVariableCollectionsAsync()) {
    for (const v of await figma.teamLibrary.getVariablesInLibraryCollectionAsync(col.key)) {
      if (!byName.has(v.name)) byName.set(v.name, []);
      byName.get(v.name).push({ key: v.key, library: col.libraryName });
    }
  }
}
const variableFor = async (name) => {
  const found = byName.get(name) ?? [];
  if (found.length === 0) return { error: `variable "${name}" is not in any attached library` };
  if (new Set(found.map((f) => f.library)).size > 1) return { error: `variable "${name}" exists in more than one attached library` };
  return { variable: await figma.variables.importVariableByKeyAsync(found[0].key) };
};

const WEIGHT_STYLE = { 100: "Thin", 200: "Extra Light", 300: "Light", 400: "Regular", 500: "Medium", 600: "Semi Bold", 700: "Bold", 800: "Extra Bold", 900: "Black" };

for (const change of INPUT.changes) {
  if (change.kind === "bind-color" || change.kind === "bind-number") {
    const { variable, error } = await variableFor(change.to);
    if (error) { for (const t of change.targets) skip(change, t, error); continue; }
    for (const t of change.targets) {
      try {
        const node = await layer(change, t);
        if (!node) continue;
        const live = variable.resolveForConsumer(node).value;
        if (change.kind === "bind-color") {
          const paints = node[t.field];
          const p = Array.isArray(paints) ? paints[t.index] : null;
          if (!p || p.type !== "SOLID" || p.boundVariables?.color || hex(p.color) !== change.from || (p.opacity ?? 1) !== 1) { skip(change, t, "layer no longer holds the audited color"); continue; }
          if (typeof live !== "object" || hex(live) !== change.from) { skip(change, t, `library value of "${change.to}" differs from ${change.from}`); continue; }
          const next = [...paints];
          next[t.index] = figma.variables.setBoundVariableForPaint(p, "color", variable);
          node[t.field] = next;
        } else {
          if (node.boundVariables?.[t.field] || typeof node[t.field] !== "number" || Math.abs(node[t.field] - change.from) > 0.01) { skip(change, t, "layer no longer holds the audited value"); continue; }
          if (typeof live !== "number" || Math.abs(live - change.from) > 0.01) { skip(change, t, `library value of "${change.to}" differs from ${change.from}`); continue; }
          node.setBoundVariable(t.field, variable);
        }
        applied.push({ id: change.id, nodeId: t.nodeId, field: t.field });
      } catch (e) { skip(change, t, e.message); }
    }
  } else if (change.kind === "swap-text-style") {
    let style;
    try { style = await figma.importStyleByKeyAsync(change.toKey); } catch (e) { for (const t of change.targets) skip(change, t, `style key did not import: ${e.message}`); continue; }
    if (style.name !== change.to) { for (const t of change.targets) skip(change, t, `style key is "${style.name}", expected "${change.to}"`); continue; }
    if (change.toFont) {
      try { await figma.loadFontAsync({ family: change.toFont.family, style: WEIGHT_STYLE[change.toFont.weight] ?? "Regular" }); } catch (e) { /* the per-layer swap below reports the failure */ }
    }
    for (const t of change.targets) {
      try {
        const node = await layer(change, t);
        if (!node) continue;
        const current = typeof node.textStyleId === "string" && node.textStyleId ? (await figma.getStyleByIdAsync(node.textStyleId))?.name : null;
        if (node.type !== "TEXT" || current !== change.from) { skip(change, t, "layer no longer uses the audited text style"); continue; }
        await Promise.all(node.getStyledTextSegments(["fontName"]).map((s) => figma.loadFontAsync(s.fontName)));
        await node.setTextStyleIdAsync(style.id);
        applied.push({ id: change.id, nodeId: t.nodeId });
      } catch (e) { skip(change, t, e.message); }
    }
  } else {
    skip(change, null, `unknown change kind "${change.kind}"`);
  }
}

return { rootId: root.id, appliedCount: applied.length, skippedCount: skipped.length, applied, skipped };
