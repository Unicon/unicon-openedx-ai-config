# [FE] Implement the plan to handle large quantities of competency criteria associations (pagination, filtering, cues to user, other?) on the frontend

GitHub: https://github.com/openedx/openedx-core/issues/683 (#683, OPEN)
Cached: 2026-10-22

## User Story

As a course author, I want the associations panel to show only the associations in the courses currently listed beside it, and the page to say how much of the course list and of the competency's associations that leaves out of view, in order to keep editing a competency reused across many course runs without loading and scrolling every run it has ever been attached to, and without mistaking a narrowed view for an unused competency.

## Acceptance Criteria

```
Scenario: The associations panel opens scoped to the courses first listed
  Given a competency has associations in courses that span more than one page of the course list
  When I select that competency
  Then the associations panel shows a course-level group only for those of its courses that are
    currently listed in the course list
  And it shows no course-level group for any course that is not currently listed

Scenario: Turning to another page of courses re-scopes the associations panel
  Given I am viewing a competency's associations for the courses on one page of the course list
  When I move to a different page of the course list
  Then the associations panel shows course-level groups only for the courses now listed
  And no course-level group, bottom-tier group, rule box, or chip belonging to the previously
    listed courses remains once the newly listed courses' associations have loaded

Scenario: Searching or changing the date filter re-scopes the associations panel
  Given I am viewing a competency's associations
  When I enter a course title search term, or change the course start-date range
  Then the associations panel shows course-level groups only for the courses the narrowed course
    list now shows
  And it shows no course-level group for a course the narrowed list excludes

Scenario: An association outside the listed courses comes back when its course is listed again
  Given a competency has an association in a course that is not among the courses currently listed
  Then the associations panel shows nothing for that course
  When I page, search, or filter the course list so that course is listed again
  Then that course's course-level group is shown again, with the same bottom-tier groups, rule
    boxes, and chips it had before

Scenario: A listed course with no associations still gets no course-level group
  Given a course among those currently listed has no associations for this competency
  When I view the associations panel, whether or not I have expanded that course in the course
    list
  Then no course-level group is shown for that course

Scenario: The summary states how many courses are listed out of all I can reach
  Given I have entered no course title search term and set no start-date range
  When I view the page
  Then the page states how many courses are currently listed and how many courses I can access
    in total
  And it names no search term and no date range, because neither is applied

Scenario: The summary names whichever filters narrowed the course list
  Given I enter a course title search term, or set a start-date range, or both
  When the course list narrows
  Then the page states how many courses are now listed out of the total I can access
  And it names each filter I have applied, and only those I have applied

Scenario: The summary states how many associations are in view and how many exist in total
  Given a competency has associations in courses that span more than one page of the course list
  When I view the page
  Then the page states how many of the competency's criteria associations are in view and how
    many the competency has in total
  And the number in view is smaller than the total
  And the number in view accounts only for the courses the same line states as currently listed

Scenario: The two association numbers match when nothing is out of view
  Given every association a competency has is in a course among those currently listed
  When I view the page
  Then the number of associations in view and the competency's total are the same number

Scenario: Neither total moves as I narrow the course list
  Given I am viewing a competency's associations
  When I search, filter by start date, or move between pages of the course list
  Then the stated total number of courses I can access stays the same throughout
  And the stated total number of the competency's associations stays the same throughout
  And only the two "in view" numbers change

Scenario: A search that matches no course
  Given I enter a course title search term that matches none of the courses I can access
  When the course list updates
  Then the page states that no courses are listed, out of the total I can access
  And the associations panel shows no course-level groups
  And the page states that none of the competency's associations are in view, alongside the
    competency's true total

Scenario: A competency with no associations anywhere
  Given a competency has no criteria associations in any course
  When I select it
  Then the associations panel shows a message that this competency has no associations yet
  And the page states that none are in view and that none exist in total

Scenario: Associations exist, but none in the courses currently listed
  Given a competency has criteria associations, and none of them are in the courses currently
    listed
  When I view the associations panel
  Then it shows a message that there are no associations in the courses currently listed, and
    how many the competency has in courses that are not
  And that message is different from the one shown when the competency has no associations
    anywhere
  And nothing on the page tells me this competency has no associations

Scenario: The panel does not look empty while it re-scopes
  Given I am viewing a competency's associations
  When I move to a different page of the course list and the associations for the newly listed
    courses have not arrived yet
  Then the associations panel shows neither of its two no-associations messages
  And the stated counts do not read as though the competency has no associations

Scenario: The associations fail to load for the courses now listed
  Given I move to a different page of the course list
  When the associations for the newly listed courses fail to load
  Then I am shown an error in the associations panel
  And the panel shows neither of its two no-associations messages
  And no association counts are stated that imply the competency has none

Scenario: The course list fails to load
  Given the course list fails to load
  When I view the page
  Then no course counts are stated, rather than a count stating that I can access no courses
  And no association counts are stated, rather than a count stating that the competency has none
  And the associations panel shows no course-level groups

Scenario: No competency selected yet
  Given I have not selected a competency
  When I view the page
  Then no course counts and no association counts are stated

Scenario: Adding an association in a listed course still appears, and both association numbers rise
  Given a course among those currently listed has no associations for this competency yet
  When I select a gradable subsection in that course
  Then a course-level group for that course appears in the associations panel containing the new
    association
  And both the number of associations in view and the competency's total go up by one
  And neither course count changes

Scenario: Subsections already associated are still marked in the course list
  Given a course among those currently listed has a subsection already associated with this
    competency
  When I expand that course in the course list
  Then that subsection is still marked as already associated

Scenario: Switching competencies re-scopes and re-counts
  Given I am viewing one competency's associations for the courses currently listed
  When I select a different competency
  Then the associations panel shows only the second competency's associations in those same
    courses
  And both stated association numbers describe the second competency, not the first
  And neither course count changes, because the course list has not moved

Scenario: The summary line on a small screen
  Given I view the page on a small screen
  Then the summary line stays visible and readable without horizontal scrolling

Scenario: A very long search term is shown truncated in the summary
  Given I enter a course title search term much longer than the summary line can reasonably
    display
  When I view the page
  Then the summary states the search term truncated with an ellipsis, rather than in full
  And the course list is still filtered by the search term I actually entered, in full
```

<img width="1422" height="1031" alt="Image" src="https://github.com/user-attachments/assets/2c2a9210-9587-46ee-8cdb-46ddcdbd43bd" />

## Description

An author reaches an association in a course that is not currently listed by paging, searching, or filtering the course list until that course is listed, not through a separate control on the associations panel. The summary line's two "in view" numbers must always describe the same set of courses: if they described different sets, the sentence would contradict itself. Those counts are the only thing that tells the author anything exists beyond what is on screen, so they have to stay correct in exactly the states where the page itself looks empty.

<details>
<summary>Technical Details</summary>
This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking, not to bind them.

### In short

**Scoping the fetch, not just the display.** Today the associations panel asks the criteria-groups endpoint for everything a competency is associated with across the whole instance, and then narrows what it draws. This ticket changes the request instead: the read hook sends the `course_keys` parameter that \#682 adds, holding exactly the course keys the course list is currently showing. A course that is not listed is never fetched, so it is never rendered, which is the intended behavior. The display-side narrowing that \#672 already does is untouched: a listed course whose name the content-search lookup cannot resolve still draws no course-level group, exactly as it does today.

**Where the currently listed course keys come from.** \#797 adds `notifyCoursesDisplayed(courseKeys)` to `CompetencyAssociationsContext` and wires the course-browse panel to call it whenever its page, search term, or start-date range changes and a new page of courses comes back. This ticket consumes that value and does not re-create it or re-wire the panel. It needs one more distinction out of it than \#797 does, so the provider holds the reported keys as "not reported yet" rather than as an empty list. Three states then exist: no page reported yet, which is what a course list that has not loaded or has failed looks like; a page reported that contains no courses, which is what a search matching nothing looks like; and a page with courses in it. The criteria query stays switched off until a page has been reported at all, which is what stops the panel from briefly rendering an empty result before any courses are known. It does run for a page containing no courses, because that is precisely the case where the author needs to be told the competency's associations still exist somewhere out of view.

**Three of the summary line's four numbers come out of that one request.** The number of courses currently listed is the length of the key list the request was built from. The number of associations in view is `criteria_count` in the response, which \#682 scopes to those same keys. The competency's total is `total_criteria_count`, which \#682 computes ignoring the keys entirely. Because all three describe one resolved request and response, they cannot contradict each other, and nothing needs to be counted or summed on the client.

**The fourth number, the total courses the author can access, needs its own request.** No response the page already fetches carries it: the course-list response's own total describes the courses matching the search and date filters currently applied, which is the number that must not appear in this line. A paginated Django REST Framework list response carries a `count` field holding how many rows match that request across all pages, not how many came back on the page, so one extra request to the same course-list endpoint, with the search and date parameters omitted and the smallest page size the endpoint honors, returns the number wanted with almost no payload. Its query key contains no page, search term, or date, so it is fetched once and reused for the life of the page rather than refetched on every keystroke.

**Both "in view" numbers must always describe the same set of courses, so the whole associations side moves together.** Do not keep the previous page's data on screen while the new page's criteria are fetching. If the panel kept the previous page's tree, the line would pair the new page's course count with the previous page's association count, and the sentence would contradict itself. Instead the criteria query is allowed to re-enter the loading state that \#672's panel already handles when the course keys change, and the line's numbers render only from resolved data for the current keys. That satisfies the requirement that the panel never looks empty while it re-scopes, since a loading state is not an empty state, and it makes the same-set property structural rather than something a future change has to remember to preserve.

**One no-associations message becomes two, distinguished by the competency's total.** The panel currently shows a single message when it has nothing to draw. It now needs to tell apart a competency with no associations at all from a competency whose associations are simply not in the courses currently listed, because the second one, shown with the first one's wording, would lead an author to add content that already exists. The condition that decides between them is the competency's instance-wide total from the response, not anything about what is rendered. The invariant to hold is narrow and worth stating on its own: the "no associations yet" message may render only when the competency's total is zero.

### Implementation specifics

- **API function.** `getCompetencyCriteriaGroups(tagId, courseKeys)` in `src/taxonomy/competency-management/data/api.ts` always sends `course_keys`, joining the array with commas, including when the array is empty. Omitting the parameter means "unfiltered" to \#682 and would fetch the competency's whole instance-wide tree, so verify the request actually carries `course_keys=` for an empty list. Axios keeps an empty-string parameter value and drops only `undefined` and `null`.  
- **Read hook.** `useCompetencyCriteriaGroups(tagId, courseKeys)` in `src/taxonomy/competency-management/data/apiHooks.ts`, gated `enabled: tagId !== undefined && courseKeys !== undefined`. This gate is deliberately different from \#797's `useBlockedCourses`, which gates on `courseKeys.length > 0`: an empty page has no courses to check for a dominance block, but it is a real scope to request criteria for, because the response still carries the competency's true total.  
- **No pagination loop.** Do not copy \#797's `next`\-following behavior. \#682 returns two flat arrays with complete subtrees in one payload, bounded by its 100-key request cap rather than by paging, so there is nothing to follow.  
- **Query key.** Extend the existing factory to `competencyCriteriaGroups(tagId, courseKeys?)`, returning `[...competency(tagId), 'criteriaGroups', ...(courseKeys ? [courseKeys] : [])]`. Including the keys is what makes a page change an independent fetch rather than a cache hit on the previous page's data. Leaving the second argument optional keeps the one-argument form a prefix, so \#672's create-mutation invalidation keeps working unchanged and clears every scoped variant for that competency.  
- **Key order is significant, so do not sort it.** \#682 returns each course's subtree in the order the caller listed its keys. Passing the keys in the order the course list returned them makes the panel's course-level groups appear in the same order as the courses beside them, with no sorting anywhere. For the same reason, `visibleRuleGroups` must stay a filter over the payload's order and must not be re-sorted.  
- **Page size versus the request cap.** \#682 rejects a request naming more than 100 course keys with a 400\. The course list's page size must therefore stay at or under 100\.  
- **Course identifier.** The keys are string course-run keys of the form `course-v1:Org+Course+Run`, the same identifier the course list, the criteria-groups payload's `course_key` field, and the content-search lookup's `contextKey` already use. No translation is needed anywhere in this ticket.  
- **Reported-keys state on the provider.** In `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx`, hold the value `notifyCoursesDisplayed` writes as `string[] | undefined`, initialized to `undefined`. Pass `courseKeys ?? []` to \#797's `useBlockedCourses` so its behavior is unchanged, and pass `courseKeys` itself to `useCompetencyCriteriaGroups`.  
- **The one line of \#797's wiring this ticket may touch.** The course-browse panel must call `notifyCoursesDisplayed([])` when the course-list query succeeds with zero results, and must not call it at all while the query is loading or after it fails. That distinction is what separates "no courses matched your search" from "the course list did not load," and both states have their own acceptance criterion. This does not change the callback's signature and does not reintroduce it.  
- **Context value additions.** Expose the two counts and the listed-course count from the provider, along with the criteria query's loading and error state, so a single component can render the line: the count of listed courses is `courseKeys.length`, and the two association numbers are `criteria_count` and `total_criteria_count` from the response, read verbatim and never recomputed.  
- **Unfiltered course total.** Add `useAccessibleCourseCount()` to `src/taxonomy/competency-management/course-search/data/apiHooks.ts`, calling the existing `getCourseSearchResults` with the same non-filter parameters the list query sends, omitting `search`, `start_date_after`, and `start_date_before`, and requesting the smallest page size the endpoint honors. Use React Query's `select` to expose only `count`. Its key has no variable parts, so it never refetches on a filter change. Export it from `course-search/index.ts` rather than importing past that index, per the MFE's module-boundary rule.  
- **Summary-line component.** `AssociationsSummaryLine.tsx` under `src/taxonomy/competency-management/associations/`, rendered as a child of `CompetencyAssociationsProvider` by the page-level two-panel container so it can read the context, and positioned above both panels per the design. It renders nothing at all when no competency is selected. It renders the course half only once the unfiltered total has resolved and a page of courses has been reported, and the association half only from resolved criteria data for the current keys, so a fetch in flight or an error suppresses that half rather than showing zeros.  
- **The two no-associations messages.** In `criteria-groups/RuleGroupList.tsx`, keep the existing emptiness test on `visibleRuleGroups.length` exactly as it is, and split only what that branch renders: with `total_criteria_count === 0`, the existing message inviting a content selection, unchanged; otherwise a new message stating that none of the competency's associations are in the courses currently listed and naming how many are in courses that are not, computed as `total_criteria_count - criteria_count`. The invariant to test directly is that the existing message never renders while `total_criteria_count` is greater than zero.  
- **Neither message renders outside the loaded branch.** \#672's panel already has four states, and a change of course keys puts the criteria query back into its pending state because the key changed, so the loading branch covers re-scoping with no new code. Add a test pinning this, so that adding a keep-previous-data option later cannot silently reintroduce an empty-looking panel or a stale count.  
- **What this ticket does not touch.** Initial focus stays once per competency and is not re-run when the listed courses change. One consequence is worth knowing rather than fixing: if the first page of courses resolved for a competency contains none of its groups, no automatic focus happens for that competency, and the author focuses a group by clicking it. The already-associated set keeps deriving from the visible course-level groups. The create-association flow is unchanged; both association numbers rise on their own after the existing invalidation refetches the scoped query.  
- **Superseding a statement in \#672.** \#672's Technical Details states as a design principle that "the fetch is unfiltered; only the display is scoped," and that the endpoint returns everything associated with the competency across the instance. That is no longer true once this ticket lands; the display-scoping half of it still is. \#672's text should get a one-line correction pointing here, so a developer reading either ticket is not left choosing between two contradictory statements.  
- **Strings and i18n.** All new strings go through `defineMessages` in `src/taxonomy/competency-management/messages.ts`. Because either half of the sentence can be suppressed on its own, define the course clause and the association clause as separately renderable messages joined by an explicit joiner message, rather than one message for the whole sentence. The course clause needs four variants, for no filters applied, a search term only, a date range only, and both, so that a translator sees each complete sentence and no clause is built by concatenation. Format the dates with the platform's i18n date formatting rather than emitting the raw values.  
- **Responsive.** The line wraps rather than scrolling horizontally on a small screen, so it must not sit in a fixed-width or no-wrap container.  
- **Long search terms.** Neither the search input nor the `search` query param `#669`'s endpoint accepts has any length limit today (confirmed against the actual `openedx-platform` code: `HomePageCoursesViewV2` declares `search` for OpenAPI documentation only, and `get_courses_accessible_to_user()` reads it as a plain, unvalidated string). Fixing that at the source is out of scope here, it would be a \#670/\#669 change. Instead, truncate only the copy of the search term the summary line displays, to 50 characters plus an ellipsis, leaving the actual value sent to the course-list query untouched. This is display-only: the course list itself keeps filtering on the full term the author typed.  
- **Assumption worth knowing.** `criteria_count` includes the always-present instance-wide part of the tree, meaning criteria under a group with no course scope. This panel renders only course-level groups, so if such a group ever held criteria, they would count as "in view" without appearing. No authoring path in this flow creates one, and the counts are used verbatim regardless, because recomputing them from what is rendered would make the two halves of the line describe different sets of courses.  
- **Companion work, out of scope here.** This ticket consumes \#682's `course_keys` parameter and counts and \#797's `notifyCoursesDisplayed` callback rather than building either; see Context for what each provides and the dependency order. Resolving which courses are listed at all, including search, date filtering, and paging, is \#669 and \#670, not this ticket.  
- **Tests.** Selecting a competency issues one criteria request carrying the current page's course keys, in the course list's order, and renders course-level groups only for those courses. Changing page, changing the search term, and changing a date bound each issue a request under a new query key, and no course-level group, bottom-tier group, rule box, or chip from the previously listed courses remains once the new data has resolved. Returning to a previously listed course renders its course-level group again with the same bottom-tier groups, rule boxes, and chips. A listed course with no associations for this competency renders no course-level group, whether or not it is expanded in the course list. A course list that successfully returns zero courses produces a request whose URL carries `course_keys=` with an empty value rather than omitting the parameter. No criteria request fires before a page of courses has been reported, and none fires when no competency is selected. The line names no filter when none is applied, and names exactly the applied filters for a search term alone, a date range alone, and both together. Across a page change, a search, and a date change, the two totals in the rendered line are unchanged while the two in-view numbers change. A search matching nothing renders zero courses listed against the true accessible total, zero associations in view against the competency's true total, and no course-level groups. A competency with no associations anywhere renders the existing invitation message with both association numbers zero; a competency whose associations are all outside the listed courses renders the new message naming the out-of-view count, and the existing message does not render. While the criteria query is fetching for newly listed courses, neither no-associations message renders and no association numbers render. A failed criteria fetch renders the panel's error state, neither message, and no association numbers; a failed course list renders no course numbers and no association numbers, and fires no criteria request. Creating an association in a listed course adds a course-level group for that course and raises both association numbers by one, with neither course number changing. A subsection already associated in a listed course is still marked as such in the course list. Switching competencies leaves both course numbers unchanged and reports both association numbers for the newly selected competency. The unfiltered course-total request fires once and does not fire again across several search-term and page changes. The line wraps rather than overflowing at a small viewport width. A search term longer than the truncation threshold renders truncated with an ellipsis in the summary line while the course list still filters on the term in full.

Files to create and modify **New files**

| File | Purpose |
| :---- | :---- |
| `src/taxonomy/competency-management/associations/AssociationsSummaryLine.tsx` | The summary line: courses listed of the total accessible, the applied filter clauses, and associations in view of the competency's total. |
| `src/taxonomy/competency-management/associations/AssociationsSummaryLine.test.tsx` | Filter-clause variants, totals holding steady across paging and filtering, the zero-match case, suppression while loading and on error, small-screen wrapping. |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/competency-management/data/api.ts` | `getCompetencyCriteriaGroups` always sends `course_keys`, including for an empty list. |
| `src/taxonomy/competency-management/data/apiHooks.ts` | Scope `useCompetencyCriteriaGroups` to the listed course keys; add the optional `courseKeys` segment to the query-key factory. |
| `src/taxonomy/competency-management/data/types.ts` | Add `criteria_count` and `total_criteria_count` to the criteria-groups response type. |
| `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx` | Hold the reported course keys and expose the listed-course count, the two association counts, and the criteria query's loading/error state. |
| `src/taxonomy/competency-management/criteria-groups/RuleGroupList.tsx` | Split the empty-state branch into the two no-associations messages. |
| `src/taxonomy/competency-management/criteria-groups/RuleGroupList.test.tsx` | The two messages and their condition, and that neither renders while fetching or on error. |
| `src/taxonomy/competency-management/course-search/data/apiHooks.ts` | Add `useAccessibleCourseCount()` for the unfiltered course total. |
| `src/taxonomy/competency-management/course-search/data/queryKeys.ts` | Add the parameterless key for the unfiltered course total. |
| `src/taxonomy/competency-management/course-search/index.ts` | Export `useAccessibleCourseCount` from the course-search module boundary. |
| `src/taxonomy/competency-management/course-search/CourseSearchBrowse.tsx` | Call `notifyCoursesDisplayed([])` only on a successful zero-result page, not while loading or after a failure. |
| The page-level two-panel container that mounts `CompetencyAssociationsProvider` | Mount `AssociationsSummaryLine` as a child of the provider, above both panels. |
| `src/taxonomy/competency-management/messages.ts` | The summary line's course clauses, association clause, and joiner, and the second no-associations message. |

- Context The course-count half of the summary line is strictly \#670's data to own, since \#670 builds the course list and holds its paging, search, and date-filter state. \#670 does not currently scope that line, so this ticket builds it. If it has already been built as part of \#670's implementation by the time this ticket starts, the acceptance criteria covering it are already satisfied and no further work on that half is needed. Do not build a second one.  
- \#682 adds the `course_keys` parameter and the two counts this ticket consumes. Omitting the parameter means unfiltered, an empty value means the instance-wide part only, and the counts already exclude removed criteria. It must land before this work starts.  
- \#797 adds `notifyCoursesDisplayed(courseKeys)` to `CompetencyAssociationsContext` and wires the course-browse panel to call it as the page, search, and date filter change. This ticket consumes that callback and does not reintroduce it or re-wire the panel. It must land before this work starts.  
- \#672 builds the associations panel, its context provider, the criteria-groups read hook and query-key factory, the content-search display-name lookup that decides which listed courses render, the already-associated marking, and the panel's four states. This ticket supersedes part of its Technical Details; see the Implementation specifics bullet "Superseding a statement in \#672" above for exactly what changes.  
- \#669 adds the start-date range filter to the accessible-courses listing, and \#670 builds the course-browse panel on top of it, including the page, search, and date state that decides which courses are listed. The Figma linked from \#670 shows the summary line this ticket builds.  
- Prior art in the same feature for a course-key-scoped read hook, including composing the course keys into the query key so a page change is an independent fetch: `useBlockedCourses` in `src/taxonomy/competency-management/data/apiHooks.ts`, added by \#797.

</details>
