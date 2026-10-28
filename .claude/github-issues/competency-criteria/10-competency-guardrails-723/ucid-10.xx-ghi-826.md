# [FE] Show competency criteria whose gradeable subsection has been deleted

GitHub: https://github.com/openedx/openedx-core/issues/826 (#826, OPEN)
Cached: 2026-10-22

## User Story

As a course author managing a competency's criteria, I want a criterion whose gradeable subsection has been deleted to be shown as unresolvable, in order to recognize a rule that a learner can no longer complete.

## Acceptance Criteria

    Scenario: A criterion whose subsection was deleted is still listed
      Given a criteria group contains a criterion for a gradeable subsection
        And that subsection has since been deleted from its course
      When I open that competency's criteria on the Competency Management page
      Then the criterion is listed in its rule box alongside the group's other criteria
        And in place of a subsection title it shows a "Content unavailable" chip, with the Warning icon
        next to the text

    Scenario: An unresolvable criterion is distinguishable at a glance
      Given a criteria group contains one criterion whose subsection still exists and one whose
        subsection was deleted
      When I view that group
      Then the deleted subsection's criterion shows the "Content unavailable" chip and the Warning
        icon, which the other criterion does not
        And the criterion whose subsection still exists shows its subsection title as it does today

    Scenario: The course the deleted subsection belonged to is named
      Given a criterion whose subsection was deleted
      When I view it
      Then the "From within ..." header of the rule box that holds the criterion names the course
        the subsection belonged to
        And two unresolvable criteria from different courses are told apart by their rule boxes'
        "From within ..." headers

    Scenario: A course's criteria are replaced by a loading placeholder while its outline loads
      Given a criteria group contains criteria for subsections in a course
      When I view that group before the course's outline has loaded
      Then that course's criteria are replaced by one ghosted placeholder rule box showing a loading
        spinner, rather than a loading state on each criterion
        And no criterion is labelled "Content unavailable" while the outline is still loading
        And once the outline has loaded, the placeholder is replaced by the criteria, each showing
        its subsection title or the "Content unavailable" chip

    Scenario: A failed or refused subsection lookup shows the same "Content unavailable" chip
      Given a criterion points at a subsection in a course whose outline cannot be read, either
        because the request fails or because I do not have access to that course
      When I view its group
      Then the criterion shows the "Content unavailable" chip with the Warning icon, the same as a
        criterion whose subsection was deleted, because the page cannot tell the two cases apart
        And the group's other criteria still render normally

    Scenario: A group whose every criterion is unresolvable still renders
      Given every criterion in a criteria group points at a deleted subsection
      When I view that group
      Then the group renders with each of its criteria showing the "Content unavailable" chip
        And the group is not shown as empty

    Scenario: The unresolvable state is available to a keyboard and screen reader user
      Given a criterion whose subsection was deleted
      When I move through its group using a keyboard or a screen reader
      Then the "Content unavailable" state is conveyed in text, not by color or the icon alone

    Scenario: The unresolvable criterion is usable on a small screen
      Given a criterion whose subsection was deleted
      When I view its group on a small screen
      Then its "Content unavailable" chip and its rule box's "From within ..." header stay readable
        without the layout overflowing

## Description

The Competency Management page lists a competency's criteria inside the criteria groups, and
shows each criterion as the gradeable subsection it points at (#672). A criterion identifies that
subsection by a usage key stored on the tagging row, with no database reference to the
content itself, and the page resolves the key to a title by looking it up in the
course's outline.

Deleting a gradeable subsection from a course leaves the criterion, its tagging row,
and every learner's recorded competency status in place. This is done so that mastery a learner has already demonstrated is not taken away because someone edited the course afterwards. What the deletion does remove is the assignment's entry in the course outline, and that entry is where the page gets the assignment's name from. With no name to display, the requirement isn't visable on the page. So a competency can end up carrying a requirement that can't ever meet again, with nothing on the page to indicate that.

This ticket makes those broken criteria visible.

Figma Designs:
[U1 · Content unavailable](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3149-32046)
[U3 · Loading](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3149-32204)

<img width="1600" height="1161" alt="Image" src="https://github.com/user-attachments/assets/7d97f7b3-7f6c-44aa-870e-007c3671ee30" />

<img width="1600" height="1161" alt="Image" src="https://github.com/user-attachments/assets/f1a92dc6-f9e9-49b6-8fb5-c839901212aa" />

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User
Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Nothing on the backend hides these criteria, so no backend change is needed.** The tagging row
a criterion points at stores the subsection as a plain opaque string with no foreign key to course
content and no resolver, and criterion creation validates only that the string parses as a usage
key whose course matches the group's scope. Deleting the subsection leaves every one of those rows
untouched, so the endpoint that returns a competency's groups and criteria returns an orphaned
criterion like any other. The one backend requirement is a negative one, that this read path never
acquires a filter on whether the content still exists, which is recorded in Open Questions rather
than built here.

**How the page decides a criterion is unresolvable.** Subsection titles are resolved on the client
by taking the criterion's usage key, reading the outline of the course that key names, and finding
the matching node. A criterion counts as unresolvable when that outline was read and contains no
node with that usage key, and also when the outline could not be read at all, because the request
failed or the author has no access to the course: from the client the two cases look the same, so
both show the same "Content unavailable" chip. A request still in flight is the one state that is
not a verdict: while a course's outline loads, that course's criteria are replaced by one ghosted
placeholder rule box with a `LoadingSpinner`, so no criterion is labelled before its outline has
been checked.

**Which course outlines the page loads, and through which query.** Parse the course key out of
each criterion's usage key, reduce that to the distinct set of courses the competency's criteria
reference, and read one outline per course. The page needs exactly these outlines anyway to title
the criteria that do resolve, so this adds no request that titling does not already require. Read
them through the same cached query the course browse panel uses rather than a second request path,
so a course already expanded in the browse panel costs nothing to resolve here.

**What the criterion shows in place of a title.** The "Content unavailable" chip, with Paragon's
`Warning` icon next to the text, so the state is named in words rather than by an icon or a color
alone. The course the subsection belonged to is not repeated on the criterion: the rule box that
holds it already names the course in its "From within ..." header, which is how an author with
several unresolvable criteria tells which course each one came from.

### Implementation specifics

- **Extend the Selected Content components #672 adds** under
  `src/taxonomy/competency-management/criteria-groups/`, rather than introducing a parallel
  rendering path for these criteria.
- **Derive the course key with `getCourseKey` from `src/generic/key-utils.ts`.** It throws on a
  string it cannot parse, so wrap the call: a criterion whose stored key does not parse as a course
  block key is unresolvable with no course to name, and must not break the surrounding list.
- **Read outlines through the query the course browse panel already uses.**
  `useCourseOutlineIndex` (`src/course-outline/data/outlineIndexQuery.ts`) wraps
  `getCourseOutlineIndex` and keys on `courseOutlineQueryKeys.index(courseId)`. The number of
  courses is only known at render time, so a hook call per course is not possible: build the batch
  with `useQueries` over that same key factory and query function, following the batching precedent
  in `src/content-tags-drawer/data/apiHooks.ts`. Reusing the key factory is what makes these
  entries share the browse panel's cache instead of duplicating its requests. Carry the hook's own
  `retry: false` and pass `refetchOnMount: false`, matching how the browse panel reads outlines.
- **Search the returned structure's full section-to-subsection tree** for the usage key, starting
  at `courseStructure` on the response envelope (`CourseOutline`, `src/course-outline/data/types.ts`)
  and recursing through each node's `childInfo.children`; the node fields come from `XBlockBase` and
  `XBlock` in `src/data/types.ts`. Do not assume a position or depth, and do not match on title.
- **Branch on the query state explicitly.** A pending outline query renders the ghosted placeholder
  rule box with a `LoadingSpinner` for that course's criteria. A successful read with no matching
  usage key and a failed read, including a permission failure, both render the "Content
  unavailable" chip.
- **Do not block the criteria list on the outline queries.** Render the groups at once, with each
  course's criteria behind its placeholder, then replace each placeholder with the criteria as that
  course's outline settles.
- **Scope a failed outline read to the criteria that depend on it.** One unreadable course marks
  only its own criteria "Content unavailable" and must not take down the rest of the competency's
  criteria.
- **Memoize the distinct course-key list on the criteria query's own data reference**, not on an
  array recomputed inline in the same render. A dependency rebuilt every render defeats the
  memoization silently, with no type error or failing test to catch it, and here it would refire a
  batch of outline queries.
- **Use Paragon's `Warning` icon from `@openedx/paragon/icons` alongside the text label**, not in
  place of it, and do not distinguish the state by color alone.
- **Carry the accessible text in a visually hidden `sr-only` sibling span, not in an `aria-label`
  on the wrapper.** A plain `span` or `div` takes the implicit `generic` role, which prohibits
  `aria-label` and is not reliably announced. `CompetencyTreeItem.tsx` in the same directory already
  does this for the tree's own accessible labels.
- **Style the state by overriding Paragon's own design tokens, not the resolved CSS properties.**
  Trace the token's resolution in the installed theme first: if it already resolves to the intended
  value, the override is dead code and should not be added. Use a relative unit (`rem`, `%`) for any
  typography token, as Paragon's own defaults do, even if a design spec names a pixel value.
- **Prefer Paragon's grid for the small-screen behavior** over new media queries, as the
  associations panel does with `Row`/`Col`. If a component-local SCSS file is added and does use
  Paragon's custom-media breakpoint names, add
  `@use "@openedx/paragon/styles/css/core/custom-media-breakpoints.css"` in that file: a component
  SCSS imported from its own `.tsx` compiles as its own root stylesheet and does not inherit the
  `@use` in `src/index.scss`, and an unresolved custom-media name is not a syntax error, so the rule
  compiles and then silently never matches. The lint and unit-test commands do not compile Sass, so
  verify any new at-rule by test-compiling the file exactly as the bundler imports it.
- **Key any selector for a criterion inside a nested group off the class marking the group unit**
  (for example `.criteria-group > ul`), not a fixed structural depth (`> ul > li > ul`), which
  matches one nesting level and stops applying past it.
- **Do not add a backend existence flag to the criteria read endpoint.** That endpoint lives in
  `openedx-core`, which must not import from `openedx-platform` (enforced by `.importlinter`), so
  it cannot resolve a usage key against the modulestore or the content search index. Resolution
  stays on the client, which is also where titling already happens.
- **Tests:** a criterion whose usage key is absent from a successfully read outline renders the
  "Content unavailable" chip and the warning icon; a criterion present in the outline renders its
  title unchanged; a pending outline query renders the ghosted placeholder rule box with a spinner
  for that course and no "Content unavailable" chip; a failed outline query and a 403 each render
  the "Content unavailable" chip; a group whose every criterion is unresolvable renders all of them;
  an unparseable stored key renders the chip without throwing; several criteria in one course fire
  a single outline query rather than one per criterion, and re-rendering fires no further ones; the
  "Content unavailable" state is present as text in the DOM; the chip and the rule box header stay
  within the layout at a small viewport width.
- **Out of scope:** removing an unresolvable criterion, which moved to a follow-up ticket in the
  10/13 rescope; a tooltip or other way to expose the stored usage key, which is its own follow-up;
  the learner-facing progress surface, which faces the same situation and has its own design work
  ahead of it; the warning shown before deleting a subsection on the Course Outline page; any job
  that prunes or reports orphaned criteria in bulk; and any competency-level indication that a
  competency's rules can no longer be satisfied.

</details>

<details>
<summary>Files to create and modify</summary>

`src/taxonomy/competency-management/` holds the Competency Management page, its competency tree,
and its shared `messages.ts` (#680), with the associations panel and course browse panel in its
`associations/` and `course-search/` subdirectories (#670). The Selected Content components this
ticket extends are added by #672 in the same tree; the rows below extend them rather than replacing
them.

**New files**

| File | Purpose |
| --- | --- |
| `src/taxonomy/competency-management/criteria-groups/useSubsectionResolution.ts` | Batches one course-outline query per distinct course key across a competency's criteria and reports each criterion as resolved, unavailable, or pending. Sits alongside the `associations/` and `course-search/` directories of the same page |
| `src/taxonomy/competency-management/criteria-groups/useSubsectionResolution.test.ts` | Covers the three resolution states and the unparseable-key case |

**Modified files**

| File | Nature of modification |
| --- | --- |
| `src/taxonomy/competency-management/criteria-groups/SelectedContentItem.tsx` | Render the "Content unavailable" chip with the warning icon in place of a subsection title, and the ghosted placeholder rule box with a spinner while the course's outline loads |
| `src/taxonomy/competency-management/criteria-groups/SelectedContentList.tsx` | Pass each criterion's resolution result through to its item |
| `src/taxonomy/competency-management/messages.ts` | Copy for the "Content unavailable" label |
| `src/taxonomy/competency-management/criteria-groups/*.test.tsx` | Component coverage for the scenarios above, including the small-viewport and text-in-DOM assertions |

</details>

<details>
<summary>Context</summary>

- #672 lists a group's criteria in its Selected Content area and owns the components this ticket
  extends.
- #670 provides the associations panel and the course browse panel, and establishes reading a
  course outline lazily per course through `useCourseOutlineIndex`.
- #680 provides the Competency Management page, its competency tree, and the page's `messages.ts`.
- `src/generic/key-utils.ts` for `getCourseKey`; `src/course-outline/data/outlineIndexQuery.ts` for
  `useCourseOutlineIndex` and `src/course-outline/data/queryKeys.ts` for the key factory to batch
  over; `src/course-outline/data/types.ts` and `src/data/types.ts` for the outline envelope and its
  node fields; `src/content-tags-drawer/data/apiHooks.ts` for the `useQueries` batching precedent.
- `src/taxonomy/competency-management/CompetencyTreeItem.tsx` for the `sr-only` accessible-label
  precedent this page already follows, and `src/taxonomy/competency-management/messages.ts` for
  where its copy lives.
- `.claude/frontend-app-authoring-architecture-overview.md` for the authoring frontend's conventions
  and how it consumes this library's APIs.

</details>

## Open Questions

- The endpoint that returns a competency's criteria groups and criteria must return criteria whose
  stored subsection key no longer resolves to live content, rather than filtering them out or
  failing on them. Nothing in the data model filters them today, so this is a requirement to record
  on that endpoint's ticket rather than work for this one. Owner: BA and architect, to fold into
  that ticket and link its issue number here.
