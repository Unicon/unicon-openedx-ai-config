// Fills in the INPUT block of a committed scripts/figma/*.figma.js file, so the code an agent
// runs through `use_figma` is exactly the committed script with only that one line changed.
// Also turns a designer's approvals into the apply script's input, refusing anything the
// plan didn't propose.

const BLOCK_RE = /\/\/ @inject-start\n[\s\S]*?\n\/\/ @inject-end/;
const PLAIN_NODE_ID = /^\d+:\d+$/;
const STYLE_KEY = /^[0-9a-f]{40}$/;

export function normalizeNodeId(raw) {
  const id = String(raw ?? '').trim().replace('-', ':');
  if (!PLAIN_NODE_ID.test(id)) {
    throw new Error(`"${raw}" is not a plain Figma node id (like 123:456). Instance sublayer ids aren't accepted.`);
  }
  return id;
}

export function injectInput(source, input) {
  if (!BLOCK_RE.test(source)) throw new Error('Script has no "// @inject-start ... // @inject-end" block.');
  return source.replace(BLOCK_RE, `// @inject-start\nconst INPUT = ${JSON.stringify(input)};\n// @inject-end`);
}

/**
 * Build apply-sync.figma.js's INPUT from a plan and the designer's approvals.
 *
 * :param plan: the object buildSyncPlan returned (plan.json).
 * :param approve: item ids the designer approved, e.g. ``['P1', 'P3']``.
 * :param picks: ``{ P2: 'gray/700' }``, one candidate per approved ambiguous item.
 * :param styleKeys: ``{ '💎 - Body/Small': '<40-hex key>' }``, for approved text-style swaps.
 * :raises Error: on an id the plan doesn't have, an ambiguous item without a valid pick, a
 *   text-style swap without a key, or a target that isn't a plain node id.
 */
export function buildApplyInput(plan, { approve, picks = {}, styleKeys = {} }) {
  if (!approve?.length) throw new Error('Nothing approved: pass --approve with one or more plan ids.');
  const byId = new Map(plan.items.map((i) => [i.id, i]));
  for (const id of Object.keys(picks)) {
    if (!approve.includes(id)) throw new Error(`--pick ${id} was given, but ${id} isn't in --approve.`);
  }

  const changes = approve.map((id) => {
    const item = byId.get(id);
    if (!item) throw new Error(`${id} is not in this plan.`);
    let to = item.to;
    if (item.status === 'ambiguous') {
      const allowed = [...item.candidates, ...(item.alsoPossible ?? [])];
      if (!picks[id]) throw new Error(`${id} needs --pick ${id}=<one of: ${allowed.join(', ')}>.`);
      if (!allowed.includes(picks[id])) throw new Error(`${id}: "${picks[id]}" isn't one of: ${allowed.join(', ')}.`);
      to = picks[id];
    }
    const change = {
      id, kind: item.kind, from: item.from, to,
      targets: item.targets.map((t) => ({ nodeId: normalizeNodeId(t.nodeId), ...(t.field ? { field: t.field } : {}), ...(t.index != null ? { index: t.index } : {}) })),
    };
    if (item.kind === 'swap-text-style') {
      const key = styleKeys[item.to];
      if (!key) throw new Error(`${id} needs --style-key "${item.to}=<key>" (look the key up with the Figma MCP's search_design_system).`);
      if (!STYLE_KEY.test(key)) throw new Error(`${id}: "${key}" doesn't look like a Figma style key (40 hex characters).`);
      change.toKey = key;
      change.toFont = item.toFont;
    }
    return change;
  });

  return { rootId: normalizeNodeId(plan.rootId), changes };
}
