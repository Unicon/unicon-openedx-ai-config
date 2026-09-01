# Competency Management Page

## Context

`frontend-app-authoring` (Studio MFE) has no page for browsing a competency
taxonomy's competencies by their stable Competency ID (`Tag.externalId`). The
ticket asks for a new read-only route, `/taxonomy/:taxonomyId/competencies`,
showing the taxonomy's tags as an expand/collapse tree with each tag's
Competency ID next to it, reusing the existing tag tree-table rendering.
Explicitly out of scope: editing the ID, any backend/data-layer change,
sorting/filtering by ID.

This plan was reviewed by a `software-architect` dispatch against the current
`master` (post-merge). Two premises in the original draft were corrected
(no plugin-contract or `.importlinter` concern actually applies here — see
below), one design decision was reversed (export the context default instead
of hand-duplicating it), and several concrete implementation hazards were
surfaced that the acceptance criteria would otherwise catch late. The user
resolved the two genuinely product-facing open questions:

- **Entry point**: URL-only for this ticket. No link is added from
  `TaxonomyDetailPage` or `TaxonomyMenu`. State this explicitly as an AC so
  QA doesn't file it as a missing-link defect.
- **Non-competency taxonomies**: `TaxonomyData` has no `CompetencyTaxonomy`
  flag (no backend change in scope), so the page renders whatever taxonomy
  id is in the URL, including system-defined ones (e.g. Language) whose tags
  may be incompletely enumerable. Accepted as a known limitation, to be
  revisited once the backend exposes a competency-enabled flag.

The Figma screenshot (fetched and inspected directly) shows the Competency ID
as a small right-aligned badge/chip next to the row, not a 50/50 split
column — this resolves the column-proportions question the architect flagged,
without needing to ask the user.

## Architecture decision

Reuse the existing tag tree-table shell (`src/taxonomy/tree-table/`) and the
tree-building class (`src/taxonomy/tag-list/tagTree.ts`) as-is. Build a
**second, read-only-only consumer** of `TreeTableContext`/`TableView`,
supplying:
- a 2-column `columns` array (Name+expand, Competency ID) that simply omits
  an `"actions"` column
- a context value where CRUD fields are the same no-op defaults
  `TreeTableContext` already falls back to when no provider is present

This works because CRUD (`CreateRow`/`EditRow`/`DeleteModal`) is only ever
triggered from the `"actions"` column's callbacks
(`src/taxonomy/tag-list/tagColumns.tsx:72-113`, `Actions.tsx`) — `TableView`/
`TableBody`/`NestedRows` themselves have no hardcoded CRUD UI. Omit that
column and CRUD becomes structurally unreachable, not just hidden — stronger
than adding a `readOnly` boolean prop to `TagListTable` (which still
constructs 3 live mutations and a `DeleteModal`).

**One small additive change to a shared file**, agreed with the architect:
export the existing default context object from
`src/taxonomy/tree-table/TreeTableContext.tsx` as a named
`treeTableContextDefaults` const, and pass it into the existing
`createContext(...)` call unchanged. This is not a new prop/mode/branch — it
names an object that already exists and already has its own test
(`TreeTableContext.test.tsx:42`). It lets the new page's context value spread
that default and only state an opinion about the 6 fields it actually owns
(`treeData`, `columns`, `isLoading`, `pageCount`, `pagination`,
`handlePaginationChange`), instead of hand-duplicating all ~20 fields (which
would silently keep stale semantics if a *default value*, not just the
interface shape, changes later — e.g. `validate`'s default). No existing
consumer (`TagListTable`) is affected.

Two premises from the first draft don't hold and are dropped from the
rationale (though the conclusions were already right): `TagListTable`'s
props aren't a published/plugin contract (this MFE has no `exports`/`files`
field and no taxonomy plugin slot), and `.importlinter` governs Python
packages elsewhere in `openedx-core`, not this MFE. The real reasons to keep
`TagListTable` untouched are that it owns 3 live mutations plus a delete
modal, and that omitting a column is a stronger read-only guarantee than a
boolean flag.

`OptionalExpandLink` and `TagTree` are imported directly from
`src/taxonomy/tag-list/` (not re-homed into `tree-table/` in this ticket,
even though neither is CRUD-specific) — moving them is a separate refactor
with test-path churn, worth doing only once a third consumer appears.

## Files

### New — `src/taxonomy/competency-management/`

- **`CompetencyManagementPage.tsx`** — route-level page. Mirrors
  `taxonomy-detail/TaxonomyDetailPage.tsx`'s shell: `Helmet` +
  `getPageHeadTitle`, `useTaxonomyDetails(taxonomyId)` with its existing
  `Loading`/`ConnectionErrorAlert` guard clauses, `Breadcrumb` (Taxonomies →
  taxonomy name linking to `/taxonomy/:taxonomyId` → active label
  "Competencies"), `SubHeader` with no `titleActions`/`headerActions` (no
  `ReadOnlyBadge`, no `TaxonomyMenu` — see "Read-only messaging" below),
  single full-width `Container` (no 9/3 `Layout` split, no side card), then
  `<CompetencyTree taxonomyId={taxonomyId} />`.
- **`CompetencyTree.tsx`** — data + context wiring:
  - `useTagListData(taxonomyId, { pageIndex: 0, pageSize: 50, disablePagination: true, enabled: true })`
    — **must** pass exactly these values. `useTagListData`'s query key
    (`taxonomyQueryKeys.taxonomyTagList(taxonomyId)`) ignores pagination
    params and is shared with `TaxonomyDetailPage`'s `TagListTable`, and
    `refetchOnMount: 'always'` means whichever page mounts last overwrites
    what the other reads on return. Different params here would make the
    tree's shape depend on navigation order between the two pages.
  - Build the tree in a `useMemo` (not directly in render, not in a bare
    `useEffect`), wrapped in try/catch: `new TagTree(tagList.results)`
    throws `TagTreeError` on duplicate values or cycles
    (`tag-list/tagTree.ts:79,117`). `TaxonomyLayout` has no error boundary,
    so an uncaught throw here breaks the page. On catch, render
    `ConnectionErrorAlert` (same component `TaxonomyDetailPage` already
    uses) instead of the tree.
  - Assemble `const contextValue: TreeTableContextValue = { ...treeTableContextDefaults, treeData, columns, isLoading, pageCount: -1, pagination: { pageIndex: 0, pageSize: 50 }, handlePaginationChange: () => {} }`
    — annotate the type explicitly (unlike `TagListTable.tsx:161-165`, which
    lacks the annotation and silently passes 7 extra fields not on the
    interface at all — don't repeat that gap).
  - Render `<TreeTableContext.Provider value={contextValue}><TableView /></TreeTableContext.Provider>`.
    No `DeleteModal`, no pagination UI (`enablePagination` left at its
    default `false`).
  - Wrap in a page-scoped container class (e.g. `competency-tree`) — see
    styling note below.
- **`competencyColumns.tsx`** — `getColumns()` returning exactly 2 columns:
  - `valueColumn`: same shape as `tag-list/tagColumns.tsx:50-64` — renders
    `<OptionalExpandLink row={row} />` (imported from
    `../tag-list/OptionalExpandLink`) plus the tag name.
  - `competencyId`: reads the row's `externalId` and renders it as a small
    badge-styled `<span>`, or `null` when falsy. Use a **truthiness check**,
    not `!== null` — `getAllAsDeepCopy()`'s `JSON.parse(JSON.stringify(...))`
    round-trip drops `undefined` keys but keeps `null`, and newly-created
    tags elsewhere are seeded with `externalId: ''`
    (`tag-list/hooks.ts:156`) — so the cell can see `undefined`, `null`, or
    `''`. Wrap the value in `<span className="tree-table-overflow-anywhere">`
    so a long ID can't overflow on root rows (nested rows already get this
    class from `NestedRows.tsx:98`; depth-0 rows don't, per
    `TableBody.tsx:77` — this AC ("responsive at narrow viewports") would
    otherwise only be covered for non-root rows).
  - Declare a local type, e.g. `interface CompetencyRowData extends TreeRowData { externalId?: string | null }`,
    and a small getter mirroring `tag-list/utils.ts:10`'s
    `getTagListRowData`, instead of casting `row.original.externalId`
    inline — `TreeRowData`'s index signature types it as `unknown`, and
    `TagData.externalId`'s `string` type declaration doesn't match the
    API's actual `null` values (don't fix that type in this ticket; it's a
    pre-existing, separate inaccuracy).
- **`competency-management.scss`** (or a scoped rule in an existing SCSS
  entry point) — the shared `TableView.tsx:108` renders
  `className="table w-100 tag-list-table tree-table-layout-fixed"` with no
  per-column width/`colgroup`, so 2 auto columns under `table-layout: fixed`
  split 50/50. Style the ID column narrow and right-aligned (badge-like, per
  the Figma screenshot) with a rule scoped to this page's own wrapper class
  (e.g. `.competency-tree .tag-list-table td:nth-child(2)`), so the existing
  taxonomy detail page's table (which shares the same `.tag-list-table`
  class) is untouched.
- **`messages.ts`** — id namespace `course-authoring.competency-management.*`,
  matching `tag-list/messages.ts:5`'s convention.
- **`index.ts`** — `export { default as CompetencyManagementPage } from './CompetencyManagementPage';`.
- Co-located `*.test.tsx` for each component (see Verification).

### Modified

| File | Change |
|---|---|
| `src/taxonomy/tree-table/TreeTableContext.tsx` | Export the existing default object as `export const treeTableContextDefaults: TreeTableContextValue = { ... }`, pass it to `createContext(...)` unchanged. Purely additive; no existing behavior changes. |
| `src/taxonomy/index.ts` | `export { CompetencyManagementPage } from './competency-management';` |
| `src/index.jsx` | Add `<Route path="/taxonomy/:taxonomyId/competencies" element={<CompetencyManagementPage />} />` as a sibling of the existing `/taxonomy/:taxonomyId` route (`src/index.jsx:111-113`), inside the same `<Route path="/taxonomy" element={<TaxonomyLayout />}>` block, gated behind the same `ENABLE_TAGGING_TAXONOMY_PAGES` flag. Written as an absolute path, matching the existing sibling's style. |

### Read-only messaging — deliberately not reused

`ReadOnlyBadge` (`src/taxonomy/read-only-badge/`) and PR #3183's
`disableTagActions` tooltips both signal "*this taxonomy* can't be edited" —
a per-taxonomy permission state on an otherwise-editable page. This page is
read-only for everyone regardless of the taxonomy, so showing either would
assert something false. `ViewOnlyPermissionsAlert`
(`src/generic/ViewOnlyPermissionsAlert.tsx`, from #3193) documents its own
contract as explaining *why controls are absent for this user* when other
users would see them — not applicable here, since no permission would ever
unlock editing on this page. None of these are used. The Figma has no banner,
consistent with all three components' own documented scope.

## Verification

1. **Lint/typecheck**: run the project's ESLint/oxlint and `tsc` (whatever
   the repo's `package.json` scripts name for lint/type-check) — not the
   full `make validate`.
2. **Unit/RTL tests**, using the newer test pattern (`@src/testUtils`:
   `initializeMocks`, custom `render(ui, { path, params })`) shown in
   `src/taxonomy/tag-list/TagListTable.test.jsx`:
   - `CompetencyManagementPage`: renders taxonomy name/title; loading and
     error states via `useTaxonomyDetails`; breadcrumb links.
   - `CompetencyTree`/`competencyColumns`: nested tree renders root → group
     → leaf with correct indentation; Expand All/Collapse All toggles
     `subRows` visibility; **structural read-only assertion** — no actions
     column header and no per-row action/menu button exist anywhere in the
     rendered output (so a future shared-column change can't silently
     reintroduce CRUD here without failing a test); Competency ID renders
     for tags with `externalId` set and renders nothing (no literal
     `"undefined"`/`"null"` text) for `undefined`, `null`, and `''`.
   - `TreeTableContext.tsx`: existing `TreeTableContext.test.tsx` should
     still pass unchanged after exporting the default (purely additive).
3. **Manual check in a browser** (`make devstack`/local run, or whatever
   this repo's `run` skill uses): open
   `/taxonomy/:taxonomyId/competencies` for a real taxonomy with nested
   tags and some tags missing `external_id`; verify expand/collapse and
   indentation, ID badge placement against the Figma, and behavior at a
   narrow viewport. Also open the existing `/taxonomy/:taxonomyId` page
   before/after visiting the new page to confirm the shared query-cache
   fix (identical `useTagListData` params) means neither page's tree
   changes shape depending on visit order.

## Implementation order (spike, then stabilize)

1. Spike: `competencyColumns.tsx` + `CompetencyTree.tsx` wired to real data,
   rendered directly (no page shell yet), to validate the context-stub /
   omitted-actions-column approach actually renders a working expand/collapse
   tree with no CRUD surface.
2. `TreeTableContext.tsx` additive export.
3. `CompetencyManagementPage.tsx` shell + route registration + barrel
   exports.
4. Styling pass (badge/ID column CSS) against the Figma.
5. Stabilize: types (`CompetencyRowData`, explicit context-value annotation),
   the `TagTree` try/catch + `useMemo`, the falsy-check + overflow class on
   the ID cell, tests from the Verification section, lint/typecheck.
