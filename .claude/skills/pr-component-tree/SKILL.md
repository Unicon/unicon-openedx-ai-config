---
name: pr-component-tree
description: Use when asked for a visual map of which React components a frontend pull request changed, how the changes sit in each page's component hierarchy, or what a PR touches before reviewing it. Also the first step of frontend-code-review. For React/JSX repositories such as frontend-app-authoring.
---

# PR component tree

Turns a frontend PR into a Markdown file with one inline SVG: a component tree per page, going
down the JSX from the page component. Edited components are red, new ones solid red, unchanged
ones grey, with a note next to each changed component saying what changed. Changed non-React
modules (data hooks, API clients, types, utils, messages, styles) appear as plain grey text under
the component that calls them.

The analysis is yours; the drawing is deterministic. You write a JSON spec, and
`scripts/render_component_tree.py` renders it. Never hand-write SVG.

## Steps

**1. Pin the PR (top-level session).** `gh pr view <pr> --json title,headRefOid,files` and
`gh pr diff`. Read the source at the PR's head SHA: use the local checkout only if
`git rev-parse HEAD` equals `headRefOid`, otherwise a temporary worktree of the PR head. Never
change the developer's checkout.

**2 to 5 are reading and reasoning over files.** Per the Delegation rule in `CLAUDE.md`, the
top-level session dispatches one `general-purpose` Sonnet sub-agent (medium-high effort, model
passed explicitly, budget 40 tool calls) with these steps, the PR facts, and the spec format
below. The sub-agent never dispatches; it returns a "Needs research" item for anything it cannot
do. It writes the spec file and returns its path.

**2. Find the pages.** Changed source files are the PR's files minus tests, snapshots, mocks,
and stories. A page is a component a router renders directly (`<Route element=...>`,
`Component=`, lazy routes). Walk the importers of each changed file upward, through barrel
`index` files and path aliases, until a route is reached. Every distinct page gets its own
diagram, even when pages share components. A component or module used by several pages appears
in each page's diagram.

**3. Trace the JSX down.** For each page, read the component source and follow the elements it
renders, depth first, in render order. Inside the feature folder that holds the changed files,
draw every component down to the leaves. Outside it, draw a component only when a changed
component sits below it, and leave out design-system and shared widgets (Paragon, generic
helpers). A component rendered in two branches appears once, where it first renders. Name nodes
as the code does, which can differ from the file name (a provider defined in `FooContext.tsx` is the node `FooProvider`). Components defined inside a file are drawn under the component that renders them.

**4. Classify.** `changed`: the component's own file has non-test changes. `new`: the file is
added. `same`: everything else, including components whose only diff is tests, which get one
note saying so. A context provider on the JSX path is a node. A file with several components is
classified per component by reading the hunks: a local component with no hunk of its own is
`same`, and one whose lines changed is `changed`, even when its exported parent is `same`.

**5. Place the modules and write the notes.**
- Every changed non-test source file that defines no component is a `mod` node, including
  type-only and style files. A change with no behavior effect says so in its note.
- A changed non-React module is a `mod` node at the depth of the parent component plus one, listed
  directly after that component's own row. It goes under the component that imports the changed
  exports. A module imported only by another changed module nests one level deeper under it (an
  API client under its hooks). A module used by several components, or by both a component and one of its
  descendants, is listed once, under the first in tree order that uses the changed exports, and a
  footnote says the others use untouched exports.
- Notes say what behavior changed, as full sentences with no em dashes and no change narration
  ("updated X"). One note per distinct change, at most 5 per component, taken from the diff, not
  from the PR description.
- Unchanged components get no note unless a fact helps (a test-only change, or a short purpose
  for the page and panel at the top).

**6. Other pages.** Search the whole source tree for importers of every changed component and
module. Pages found become sections in `pages`. When none are found, set `otherPages` to a
heading ending in "none" and lines stating what was searched, so the claim is checkable.
`footnotes` names what is not drawn (test-only files, shared widgets).

**7. Render and verify (top-level session).**

```bash
python3 scripts/render_component_tree.py SPEC.json --md component-tree-pr-<N>.md --outline component-tree-pr-<N>-context.txt
```

Write both files to the session scratchpad directory when one is listed, otherwise the current
directory, never inside the repository under review. Then map every changed source file in the PR
to the node or nodes that define it (by the components and modules the file defines, not by
file name) or to the "not drawn" footnote, and confirm none is unmapped.
Fix the spec and re-render until none is missing.

**8. Deliver.** Tell the user the absolute path of the `.md` and summarize in at most five lines:
the pages, the changed and new components, the changed modules. The `.md` renders in a Markdown
preview (VS Code, any CommonMark viewer that allows inline HTML); GitHub does not render inline
SVG. The `-context.txt` outline is the text form of the same tree and notes, for whoever needs it
as context.

## Spec format

```json
{
  "title": "Component trees per page: what PR #6 changed",
  "subtitle": "owner/repo PR #6 \"PR title\", head <short sha>.",
  "pages": [{
    "title": "Page: SomePage",
    "sub": "Route /path (src/index.jsx). Components follow the JSX nesting; grey text lines are changed non-React modules, listed under the component that calls them.",
    "nodes": [
      {"depth": 0, "name": "SomePage", "status": "same", "notes": ["Unchanged. One-line purpose."]},
      {"depth": 1, "name": "Panel", "status": "changed", "notes": ["What behavior changed."]},
      {"depth": 2, "name": "data/apiHooks.ts", "status": "mod", "notes": ["What changed in it."]},
      {"depth": 2, "name": "NewThing", "status": "new", "notes": ["NEW component: what it does."]}
    ]
  }],
  "otherPages": {"heading": "Other pages that use this PR's changed components or modules: none", "lines": ["What was searched."]},
  "footnotes": ["Not drawn: ..."]
}
```

`status` is `same`, `changed`, `new`, or `mod`. `depth` follows the JSX nesting (page = 0).
`notes` may be empty. `otherPages` may be omitted when other pages are listed in `pages`.
`testdata/pr6-spec.json` is a regression fixture for maintainers testing the renderer; do not read it
when building a spec.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Guessing the hierarchy from file names or folders | Follow the JSX of each file; folders say nothing about nesting. |
| Drawing Paragon and shared widgets | Leave them out; footnote them. |
| Boxing or coloring modules | Modules are plain grey `mod` nodes. |
| Writing "no other pages" without searching | Search importers first; list what was searched. |
| Describing the PR description's claims in notes | Describe what the diff changes. |
| Editing the SVG or Markdown by hand | Change the spec and re-render. |
