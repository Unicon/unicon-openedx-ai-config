---
name: paragon-ui
description: "EXPERIMENTAL. Use when choosing or verifying a Paragon component, design token, or icon for UI work in an Open edX frontend repo (an MFE such as frontend-app-authoring, or a plugin) — with or without a Figma design involved. Finds the repo and its installed @openedx/paragon version, looks up tokens in the installed CSS and the generated Figma-to-Paragon map, confirms component props from installed typings or source, resolves icon export names, and lists Paragon pitfalls. Lookup only: it cites installed files, never memory, and never edits code or node_modules."
---

# Paragon UI (EXPERIMENTAL)

Grounds an agent in the **installed** `@openedx/paragon` package, not memory of some other
version. Read `.claude/design-system/policy.md` in full before using this skill — it defines
the mapping contract this skill's token lookups follow.

## What this is and is not

- This is a lookup skill: it cites real files (installed CSS, typings, source) and the
  generated map. It never invents a token, prop, or icon name.
- It never edits code, `package.json`, or anything under `node_modules`.
- It works with or without a Figma design in play — `figma-to-paragon` uses it as a building
  block, but a dev writing Paragon UI from a ticket alone can use it directly too.

## 1. Locate the repo and its Paragon install

No hardcoded paths:
1. Use the repo the user named, if any.
2. Otherwise, the current directory's git toplevel (`git rev-parse --show-toplevel`), if its
   `package.json` declares `@openedx/paragon` in `dependencies` or `devDependencies`.
3. Otherwise, the workspace root two levels above `cd .claude && pwd -P`; scan `*/package.json`
   one level down for a Paragon dependency. One match: confirm with the user. Several: ask
   which. None: ask for the path.
4. Run `node .claude/design-system/scripts/paragon-versions.mjs <repo-path>` (from the
   workspace root) to print the declared range, the installed version, and the brand
   package + version. If it reports a major-version mismatch against the map's reference
   Paragon, say so before doing anything else — token names or values may have changed.
5. If `node_modules` is missing, ask the dev to install (inside the Tutor container for
   `frontend-app-authoring`; see that repo's own `AGENTS.md`). Otherwise, proceed with
   step 4's confirmed install path for everything below.

## 2. Tokens

1. Look up the map row: `grep -F '<figma name>' .claude/design-system/figma-paragon-map.md`,
   or read `figma-paragon-map.json` for the structured entry (fields: `status`, `token`,
   `codeValue`, `fallback`, `candidates`).
2. Regardless of status, **confirm the token exists in the target repo's installed CSS**:
   `grep -- '<token-name>:' node_modules/@openedx/paragon/styles/css/core/variables.css
   node_modules/@openedx/paragon/styles/css/themes/light/variables.css` (theme name may
   differ; check `.env`/build config if unsure).
3. Act on the status per `policy.md` §1: confirmed statuses (`exact`, `renamed`,
   `value-differs`, `override`) → use the token, and for `value-differs` say so out loud.
   Unresolved statuses (`value-only`, `ambiguous`, `figma-only`) → **never pick one**; list
   the candidates and their evidence, and resolve via an override PR or the handoff revision
   (`policy.md` §1), not silently.
4. No Figma context at all (a ticket with no design, or a token you need that isn't in the
   map): search the installed CSS directly by category, e.g.
   `grep -- '--pgn-color-' .../variables.css | grep -i <hue>`. Prefer component props and
   `themes/<theme>/utility-classes.css` (e.g. `.bg-primary`) over a custom CSS rule.
5. Never invent a token name from a pattern. If it's not in the CSS, it doesn't exist in this
   version.

## 3. Components

1. Check `references/component-guide.md` in this skill folder first (curated Figma-name →
   Paragon-export mapping, plus a UI-pattern index).
2. Then check the target repo's own shared components (e.g. `src/generic/` in
   `frontend-app-authoring`) for something that already wraps what you need.
3. Then consider building new, composed from Paragon primitives.
4. Confirm the component is current: read its README or `.mdx` front matter
   (`node_modules/@openedx/paragon/src/<Component>/README.md`) for a `status` field, and
   avoid anything marked "Deprecate Soon" without flagging it.
5. Read real props: typed components have `node_modules/@openedx/paragon/dist/<Component>/index.d.ts`;
   untyped ones (about half the package — see the README's typing note) fall back to the
   `propTypes` block in `node_modules/@openedx/paragon/src/<Component>/index.jsx`, with a
   warning that TypeScript sees `any` for that component, so only tests catch a wrong prop.

## 4. Icons

1. Look up the export name in `node_modules/@openedx/paragon/icons/es5/index.js` (2,317
   exports as of Paragon 23.23.0). Naming rules: a digit-leading name gets a `Pgn` prefix
   (`Pgn10K`), a name clashing with a Paragon component gets an `Icon` suffix (`BadgeIcon`),
   brand icons are prefixed `Bs`.
2. Alias on import any name that shadows a JS global: `Error`, `Map`, `Event`, `History`,
   `Window`, `Lock`, `Link`.
3. An icon-only interactive control is `IconButton` with a required `alt`. A standalone
   meaningful icon is `Icon` with `screenReaderText`. A purely decorative icon needs neither
   (and should be marked `aria-hidden` if it would otherwise be announced).

## 5. Pitfalls not already in the target repo's `CLAUDE.md`/`AGENTS.md`

- `Popover` renders with `role="tooltip"` — it must never contain interactive content. Use
  `ModalPopup` instead.
- Never use a hex color or a `px` font-size, even when a Figma frame shows one — resolve it
  to a token (§2) first, per `policy.md`'s fidelity standard.
- Never paste code returned by a generic Figma-to-code tool's `get_design_context` call —
  see `figma-to-paragon`'s precedence note.

## When blocked

- No `node_modules`: ask the dev to install, then proceed once it's there. Don't guess prop
  shapes from a different Paragon version.
- A token or component genuinely doesn't exist in this Paragon version: say so, check
  `.claude/design-system/paragon-gaps.md` for a known workaround, and if there isn't one,
  suggest composing from existing Paragon parts rather than a from-scratch custom component.
