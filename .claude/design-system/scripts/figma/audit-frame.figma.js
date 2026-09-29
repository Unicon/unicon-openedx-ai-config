// Read-only audit of one Figma node for paragon-design-check's sync-to-code mode. Runs
// through the Figma MCP `use_figma` tool; get the ready-to-run code from
// `node scripts/figma-script.mjs audit <node-id>`, which fills in the INPUT block below.
//
// Lists, for the designer's own layers under the node: unbound solid colors, unbound
// spacing and corner radii, text styles, paint styles, and bound variables. It never looks
// inside a component instance, because an instance's internals belong to its library
// component; instances are counted instead. It changes nothing in the file.
// @inject-start
const INPUT = { rootId: "" };
// @inject-end

const root = await figma.getNodeByIdAsync(INPUT.rootId);
if (!root) throw new Error(`Node ${INPUT.rootId} was not found in this file.`);
let page = root;
while (page && page.type !== "PAGE") page = page.parent;
if (page) await figma.setCurrentPageAsync(page);

const SPACING = ["itemSpacing", "counterAxisSpacing", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft"];
const RADII = ["topLeftRadius", "topRightRadius", "bottomLeftRadius", "bottomRightRadius"];
const hex = (c) => "#" + [c.r, c.g, c.b].map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("");

const out = {
  schema: "unicon.figma-audit/1",
  rootId: root.id, rootName: root.name, rootType: root.type,
  paints: [], numbers: [], textStyles: [], paintStyles: [], boundVariables: [],
  skipped: { instances: 0, mixedPaints: 0, nonSolidPaints: 0 },
};

const names = new Map();
const variableName = async (id) => {
  if (!names.has(id)) names.set(id, (await figma.variables.getVariableByIdAsync(id))?.name ?? null);
  return names.get(id);
};
const styleName = async (id) => {
  if (!names.has(id)) names.set(id, (await figma.getStyleByIdAsync(id))?.name ?? null);
  return names.get(id);
};

const visit = async (node) => {
  if (node.type === "INSTANCE") { out.skipped.instances++; return; }
  const base = { nodeId: node.id, nodeName: node.name };
  const bound = node.boundVariables ?? {};

  for (const field of ["fills", "strokes"]) {
    if (!(field in node)) continue;
    const styleField = field === "fills" ? "fillStyleId" : "strokeStyleId";
    const sid = node[styleField];
    if (typeof sid === "string" && sid) {
      out.paintStyles.push({ ...base, field, styleName: await styleName(sid) });
      continue;
    }
    const paints = node[field];
    if (paints === figma.mixed) { out.skipped.mixedPaints++; continue; }
    for (let index = 0; index < paints.length; index++) {
      const p = paints[index];
      if (p.visible === false) continue;
      if (p.type !== "SOLID") { out.skipped.nonSolidPaints++; continue; }
      if (p.boundVariables?.color) {
        out.boundVariables.push({ ...base, field: `${field}[${index}]`, variableName: await variableName(p.boundVariables.color.id) });
      } else {
        out.paints.push({ ...base, field, index, hex: hex(p.color), opacity: p.opacity ?? 1 });
      }
    }
  }

  if ("layoutMode" in node && node.layoutMode !== "NONE") {
    for (const field of SPACING) {
      if (field === "counterAxisSpacing" && node.layoutWrap !== "WRAP") continue;
      const value = node[field];
      if (typeof value === "number" && value !== 0 && !bound[field]) out.numbers.push({ ...base, field, value });
    }
  }
  if ("topLeftRadius" in node) {
    for (const field of RADII) {
      const value = node[field];
      if (typeof value === "number" && value !== 0 && !bound[field]) out.numbers.push({ ...base, field, value });
    }
  }
  for (const [field, binding] of Object.entries(bound)) {
    if (field === "fills" || field === "strokes") continue;
    for (const b of Array.isArray(binding) ? binding : [binding]) {
      if (b?.id) out.boundVariables.push({ ...base, field, variableName: await variableName(b.id) });
    }
  }

  if (node.type === "TEXT") {
    const sid = node.textStyleId;
    if (sid === figma.mixed) out.textStyles.push({ ...base, mixed: true });
    else out.textStyles.push({ ...base, styleName: sid ? await styleName(sid) : null });
  }

  if ("children" in node) for (const child of node.children) await visit(child);
};

await visit(root);
return out;
