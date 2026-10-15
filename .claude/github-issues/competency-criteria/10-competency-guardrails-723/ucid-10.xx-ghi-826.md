# [FE] Show and remove competency criteria whose gradeable subsection has been deleted

GitHub: https://github.com/openedx/openedx-core/issues/826 (#826, OPEN)
Cached: 2026-10-14

## User Story

As a course author managing a competency's criteria, I want a criterion whose gradeable subsection has been deleted to be shown as unresolvable and allow me to remove it, in order to recognize a rule that a learner can no longer complete and remove it from the competency.

## Acceptance Criteria

    Scenario: A criterion whose subsection was deleted is still listed
      Given a criteria group contains a criterion for a gradeable subsection
        And that subsection has since been deleted from its course
      When I open that competency's criteria on the Competency Management page
      Then the criterion is listed in its group alongside the group's other criteria
        And it is labelled as an unresolvable subsection instead of showing a subsection title

    Scenario: An unresolvable criterion is distinguishable at a glance
      Given a criteria group contains one criterion whose subsection still exists and one whose
        subsection was deleted
      When I view that group
      Then the unresolvable criterion carries a warning indication that the other criterion does not
        And the criterion whose subsection still exists shows its subsection title as it does today

    Scenario: The course the deleted subsection belonged to is named
      Given a criterion whose subsection was deleted
      When I view it
      Then the course that subsection belonged to is identified on the criterion
        And two unresolvable criteria from different courses are told apart by that course name

    Scenario: Removing an unresolvable criterion
      Given a criteria group contains a criterion whose subsection was deleted
      When I remove that criterion
      Then it is no longer listed in the group
        And the group's other criteria are still listed
        And I am asked to confirm the removal in the same way I am for any other criterion

    Scenario: A subsection title that has not loaded yet is not reported as unresolvable
      Given a criterion whose subsection still exists
      When I view its group before its subsection title has loaded
      Then the criterion shows a loading state
        And it is not labelled unresolvable

    Scenario: A failed or refused subsection lookup is not reported as unresolvable
      Given a criterion points at a subsection in a course whose outline cannot be read, either
        because the request fails or because I do not have access to that course
      When I view its group
      Then the criterion shows that its subsection could not be checked
        And it is not labelled unresolvable
        And the group's other criteria still render normally

    Scenario: A group whose every criterion is unresolvable still renders
      Given every criterion in a criteria group points at a deleted subsection
      When I view that group
      Then the group renders with each of its criteria labelled unresolvable
        And the group is not shown as empty

    Scenario: The unresolvable state is available to a keyboard and screen reader user
      Given a criterion whose subsection was deleted
      When I move through its group using a keyboard
      Then the unresolvable state is conveyed in text, not by color or an icon alone
        And the criterion's removal control receives focus and is announced

    Scenario: The unresolvable criterion is usable on a small screen
      Given a criterion whose subsection was deleted
      When I view its group on a small screen
      Then its label and the course it belonged to stay readable without the layout overflowing
        And its removal control is reachable

## Description

The Competency Management page lists a competency's criteria inside the criteria groups, and
shows each criterion as the gradeable subsection it points at (#672). A criterion identifies that
subsection by a usage key stored on the tagging row, with no database reference to the
content itself, and the page resolves the key to a title by looking it up in the
course's outline.

Deleting a gradeable subsection from a course leaves the criterion, its tagging row,
and every learner's recorded competency status in place. This is done so that mastery a learner has already demonstrated is not taken away because someone edited the course afterwards. What the deletion does remove is the assignment's entry in the course outline, and that entry is where the page gets the assignment's name from. With no name to display, the requirement isn't visable on the page. So a competency can end up carrying a requirement that can't ever meet again, with nothing on the page to indicate that.

This ticket makes those broken criteria visible, and allows the user to removable them.

[Figma Design](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3149-32046&t=4aB6WHRUR0eYluqv-1)

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/50041e84-483d-4da7-94eb-ce5795a684dc" />

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
the matching node. A criterion counts as unresolvable only when that outline was read successfully
and contains no node with that usage key. Every other state is not evidence of a deletion: a
request still in flight, a request that failed, and a course the author has no access to must each
render as their own state. Treating them as deletions would show authors phantom warnings whenever
a request failed.

**Which course outlines the page loads, and through which query.** Parse the course key out of
each criterion's usage key, reduce that to the distinct set of courses the competency's criteria
reference, and read one outline per course. The page needs exactly these outlines anyway to title
the criteria that do resolve, so this adds no request that titling does not already require. Read
them through the same cached query the course browse panel uses rather than a second request path,
so a course already expanded in the browse panel costs nothing to resolve here.

**Removal needs no new endpoint.** The single-criterion removal endpoint (#674) takes a criterion
id, decides internally between deleting the row and archiving it depending on whether a learner
status row references it, and never touches the shared tagging row. None of that depends on the
subsection existing, so an unresolvable criterion removes exactly like any other one.

**What the criterion shows in place of a title.** Name the state in words rather than leaning on an
icon or a color, and include the course the deleted subsection belonged to, so an author with
several unresolvable criteria can tell which course each one came from and judge which competency
rule is affected.

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
- **Branch on the query state explicitly.** Only a successful outline read with no matching usage
  key yields the unresolvable state; pending and error states each render their own state, and a
  permission failure is an error, not a deletion.
- **Do not block the criteria list on the outline queries.** Render the groups and their criteria
  first with titles pending, then settle each criterion as its course's outline resolves.
- **Scope a failed outline read to the criteria that depend on it**, the way the course browse panel
  renders a per-course outline failure as an inline error on that course's row rather than failing
  the whole panel. One unreadable course must not take down the rest of the competency's criteria.
- **Leave the removal control enabled while a title lookup is pending.** Removal needs only the
  criterion id, which the criteria response already carries, so it does not depend on the outline
  queries and must not be gated on them.
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
- **Reuse the confirmation the criteria removal flow already shows.** Do not add a second dialog or
  write new confirmation copy for this case.
- **A removed criterion that carries learner status is archived rather than deleted**, and archived
  records are excluded from read paths, so the criterion leaves the list on either branch without
  this ticket special-casing the outcome.
- **Tests:** a criterion whose usage key is absent from a successfully read outline renders the
  unresolvable label, the warning icon, and its course; a criterion present in the outline renders
  its title unchanged; a pending outline query renders a loading state and not the unresolvable
  label; a failed outline query and a 403 each render the could-not-check state and not the
  unresolvable label; a group whose every criterion is unresolvable renders all of them; an
  unparseable stored key renders unresolvable without a course and without throwing; removal posts
  the criterion id to the removal endpoint and drops the criterion from the list; several criteria
  in one course fire a single outline query rather than one per criterion, and re-rendering fires no
  further ones; the unresolvable state is present as text in the DOM; the label and course stay
  within the layout at a small viewport width.
- **Out of scope:** the learner-facing progress surface, which faces the same situation and has its
  own design work ahead of it; the warning shown before deleting a subsection on the Course Outline
  page; any job that prunes or reports orphaned criteria in bulk; and any competency-level
  indication that a competency's rules can no longer be satisfied.

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
| `src/taxonomy/competency-management/criteria-groups/useSubsectionResolution.ts` | Batches one course-outline query per distinct course key across a competency's criteria and reports each criterion as resolved, unresolvable, pending, or unreadable. Sits alongside the `associations/` and `course-search/` directories of the same page |
| `src/taxonomy/competency-management/criteria-groups/useSubsectionResolution.test.ts` | Covers the four resolution states and the unparseable-key case |

**Modified files**

| File | Nature of modification |
| --- | --- |
| `src/taxonomy/competency-management/criteria-groups/SelectedContentItem.tsx` | Render the unresolvable, pending, and unreadable states in place of a subsection title, with the warning icon, the text label, and the course |
| `src/taxonomy/competency-management/criteria-groups/SelectedContentList.tsx` | Pass each criterion's resolution result through to its item |
| `src/taxonomy/competency-management/messages.ts` | Copy for the unresolvable, pending, and unreadable labels |
| `src/taxonomy/competency-management/criteria-groups/*.test.tsx` | Component coverage for the scenarios above, including the small-viewport and text-in-DOM assertions |

</details>

<details>
<summary>Context</summary>

- #672 lists a group's criteria in its Selected Content area and owns the components this ticket
  extends.
- #670 provides the associations panel and the course browse panel, and establishes reading a
  course outline lazily per course through `useCourseOutlineIndex`.
- #680 provides the Competency Management page, its competency tree, and the page's `messages.ts`.
- #674 removes a single criterion by id, branching between deletion and archiving.
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
- What should the label read? "Unknown subsection" and "Deleted subsection" both claim more than
  the page can prove, since an unreadable course looks the same from the client as a deleted
  subsection, and only a successful outline read distinguishes them. Owner: designer, with the BA.
- Should the criterion expose the stored usage key, for instance on hover or behind an expand, so a
  support engineer can identify the content that was deleted? Owner: designer.
- Should a criterion in a course the author has no access to read differently from one whose outline
  request failed? They are the same state to the client, but an author with partial course access
  would see the second message permanently. Owner: designer, with the BA.
