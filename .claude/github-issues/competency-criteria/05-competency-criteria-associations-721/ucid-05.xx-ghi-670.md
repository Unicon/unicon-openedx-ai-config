# [FE] Competency Management Course Search/View

GitHub: https://github.com/openedx/openedx-core/issues/670 (#670, OPEN)
Cached: 2026-09-21

## Use Case

As a Platform Administrator configuring Competency Criteria associations, I want to select a competency from the taxonomy's competency tree and then search the courses I have access to (filtered by course-run start date), browse a course's sections and gradeable subsections, so that I can find the exact gradeable subsection to attach criteria to without opening each course individually.

## Acceptance Criteria

```
Scenario: Competency tree lists the taxonomy's competencies
  Given I open the Manage & Apply Competencies page for a competency taxonomy
  Then the left panel shows that taxonomy's competencies as a nested tree

Scenario: Selecting a competency drives the right-hand panel
  Given the competency tree is shown
  When I select any competency in the tree
  Then it becomes the active competency
  And the right-hand course-browse panel loads for that competency
  And this is true for every row in the tree, whether or not it has sub-competencies

Scenario: A competency with sub-competencies is selectable like any other
  Given the competency tree shows a competency that has sub-competencies beneath it
  When I click that competency's row
  Then it becomes the active competency
  And the right-hand course-browse panel loads for it
  And it behaves no differently from clicking a competency that has no sub-competencies

Scenario: Clicking a row selects it without expanding it
  Given a collapsed competency that has sub-competencies
  When I click its row
  Then it becomes the active competency
  And its sub-competencies stay collapsed

Scenario: The expand/collapse control only expands and collapses
  Given a competency that has sub-competencies
  When I click its expand/collapse arrow
  Then its sub-competencies show or hide
  And the active competency does not change
  And the right-hand panel does not change or reload

Scenario: A row's two controls are separately reachable and distinguishable
  Given the competency tree is shown
  When I move through a row that has sub-competencies using a keyboard
  Then I can reach both selecting the competency and expanding it as distinct controls
  And each is announced as a distinct action

Scenario: No competency selected yet
  Given I open the page and have not selected a competency
  Then the right-hand column is not rendered at all
  And nothing occupies that space: no panel, no background, no border, and no prompt
  And the competency tree is the only content on the page
  And no course search runs

Scenario: The right-hand column appears on the first selection
  Given I have not selected a competency and the right-hand column is absent
  When I select a competency
  Then the right-hand column renders for the first time
  And it shows the course-browse panel for that competency

Scenario: Search courses by title
  Given I have selected a competency and am viewing the course-browse panel
  When I enter a title filter
  Then the course list narrows to accessible courses whose title matches

Scenario: Filter courses by start-date range
  Given I am viewing the panel
  When I set a start and end boundary in the date-range picker
  Then the list shows only courses whose course-run start date falls within that range
  And the UI makes clear the filter is on course start date

Scenario: Default view shows all accessible courses
  Given I have entered no title filter and no date range
  When the panel loads
  Then it shows all courses I have access to

Scenario: Expand a course to browse its gradeable subsections
  Given a course appears in the results
  When I expand it
  Then its sections and gradeable subsections are displayed
  And the course and section rows are navigation only, not selectable as association targets

Scenario: Course search fails
  Given the #669 course-search call fails
  Then an inline error state is shown, distinct from an empty-results state

Scenario: No matching courses
  Given the search/filter matches no accessible course
  Then an empty state is shown

Scenario: Small-screen rendering
  Given I view the page on a small screen
  Then the competency tree, search, date picker, and expand/collapse remain usable
```
## Designs
[Figma Link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1878-43666&t=wRYaYcGontqPW0qp-1)

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/f317929c-cf1a-471d-a7f0-72e284a32e46" />


## Description

**Current state**

No implementation exists. \#623 built only a placeholder Competency Management page (`/taxonomy/:taxonomyId/competencies`) whose real content is deferred to future tickets; this is one. There is no left-hand competency tree in code yet: \#648 *designs* the shell and that tree, but no implementation ticket builds it, and this is the first ticket that needs a competency actually selected. Studio's existing `StudioHome` course listing is general and competency-unaware, with no date-range filter and no drill-down into a course's gradeable structure.

**Requested change**

Build the Manage & Apply Competencies associations workspace: a minimal two-panel layout with a competency-selection tree on the left and the course-browsing panel on the right, driven by the selected competency.

1. **Minimal competency-selection tree (left panel).** Render the current taxonomy's competencies as a selectable tree (nested competencies with their codes). Selecting a competency sets the active competency and populates/refreshes the right-hand panel against it. Reuse the existing tag-tree rendering; this is the *minimal functional* tree, not the finished shell. Expand/collapse polish, switcher styling, empty-state design, and responsive spec are \#648's; the Competency ID badge on rows is a separate ticket's. Neither is built here.  
2. **Course search with a start-date range filter (right panel).** A title search plus a date-range picker, scoped to the selected competency. Use React Date Picker lightly styled with Paragon (Paragon has no native range picker). For MVP the range filters on course-run **start date** only; make that explicit to the user ("courses whose start date falls between X and Y"). Results come from \#669 (paginated accessible courses).  
3. **Browse each course's outline.** Expanding a course reveals its sections and gradeable subsections (from the course outline — see \#669 / `CourseIndexView`). Sections are navigation; only gradeable subsections are the actionable leaves. For this ticket the subsections are **read-only** (browse only); making them actionable for association is \#672.


**Out of scope**

- The **full** Manage & Apply shell design and tree polish — the switcher styling, expand/collapse-all affordances, empty states, and responsive spec (\#648). This ticket builds only the minimal functional tree \+ selection needed to drive the right panel.  
- The Competency ID badge on tree rows (a separate ticket).  
- Any backend endpoint — this consumes \#669 (courses \+ outlines) and reuses the existing taxonomy tags API for the tree; it builds none.  
- Competency-to-course or section-level association — only gradeable subsections are associable (confirmed).  
- The select/deselect-association UI itself — that is ticket **\#672**, a separate design/build ticket. This ticket (\#670) ends at browsing-and-surfacing: it renders the gradeable-subsection rows and nothing more. \#672 adds its own select control to those rows.  
- End-date filtering (deferred past MVP).  
- The "Programs" button / program "P" icon, and any course-level associate button — these were removed from the design; do not build them regardless of what a screenshot shows.  
- The "Demonstrate Mastery For" rule header and its controls, and "Import Competency Framework" — separate, unrelated tickets.

<details>
<summary>Open Questions</summary>

- **\[non-blocking, owner: architect\] Boundary with the \#648 shell implementation.** \#648 is being reframed as a parent UX-design ticket with implementation children, one of which builds the full shell \+ competency tree. If that shell-implementation child lands, this ticket's minimal tree should be *absorbed/superseded* by it, not duplicated. Until it exists, the minimal tree lives here. Confirm the intended sequencing so the tree is built once.  
- **\[BLOCKING, owner: BA\] What was this ticket's "different confusion"?** An earlier note flagged this ticket for redoing "due to a different confusion" without specifying what. This rewrite assumes it's the course-vs-subsection level correction (associate at gradeable-subsection level; courses/sections are navigation). Confirm before this is treated as final.  
- **\[BLOCKING, owner: architect/implementer\] Where does the outline come from?** Either \#669 returns outlines inline, or this UI lazily calls the existing `CourseIndexView` (`GET /api/contentstore/v1/course_index/{course_id}`) per expanded course. This ticket's data layer should be written to whichever \#669 lands on. **\[recommended: lazy per-course CourseIndexView call on expand — lighter, reuses an existing endpoint\]**  
- **\[non-blocking, owner: designer\] Figma refresh.** The Figma is being updated (date picker representation; removing Programs button / P icon / course-associate button). Low rework risk for the tree/search/outline structure; re-verify the out-of-scope removal list against the refreshed Figma before build.
</details>
<details>
<summary>Context</summary>

- **Decision:** \#648 is being reframed as a parent UX-design ticket with implementation children. Because this is the first ticket that needs a competency selected, the minimal tree \+ selection belongs here rather than deferred to a later ticket.  
- **Decision (MVP):** the course filter is on course-run start date only; end-date filtering is deferred. React Date Picker (lightly styled with Paragon) fills the gap since Paragon has no native range picker.  
- **Decision:** criteria are associated only at the gradeable-subsection level; courses and sections are navigation, not association targets.  
- **Competency tree data:** the taxonomy tags list API already returns a competency taxonomy's tags (already satisfied, no backend work); the MFE data layer already carries them (`TagData` via `useTagListData` in `src/taxonomy/data/apiHooks.ts`, nested by `TagTree` in `src/taxonomy/tag-list/tagTree.ts`). No backend or data-layer change for the tree.  
- `CourseIndexView` (`GET /api/contentstore/v1/course_index/{course_id}`, `openedx-platform`): existing full course-outline endpoint (sections→subsections, with `graded` flag); the likely per-course outline source.  
- Tree-rendering precedents (frontend; none a drop-in): `src/taxonomy/tag-list/tagTree.ts` (`TagTree` nests a taxonomy's tags — the competency tree's basis); `src/taxonomy/tree-table/` `NestedRows`/`getSubRows` (arbitrary-depth recursion, bundled with tag-CRUD context to strip); `src/course-outline/OutlineTree.tsx` (real 3-level course tree, hardcoded depth and dnd/XBlock-coupled). Reuse `TagTree` for the competency tree; borrow the recursion pattern for the course outline.  
- `src/generic/datepicker-control/DatepickerControl.jsx` (wraps `react-datepicker`): the single-date picker to compose into a from/to range.  
- \#623: the placeholder Competency Management page this workspace lives inside.
</details>
<details>
<summary>Technical Notes</summary>

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/taxonomy/competency-management/associations/CompetencyAssociationsPanel.tsx` | Two-panel container: left competency tree \+ right course-browse panel; owns the selected-competency state that drives the right panel |
| `src/taxonomy/competency-management/associations/CompetencyTree.tsx` | Minimal selectable competency tree for the current taxonomy; reuses `TagTree`/tree-table recursion; emits the selected competency. No ID badge (separate ticket), no CRUD affordances |
| `src/taxonomy/competency-management/course-search/index.ts` | Public interface exporting the browse panel component |
| `src/taxonomy/competency-management/course-search/CourseSearchBrowse.tsx` | Search \+ date-range filter \+ paginated course list; each row expands to the outline tree; takes the active competency as input |
| `src/taxonomy/competency-management/course-search/CourseOutlineTree.tsx` | Recursive section→gradeable-subsection renderer; borrows `NestedRows`' recursion pattern, no TanStack/CRUD context |
| `src/taxonomy/competency-management/*/messages.ts` | i18n strings |
| `src/taxonomy/competency-management/course-search/data/api.ts` | `getCourseSearchResults(params)` (\#669), `getCourseOutline(courseKey)` (CourseIndexView or \#669 inline, per decision) |
| `src/taxonomy/competency-management/course-search/data/apiHooks.ts` | React Query hooks for course search and outline |
| `src/taxonomy/competency-management/course-search/data/queryKeys.ts` | Query-key factory |
| `src/taxonomy/competency-management/**/*.test.tsx` | RTL: tree renders \+ selection drives the panel \+ nothing rendered for the right-hand column before a selection; search, date filter (start-date semantics), expand, empty/error states |

### Files to Modify

| File | Nature |
| :---- | :---- |
| `src/taxonomy/competency-management/index.ts` | Re-export `CompetencyAssociationsPanel` alongside `CompetencyManagementPage` (from \#623) |
| the \#623 Competency Management page component | Mount `CompetencyAssociationsPanel` as the page's real content, replacing the placeholder |

### Implementation Notes

**Competency tree (minimal).** Reuse `useTagListData` (`src/taxonomy/data/apiHooks.ts`), which already returns a taxonomy's tags, and `TagTree` (`src/taxonomy/tag-list/tagTree.ts`) to render the current taxonomy's competencies as a nested, selectable tree. The taxonomy id comes from the `/taxonomy/:taxonomyId/competencies` route (\#623). Track the selected competency in `CompetencyAssociationsPanel` state and pass it (tag id / `external_id`) to the browse panel as its active competency. Keep it minimal: no ID badge (separate ticket), no create/remove or other CRUD affordances, no switcher/empty-state/responsive polish (\#648). Until a selection is made, the right panel is not rendered at all: no container, no background, no border, and no placeholder or prompt inside it. The right-hand column mounts only once a competency is selected, and no course query runs before that.

**Course browse.** Compose two data sources client-side: \#669 for the course list (start-date filter, pagination) and the outline per course (lazily on expand, via `CourseIndexView` unless \#669 returns it inline).

Date filter: compose two `DatepickerControl` instances into a from/to range bound to \#669's start-date parameter; label it as filtering on course start date. Don't send an end-date filter (MVP).

Build `CourseOutlineTree` as a plain recursive component (borrow `NestedRows`' `childRowsData`/`depth` shape; skip its TanStack table and CRUD context). Filter outline nodes to sections (navigation) and gradeable subsections (the actionable leaves) using the outline's `graded` flag; don't render unit/component levels. Subsections are read-only here and emit nothing: no row click handler and no selection callback. \#672 adds its own per-subsection select control to these rows when it lands, calling `associateSubsection(objectId, courseId)` and hiding that control per subsection according to the author's write access to the course. Neither the course id nor that permission is expressible through an always-on click on the whole row, so do not build one here in anticipation of \#672.

MFE-only; no ADR. Reuses `frontend-app-authoring` conventions (React Query, feature-folder, Paragon, `defineMessages`).

### Example Resolution Prompt

> In `frontend-app-authoring`, build the Competency Criteria associations workspace at `src/taxonomy/competency-management/`. `CompetencyAssociationsPanel.tsx`: a two-panel layout that owns the selected-competency state. Left panel `CompetencyTree.tsx`: render the current taxonomy's competencies (taxonomy id from the `/taxonomy/:taxonomyId/competencies` route, \#623) as a minimal selectable nested tree, reusing `useTagListData` (`src/taxonomy/data/apiHooks.ts`) and `TagTree` (`src/taxonomy/tag-list/tagTree.ts`); selecting a competency sets it active and drives the right panel; no ID badge (a separate ticket), no CRUD, no shell polish (\#648). Right panel `course-search/CourseSearchBrowse.tsx`: until a competency is selected the whole right-hand column is not rendered at all (no container, background, border, or prompt) and no query runs; once selected, a title search \+ a from/to date-range filter built from two `src/generic/datepicker-control/DatepickerControl.jsx` instances, bound to \#669's course-search endpoint (accessible courses filtered by course-run **start** date only; label it as such;). Paginated course list; each row expands. On expand, render `CourseOutlineTree.tsx`: fetch the course outline (via the existing `CourseIndexView`, `GET /api/contentstore/v1/course_index/{course_id}`, unless the team has \#669 return it inline — confirm), a plain recursive renderer (model on `src/taxonomy/tree-table/NestedRows.tsx`'s recursion, without its TanStack table or `TreeTableContext`) showing sections (navigation) and gradeable subsections (read-only leaves, filtered by the outline `graded` flag). Gradeable subsections are read-only leaves with no click handler and no selection callback; \#672 adds its own select control to these rows later. Mount the panel as the \#623 page's real content. Do NOT build any backend endpoint, any course-level or section-level association, a Programs button, or a course-associate button. Tests: tree renders and selection drives the panel, nothing rendered for the right-hand column before a selection, title search, start-date filtering, expand-to-outline, empty and error states, small-screen.

**Blocked by:** \#669 (the accessible-courses-by-date endpoint \+ course outlines) — a TBD contract; wire against it and flag real paths as fill-in-later. The competency tree itself has **no new backend dependency** — it reuses the existing taxonomy tags list API (a competency is a `Tag` in a competency taxonomy; that endpoint already returns them).

Repo: `frontend-app-authoring`. MFE-only. This ticket is \#670; the select/deselect-association UI is \#672.

</details>
