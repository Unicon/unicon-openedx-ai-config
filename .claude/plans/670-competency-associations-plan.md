# Competency Criteria Associations Workspace (#670)

## Context

`frontend-app-authoring` (Studio MFE) has a read-only Competency Management page
at `/taxonomy/:taxonomyId/competencies` (built by the just-completed ticket
`#680`), showing a taxonomy's competencies as an expand/collapse tree with each
leaf's Competency ID badge. Ticket `#670` asks for that same page to become a
two-panel "Manage & Apply Competencies" associations workspace: a selectable
competency tree on the left drives a course-search-and-outline-browse panel on
the right, so a Platform Administrator can find the exact gradeable subsection
to attach criteria to without opening each course individually. This ticket
stops at browse-and-surface: the actual associate action is a separate ticket,
`#672`.

This plan was built from the ticket's own text (fetched directly from the
GitHub API, not the stale project-board summary), corroborated and corrected
against the current codebase by two `Explore` dispatches, and reviewed by a
`business-analyst` and a `software-architect` dispatched in parallel. Both
found the ticket's own "Current state" section stale (it assumes `#623`'s
placeholder, which `#680` already replaced with a real, badge-bearing tree) and
surfaced a real scope conflict with a sibling ticket, `#669`. Four product
questions were batched to the user and resolved below; the mechanism questions
were resolved by the architect and are adopted directly.

**One correction to the research above, made after the fact:** the
business analyst's follow-up flagged a suspected gap in `#669`'s date filter
(that it might only expose the start date as response data, not as a real
filter parameter). That was traced back to an incomplete relay on my part, not
to `#669`'s actual text. `#669`'s raw body (fetched directly, not summarized)
is unambiguous: `start_date_after`/`start_date_before` are real query params,
applied inside `CourseOverview.get_all_courses()` via
`Q(start__isnull=True) | Q(start__gte=after, start__lte=before)` at the
queryset level, before pagination. Filtering is correctly server-side across
all pages. The only genuinely unnamed thing in `#669` is the *response field*
that will carry each course's own start date for display - a minor, non-blocking
naming detail, not a filtering gap. This plan assumes correct server-side
filtering once `#669` ships.

## Decisions made by the user

- **Page structure**: replace in place. The existing tree gains selection and
  keeps the Competency ID badge; the course-browse panel is added alongside it
  on the same page, same URL. No tabs, no mode switch.
- **Associated-subsection marking** (the `#669`/`#670` scope conflict over
  cross-referencing existing competency-criteria against the outline, via an
  internal "ticket 5.7" that has no GitHub issue yet): in scope for `#670`, but
  blocked on ticket 5.7 getting a real GitHub issue and a defined API contract.
  This plan builds the seam (an `isAssociated`-shaped prop on the subsection
  row, unset/`false` for now) but not the actual fetch-and-cross-reference
  logic, which has no contract to build against yet.
- **Selection scope**: leaves only, single-select. A competency with
  sub-competencies expands/collapses like today; it is never itself a selection
  target. Matches the CBE model, where parent competencies are mastered by
  roll-up from their children, not directly associated.
- **Filter-state lifecycle**: persists. Switching the selected competency does
  not reset the title search, date range, or which courses are expanded in the
  right panel.

## Architecture decisions (from the `software-architect` dispatch, adopted directly)

- **Outline fetching**: lazy, per course, on expand, via the existing
  `useCourseOutlineIndex` hook (`src/course-outline/data/outlineIndexQuery.ts`)
  against the existing `GET /api/contentstore/v1/course_index/{courseId}`
  endpoint - confirmed by `#669`'s own text too ("the frontend fetches each
  course's outline lazily, per course... this ticket does not add outline data
  to the course-list response"). Pass `refetchOnMount: false` so collapsing and
  re-expanding a course within the app's hour-long `staleTime` doesn't
  re-fetch. Each course's outline node type comes from `@src/data/types`
  (`XBlockBase`, `graded: boolean`, `category` string), not
  `src/course-outline/data/types.ts` (which holds only the top-level
  `CourseOutline`/`CourseStructure` envelope).
- **Component reuse over forking**: extend `CompetencyTree.tsx` and
  `CompetencyTreeItem.tsx` with optional `selectedCompetencyId?: string | null`
  and `onSelectCompetency?: (node: CompetencyTreeNode) => void` props, rather
  than building a second tree component. Both props default to absent, so
  today's read-only rendering, its SCSS, and its existing tests
  (`CompetencyTree.test.tsx`, `CompetencyManagementPage.test.tsx`) are
  unaffected. Only leaf rows (`!hasChildren`) become clickable/selectable when
  `onSelectCompetency` is provided; group rows keep their current
  expand/collapse-only behavior.
- **Data layer**: add to the existing `src/studio-home/data/` module, not a new
  query-key namespace under `competency-management/`. `getStudioHomeCoursesV2`
  (`src/studio-home/data/api.ts:30`) already runs `customParams` through
  `snakeCaseObject`, so passing `{startDateAfter, startDateBefore}` needs no
  signature change - it becomes `start_date_after`/`start_date_before` on the
  wire for free. Add a `coursesV2(params)` key to the existing
  `studioHomeQueryKeys` factory and a new `useStudioHomeCoursesV2(params)` hook
  in `src/studio-home/data/apiHooks.ts`, next to the existing
  `useLibrariesV1Data`. This is additive; it does not touch the Redux thunk
  path Studio Home still uses. Introduce typed `Course` and
  `StudioHomeCoursesV2Response` interfaces (today's response is untyped `any`),
  scoped to the fields this UI reads plus the pagination envelope
  (`results.courses`, `numPages`, `count`; params `page`, `pageSize`, `search`,
  `order`, `startDateAfter`, `startDateBefore`).
- **Date-range picker**: extend `src/generic/datepicker-control/DatepickerControl.jsx`
  with optional passthrough props (`selectsStart`, `selectsEnd`, `startDate`,
  `endDate`, `minDate`, `maxDate`), all defaulting to today's behavior, so its
  six existing consumers are unaffected. Its `selectsStart` is already
  hardcoded `true` today but is a no-op without the paired props - making it a
  prop with a default of `true` is behavior-neutral. Compose two instances
  ("from"/"to") wired to each other's `minDate`/`maxDate` for a real linked
  range, rather than shipping two unlinked date inputs.
- **Building against `#669` before it ships**: safe. Verified directly against
  the local `openedx-platform` checkout -
  `get_query_params_if_present` (`cms/djangoapps/contentstore/views/course.py:473`)
  reads only its known params via plain `request.GET.get(...)` calls, and
  `HomePageCoursesViewV2.get()` (`cms/djangoapps/contentstore/rest_api/v2/views/home.py:88`)
  is a plain `APIView` with no strict param-validating serializer - the
  `@apidocs.schema` decorator only documents params for the OpenAPI schema, it
  doesn't enforce them. Sending `start_date_after`/`start_date_before` today
  is silently ignored (no 400, no effect), the same way an undocumented `org`
  param is already silently ignored today. So this ticket's date-filter UI can
  be built and tested now (asserting the outgoing query params via
  `axios-mock-adapter`), and it will start actually filtering the moment
  `#669` ships, with no frontend code change needed.
- **Selection-callback shape**: mirror the confirmed precedent,
  `ComponentSelectedEvent` in
  `src/library-authoring/common/context/ComponentPickerContext.tsx`:
  `(selected: {usageKey: string; blockType: string}) => void`. Define it as a
  plain prop passed down through `CourseRow`/`CourseOutlineSubtree`, not a
  React context - there's exactly one consumer at one depth within one panel,
  unlike the component picker's cross-route usage.
- **Selected-row visual state, not a silent callback**: per the
  `business-analyst`'s recommendation, clicking a gradeable subsection shows a
  visible selected/active state on that row (adopted into this ticket's scope,
  not deferred to `#672`), in addition to firing the callback. A click with no
  visible effect reads as a bug regardless of ticket boundaries, and it makes
  the behavior actually testable within `#670`.

## Files

### New - `src/taxonomy/competency-management/associations/`

- **`CompetencyAssociationsPanel.tsx`** + **`index.ts`** - the two-column
  layout, using Paragon `Row`/`Col` (`lg={4}` / `lg={8}`) so small-screen
  stacking comes from the existing grid rather than new media queries. Owns
  `selectedCompetency: CompetencyTreeNode | null` state (lifted here, not in
  `CompetencyTree`, since the right panel needs it too). Renders
  `<CompetencyTree taxonomyId taxonomyName selectedCompetencyId={...} onSelectCompetency={...} />`
  on the left and `<CourseSearchBrowse activeCompetency={selectedCompetency} />`
  on the right.

### New - `src/taxonomy/competency-management/course-search/`

- **`CourseSearchBrowse.tsx`** - title search (Paragon `SearchField`,
  400ms-debounced, matching the existing precedent in
  `src/studio-home/tabs-section/courses-tab/courses-filters/index.tsx`) + a
  linked date-range filter (two extended `DatepickerControl` instances) +
  paginated course list via `useStudioHomeCoursesV2`, called with
  `enabled: !!activeCompetency` so no query runs until a competency is
  selected (per the AC). Renders: a "select a competency" prompt when nothing
  is active; a loading state; an inline error state distinct from empty
  results; an empty state distinguishing "zero accessible courses" from "zero
  matches for the current filters"; Paragon `Pagination` using the response's
  `numPages`, at the existing Studio Home default `pageSize` of 10.
- **`CourseRow.tsx`** - one course's collapsible row (navigation-only,
  never itself selectable). Mounts `<CourseOutlineSubtree>` only while
  expanded, so the outline query's lifecycle follows component mount/unmount
  rather than a manually-tracked `enabled` flag.
- **`CourseOutlineSubtree.tsx`** - calls
  `useCourseOutlineIndex(courseId, { enabled: isExpanded, refetchOnMount: false })`
  and recursively renders sections (navigation-only) and gradeable subsections
  (filtered by the `graded` flag from `@src/data/types`), each subsection row
  clickable: shows a selected-state on click and fires
  `onSubsectionSelected({usageKey, blockType})`. Carries an `isAssociated`
  prop on each subsection row, always `false`/unset for now (the seam for the
  blocked ticket-5.7 work - see Decisions above). Handles: a course row
  expanding to no gradeable subsections at all; a per-course outline fetch
  failure rendered as a scoped inline error on that row (not a whole-panel
  error), since the course list itself may have loaded fine.
- **`types.ts`** - the `SubsectionSelectedEvent` type (mirroring
  `ComponentSelectedEvent`'s shape) and local `Course`/`CourseRowData`-style
  types for this panel's own use.
- **`messages.ts`** - i18n strings: search placeholder, date-range labels
  (explicitly stating the filter is on course-run *start* date, per the AC),
  empty/error/loading states, the "select a competency" prompt, and the
  subsection-selected accessible label.

### Modified

| File | Change |
|---|---|
| `src/taxonomy/competency-management/CompetencyManagementPage.tsx` | Render `<CompetencyAssociationsPanel taxonomyId taxonomyName />` in place of the current direct `<CompetencyTree>` render. |
| `src/taxonomy/competency-management/CompetencyTree.tsx` | Add optional `selectedCompetencyId`/`onSelectCompetency` props; thread through to `CompetencyTreeItem`. Absent by default, so `#680`'s existing read-only behavior and tests are unaffected. |
| `src/taxonomy/competency-management/CompetencyTreeItem.tsx` | Thread the same two props through the recursion; leaf rows (`!hasChildren`) become clickable/selectable when `onSelectCompetency` is provided, with a keyboard-activatable, `aria-selected`-carrying row. Group rows are never selectable. |
| `src/taxonomy/competency-management/CompetencyTree.scss` | Add selected-leaf styling. |
| `src/taxonomy/competency-management/messages.ts` | Add an accessible label for the selected-competency state. |
| `src/studio-home/data/api.ts` | Add typed `Course`/`StudioHomeCoursesV2Response` interfaces; no signature change to `getStudioHomeCoursesV2`. |
| `src/studio-home/data/apiHooks.ts` | Add `studioHomeQueryKeys.coursesV2(params)` and a new `useStudioHomeCoursesV2(params)` hook, additive alongside the existing `useLibrariesV1Data`. |
| `src/generic/datepicker-control/DatepickerControl.jsx` | Add optional `selectsStart`/`selectsEnd`/`startDate`/`endDate`/`minDate`/`maxDate` passthrough props, all defaulting to current behavior. |

### Explicitly not created

- `course-search/data/{api.ts,apiHooks.ts,queryKeys.ts}` (from the ticket's own
  proposed file list) - superseded by extending `studio-home/data/` instead,
  per the architect's recommendation, to avoid a second query-key namespace for
  the same endpoint.
- Any actual fetch/cross-reference of competency-criteria data (the blocked
  ticket-5.7 work) - only the `isAssociated` seam is built now.

## Known gaps, out of this ticket's scope, flagged for the user to action separately

These are cross-ticket/process items, not implementation decisions - none are
acted on here without your go-ahead, since editing another team's GitHub issue
is a visible-to-others action:

- `#669`'s body cites an internal-only "ticket 5.7" with no GitHub issue, and
  `#669`/`#670` currently contradict each other about whether `#670` owns
  criteria cross-referencing. Worth a comment on one or both issues to
  reconcile, once ticket 5.7 has a real issue number.
- No ticket currently owns adding an in-app navigation entry point to
  `/taxonomy/:taxonomyId/competencies` - same gap `#680` already accepted as a
  known limitation. `#670`, `#671`, and `#672` can all merge reachable only by
  typing the URL.
- `#669`'s own open question about naming the response's start-date field is
  non-blocking for this ticket; the frontend will consume whatever name ships.

## Verification

1. **Lint/typecheck**: `npx tsc --noEmit`, `npx oxlint --type-aware --deny-warnings`
   (scoped to touched files), `npx dprint check`, `npx stylelint` on touched
   SCSS.
2. **Unit/RTL tests** (`@src/testUtils`, `axios-mock-adapter`):
   - Selecting a leaf competency populates the right panel and runs the course
     query; selecting a group node does nothing but expand/collapse (structural
     assertion that group nodes never become selectable).
   - Switching the selected competency preserves existing search/date/expanded
     state in the right panel (per the persist decision).
   - Date-range and title-search inputs produce the correct outgoing
     `start_date_after`/`start_date_before`/`search` query params (asserted via
     the mock adapter), independent of whether the real backend supports them
     yet.
   - Course list: loading, error (distinct from empty), zero-accessible-courses
     (distinct from zero-matches-for-filters), and pagination.
   - Course row expansion: lazy outline fetch on first expand only; no re-fetch
     on collapse/re-expand within the cache window; per-course outline error
     shown scoped to that row, not the whole panel; a course with no gradeable
     subsections communicates that rather than showing an empty expansion.
   - Clicking a gradeable subsection shows a selected state and fires
     `onSubsectionSelected` with the correct `{usageKey, blockType}`; clicking a
     section, unit, or course row does nothing (structural read-only
     assertion, same pattern used in `#680`'s tests).
   - `CompetencyTree.test.tsx`/`CompetencyManagementPage.test.tsx` continue to
     pass unchanged (confirming the new props are truly additive).
3. **Manual check in a browser**, via the `run-frontend-app-authoring` skill:
   open `/taxonomy/:taxonomyId/competencies`, confirm the Competency ID badge
   is still visible on the left tree, select a leaf competency, verify the
   right panel populates, filter by title and by date range and confirm the
   outgoing request (network tab) carries the right params even though the
   live backend ignores them today, expand a course and confirm its outline
   loads lazily, click a gradeable subsection and confirm the selected-state
   renders, and check the layout at a narrow viewport for the two-column
   stacking behavior.

## Implementation order (spike, then stabilize)

1. Spike: extend `CompetencyTree`/`CompetencyTreeItem` with selection props in
   isolation (no course panel yet) to validate the additive-props approach
   against the existing tests.
2. `useStudioHomeCoursesV2` hook + typed `Course` response, verified against a
   mocked endpoint.
3. `CourseSearchBrowse` + `CourseRow` wired to the new hook, no outline yet:
   search, date filter, pagination, empty/error states.
4. `DatepickerControl` range extension, wired into `CourseSearchBrowse`.
5. `CourseOutlineSubtree` wired to `useCourseOutlineIndex`, lazy-on-expand,
   with the `isAssociated` seam and the subsection-selected callback +
   selected-row visual state.
6. `CompetencyAssociationsPanel` assembly + `CompetencyManagementPage.tsx`
   mount.
7. Stabilize: full test suite from Verification, lint/typecheck, manual
   browser pass against the Figma.

## Status

Step 1 (spike) complete and reviewed: `CompetencyTree`/`CompetencyTreeItem`
extended with `selectedCompetencyId`/`onSelectCompetency`, marked
`// SPIKE: shape not final`, existing tests pass unchanged. Steps 2-7 not yet
started.
