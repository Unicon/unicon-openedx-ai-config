# [FE] Manage & Apply Competencies: disable dominance-ineligible content before selection

GitHub: https://github.com/openedx/openedx-core/issues/797 (#797, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want content in a course that is already ineligible under the competency dominance rule to appear disabled with an explanation, in order to see that a selection would be rejected before I attempt it rather than only after \#666 rejects it.

## Acceptance Criteria

```
Scenario: Content in a course claimed by a related competency is disabled with a tooltip
  Given a competency above or below the competency being edited in the taxonomy already has
    an association in a course
  When I browse that course's content in the content panel
  Then every gradable subsection's select control in that course is disabled
  And hovering or focusing a disabled control shows a tooltip naming the competency it
    conflicts with, for example "Already associated with [Competency Name] in this course"

Scenario: A course claimed only by a sibling competency stays fully selectable
  Given a competency that is a sibling of the competency being edited, neither its ancestor
    nor its descendant, already has an association in a course
  And no ancestor or descendant of the competency being edited has an association in that
    same course
  When I browse that course's content in the content panel
  Then every gradable subsection's select control in that course remains enabled

Scenario: The competency being edited can have multiple associations in the same course
  Given the competency being edited already has an association with one gradable subsection
    in a course
  And no ancestor or descendant of the competency being edited has any association in that
    same course
  When I browse a different gradable subsection in that same course in the content panel
  Then that different subsection's select control remains enabled

Scenario: A different, unaffected course stays fully selectable
  Given a competency above or below the competency being edited in the taxonomy already has
    an association in one course
  When I browse a different course's content in the content panel
  Then every gradable subsection's select control in that other course remains enabled

Scenario: Content already associated with the competency being edited stays visually distinct
  Given a gradable subsection is already associated with the competency being edited
  And a different gradable subsection, in a course claimed by a related competency, is
    dominance-ineligible
  When I browse both subsections in the content panel
  Then the already-associated subsection shows its existing already-associated marking, with
    its select control enabled as it is today
  And the dominance-ineligible subsection shows a disabled select control with its
    explanatory tooltip
  And the two states are visually distinguishable from each other

Scenario: Content remains selectable while the blocked-courses data has not yet loaded
  Given the blocked-courses data for the currently displayed page of courses has not
    finished loading
  When I browse content in the content panel
  Then every gradable subsection's select control renders as if no course were blocked

Scenario: Content remains selectable when the blocked-courses fetch fails
  Given the blocked-courses fetch for the currently displayed page of courses has failed
  When I browse content in the content panel
  Then every gradable subsection's select control renders as if no course were blocked
  And no error is shown that blocks authoring, since #666 remains the authoritative check at
    write time regardless of whether this data loaded

Scenario: Navigating to a different page refetches blocked-courses scoped to that page
  Given the author is viewing one page of the course list
  And a course on a different page is blocked by a related competency
  When the author navigates to that different page
  Then the select controls on the newly displayed page reflect blocked-courses data fetched
    for that page's specific courses
  And no select control reflects stale blocked-courses data carried over from the previous
    page, or data for a course never requested
```

## Description

This ticket does not implement or change \#666's server-side dominance enforcement. It renders what a new backend endpoint already reports, so an author sees a conflict before attempting a selection instead of only after \#666 rejects it with a 400\. The course list is server-side paginated with a fixed page size (\#669/\#670), so this ticket only ever asks the backend about the courses on the page currently displayed, refetching as the author changes page, search term, or filter; it never fetches a whole competency's blocked-course list in one request. The block is resolved at the whole-course level: a course is either flagged by the endpoint or it is not, and every gradable subsection in a flagged course is treated identically, with no subsection-level distinction drawn. This is a per-course concern only, so it does not affect whether the content panel can open or browse a blocked course, and it is unrelated to an author's own existing associations with the competency being edited; see Technical Details for how this stays visually and mechanically separate from \#672's already-associated marking and from \#672/\#671's course-permission hiding.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking, not to bind them.

### In short

**Consuming the backend's answer verbatim, never recomputing it client-side.** The dominance rule cascades through a competency tag's whole ancestor and descendant chain in the taxonomy, and is resolved authoritatively by \#666 at write time. This ticket does not walk the taxonomy or recompute that chain: it fetches the sibling backend ticket's read-only endpoint, narrowed via its `course_keys` parameter to the currently displayed page of courses, and renders exactly what it reports. Reimplementing the rule here would risk it drifting from \#666's, the same reasoning \#672 already applied to `canEditCourse`.

**Extending the existing per-competency provider rather than building a parallel one.** \#672's `CompetencyAssociationsContext` already fetches and exposes per-course facts for the competency currently selected, remounting on `key={tagId}` so every per-competency value resets automatically when the author picks a different competency. This ticket adds one more such value, following the same shape as `canEditCourse(courseId)`: a lookup from a course to whether, and why, it is dominance-blocked for this competency. Because the underlying fetch is scoped to the current page of courses rather than the whole competency, the context also needs to know which courses that page contains; it gains a `notifyCoursesDisplayed(courseKeys: string[])` callback, mirroring the `notifyCourseExpanded(courseId)` callback \#672 already established for the same purpose (the panel tells the context what's currently visible), so the course-browse panel from \#670 can report each new page's course keys as the author navigates, searches, or filters.

**Disabling the select control and explaining why, reusing \#671's existing mechanism rather than inventing one.** \#671 already disables its "+ Rule" and "+ Rule Group" controls with a tooltip when an empty placeholder exists elsewhere on the page, wrapping the disabled button in a span so the tooltip still has something to trigger on, since a disabled native button fires no mouse or focus events. This ticket applies that same disabled-button-plus- tooltip treatment to the content panel's own select control, populating the tooltip with the conflicting competency's name from the endpoint's row instead of \#671's placeholder message. No new icon or visual language is introduced.

**This is a different situation from \#672/\#671's course-permission gating, and stays a different mechanism on purpose.** `canEditCourse` hides its controls entirely, because an author with no write access to a course has no legitimate reason to see a control there at all. Here, the author generally can add associations in this course; only this specific piece of content is blocked for a taxonomy reason they need to understand, or the disabled control reads as broken. The select control must therefore stay visible and self-explanatory rather than disappearing, and this ticket must not reuse the hide-entirely pattern for it.

**Failing open when the data isn't ready.** While the blocked-courses fetch for the currently displayed page of courses is still loading or has failed, this ticket treats every course on that page as unblocked rather than gray out anything. \#666 remains the authoritative enforcement at write time regardless of whether this UI hint loaded, so a stale or missing read only costs an author an occasional rejected attempt, which is a smaller failure than blocking every selection in the page whenever this one fetch is slow or down. This is the opposite default from `canEditCourse`, which denies until an answer arrives; the two lookups fail toward opposite defaults because getting a permission check wrong risks a write the author was never allowed to make, while getting this one wrong only costs a redundant attempt \#666 will still catch.

### Implementation specifics

- **API function.** `getBlockedCourses(tagId, courseKeys)` in `src/taxonomy/competency-management/data/api.ts`, hitting the sibling ticket's `GET /cbe/rest_api/v1/competencies/<tag_id>/blocked-courses/` with `courseKeys` passed through as the endpoint's `course_keys` query parameter, following the same `apiUrls` and `getAuthenticatedHttpClient()` conventions as this feature's other API functions.  
- **Read hook.** `useBlockedCourses(tagId, courseKeys)` in `data/apiHooks.ts`, a `useQuery` gated with `enabled: tagId !== undefined && courseKeys.length > 0`, so the fetch is dependent: it only runs once both the selected competency and the current page's course keys are known. The query key must include `courseKeys` alongside `tagId`, e.g. `competencyQueryKeys.blockedCourses(tagId, courseKeys)`; a naive `competencyQueryKeys.blockedCourses(tagId)` key would incorrectly reuse a previous page's cached data when only the page changes, since a different page is a different, independent fetch. The endpoint's envelope is paginated; the hook pages through the full result for the requested `courseKeys` before the derived map below is built, the same as this MFE's other paginated DRF list consumers.  
- **Derivation.** Add a helper to `utils.ts` that reduces the fetched rows into a map from a course's identifier to the conflicting competency's id and value, keyed by whatever identifier the row names as the course's key. Confirm that identifier matches the course identifier `CompetencyAssociationsContext` and the content panel already use for a course (see Open Questions); this ticket does not introduce a second, competing course identifier.  
- **Provider addition.** Add `dominanceConflictForCourse(courseId): { competencyId: number; competencyValue: string } | null` to `CompetencyAssociationsContext.tsx`'s context value, backed by `useBlockedCourses(tagId, courseKeys)` and the map above, where `courseKeys` is the current page's course keys as reported through `notifyCoursesDisplayed` (below). Returns `null` while the query is loading, on failure, and for any course absent from the map; returns the conflicting competency's id and value only for a course the endpoint actually lists. Never returns a value derived from anything other than this one fetch, and never from a page other than the one currently displayed.  
- **Reporting the current page to the context.** Add `notifyCoursesDisplayed(courseKeys: string[])` to `CompetencyAssociationsContext.tsx`, mirroring the shape of \#672's existing `notifyCourseExpanded(courseId)` (the panel tells the context what's currently visible). The course-browse panel from \#670 calls it whenever its page, search, or filter state changes and it receives a new page of courses back from the paginated course-list query \#669/\#670 already build, so the context always holds the course keys `useBlockedCourses` should be scoped to.  
- **Wiring into the content panel's select control.** The select control \#672 already adds to each content-panel row, gated there by `canEditCourse(courseId)`, is extended with a second, independent check: when `dominanceConflictForCourse(courseId)` is non-null, render the same control disabled and wrapped for a tooltip, using the conflicting competency's value in the tooltip text. The two gates are independent and can both apply to the same row; neither's absence implies anything about the other.  
- **No re-validation on selection.** `associateSubsection` is not touched by this ticket. A disabled control cannot be clicked, so there is nothing to guard against on the create path; a race where this read is stale and the author still manages to attempt a blocked selection is left to \#666's existing 400 rejection, which the create mutation's error handling already surfaces.  
- **All user-facing strings**, including the tooltip message, go through `defineMessages` in the feature's `messages.ts`, per this MFE's i18n convention.  
- **Module boundaries.** Import other features only through their `index.ts`; do not import upward from `competency-management` into `taxonomy`. Nothing here touches `openedx-core`, so its import-layering and DEPR rules do not apply.  
- **Out of scope, owned elsewhere.** The blocked-courses endpoint itself is the backend sibling ticket, not yet numbered, referenced in Context. Any change to \#666's server-side enforcement is out of scope. Subsection-level granularity is out of scope; a blocked course's gradable subsections are all treated identically. Course-level (final-grade) associations and the "same content path" rule are out of scope and not applicable to current scope.  
- **Test cases to cover.**  
  - A course present in the blocked-courses response disables the select control on every gradable subsection in that course, each carrying a tooltip naming the conflicting competency.  
  - A course absent from the response, including one where only a sibling competency has an association, leaves every select control in that course enabled.  
  - A course where only the competency being edited itself already has an association (no ancestor or descendant relative involved) leaves every other select control in that same course enabled — the same competency is never its own ancestor or descendant, so it can never trigger this rule against itself.  
  - A different course than the one flagged remains fully enabled.  
  - A subsection already associated with the competency being edited keeps its existing already-associated marking and an enabled select control, distinct from a disabled, dominance-ineligible subsection elsewhere in the panel.  
  - While `useBlockedCourses` is loading for the currently displayed page, every select control renders enabled.  
  - When `useBlockedCourses` fails for the currently displayed page, every select control renders enabled and no blocking error is shown.  
  - Switching to a different competency (`key={tagId}` remount) refetches blocked courses for the current page and does not carry over the previous competency's conflicts.  
  - Navigating to a different page, or changing the course list's search term or filter, calls `notifyCoursesDisplayed` with the newly displayed page's course keys, triggers a fresh `useBlockedCourses` fetch scoped to those keys, and does not carry over the previous page's conflicts into the new page's select controls.  
  - When the blocked-courses endpoint's own response for the requested `courseKeys` spans more than one page, `useBlockedCourses` follows `next` until exhausted before the derived map is built, rather than assuming a filtered request always fits in one page — every requested course's conflict, not just the first page's worth, is reflected in the rendered select controls.  
  - A course flagged by the endpoint and also gated by `canEditCourse` returning false renders with the control hidden, per `canEditCourse`, not merely disabled, since the two checks are independent and hiding takes precedence over disabling for the same row.

Files to create and modify This ticket creates no new files; it extends files \#672 and \#670 already create.

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/competency-management/data/api.ts` | Add `getBlockedCourses(tagId, courseKeys)`, passing `courseKeys` through as the endpoint's `course_keys` query parameter. |
| `src/taxonomy/competency-management/data/apiHooks.ts` | Add `useBlockedCourses(tagId, courseKeys)` and its query key (keyed on both `tagId` and `courseKeys`), enabled only once both are available, paging through the full paginated response for the requested course keys. |
| `src/taxonomy/competency-management/data/types.ts` | Add the blocked-courses response row type. |
| `src/taxonomy/competency-management/utils.ts` | Add the reducer from fetched rows to a course-id-to-conflict map. |
| `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx` | Add `dominanceConflictForCourse(courseId)` to the context value, backed by `useBlockedCourses(tagId, courseKeys)`; add `notifyCoursesDisplayed(courseKeys: string[])`, mirroring `notifyCourseExpanded`, so the current page's course keys reach the provider. |
| The content panel component from \#670 (the course-browse panel) | Extend the select control \#672 adds with a second, independent disabled-plus-tooltip state driven by `dominanceConflictForCourse(courseId)`; call `notifyCoursesDisplayed(courseKeys)` whenever its page, search, or filter state changes and it receives a new page of courses back from the paginated course-list query \#669/\#670 already build. |
| `src/taxonomy/competency-management/messages.ts` | Add the tooltip message naming the conflicting competency. |

- Context \#666 defines and enforces the dominance rule this ticket only surfaces ahead of time; it remains the sole authority, and this ticket makes no change to it.  
- The backend sibling ticket, not yet numbered, provides `GET /cbe/rest_api/v1/competencies/<tag_id>/blocked-courses/`, a paginated envelope of rows each carrying a blocked course's key and the conflicting competency's id and value, optionally narrowed via its `course_keys` query parameter to a caller-supplied set of course keys. This ticket's only data source is that endpoint, and it always supplies `course_keys` scoped to the currently displayed page of courses rather than omitting it.  
- \#672 builds `CompetencyAssociationsContext`, its `canEditCourse(courseId)` per-course lookup pattern this ticket's `dominanceConflictForCourse` mirrors, the content panel's select control this ticket extends, and the `associatedObjectIds` already-associated marking this ticket must stay visually distinct from.  
- \#671 is the source of the disabled-button-plus-tooltip mechanism this ticket reuses without modification: a disabled control wrapped in a span so it still has a tooltip trigger, since a disabled native button fires no mouse or focus events.  
- \#669 is the paginated `GET /api/contentstore/v2/home/courses` endpoint the course-browse panel's course list is sourced from; its server-side pagination is why this ticket's fetch is scoped to one page's course keys rather than a whole competency's.  
- \#670 builds the course-browse panel itself ("Paginated course list; each row expands," using \#669's paginated endpoint), confirming the author only ever has one page's worth of courses on screen at a time. That confirmed, fixed-page-size pagination is what makes "the currently displayed page" a well-defined, non-ambiguous set of course keys for `notifyCoursesDisplayed` to report and `useBlockedCourses` to fetch against.

</details>
